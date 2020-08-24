# coding: utf-8

'''
Created on 20191018
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
import pymongo
import os
import time
import json as js
from BigARM_Dynamic_frank import generate_dynamic_adjustment_plan

# Collect to the database.
client = pymongo.MongoClient("mongodb://201902alex:a145922PolyU@158.132.10.150/bigARM")
db = client['bigARM']
carousel_cnt = 12
#/var/www/Bigarm/Bigarm/data/
# history_load_df = pd.read_csv('data/BigARM_BagAveHist2.csv')
history_load_df = pd.read_csv(r'/var/www/Bigarm/Bigarm/data/BigARM_BagAveHist2.csv')
# history_load_df = pd.read_csv('./data/BigARM_BagAveHist2.csv')
pd.set_option('display.max_columns', None)


# Load the distribution of bag on the carousel.
def load_bag_distribution():

    X = np.float32(np.loadtxt("/var/www/Bigarm/Bigarm/data/survey.txt"))
    #X = np.float32(np.loadtxt("data/survey.txt"))
    N = X.shape[0]
    def func(during, total_load):
        t = np.arange(1 ,during+1).astype(np.float32)
        h = 0.3208829675
        y = np.sum(np.exp(-(X-t[:,None]) ** 2 / (2* h**2)), axis=1) / (N * h * np.sqrt(2 * np.pi))
        out = total_load * y
        return out
    return func

# Mapping the new carousel number to the old one.
def carousel_number_mapping(carousel_no, collect_time):
    # No need to map before the given time.
    if(collect_time<pd.Timestamp('2019-06-20 01:15:00')):
        return carousel_no
    # Mapping
    else:
        #1222
        #if(carousel_no==None or math.isnan(carousel_no)):
        if carousel_no is None:
            return None
        elif(int(carousel_no)<5):  # Remove this line after 5 days.
            return carousel_no
        elif(int(carousel_no)<=10):
            return int(int(carousel_no)-3)
        else:
            return int(int(carousel_no)-4)

def preprocess_flight_data(df_data, sta_date):
    #df_data['Allocation']=df_data['AA_initial_allocation']
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
    df_data = df_data[df_data.During>0]

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
    # print("#", len(df_data[df_data.load.isnull()]))
    df_data=df_data.fillna({'load':100})  ## Fill none with 100, Improve? Based on flight type
    df_data=df_data.round({'load': 0})

    #1221
    #get the latest flights loads from airport
    # ts1=sta_date+timedelta(hours=3)
    # ts2=sta_date+timedelta(hours=24+3)
    #1217
    # if (ts1 > pd.Timestamp('2019-09-24')) and (ts2 < pd.Timestamp('2019-12-17')):
    #     print('Update load of %s from AA' %sta_date.strftime("%Y-%m-%d"))
    #     df_data = update_load_from_AA(ts1, ts2, sta_date, df_data)
    #1222
    #20200122
    ts1 = df_data.iloc[0]['ETO_start']
    ts2 = df_data.iloc[-1]['ETO_end']
    print('ts1:',ts1)

    if (ts1 >= pd.Timestamp('2019-09-24')) and (ts2 < pd.Timestamp('2019-10-25')) \
    or (ts1 >= pd.Timestamp('2019-11-2')) and (ts2 < pd.Timestamp('2019-12-17')) \
	or (ts1 >= pd.Timestamp('2020-01-16')) and (ts2 < pd.Timestamp('2020-01-18 3:00:00')):
        #print('Update load of %s from AA' %sta_date.strftime("%Y-%m-%d"))
        df_data = update_load_from_AA(ts1, ts2, df_data)

    # else if (ts1 >= pd.Timestamp('2020-01-16')) and (ts2 < pd.Timestamp('2020-01-18')):
        # df_data = update_load_from_AA(ts1, ts2, df_data)

    return df_data

# get the latest flights loads from airport between 2019-09-24 and 2019-10-25
def update_load_from_AA(ts1, ts2, simulated):

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
def get_latest_flight_records(sta_date):

    ts1=sta_date+timedelta(hours=3)
    ts2=sta_date+timedelta(hours=24+3)
    #df_data = pd.DataFrame(list(db['real_time_flight_records_v3'].find({"$and": [{"collect_time":{"$lte": ts}},
    #                                                      {"ScheduledDateTime":{"$regex": sta_date.strftime("%Y-%m-%d")}}]})))
    df_data = pd.DataFrame(list(db['real_time_flight_records_v3'].find({"$and": [{"collect_time":{"$lte": sta_date}},
                                                          {"ScheduledDateTime":{"$gt": ts1.strftime("%Y-%m-%dT%H")}},
                                                        {"ScheduledDateTime":{"$lte": ts2.strftime("%Y-%m-%dT%H")}}]})))

    #df_data = pd.DataFrame(list(db['real_time_flight_records_v3'].find({"ScheduledDateTime":{"$regex": sta_date.strftime("%Y-%m-%d")}})))

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

class Initial_Plan():
    def __init__(self, date_crt, date_sta=None, date_end=None):
        #self.df_flights = get_flights_for_allocation(sta_date=date_crt)
        self.df_flights= get_latest_flight_records(sta_date=date_crt)
        if self.df_flights is None:
            raise RuntimeError('current date %s is not in database' % date_crt)

        self.end_time = int(self.df_flights.STA.max() + 120)
        self.belt_arr = np.zeros([carousel_cnt, self.end_time])

        self.date_crt = date_crt
        self.date_sta = date_sta if date_sta is not None else date_crt
        self.date_end = date_end if date_end is not None else date_crt

        self.window          = 10
        self.baseline        = -100 # -44
        self.reward_scale    = 10
        self.is_norm         = True
        self.dist_load       = False
        self.fix_during      = True
        self.distributed_load = load_bag_distribution()

    def rdm_dataset(self):
        ran_t         = np.random.randint(self.date_sta.timestamp(), self.date_end.timestamp())
        new_date      = datetime.fromtimestamp(ran_t)
        self.date_crt = new_date
        self.df_flights   = get_flights_for_allocation(new_date)
        if self.df_flights is not None:
            self.end_time = int(self.df_flights.END.max())
            self.belt_arr = np.zeros([carousel_cnt, self.end_time])
        else:
            self.rdm_dataset()

    def next_dataset(self):
        self.date_crt += timedelta(days=1)
        if self.date_crt > self.date_end:
            self.date_crt = self.date_sta
        self.df_flights   = get_flights_for_allocation(self.date_crt)
        if self.df_flights is not None:
            self.end_time = int(self.df_flights.END.max())
            self.belt_arr = np.zeros([carousel_cnt, self.end_time])
        else:
            self.next_dataset()

    def empty_belt(self):
        self.belt_arr = np.zeros([carousel_cnt, self.end_time])

    def assign(self,num,sta,end,load):
        print('Entry assign')
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
            print('normal load is assigned')
            self.belt_arr[num, sta:end] += load

    def state(self,i):
        #time0 = int(self.df_flights.iloc[i].DEC)
        #print('进入state')
        time1 = int(self.df_flights.iloc[i].STA)
        belt_window = 60#更改
        end_belttime = (time1 + belt_window) if (time1 + belt_window) <= self.end_time else self.end_time
        belt = self.belt_arr[:, time1:end_belttime].mean(axis=1)

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
            # total_rewards.append(game.greedy_rwd(s, a))
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


    #返回的是满足大于15min间隔的传送带,不用<= operand
    def cx45_flight_1900_allocation(self, carousel_sort, sta, carousel_CX45_flight_1900_allocation_record):
        new_carousel_sort =  []
        operand = sta - 15
        for element in carousel_sort:
            if carousel_CX45_flight_1900_allocation_record[element] < operand:
                new_carousel_sort.append(element)
        return new_carousel_sort


    #use the latest parameters to generate a set of actions and total rewards
    def current_act_rd(self):
        current_acts = []
        #step_greedy_acts = []
        total_rewards = 0
        self.empty_belt()

        path = "/var/www/Bigarm/Bigarm/data/"
        file = path + (self.date_crt - timedelta(days=7)).strftime('%d-%b-%Y') + '.csv'
        file_exist_flag = os.path.exists(file)
        if file_exist_flag:
            df_previous_plan=pd.read_csv(file)
            print ("Previous plan exists.")
        else:
            df_previous_plan= None
            print ("Previous plan does not exist.")

        # Two orange or red planes on the same conveyor belt are more than 90 minutes apart
        carousel_load_orange_red_time_record = np.ones((12,),dtype=np.int) * (-90)

        carousel_load_blue_time_record = np.ones((12,),dtype=np.int) * (-90)

        #EK flights with close STA should Not be assigned on the same belt.
        carousel_EK_flight_allocation_record = np.zeros((12,), dtype= np.int)+(-1)

        #2020_01016
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
            print('---------------------------')
            print(i, ": ",self.df_flights.iloc[i].Flight_no)
            belt = self.state(i)
            #print("current load:", belt)
            sta = int(self.df_flights.iloc[i].STA)
            end = int(self.df_flights.iloc[i].END)

            chock_on_time=self.df_flights.iloc[i].ChocksDateTime
            carousel_no = self.df_flights.iloc[i].Carousel_No

            flight_no  = self.df_flights.iloc[i].Flight_no
            stand = self.df_flights.iloc[i].Stand
            aircraft_type = self.df_flights.iloc[i].AircraftType
            #Two orange or red planes on the same conveyor belt are more than 90 minutes apart
            load = self.df_flights.iloc[i].load
            #print(load)

            # solve inconsistency problem by baseline plan of previous week
            if file_exist_flag:
                df_previous_allocation = df_previous_plan[df_previous_plan.FLIGHT_ID == self.df_flights.iloc[i].Flight_id]
            else:
                # null dataframe
                df_previous_allocation = pd.DataFrame(columns=['A', 'B', 'C', 'D'])
                #df_previous_allocation.empty = True

            carousel=-1
            # Rule 2.2: No belt changes should be made when the flights are properly chocked
            #or ATA+10mins if no check time received..
            if chock_on_time:
                carousel = int(carousel_no) - 2
            else:
                candidate_carousel_list=range(0, 12)

                #1221
                #Enhancement work rule: No belt NO.7(python NO.2) allocation from 15 Oct to 25 Nov.
                # if self.df_flights.iloc[i].ETO_start > pd.Timestamp('2019-10-15 00:00:00') \
                # and self.df_flights.iloc[i].ETO_start < pd.Timestamp('2019-12-13 23:59:59'):
                #     print('Enhancement work')
                #     new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set([2])))
                #     if(len(new_candidate_carousel_list)!=0):
                #         candidate_carousel_list=new_candidate_carousel_list
                #         print(candidate_carousel_list)
                #     else:
                #         print('Violation')
                print("进入close belt")
                collection_close=db['belt_status']
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

                print("Rule Maintenance", len(candidate_carousel_list))
                print("satrt time",self.df_flights.iloc[i].ETO_start)
                
                print(candidate_carousel_list)
                print("完成close belt")

                #Regular rule 0.1: Belt 5 to belt 10 are close from 00:30 to 06:00 everyday
                #1221
                temp_list=[]
                if (sta <= 360 and sta >= 30) or (sta <= 1740 and sta >= 1410):
                    temp_list = list(range(6,12))

                new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set(temp_list)))
                if(len(new_candidate_carousel_list)!=0):
                    candidate_carousel_list=new_candidate_carousel_list

                print("Rule 0.1", len(candidate_carousel_list))

                # Rule 0.2 BigARM shall allocate maximum 4 flights on the same belts. In busy hours, this rule is not necessary.
                temp_list=[]
                for c in candidate_carousel_list:
                    if max(flight_count_arr[c, sta:sta+60])>=4:
                        temp_list.append(c)

                new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                if(len(new_candidate_carousel_list)!=0):
                    candidate_carousel_list=new_candidate_carousel_list
                print("Rule 0.2", len(candidate_carousel_list))

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
                print("Rule 1.1", len(candidate_carousel_list))

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
                print("Rule 1.3", len(candidate_carousel_list))

                # Rule 1.4: No KA & CX flight assigned to Belt 2, 3, 5 & 6 from 06:00-08:00.
                if (flight_no.startswith("KA") or flight_no.startswith("CX")) and (sta <= 480 and sta >= 300):
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set([0,1])))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                print("Rule 1.4", len(candidate_carousel_list))

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
                print("Rule 1.5", len(candidate_carousel_list))


                # Rule 1.6: Heavy loading flight (red & orange) shall be allocated with lighter loading
                # flights (yellow & green) first, then medium flights (blue).
                if load >= 240:
                    temp_list=[]
                    print(carousel_load_blue_time_record)
                    for c in candidate_carousel_list:
                        if(carousel_load_blue_time_record[c] >= sta):
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

                print("Rule 1.6", len(candidate_carousel_list))

                # Rule 1.7: 15 mins allocation clearance between CX 4XX & CX5XX flights if they are assigned on the same belt
                if flight_no.startswith("CX 4") or flight_no.startswith("CX 5"):
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_CX45_flight_1900_allocation_record[c]+15>=sta):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                print("Rule 1.7", len(candidate_carousel_list))

                # Rule 2.1 All KA flights should not be allocated with EK before 0800h daily.
                if (flight_no.startswith("KA")) and (sta <= 480 or (sta >= 1440 and sta <= 1620 )):
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_EK_flight_allocation_record[c] >= 0):
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

                print("Rule 2.1", len(candidate_carousel_list))

                # Rule 2.2 STA of EK flights within 3 hours should not assigned on the same belt.
                if (flight_no.startswith("EK")):
                    temp_list=[]
                    for c in candidate_carousel_list:
                        if(carousel_EK_flight_allocation_record[c]+180>=sta):
                            temp_list.append(c)
                    new_candidate_carousel_list=list(set(candidate_carousel_list).difference(set(temp_list)))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                print("Rule 2.2", len(candidate_carousel_list))

                # Rule 2.3 NH should be allocated on two belts next to each other and at the same hall.
                if (flight_no.startswith("NH") or flight_no.startswith("NQ")):
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
                print("Rule 2.3", len(candidate_carousel_list))
                print("Rule 2.3", candidate_carousel_list)

                # Rule 2.4 SQ856 (A380) shall be assigned to Belt 10/12.
                if (flight_no=="SQ 856"):
                    new_candidate_carousel_list=list(set(candidate_carousel_list).intersection(set([5,6])))
                    if(len(new_candidate_carousel_list)!=0):
                        candidate_carousel_list=new_candidate_carousel_list
                print("Rule 2.4", len(candidate_carousel_list))

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

                
                print('candidate_carousel_list',candidate_carousel_list)
                # Allocation while considering consistency
                #1221:add null candidate
                if len(candidate_carousel_list) == 0:
                    raise RuntimeError('No carousel to be allocated! Re-check input of closed belts Please!')
                        
                carousel=candidate_carousel_list[0]
                if(file_exist_flag) and (not df_previous_allocation.empty):
                    carousel = df_previous_allocation.dyn_belt.real[0] - 1
                    if(carousel not in candidate_carousel_list):
                        carousel = candidate_carousel_list[0]
                        for c in candidate_carousel_list:
                            if(belt[c]<belt[carousel]):
                                carousel=c
                else:
                    for c in candidate_carousel_list:
                        if(belt[c]<belt[carousel]):
                            carousel=c

            # Update carousel load, carousel flags, etc.
            print('allocated belt:', carousel)
            current_acts.append(carousel)
            # Update the belt state
            load = self.df_flights.iloc[i].load
            self.assign(carousel, sta, end, load)
            #print("new load:", belt)

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
            #2020_01016
            if(flight_no.startswith("KA")):
                carousel_KA_flight_allocation_record[carousel]=end

            if (flight_no.startswith("NH") or flight_no.startswith("NQ")):
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

def adjust_carousel_tmp(carousel_no, SCH_START):
    # No need to revise.
    if((SCH_START>=pd.Timestamp('2019-06-22 06:00:00')) or (SCH_START<=pd.Timestamp('2019-06-22 00:30:00'))):
        return carousel_no
    # revise
    else:
        return carousel_no-6


def generate_initial_plan(date_sta,plot_result=False, save_result_plot=False, save_csv=False):
    plot_result = True if save_result_plot else plot_result

    initial_plan = Initial_Plan(date_sta, date_sta, (date_sta+timedelta(days=1)))
    initial_plan.dist_load = True
    initial_plan.fix_during = True

    ACTION_dyn = initial_plan.current_act_rd()[0]
    print('ACTION_dyn:')
    print(ACTION_dyn)
    print('-------------')

    out_df = initial_plan.df_flights.copy()
    #out_df = out_df[['load', 'Flight_id', 'Flight_no', 'ETO_start', 'ETO_end', 'IataCode', 'GroundAgent']]
    out_df['dyn_belt'] = list(map(lambda x:x+1, ACTION_dyn))

    out_df = out_df[['load', 'Flight_id', 'Flight_no', 'ETO_start', 'ETO_end', 'IataCode', 'GroundAgent', 'dyn_belt']]
    #out_df['dyn_belt'] = list(map(lambda x:x+1, ACTION_dyn))

    #out_df['origin_belt'] = list(map(lambda x:x+1, ACTION_origin))
    out_df['SCH_TIME_LENGTH'] = "01:00"
    out_df['EST_TIME_LENGTH'] = "01:00"
    out_df = out_df[['dyn_belt', 'load', 'Flight_id', 'Flight_no',
                         'ETO_start', 'ETO_end', 'SCH_TIME_LENGTH', 'ETO_start', 'ETO_end', 'SCH_TIME_LENGTH',
                         'IataCode', 'GroundAgent']]
    out_df.columns = ['dyn_belt', 'load', 'FLIGHT_ID', 'FLIGHT_ID_IATA_PREFERRED',
                            'SCH_START', 'SCH_END', 'SCH_TIME_LENGTH', 'EST_START',
                            'EST_END', 'EST_TIME_LENGTH', 'AP_ORIGIN_DEST', 'HA_GROUND_AGENT']

    dt=datetime.now()
    out_df['date_time']=dt.strftime('%Y-%m-%d %H:%M:%S')

    if save_csv:
        print(len(out_df))

        out_df.to_csv("/var/www/Bigarm/Bigarm/data/"+initial_plan.date_crt.strftime('%d-%b-%Y') + '.csv', index=False)
        out_df.to_csv("/var/www/Bigarm/Bigarm/data/"+initial_plan.date_crt.strftime('%d-%b-%Y') + '-cf.csv', index=False)
        #20200107
        out_df.to_csv("/var/www/Bigarm/Bigarm/data/" + initial_plan.date_crt.strftime('%d-%b-%Y') + '-Current-Plan.csv', index=False)
    
        #out_df.to_csv("data/"+initial_plan.date_crt.strftime('%d-%b-%Y') + '.csv', index=False)
        #out_df.to_csv("data/"+initial_plan.date_crt.strftime('%d-%b-%Y') + '-cf.csv', index=False)

#     collection=db['carousel_allocation_records']
#     to_dict=out_df.to_dict(orient='records')
#     #clean the mongoDB
#     #collection.delete_many({})
#     for x in to_dict:
#         collection.insert_one(x)
#     print('save')

    return out_df


def belt_load(game, actions, carousel_cnt):   # 返回分配后的 belt
    game.empty_belt()
    df_test = game.df_tmp
    df_test['ACTION']=actions
    for time in range(game.end_time):
        come = df_test[df_test['DEC']==time] # Choose the rows that satisfy: df_test['STA']==time
        if not come.empty:
            for i in range(len(come)):
                ARV = come.iloc[i]
                num = int(ARV['ACTION'])  # the No. of allocation belt
                game.assign(num, int(ARV.STA), int(ARV.END), ARV.load)
    return game.belt_arr.copy()

def plot_belt(belt, carousel_cnt, title=None):
    plt.figure()
    for i in range(carousel_cnt):
        plt.plot(belt[i], label='belt %d' % (i+1))
    plt.legend(loc='upper left')
    plt.xlabel('Time (mins)')
    plt.ylabel('number of baggages ')
    if title:
        plt.title(title)
    plt.ylim([0, 700])
    plt.show()

def twoDplot(belt, title, pdf_file=None):
    fig = plt.figure(figsize=(17,3))
    y = belt
    df = pd.DataFrame(y, columns=[x/60 for x in range(y.shape[1])], index=[x+1 for x in range(y.shape[0])])
    plt.xlim([0,24])
    sns.heatmap(df, cmap="Reds", xticklabels=120)
#     plt.ylim([0,25])
    plt.title(title)
    if pdf_file is not None:
        pdf_file.savefig(fig)
    plt.show()

def load_std(belt):
    windows=30
    STD3=[]
    log=[]
    for time in range(len(belt[0])):
        lf=time
        rt=lf+windows
        STD3.append(belt[:,lf:rt].std(axis=0).mean())
    return STD3

def plot_std(std_man, std_dyn, title='', pdf_file=None):
    #std_man=[0] * len(std_man)
    fig = plt.figure(figsize=(16,9))
    plt.title(title)
    labels = []
    if std_man is not None:
        plt.plot(std_man,'b')
        labels.append('AA initial plan')
    if std_dyn is not None:
        plt.plot(std_dyn,'r')
        labels.append('BigARM initial plan')
    plt.xlabel('Time Minites')
    plt.ylabel('STD on intial plan')
    plt.xlim(0, 1600)
    plt.legend(labels=labels)
    if pdf_file is not None:
        pdf_file.savefig(fig)
    plt.show()

# For Jun 22 and 23 revision.
def adjust_carousel_tmp(carousel_no, SCH_START):
    # No need to revise.
    if((SCH_START>=pd.Timestamp('2019-06-22 06:00:00')) or (SCH_START<=pd.Timestamp('2019-06-22 00:30:00'))):
        return carousel_no
    # revise
    else:
        return carousel_no-6

# For Initial Plan generated from DB data
# def get_init_plan_for_plot(date_sta, save_csv=True):
    # print('进入init_plan')
    # initial_plan = Initial_Plan(date_sta, date_sta, (date_sta+timedelta(days=1)))
    # initial_plan.dist_load = True
    # initial_plan.fix_during = True
    # print('完成init_plan')

    # ACTION_dyn = initial_plan.current_act_rd()[0]

    # out_df = initial_plan.df_flights.copy()

    # # out_df = out_df[['load', 'Flight_id', 'Flight_no', 'ETO_start', 'ETO_end', 'IataCode', 'GroundAgent']]
    # out_df['dyn_belt'] = list(map(lambda x:x+1, ACTION_dyn))


    # if date_sta >= datetime(2019,6,27) and date_sta <= datetime(2019,6,30):
        # # out_df_1 = out_df[(out_df.STA>=0) & (out_df.STA < 360) & (out_df.ChocksDateTime.isnull())]
        # out_df_1 = out_df[(out_df.STA < 360) & (out_df.ChocksDateTime.isnull())]
        # out_df_1['dyn_belt'] = out_df_1.dyn_belt.apply(lambda x: x if x<=6 else x-6)
        # out_df_1['flag'] = 1
        # out_df_1 = out_df_1[['load', 'Flight_id', 'Flight_no', 'ETO_start', 'ETO_end', 'IataCode', 'GroundAgent', 'dyn_belt', 'flag', 'Stand', 'AircraftType']]

        # out_df = out_df[['load', 'Flight_id', 'Flight_no', 'ETO_start', 'ETO_end', 'IataCode', 'GroundAgent', 'dyn_belt', 'Stand', 'AircraftType']]
        # out_df['flag'] = 0

        # df_flight_data = pd.concat([out_df_1, out_df], sort = True)
        # df_flight_data = df_flight_data.sort_values(by=['Flight_id', 'flag'])
        # df_flight_data = df_flight_data.drop_duplicates(subset= ['Flight_id'], keep='last', inplace=False)
        # df_flight_data = df_flight_data.sort_values(by=['ETO_start', 'Flight_id'])
        # out_df = df_flight_data.copy()
        # del out_df['flag']
    # else:
        # out_df = out_df[['load', 'Flight_id', 'Flight_no', 'ETO_start', 'ETO_end', 'IataCode', 'GroundAgent', 'dyn_belt', 'Stand', 'AircraftType']]
        # # out_df['dyn_belt'] = list(map(lambda x:x+1, ACTION_dyn))

    # # out_df['origin_belt'] = list(map(lambda x:x+1, ACTION_origin))
    # out_df['SCH_TIME_LENGTH'] = "01:00"
    # out_df['EST_TIME_LENGTH'] = "01:00"
    # out_df = out_df[['dyn_belt', 'load', 'Flight_id', 'Flight_no',
                         # 'ETO_start', 'ETO_end', 'SCH_TIME_LENGTH', 'ETO_start', 'ETO_end', 'SCH_TIME_LENGTH',
                         # 'IataCode', 'GroundAgent', 'Stand', 'AircraftType']]
    # out_df.columns = ['dyn_belt', 'load', 'FLIGHT_ID', 'FLIGHT_ID_IATA_PREFERRED',
                            # 'SCH_START', 'SCH_END', 'SCH_TIME_LENGTH', 'EST_START',
                            # 'EST_END', 'EST_TIME_LENGTH', 'AP_ORIGIN_DEST', 'HA_GROUND_AGENT', 'Stand', 'AircraftType']

    # dt=datetime.now()
    # out_df['date_time']=dt.strftime('%Y-%m-%d %H:%M:%S')

    # print('initial plan完成')
    # if save_csv:
        # print(len(out_df))

        # out_df.to_csv("/var/www/Bigarm/Bigarm/data/"+initial_plan.date_crt.strftime('%d-%b-%Y') + '.csv', index=False)
        # out_df.to_csv("/var/www/Bigarm/Bigarm/data/"+initial_plan.date_crt.strftime('%d-%b-%Y') + '-cf.csv', index=False)
        # # 20200107
        # out_df.to_csv("/var/www/Bigarm/Bigarm/data/" + initial_plan.date_crt.strftime('%d-%b-%Y') + '-Current-Plan.csv', index=False)
    
        # # out_df.to_csv("data/"+initial_plan.date_crt.strftime('%d-%b-%Y') + '.csv', index=False)
        # # out_df.to_csv("data/"+initial_plan.date_crt.strftime('%d-%b-%Y') + '-cf.csv', index=False)

    # # save in mongoDB
    # collection=db['carousel_allocation_records']
    # to_dict=out_df.to_dict(orient='records')
    # # clean the mongoDB
    # # collection.delete_many({})
    # for x in to_dict:
        # collection.insert_one(x)
    # print('saved')

    # try:

        # db_data = out_df.copy()
        # details = []
        # for i in range(len(db_data)):
            # flight = db_data.iloc[i]
            # # print(flight)
            # f_json = {
                # # "AircraftType": flight['AircraftType'],
                # # "Stand": flight['Stand'],
                # "Flight_no": flight['FLIGHT_ID_IATA_PREFERRED'],
                # "STA":       flight['SCH_START'],
                # "Load":      str(flight['load']),
                # "ETO_start": flight['SCH_START'],
                # "ETO_end":   flight['SCH_END'],
                # "ID":        flight['FLIGHT_ID'],
                # "Allocation": str(flight['dyn_belt'])
                # # ,"First_carousel_no": str(flight['origin_belt'])
                # # ,"test": "here"
            # }
            # details.append(f_json)
        # return_json = {
            # 'Flight_count': len(db_data),
            # 'Details':      details,
            # 'Error':        False,
        # }
    # except Exception as e:
        # return_json = {
            # 'Error': True,
            # 'Msg':   repr(e)
        # }
    # return json.dumps(return_json)
# End db csv part 
#print(get_init_plan_for_plot(datetime(2020, 2, 3)))

#For Display Initial Plan from server csv
def get_init_plan_for_plot(df_initial_plan):
    try:
        #date_str = request.form['date']
        #initialize = False if request.form['initialize'] == 'false' else True
        #date = parser.parse(date_str)
        db_data = df_initial_plan.copy()
        #print(len(db_data))

        details = []
        for i in range(len(db_data)):
            flight = db_data.iloc[i]
            #print(flight)
            f_json = {
                "Flight_no": flight['FLIGHT_ID_IATA_PREFERRED'],
                "STA":       flight['SCH_START'],
                "Load":      str(flight['load']),
                "ETO_start": flight['SCH_START'],
                "ETO_end":   flight['SCH_END'],
                "ID":        flight['FLIGHT_ID'],
                "Allocation": str(flight['dyn_belt']),
#                "First_carousel_no": str(flight['origin_belt'])
            }
            details.append(f_json)
        return_json = {
            'Flight_count': len(db_data),
            'Details':      details,
            'Error':        False,
        }
    except Exception as e:
        return_json = {
            'Error': True,
            'Msg':   repr(e)
        }
    return json.dumps(return_json)


#usage
#interaction_string = get_init_plan_for_plot((datetime(2019,6,28)))
#print(interaction_string)

##Test
#begin_time=datetime.now()
##df_initial_plan = generate_initial_plan(datetime(2019,8,24), plot_result=False, save_result_plot=False, save_csv=True)
#interaction_string = get_init_plan_for_plot((datetime(2019,7,12)))
#interaction_string.to_csv("data_test/"+datetime(2019,7,12).strftime('%d-%b-%Y') + '-test-dyn_belt.csv', index=False)
#print (datetime.now()-begin_time)
#

'''
demo
def main():    
    begin = datetime(2019,9,29)    
    end = datetime(2019,9,29)    
    for i in range((end - begin).days+1):        
        day = begin + timedelta(days=i)  
        begin_time=datetime.now()
        print (str(day))
        df_initial_plan = get_init_plan_for_plot(day)
        #df_initial_plan = generate_initial_plan(day, plot_result=False, save_result_plot=False, save_csv=True)
        print('flights: ', len(df_initial_plan))
        print(datetime.now()-begin_time)
        print ("-------------------------------")

main()



hostname= "bigarm-comp1.comp.polyu.edu.hk" 
username= "svradmin"
#password= "admin154122Comp" 
password= "ZufWaj38" 
port= 22

def upload(local_dir,remote_dir, file_name):  
    try:  
        t=paramiko.Transport((hostname,port))  
        t.connect(username=username,password=password)  
        sftp=paramiko.SFTPClient.from_transport(t)  
        #print('upload file start %s ' % datetime.now()) 
        fileFlag = 0 
        for root,dirs,files in os.walk(local_dir):  
            #print('[%s][%s][%s]' % (root,dirs,files))  
            for filespath in files:
                if filespath == file_name:
                    fileFlag = 1  
                    local_file = os.path.join(root,filespath)  
                    #print(11,'[%s][%s][%s][%s]' % (root,filespath,local_file,local_dir))  
                    a = local_file.replace(local_dir,'').replace('\\','/').lstrip('/')  
                    #print('01',a,'[%s]' % remote_dir)  
                    remote_file = os.path.join(remote_dir,a)  
                    #print(22,remote_file)  
                    try:  
                        sftp.put(local_file,remote_file)  
                    except Exception as e:  
                        sftp.mkdir(os.path.split(remote_file)[0])  
                        sftp.put(local_file,remote_file)  
                        print("66 upload %s to remote %s" % (local_file,remote_file))
                    
            for name in dirs:  
                local_path = os.path.join(root,name)  
                print(0,local_path,local_dir)  
                a = local_path.replace(local_dir,'').replace('\\','')  
                print(1,a)  
                print(1,remote_dir)  
                remote_path = os.path.join(remote_dir,a)  
                print(33,remote_path)  
                
                try:  
                    sftp.mkdir(remote_path)  
                    print(44,"mkdir path %s" % remote_path)  
                except Exception as e:  
                    print(55,e) 
        if fileFlag: 
            print('77,upload file success %s ' % datetime.now())  
            t.close() 
        else:
            print("99,the current dir does't have the specific file") 
            t.close()
    except Exception as e:  
        print(88,e)  
        
schedule = sched.scheduler(time.time, time.sleep)

start_time = 0
end_time = 0

class Timer(object):
    # 被周期性调度触发的函数
    def execute_command(self, inc):
        start_time = datetime.now()
        date_crt = datetime.now()
        df_initial_plan = generate_initial_plan(datetime(date_crt.year,date_crt.month,date_crt.day), plot_result=False, save_result_plot=False, save_csv=True)
        
        local_dir= "C:/Users/csjdli/Desktop/bigarm0313/" # 本地需要上传的文件所处的目录
        remote_dir= "/var/www/Bigarm/Bigarm/data/"  #linux下目录
        fileName = date_crt.strftime('%d-%b-%Y') + '.csv'
        upload(local_dir,remote_dir, fileName)
        
        fileName2 = date_crt.strftime('%d-%b-%Y') + '-cf.csv'
        upload(local_dir,remote_dir, fileName2)
        
        time.sleep(3)
        end_time = datetime.now()
        delay = round((end_time-start_time).total_seconds())

        schedule.enter(int(inc-delay), 0, self.execute_command, (inc, ))
        
        print (date_crt.strftime('%d-%b-%Y') + ": task done")
        print ("")
        next_schedule_time = datetime.strptime("00:01",'%H:%M').replace(year=date_crt.year,month=date_crt.month,day=date_crt.day) + timedelta(days=1)
        print (u"BigARMtimer: next scheduled execution time => " + str(next_schedule_time) + ", %s seconds left." %inc)
        

    def cmd_timer(self, time_str, inc=60):
        # time_str：哪一个时间点开始第一次执行
        # inc：两次执行的间隔时间
        # enter四个参数分别为：间隔时间、优先级（用于同时间到达的两个事件同时执行时定序）、被调用触发的函数，
        # 给该触发函数的参数（tuple形式）
        now = datetime.now()
        schedule_time = datetime.strptime(time_str,'%H:%M').replace(year=now.year,month=now.month,day=now.day)
        if schedule_time < now:
            schedule_time = schedule_time + timedelta(days=1)
        time_before_start = int(round((schedule_time-datetime.now()).total_seconds()))
        print (u"BigARMtimer: scheduled execution time => " + str(schedule_time) + ", %s seconds left." %time_before_start)
        schedule.enter(time_before_start, 0, self.execute_command, argument=(inc, ))
        schedule.run() 

        
if __name__=='__main__':  
    timer = Timer()
    # 每天的00:01执行行李传送算法， 间隔为一天，即86400秒
    timer.cmd_timer("00:30", 86400)
'''

#?flag

def get_realtime_for_update(date_str,timestamp,load,loop_no):
    details = []
    all_details = []
    date_sta= parser.parse(date_str)  #datetime.datetime type
    ts= pd.Timestamp(timestamp) #pandas.Timestamp type
    delta =  15 # 5minute integer type
    loop_no=int(loop_no)
    try:
        complete_flights_plan, updated_flights_plan = generate_dynamic_adjustment_plan(date_sta, ts, delta, save_csv=True)
        for i in range(len(updated_flights_plan)):
            flight = updated_flights_plan.iloc[i]
            f_json = {
                "Allocation": flight['dyn_belt'],
                "ETO_start": flight['SCH_START'],
                "ETO_end":    flight['SCH_END'],
                "Flight_no":  flight['FLIGHT_ID_IATA_PREFERRED'],
                "ID":         flight['FLIGHT_ID'],
                "Load":       flight['load'],
                "STA":        flight['SCH_START'],
            }
            details.append(f_json)
        for j in range(len(complete_flights_plan)):
            flight = complete_flights_plan.iloc[j]
            f_json = {
                "Allocation": flight['dyn_belt'],
                "ETO_start": flight['SCH_START'],
                "ETO_end":    flight['SCH_END'],
                "Flight_no":  flight['FLIGHT_ID_IATA_PREFERRED'],
                "ID":         flight['FLIGHT_ID'],
                "Load":       flight['load'],
                "STA":        flight['SCH_START'],
            }
            all_details.append(f_json)
        
        return_json = {
            'Flight_count': len(updated_flights_plan),
            'Details':      details,
            'All_Details':  all_details,
            'Error':        False,
            'date_sta':     date_sta,
            'loopno':    loop_no,
        }

    except Exception as e:
        return_json = {
            'Error': True,
            'Msg':   repr(e)
    }
    return return_json
#print(get_realtime_for_update('2020-2-3',datetime(2020,2,3,6,0,0),1,0))


def get_realtime_for_update_not_simulation(date_str,timestamp,starttime,load,loop_no):
    details = []
    all_details = []
    begin_time=datetime.now()
    date_sta= parser.parse(date_str)  #datetime.datetime type
    ts_button=pd.Timestamp(starttime)
    ts= pd.Timestamp(timestamp) #pandas.Timestamp type
    delta =  5
    loop_no=int(loop_no)
    print(1)
    try:
        complete_flights_plan, updated_flights_plan = generate_dynamic_adjustment_plan(date_sta, ts, delta, save_csv=True)
#        print(updated_flights_plan)
        if updated_flights_plan is None:
            return_json = {
                'Flight_count': 0,
                'Details':      details,
                'All_Details':  all_details,
                'Error':        False,
                'date_sta':     date_sta,
                'ts_button':    ts_button,
                'ts':    ts,
                'loopno':    loop_no,
                'test':    'this is a real time test',
        }
        else:
            for i in range(len(updated_flights_plan)):
                flight = updated_flights_plan.iloc[i]
                f_json = {
                    "Allocation": flight['dyn_belt'],
                    "ETO_start": flight['SCH_START'],
                    "ETO_end":    flight['SCH_END'],
                    "Flight_no":  flight['FLIGHT_ID_IATA_PREFERRED'],
                    "ID":         flight['FLIGHT_ID'],
                    "Load":       flight['load'],
                    "STA":        flight['SCH_START'],
                }
                details.append(f_json)
            for j in range(len(complete_flights_plan)):
                flight = complete_flights_plan.iloc[j]
                f_json = {
                    "Allocation": flight['dyn_belt'],
                    "ETO_start": flight['SCH_START'],
                    "ETO_end":    flight['SCH_END'],
                    "Flight_no":  flight['FLIGHT_ID_IATA_PREFERRED'],
                    "ID":         flight['FLIGHT_ID'],
                    "Load":       flight['load'],
                    "STA":        flight['SCH_START'],
                }
                all_details.append(f_json)
            
            return_json = {
                'Flight_count': len(updated_flights_plan),
                'Details':      details,
                'All_Details':  all_details,
                'Error':        False,
                'date_sta':     date_sta,
                'ts_button':    ts_button,
                'ts':    ts,
                'test':    'this is a real time test',
                }
    except Exception as e:
        return_json = {
            'Error': True,
                'Msg':   repr(e)
        }
    return return_json

#print(get_realtime_for_update_not_simulation('2019-12-19',datetime(2019, 12, 22,21,15,0),datetime(2019, 12, 22,21,15,0),1,0))


# def update_dynamic_CSV(date,updateList):
#     if len(updateList)==0:
#         return_json = {
#             'Details':      'Nothing to update',
#             'Error':        False,
#         }
#         return return_json
#     try:
#         date_sta= parser.parse(date)
#         csv_name = date_sta.strftime('%d-%b-%Y')
#         df_previous_plan=pd.read_csv('/var/www/Bigarm/Bigarm/data/' + csv_name + '-cf.csv')
#         for item in updateList:
#             df_previous_plan.loc[df_previous_plan['FLIGHT_ID_IATA_PREFERRED']==item['Flight_no'],'dyn_belt']=item['Allocation']
#         df_previous_plan.to_csv('/var/www/Bigarm/Bigarm/data/' + csv_name + '-cf.csv', index=False)
#         return_json = {
#             'Details':      'Update complete',
#             'Error':        False,
#             }
#     except Exception as e:
#         return_json = {
#             'Error': True,
#             'Msg':   repr(e)
#         }
#     return return_json

def update_dynamic_CSV(date,updateList):
    if len(updateList)==0:
        return_json = {
            'Details':      'Nothing to update',
            'Error':        False,
        }
        return return_json
    try:
        date_sta= parser.parse(date)
        csv_name = date_sta.strftime('%d-%b-%Y')
        df_previous_plan=pd.read_csv('/var/www/Bigarm/Bigarm/data/' + csv_name + '-Current-Plan.csv')
        dt = datetime.now()
        dt_str = dt.strftime('%d-%b-%Y-%H-%M-%S')
        df_previous_plan.to_csv('/var/www/Bigarm/Bigarm/data/' + dt_str + '-Current-Plan-Front.csv', index=False)
        for item in updateList:
            df_previous_plan.loc[df_previous_plan['FLIGHT_ID_IATA_PREFERRED']==item['Flight_no'],'dyn_belt']=item['Allocation']
        df_previous_plan.to_csv('/var/www/Bigarm/Bigarm/data/' + csv_name + '-Current-Plan.csv', index=False)
        return_json = {
            'Details':      'Update complete',
            'Error':        False,
            }
    except Exception as e:
        return_json = {
            'Error': True,
            'Msg':   repr(e)
        }
    return return_json

# def update_dynamic_CSV_not_simulation(date,updateList):
#     if len(updateList)==0:
#         return_json = {
#             'Details':      'Nothing to update, this is realtime',
#             'Error':        False,
#         }
#         return return_json
#     try:
#         date_sta= parser.parse(date)
#         csv_name = date_sta.strftime('%d-%b-%Y')
#         df_previous_plan=pd.read_csv('/var/www/Bigarm/Bigarm/data/' + csv_name + '-cf.csv')
#         for item in updateList:
#             date_str =parser.parse(item['Flight_time'])
#             date_str=date_str.strftime('%-d/%-m/%Y %-H:%M')
#             df_previous_plan.loc[df_previous_plan['FLIGHT_ID_IATA_PREFERRED']==item['Flight_no'],'dyn_belt']=item['Allocation']
#         df_previous_plan.to_csv('/var/www/Bigarm/Bigarm/data/' + csv_name + '-cf.csv', index=False)
#         return_json = {
#             'Details':      'Update complete',
#             'Flight_time':  datetime.now().strftime('%-d/%-m/%Y %-H:%M'),
#             'Error':        False,
#         }
#     except Exception as e:
#         return_json = {
#             'Error': True,
#             'Msg':   repr(e)
#         }
#     return return_json

def update_dynamic_CSV_not_simulation(date,updateList):
    if len(updateList)==0:
        return_json = {
            'Details':      'Nothing to update, this is realtime',
            'Error':        False,
        }
        return return_json
    try:
        date_sta= parser.parse(date)
        csv_name = date_sta.strftime('%d-%b-%Y')
        df_previous_plan=pd.read_csv('/var/www/Bigarm/Bigarm/data/' + csv_name + '-Current-Plan.csv')
        dt = datetime.now()
        dt_str = dt.strftime('%d-%b-%Y-%H-%M-%S')
        df_previous_plan.to_csv('/var/www/Bigarm/Bigarm/data/' + dt_str + '-Current-Plan-Front.csv', index=False)
        
        for item in updateList:
            date_str =parser.parse(item['Flight_time'])
            date_str=date_str.strftime('%-d/%-m/%Y %-H:%M')
            df_previous_plan.loc[df_previous_plan['FLIGHT_ID_IATA_PREFERRED']==item['Flight_no'],'dyn_belt']=item['Allocation']
        df_previous_plan.to_csv('/var/www/Bigarm/Bigarm/data/' + csv_name + '-Current-Plan.csv', index=False)
        return_json = {
            'Details':      'Update complete',
            'Flight_time':  datetime.now().strftime('%-d/%-m/%Y %-H:%M'),
            'Error':        False,
        }
    except Exception as e:
        return_json = {
            'Error': True,
            'Msg':   repr(e)
        }
    return return_json

def update_initplan(date,updateList):
    if len(updateList)==0:
        return_json = {
            'Details':      'Nothing to update, this is initplan',
            'Error':        False,
        }
        return return_json
    try:
        # heres where we put to mongo DB and CSV?

        # return
        return_json ={
            'Details':      'Initplan update complete',
            'Flight_time':  datetime.now().strftime('%-d/%-m/%Y %-H:%M'),
            'Error':        False,
        }


    except Exception as e:
        return_json ={
            'Error': True,
            'Msg':   repr(e)
        }
    return return_json


