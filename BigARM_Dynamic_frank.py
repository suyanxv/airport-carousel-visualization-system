# coding: utf-8

'''
Updated on 20191217
@author: csfrank
'''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

from datetime import datetime, timedelta
from dateutil import parser
import math
from flask import json
from random import randint

import pymongo
import os
import warnings


# Collect to the database.
client = pymongo.MongoClient("mongodb://lwg201902:l144233Comp@158.132.10.150/bigARM")
db = client['bigARM']

carousel_cnt = 12

# Get the average number of bags in history for each flight.
history_load_df = pd.read_csv(r'/var/www/Bigarm/Bigarm/data/BigARM_BagAveHist2.csv')

def load_bag_distribution():
    X = np.float32(np.loadtxt("/var/www/Bigarm/Bigarm/data/survey.txt"))
    N = X.shape[0]
    def func(during, total_load):
        t = np.arange(1 ,during+1).astype(np.float32)
        h = 0.3208829675
        y = np.sum(np.exp(-(X-t[:,None]) ** 2 / (2* h**2)), axis=1) / (N * h * np.sqrt(2 * np.pi))
        out = total_load * y
        return out
    return func

# map 传送带编号到2--13 since 2019-06-20 01:15:00
def carousel_number_mapping(carousel_no, collect_time):
    # No need to map before the given time.
    if(collect_time<pd.Timestamp('2019-06-20 01:15:00')):
        return carousel_no
    # Mapping
    else:
        if (carousel_no is None):
            return None
        elif(int(carousel_no)<5):  # Remove this line after 5 days.
            return carousel_no
        elif(int(carousel_no)<=10):
            return int(int(carousel_no)-3)
        else:
            return int(int(carousel_no)-4)

#对数据库中读取的数据进行预处理，增加load和转换为分钟数
def preprocess_flight_data(df_data, sta_date):
    df_data['ETO_start'] = df_data.allocation_start_time.apply(lambda x:parser.parse(x[:-6]))
    df_data['ETO_end'] = df_data.ETO_start.apply(lambda x: (x+timedelta(hours=1)))

    df_data['STA_origin']  = df_data.allocation_start_time.apply(lambda x:(x[:-6]))
    df_data['DEC_Time']    = df_data.STA_origin.apply(lambda x: (parser.parse(x)+timedelta(hours=0)))
    df_data['ALCT_Start']  = df_data.STA_origin.apply(lambda x: (parser.parse(x)+timedelta(hours=0)))
    df_data['ALCT_End']    = df_data.ETO_end.apply(lambda x: ((x)+timedelta(hours=0)))
    df_data                = df_data.loc[pd.to_datetime(df_data.STA_origin).sort_values().index].reset_index(drop=True)
    time0             = datetime(sta_date.year, sta_date.month, sta_date.day, 0, 0)
    df_data['DEC']    = (df_data.DEC_Time  - time0).apply(lambda x: x.total_seconds()/60)
    df_data['STA']    = (df_data.ALCT_Start - time0).apply(lambda x: x.total_seconds()/60)
    df_data['END']    = (df_data.ALCT_End   - time0).apply(lambda x: x.total_seconds()/60)
    df_data['During'] = df_data.END - df_data.STA
    df_data = df_data[df_data.During>0]  ## ??

    ## Add historical baggage load
    #1217
    if sta_date > pd.Timestamp('2019-09-08'):
        history_load_df = pd.read_csv('/var/www/Bigarm/Bigarm/data/BigARM_BagAveHist3.csv')
        #history_load_df = pd.read_csv('data/BigARM_BagAveHist3.csv')
    df_data = pd.merge(df_data, history_load_df[['Flight_no', 'Monday','Tuesday', 'Wednesday','Thursday','Friday',
                                               'Saturday','Sunday']], on='Flight_no', how='left')
    load = []
    for i,d in df_data.iterrows():
        weekday = d['ETO_start'].weekday()
        load.append(d[['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][weekday]])
    df_data['load'] = load
    df_data.drop(['Monday','Tuesday', 'Wednesday','Thursday','Friday', 'Saturday','Sunday'], axis=1, inplace=True)
    df_data=df_data.fillna({'load':100})  ## Fill none with 100, Improve? Based on flight type
    df_data=df_data.round({'load': 0})

    df_data['allocation_start_time'] = df_data.allocation_start_time.apply(lambda x:parser.parse(x[:-6]))

    #get the latest flights loads from airport
    # ts1=sta_date+timedelta(hours=3)
    # ts2=sta_date+timedelta(hours=24+3)
    #1217
    # if (ts1 > pd.Timestamp('2019-09-24')) and (ts2 < pd.Timestamp('2019-12-17')):
    #     print('Update load of %s from AA' %sta_date.strftime("%Y-%m-%d"))
    #     df_data = update_load_from_AA(ts1, ts2, sta_date, df_data)
    
    #1222
    ts1 = df_data.iloc[0]['ETO_start']
    ts2 = df_data.iloc[-1]['ETO_end']
    #20200122
    # if (ts1 >= pd.Timestamp('2019-09-24')) and (ts2 < pd.Timestamp('2019-10-25')) \
    # or (ts1 >= pd.Timestamp('2019-11-2')) and (ts2 < pd.Timestamp('2019-12-17')):
    #     print('Update load of %s from AA' %sta_date.strftime("%Y-%m-%d"))
    #     df_data = update_load_from_AA(ts1, ts2, df_data)
    #20200122
    if (ts1 >= pd.Timestamp('2019-09-24')) and (ts2 < pd.Timestamp('2019-10-25')) \
    or (ts1 >= pd.Timestamp('2019-11-2')) and (ts2 < pd.Timestamp('2019-12-17')) \
	or (ts1 >= pd.Timestamp('2020-01-16 2:00:00')) and (ts2 < pd.Timestamp('2020-01-18 3:00:00')):
        print('Update load of %s from AA' %sta_date.strftime("%Y-%m-%d"))
        df_data = update_load_from_AA(ts1, ts2, sta_date, df_data)
        
    return df_data

# get the latest flights loads from airport between 2019-09-24 and 2019-10-25
def update_load_from_AA(ts1, ts2, sta_date, simulated):

    isExists_load_from_AA=os.path.exists('/var/www/Bigarm/Bigarm/data/bag_count_AA.csv')
    if (not isExists_load_from_AA):
        print("AA load data is not in database")
        raise RuntimeError('AA load data is not in database')
    else:
        df_load_AA = pd.read_csv('/var/www/Bigarm/Bigarm/data/bag_count_AA.csv')

    df_load_AA['STA']=pd.to_datetime(df_load_AA['STA'])
    df = df_load_AA[df_load_AA.STA>=ts1].copy()
    df = df[df.STA<=ts2].copy()
    df_data = pd.merge(simulated, df, on='Flight_no', how='left')
    df_data = df_data.drop_duplicates(subset=['Flight_no'], keep='last')
    df_data = df_data.reset_index(drop=True)
    del df_data['load_x']
    del df_data['STA_y']
    df_data = df_data.rename(columns={"STA_x": "STA", "load_y": "load"})
    return df_data

# get the latest records for flights by time ts, covering flights 3am today->3am tomorrow
def get_latest_flight_records(sta_date, ts):
    ts1=sta_date+timedelta(hours=3)
    ts2=sta_date+timedelta(hours=24+3)
    df_data = pd.DataFrame(list(db['real_time_flight_records_v3'].find({"$and": [{"collect_time":{"$lte": ts}},
                                                          {"ScheduledDateTime":{"$gt": ts1.strftime("%Y-%m-%dT%H")}},
                                                        {"ScheduledDateTime":{"$lte": ts2.strftime("%Y-%m-%dT%H")}}]})))

    # Carousel mapping
    df_data['Carousel_No']=df_data[['Carousel_No', 'collect_time']].apply(lambda x: carousel_number_mapping(x[0], x[1]), axis=1)

    #Carousel_No是机场自己分配的结果
    df_data = df_data[['PreferredIdentifier', 'PrimaryIdentification', 'ScheduledDateTime','EstimatedDateTime', 'Stand',
                       'GroundAgent', 'IataCode', 'AircraftType', 'ChocksDateTime','Carousel_No','PrimaryObjectIdentifier','CurrentStatus']].copy()
    df_data.columns=['Flight_no', 'Flight_id', 'ScheduledDateTime','EstimatedDateTime', 'Stand', 'GroundAgent',
                     'IataCode', 'AircraftType', 'ChocksDateTime','Carousel_No','PrimaryObjectIdentifier','CurrentStatus']

    ## Remove duplicate records and merge code-share flights
    df_data = df_data.sort_values(by=['Flight_no','ScheduledDateTime'])
    df_data = df_data.drop_duplicates(subset=['Flight_no'], keep='last')
    df_data = df_data[df_data.PrimaryObjectIdentifier=='0'].copy()
    del df_data['PrimaryObjectIdentifier']

    #Remove cancelled flights
    df_data=df_data[df_data.CurrentStatus!='X'].copy()

    # Remove testing flights
    df_data['testing_flights']=df_data.Flight_no.apply(lambda x: x.endswith('X'))
    df_data=df_data[df_data.testing_flights==False].copy()
    del df_data['testing_flights']

    # Replate STA with ETA if the ETA is ready.
    df_data['allocation_start_time']=df_data['ScheduledDateTime']
    df_data.loc[~df_data['EstimatedDateTime'].isna(), 'allocation_start_time'] = df_data[~df_data['EstimatedDateTime'].isna()]['EstimatedDateTime']

    df_data = preprocess_flight_data(df_data, sta_date)

    return df_data

# get the current bigarm allocation plan
#20200107
#def get_current_bigarm_plan(ts,delta):
def get_current_bigarm_plan(sta_date,delta):
    #add warnings
    #isExists_raw=os.path.exists('data/dynamic/' + ts.strftime('%d-%b-%Y') + '-cf.csv')
    #isExists_previous=os.path.exists('data/dynamic/' + (ts-timedelta(minutes=delta)).strftime('%d-%b-%Y-%H-%M-%S') + '-cf.csv')

    # isExists_raw=os.path.exists('/var/www/Bigarm/Bigarm/data/' + ts.strftime('%d-%b-%Y') + '-cf.csv')
    # isExists_previous=os.path.exists('/var/www/Bigarm/Bigarm/data/' + (ts-timedelta(minutes=delta)).strftime('%d-%b-%Y-%H-%M-%S') + '-cf.csv')


    # if (not isExists_raw) and (not isExists_previous):
    #     print("Both raw and previous data exist")
    #     df_current_bigarm_plan = None
    #     return df_current_bigarm_plan

    # elif (isExists_raw) and (not isExists_previous):
    #     print("Only raw data exists")
    #     #df_current_bigarm_plan = pd.read_csv('data/dynamic/' + ts.strftime('%d-%b-%Y') + '-cf.csv')
    #     df_current_bigarm_plan = pd.read_csv('/var/www/Bigarm/Bigarm/data/' + ts.strftime('%d-%b-%Y') + '-cf.csv')
    #     #print('has read raw data')

    # elif isExists_previous:
    #     print("Previous data exists")
    #     #df_current_bigarm_plan = pd.read_csv('data/dynamic/' + (ts-timedelta(minutes=delta)).strftime('%d-%b-%Y-%H-%M-%S') + '-cf.csv')
    #     df_current_bigarm_plan = pd.read_csv('/var/www/Bigarm/Bigarm/data/' + (ts-timedelta(minutes=delta)).strftime('%d-%b-%Y-%H-%M-%S') + '-cf.csv')
    #20200107
    if (os.path.exists('/var/www/Bigarm/Bigarm/data/' + sta_date.strftime('%d-%b-%Y') + '-Current-Plan.csv')):
        df_current_bigarm_plan = pd.read_csv('/var/www/Bigarm/Bigarm/data/' + sta_date.strftime('%d-%b-%Y') + '-Current-Plan.csv')
    else:
        return None

    df_current_bigarm_plan = df_current_bigarm_plan[['FLIGHT_ID_IATA_PREFERRED', 'SCH_START','dyn_belt']]
    df_current_bigarm_plan.columns=['Flight_no', 'EstimatedDateTime', 'Carousel_No_Bigarm']
    df_current_bigarm_plan['allocation_start_time'] = df_current_bigarm_plan.EstimatedDateTime.apply(lambda x: parser.parse(x))
    #no_updation_flag
    df_current_bigarm_plan = df_current_bigarm_plan[['Flight_no', 'EstimatedDateTime', 'Carousel_No_Bigarm',
                                                     'allocation_start_time']]
    df_current_bigarm_plan.columns=['Flight_no', 'EstimatedDateTime_Bigarm', 'Carousel_No_Bigarm',
                                                     'allocation_start_time_Bigarm']
    return df_current_bigarm_plan

def merge_latest_previous_data(sta_date, ts, delta):
    df1=get_latest_flight_records(sta_date, ts)
    
    #20200107
    #df2=get_current_bigarm_plan(ts,delta)
    df2=get_current_bigarm_plan(sta_date,delta)
    #print('get_current_bigarm_plan结束')

    if df1 is None:
            raise RuntimeError('current date %s is not in online database' % ts)
    if df2 is None:
            raise RuntimeError('current date %s is not in local database' % sta_date.strftime('%d-%b-%Y'))

    df=pd.merge(df1, df2, on='Flight_no', how='left')
    #df['update_flag']=df[['allocation_start_time_Bigarm', 'allocation_start_time']].apply(lambda x: 0 if x[0]==x[1] else 1, axis=1)
    df['Carousel_No_Bigarm'] = df['Carousel_No_Bigarm'].fillna(-1)
    df['Carousel_No_Bigarm'] = df['Carousel_No_Bigarm'].astype(np.int32)
    #df['update_flag'] = df['update_flag'].astype(np.int32)
    return df

def belt_load(dynamic_recomm, actions, carousel_cnt):   # 返回分配后的 belt
    dynamic_recomm.empty_belt()
    df_test = dynamic_recomm.df_flights
    df_test['ACTION']=actions
    for time in range(dynamic_recomm.end_time):
        come = df_test[df_test['DEC']==time] # Choose the rows that satisfy: df_test['STA']==time
        if not come.empty:
            for i in range(len(come)):
                ARV = come.iloc[i]
                num = int(ARV['ACTION'])  # the No. of allocation belt
                dynamic_recomm.assign(num, int(ARV.STA), int(ARV.END), ARV.load)
    return dynamic_recomm.belt_arr.copy()


class DynamicRecommendation():
    def __init__(self, date_sta,df_flight_data):
        #print('进入DynamicRecommendation')

        self.df_flights = df_flight_data
        #print('self.df_flights',self.df_flights)

        if self.df_flights is None:
            raise RuntimeError('current date %s is not in database' % date_sta)

        if self.df_flights.empty is True:
            raise RuntimeError('current date or check time %s is not in database' % date_sta)

        #print('分配end_time')
        #print('df_flights.STA.max:', self.df_flights.STA.max())
        #self.end_time = (self.df_flights.STA.max() + 120.0).round().astype(int)
        self.end_time = int(self.df_flights.STA.max() + 120)
        #print('结束分配end_time')

        self.belt_arr = np.zeros([carousel_cnt, self.end_time])

        self.date_crt = date_sta
        self.date_sta = date_sta
        #10.26更改
        #self.date_crt = date_crt
        #self.date_sta = date_sta if date_sta is not None else date_crt
        #self.date_end = date_end if date_end is not None else date_crt

        self.window          = 10
        self.baseline        = -100 # -44
        self.reward_scale    = 10
        self.is_norm         = True
        #self.state_len       = len(self.state(0)[0])
        self.dist_load       = False
        self.fix_during      = True
        self.distributed_load = load_bag_distribution()
        #print('load_bag_distribution分配结束')

    def empty_belt(self):
        self.belt_arr = np.zeros([carousel_cnt, self.end_time])

    def assign(self,num,sta,end,load):
        if math.isnan(load):
            return
        if self.fix_during:
            end = sta + 60 if (sta+60) < self.end_time else self.end_time
        if self.dist_load:
            if(sta<0):
                sta=0
            dist_load = self.distributed_load(end-sta, load)
            self.belt_arr[num, sta:end] += dist_load
        else:
            self.belt_arr[num, sta:end] += load

    def state(self,i):
        #time0 = int(self.df_tmp.iloc[i].DEC)
        time1 = int(self.df_flights.iloc[i].STA)
        belt_window = 60
        end_belttime = (time1 + belt_window) if (time1 + belt_window) <= self.end_time else self.end_time
        belt = self.belt_arr[:, time1:end_belttime].mean(axis=1)
        def center_zero(arr):
            arr -= arr.mean()
            std = arr.std()
            if std != 0:
                arr /= std
            return arr

        if self.is_norm:
            belt     = center_zero(belt)

        return belt.tolist()

    def reward(self,sta,end, force=False):
        if force == False and self.fix_during:
            end = sta + 60 if (sta+60) < self.end_time else self.end_time
        data = self.belt_arr[:, sta:end]
        result = data.std(axis=0).mean()
        reward = - result - self.baseline
        if math.isnan(reward):
            reward = 0
        return reward/self.reward_scale

    # get the rewards of the given actions
    def actions_reward(self, actions):
        total_rewards = []
        self.empty_belt()
        for i in range(len(self.df_flights)):
            a = actions[i]
            s = self.state(i)[0]
            sta = int(self.df_flights.iloc[i].STA)
            end = int(self.df_flights.iloc[i].END)
            load = self.df_flights.iloc[i].load
            # total_rewards.append(dynamic_recomm.greedy_rwd(s, a))
            self.assign(a, sta, end, load)
            total_rewards.append(self.reward(sta,end))
        return total_rewards

    # EK flight allocation assistant, EK flights with close STA(3h) should Not be assigned on the same belt.
    def ek_flight_allocation(self, carousel_sort, sta, carousel_EK_flight_allocation_record):
        new_carousel_sort =  []
        operand = sta - 180
        for element in carousel_sort:
            if carousel_EK_flight_allocation_record[element] < operand:
                new_carousel_sort.append(element)
        return new_carousel_sort

   #CX45
    def cx45_flight_1900_allocation(self, carousel_sort, sta, carousel_CX45_flight_1900_allocation_record):
        new_carousel_sort =  []
        operand = sta - 15
        for element in carousel_sort:
            if carousel_CX45_flight_1900_allocation_record[element] < operand:
                new_carousel_sort.append(element)
        return new_carousel_sort

    # Conduct the carousel allocation and updating.
    def current_act_rd(self, ts):
        #print('进入 Dynamic Recommendation current_act_rd')
        current_acts = []
        total_rewards = 0
        self.empty_belt()

        # Two orange or red planes on the same conveyor belt are more than 90 minutes apart
        carousel_load_orange_red_time_record = np.ones((12,),dtype=np.int) * (-90)

        carousel_load_blue_time_record = np.ones((12,),dtype=np.int) * (-90)

        #EK flights with close STA should Not be assigned on the same belt.
        carousel_EK_flight_allocation_record = np.zeros((12,), dtype= np.int)+(-1)

        #2020_0106
        #All KA flights should not be allocated with EK before 0800h daily.
        carousel_KA_flight_allocation_record = np.zeros((12,), dtype= np.int)+(-1)

        #New:CX 4** and CX 5** should not be assigned on the same belt between 15 mins
        #old:CX 4** and CX 5** should not be assigned on the same belt around 19:00 local time.
        carousel_CX45_flight_1900_allocation_record = np.zeros((12,), dtype= np.int)

        previous_a380_hall='C'
        carousel_NH_flight_allocation_record = np.zeros((12,), dtype= np.int)*(-1)
        flight_count_arr = np.zeros([carousel_cnt, self.end_time])
        hall_a_carousels=list(range(0, 6))
        hall_b_carousels=list(range(6, 12))
        NH_belt_list=[]

        for i in range(len(self.df_flights)):
            print("Loop: ",i)
            belt = self.state(i)
            sta = int(self.df_flights.iloc[i].STA)
            end = int(self.df_flights.iloc[i].END)
            chock_on_time=self.df_flights.iloc[i].ChocksDateTime
            carousel_no = self.df_flights.iloc[i].Carousel_No
            flight_no  = self.df_flights.iloc[i].Flight_no
            stand = self.df_flights.iloc[i].Stand
            aircraft_type = self.df_flights.iloc[i].AircraftType
            #Two orange or red planes on the same conveyor belt are more than 90 minutes apart
            load = self.df_flights.iloc[i].load
            print("flight_no: ",flight_no)
            
            if(self.df_flights.iloc[i]['ETO_start']<=pd.to_datetime(ts+timedelta(minutes=120)) and
                     (self.df_flights.iloc[i]['ETO_start']>pd.to_datetime(ts+timedelta(minutes=30)))):

                print('into 30-120 mins analysis')            

                ################
                carousel=-1
                # Rule 2.2: No belt changes should be made when the flights are properly chocked
                #or ATA+10mins if no check time received..
                #if chock_on_time:
                #    carousel = int(carousel_no) - 2


                #else:
                candidate_carousel_list=range(0, 12)

                #1221
                #Enhancement work rule: No belt NO.7(python NO.2) allocation from 15 Oct to 25 Nov.
                # print("go to close belt")

                # if self.df_flights.iloc[i].ETO_start > pd.Timestamp('2019-10-15 00:00:00') \
                # and self.df_flights.iloc[i].ETO_start < pd.Timestamp('2019-12-13 23:59:59'):
                #     print('Enhancement work')
                #     new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set([2])))
                #     if(len(new_candidate_carousel_list)!=0):
                #         candidate_carousel_list=new_candidate_carousel_list
                #         print(candidate_carousel_list)
                #     else:
                #         print('Violation')

                #1225
                collection_close=db['belt_status_comp1']
                close_record = collection_close.find().clone()
                temp_list=[]
                for j in close_record:
                    if j['start'] == '':
                        print('Invalid Start Time! Please enter a valid time.')
                        collection_close.delete_one({'start': ''})
                        raise RuntimeError('Invalid Start Time! Please enter a valid time.')

                    if j['end'] == '':
                        print('Invalid End Time! Please enter a valid time.')
                        collection_close.delete_one({'end': ''})
                        raise RuntimeError('Invalid End Time! Please enter a valid time.')
                    
                    if self.df_flights.iloc[i].ETO_start >= parser.parse(j['start']) \
                    and self.df_flights.iloc[i].ETO_start <= parser.parse(j['end']):
                        temp_list.append(int(j['belt']))

                new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))  
                if(len(new_candidate_carousel_list)!=0):
                    candidate_carousel_list=new_candidate_carousel_list
                    print(candidate_carousel_list)
                else:         
                    print('No carousel to be allocated! Please Re-check input of closed belts!')
                    raise RuntimeError('No carousel to be allocated! Please Re-check input of closed belts!')
                
                #Regular rule 0.1: Belt 5 to belt 10 are closed from 00:30 to 06:00 everyday
                #1221
                temp_list=[]
                if (sta <= 360 and sta >= 30) or (sta <= 1740 and sta >= 1410):
                    temp_list = list(range(6,12))

                new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set(temp_list)))
                if(len(new_candidate_carousel_list)!=0):
                    candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 0.1", len(candidate_carousel_list))

                # Rule 0.2 BigARM shall allocate maximum 4 flights on the same belts. In busy hours, this rule is not necessary.
                temp_list=[]
                for c in candidate_carousel_list:
                    if max(flight_count_arr[c, sta:sta+60])>=4:
                        temp_list.append(c)
                new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                if(len(new_candidate_carousel_list)!=0):
                    candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 0.2", len(candidate_carousel_list))

                #Rule 1.1: Reclaim carousels from belt 12 to belt 17 should be given priority
                #for the arrival flights parked at parking stands E1 – E4. For belt 5 to belt 10,
                #they would be assigned to E5 to E9 first.
                temp_list=[]
                if stand in ['E1', 'E2', 'E3', 'E4']:
                    temp_list = list(range(6,12))
                elif stand in ['E5', 'E6', 'E7', 'E8', 'E9']:
                    temp_list = list(range(0,6))
                new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set(temp_list)))
                if(len(new_candidate_carousel_list)!=0):
                    candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 1.1", len(candidate_carousel_list))

                # Rule 1.3: A380 should be allocated alternately in hall A and B to avoid congestion
                # at the baggage reclaim hall.
                if aircraft_type=='380':
                    temp_list=[]
                    if previous_a380_hall=='A':
                        new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set(hall_b_carousels)))
                    elif previous_a380_hall=='B':
                        new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set(hall_a_carousels)))
                    #1221
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 1.3", len(candidate_carousel_list))

                # Rule 1.4: No KA & CX flight assigned to Belt 2, 3, 5 & 6 from 06:00-08:00.
                if (flight_no.startswith("KA") or flight_no.startswith("CX")) and (sta <= 480 and sta >= 300):
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set([0,1])))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 1.4", len(candidate_carousel_list))

                # Rule 1.5: Heavy loading flight (red & orange) shall not be assigned on the same
                # arrival belt, the time gap should larger than 90 minutes
                if load >= 240:
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_load_orange_red_time_record[c]+90 > sta):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 1.5", len(candidate_carousel_list))


                # Rule 1.6: Heavy loading flight (red & orange) shall be allocated with lighter loading
                # flights (yellow & green) first, then medium flights (blue).
                if load >= 240:
                    temp_list=[]
                    print(carousel_load_blue_time_record)
                    for c in candidate_carousel_list:
                        if(carousel_load_blue_time_record[c]>=sta):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list

                elif load >=160:#更改
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_load_orange_red_time_record[c]>=sta):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list

                #print("Rule 1.6", len(candidate_carousel_list))

                # Rule 1.7: 15 mins allocation clearance between CX 4XX & CX5XX flights if they are assigned on the same belt
                if flight_no.startswith("CX 4") or flight_no.startswith("CX 5"):
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_CX45_flight_1900_allocation_record[c]+15>=sta):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 1.7", len(candidate_carousel_list))

                # Rule 2.1 All KA flights should not be allocated with EK before 0800h daily.
                if (flight_no.startswith("KA")) and (sta <= 480 or (sta >= 1440 and sta <= 1620 )):
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_EK_flight_allocation_record[c]>= 0):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(temp_list))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                #2020_0106
                elif (flight_no.startswith("EK")) and (sta <= 480 or (sta >= 1440 and sta <= 1620 )):
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_KA_flight_allocation_record[c]>= 0):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(temp_list))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 2.1", len(candidate_carousel_list))

                # Rule 2.2 STA of EK flights within 3 hours should not assigned on the same belt.
                if (flight_no.startswith("EK")):
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_EK_flight_allocation_record[c]+180>=sta):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 2.2", len(candidate_carousel_list))

                # Rule 2.3 NH should be allocated on two belts next to each other and at the same hall.
                if(flight_no.startswith("NH") or flight_no.startswith("NQ")):
                    temp_list=[]
                    if len(NH_belt_list) == 1:
                        temp_list.append(NH_belt_list[0])
                        if NH_belt_list[0]==5 or NH_belt_list[0] == 11:
                            temp_list.append(NH_belt_list[0]-1)

                        elif NH_belt_list[0]==0 or NH_belt_list[0]==6:
                            temp_list.append(NH_belt_list[0]+1) 

                        else:
                            temp_list.append(NH_belt_list[0]-1)
                            temp_list.append(NH_belt_list[0]+1) 

                    elif len(NH_belt_list) == 2:
                        temp_list = NH_belt_list

                    new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set(temp_list)))  
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                    #print("Rule 2.3", len(candidate_carousel_list))
                    #print("Rule 2.3", candidate_carousel_list)


                # Rule 2.4 SQ856 (A380) shall be assigned to Belt 10/12.
                if (flight_no=="SQ 856"):
                    new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set([5,6])))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                #print("Rule 2.4", len(candidate_carousel_list))

                #2020_0210    
                # Rule 0.3 BigARM shall allocate minimum 1 flights on the same belts. 
                temp_list=[]
                for c in candidate_carousel_list:
                    if min(flight_count_arr[c, sta:sta+60])<=1:
                        temp_list.append(c)
                new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set(temp_list)))  
                if(len(new_candidate_carousel_list)!=0):
                    candidate_carousel_list=new_candidate_carousel_list
                print("Rule 0.3", len(candidate_carousel_list))

                
                # Dynamic 2 hours consistency
                #1221:add null candidate
                #print('into consistency')
                if len(candidate_carousel_list) == 0:
                    #print('candidate_carousel_list is 0')
                    raise RuntimeError('No carousel to be allocated! Re-check input of closed belts Please!')

                    
                carousel=candidate_carousel_list[0]
                if self.df_flights.iloc[i]['allocation_start_time_Bigarm']==self.df_flights.iloc[i]['allocation_start_time']:          
                    ##carousel = self.df_flights.iloc[i].Carousel_No_Bigarm - 1
                    #1223
                    #print('allocation_start_time_Bigarm = allocation_start_time')
                    #1220
                    carousel = self.df_flights.iloc[i].Carousel_No

                    #print('carousel',carousel)
                    #1222
                    #if carousel is None:
                    if (carousel is None) or (math.isnan(carousel)):
                        carousel = self.df_flights.iloc[i].Carousel_No_Bigarm - 1
                    else:
                        carousel = int(carousel) - 2
                    #print("No need to allocate")
                    if(carousel not in candidate_carousel_list):
                        #print("上次分配带号不在candidate中")
                        carousel = candidate_carousel_list[0]
                        for c in candidate_carousel_list:
                            if(belt[c]<belt[carousel]):
                                carousel=c 
                else:
                    #print('allocation_start_time_Bigarm != allocation_start_time')      
                    for c in candidate_carousel_list:
                        if(belt[c]<belt[carousel]):
                            carousel=c 
                    #print("Re-allocated carousel:",carousel)
                    
            
            elif(self.df_flights.iloc[i]['ETO_start']>pd.to_datetime(ts+timedelta(minutes=120))):
                #print('into >120 mins analysis')    
                current_acts.append(self.df_flights.iloc[i]['Carousel_No_Bigarm']-1)
                continue
            
            else:
                #1223
                #print('into <30 mins analysis')  
                #1220
                carousel=self.df_flights.iloc[i]['Carousel_No']
                if (carousel is None) or (math.isnan(carousel)):
                        carousel = self.df_flights.iloc[i].Carousel_No_Bigarm - 1
                else:
                    carousel = int(carousel) - 2

            # Update carousel load, etc.
            #print('allocated belt:', carousel)
            current_acts.append(carousel)
            # Update the belt state
            load = self.df_flights.iloc[i].load
            self.assign(carousel, sta, end, load)

            if aircraft_type=='380':
                if carousel in hall_a_carousels:
                    previous_a380_hall='A'
                else:
                    previous_a380_hall='B'

            if(load >= 240):
                carousel_load_orange_red_time_record[carousel]=end
            elif (load>=160):
                carousel_load_blue_time_record[carousel]=end
            if(flight_no.startswith("EK")):
                carousel_EK_flight_allocation_record[carousel]=end
            #2020_0106
            if(flight_no.startswith("KA")):
                carousel_KA_flight_allocation_record[carousel]=end

            if(flight_no.startswith("NH") or flight_no.startswith("NQ")):
                if len(NH_belt_list) == 0:
                    NH_belt_list.append(carousel)
                if len(NH_belt_list) == 1:
                    if NH_belt_list[0] != carousel:
                        NH_belt_list.append(carousel)

            if flight_no.startswith("CX 4") or flight_no.startswith("CX 5"):
                carousel_CX45_flight_1900_allocation_record[carousel]=end
            # Record the numbers of flights on carousels
            flight_count_arr[carousel, sta:sta+60]+=np.ones((60,),dtype=np.int)

        return current_acts, total_rewards

    
def generate_dynamic_adjustment_plan(sta_date, ts, delta, save_csv=True):
    #print('get latest flight records!')

    #20200107
    if ts >= (sta_date + timedelta(hours = 27)):
        #print("Recommendation cross the day!")
        raise RuntimeError('Recommendation cross the day!')
    #20200108
    if ts < (sta_date + timedelta(hours = 3)):
        sta_date = sta_date - timedelta(hours = 24)

    #1220_v2
    #print('into merge_latest_previous_data')
    df_flight_data = merge_latest_previous_data(sta_date, ts, delta)
    #print('df_flight_data compeleted')

    #print('into DynamicRecommendation')
    test_dynamic_recomm = DynamicRecommendation(sta_date, df_flight_data)
    #print('DynamicRecommendation compeleted')
    
    test_dynamic_recomm.dist_load = True
    test_dynamic_recomm.fix_during = True

    ACTION_dyn = test_dynamic_recomm.current_act_rd(ts)[0]

    #concatenate processed and unprocessed data
    out_df = test_dynamic_recomm.df_flights.copy()
    out_df['dyn_belt'] = list(map(lambda x:x+1, ACTION_dyn))

    #updated_flights 
    out_df_updated_flights = out_df[(out_df['ETO_start']<=pd.to_datetime(ts+timedelta(minutes=120))) &
                     (out_df['ETO_start']>pd.to_datetime(ts+timedelta(minutes=30)))].copy()

    #1220
    for index,row in out_df_updated_flights.iterrows():
        if (row['Carousel_No'] is None):
            out_df_updated_flights.at[index,'Carousel_No'] = out_df_updated_flights.at[index,'Carousel_No_Bigarm']
        
        else:
            out_df_updated_flights.at[index,'Carousel_No'] = out_df_updated_flights.at[index,'Carousel_No']-1
          
    out_df_updated_flights = out_df_updated_flights[(out_df_updated_flights['dyn_belt'] != out_df_updated_flights['Carousel_No'])].copy()
    
    #out_df_updated_flights = out_df[(out_df['dyn_belt'] != out_df['Carousel_No_Bigarm'])].copy()

    out_df_updated_flights = out_df_updated_flights[['dyn_belt','load', 'Flight_id', 'Flight_no', 'ETO_start', 'ETO_end', 'IataCode', 'GroundAgent', 'Stand', 'AircraftType']]
    out_df_updated_flights['SCH_TIME_LENGTH'] = "01:00"
    out_df_updated_flights['EST_TIME_LENGTH'] = "01:00"
  
    out_df = out_df.sort_values(by=['allocation_start_time']).reset_index(drop=True)

    out_df = out_df[['dyn_belt','load', 'Flight_id', 'Flight_no', 'ETO_start', 'ETO_end', 'IataCode', 'GroundAgent', 'Stand', 'AircraftType']]
    out_df['SCH_TIME_LENGTH'] = "01:00"
    out_df['EST_TIME_LENGTH'] = "01:00"    

    out_df_updated_flights =  out_df_updated_flights[['dyn_belt', 'load', 'Flight_id', 'Flight_no',
                 'ETO_start', 'ETO_end', 'SCH_TIME_LENGTH', 'ETO_start', 'ETO_end', 'SCH_TIME_LENGTH',
                 'IataCode', 'GroundAgent', 'Stand', 'AircraftType']]

    out_df_updated_flights.columns = ['dyn_belt', 'load', 'FLIGHT_ID', 'FLIGHT_ID_IATA_PREFERRED',
                        'SCH_START', 'SCH_END', 'SCH_TIME_LENGTH', 'EST_START',
                        'EST_END', 'EST_TIME_LENGTH', 'AP_ORIGIN_DEST', 'HA_GROUND_AGENT', 'Stand', 'AircraftType']

    out_df_complete_flights = out_df[['dyn_belt', 'load', 'Flight_id', 'Flight_no',
                         'ETO_start', 'ETO_end', 'SCH_TIME_LENGTH', 'ETO_start', 'ETO_end', 'SCH_TIME_LENGTH',
                         'IataCode', 'GroundAgent', 'Stand', 'AircraftType']]

    out_df_complete_flights.columns = ['dyn_belt', 'load', 'FLIGHT_ID', 'FLIGHT_ID_IATA_PREFERRED',
                            'SCH_START', 'SCH_END', 'SCH_TIME_LENGTH', 'EST_START',
                            'EST_END', 'EST_TIME_LENGTH', 'AP_ORIGIN_DEST', 'HA_GROUND_AGENT', 'Stand', 'AircraftType']

    #if save_csv:
    #path = 'data/dynamic/'
    #path = "data/"
    path = "/var/www/Bigarm/Bigarm/data/"
    isExists=os.path.exists(path)
    if not isExists:
        os.makedirs(path)
    name = datetime.strptime(str(ts),'%Y-%m-%d %H:%M:%S') # assistancy

    #1220_V2
    #out_df_complete_flights['dyn_belt'] = out_df_complete_flights['dyn_belt'].astype(np.int32)
    #out_df_updated_flights['dyn_belt'] = out_df_updated_flights['dyn_belt'].astype(np.int32)
 
    out_df_complete_flights.to_csv(path + name.strftime('%d-%b-%Y-%H-%M-%S') + '-cf.csv', index=False)
    out_df_updated_flights.to_csv(path + name.strftime('%d-%b-%Y-%H-%M-%S') + '-uf.csv', index=False)
    #20200107
    out_df_complete_flights.to_csv(path + sta_date.strftime('%d-%b-%Y') + '-Current-Plan.csv', index=False)
    
    
    return out_df_complete_flights, out_df_updated_flights

