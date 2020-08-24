from flask import Flask, render_template, send_from_directory
from flask import abort, redirect, url_for, session, json, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from functools import wraps
import pandas as pd
import os
import io

from datetime import datetime, timedelta
from dateutil import parser

from basic import get_database_data, connect_db
from basic import get_plans, Net, get_figure_url
import pymongo
from flask_pymongo import *
from bson.objectid import ObjectId
import logging
import sys
import bigarm_carousel_allocation as bca
import changeformat as cf
#import Maintainace_0621 as bcm_new
date = datetime.now()
import json as js
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = '/var/www/Bigarm/Bigarm/data'
ALLOWED_EXTENSIONS = ['jpg','csv']

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
log_format = "%(levelname)s - %(asctime)s - %(message)s"
logging.basicConfig(filename="/var/www/Bigarm/Bigarm/bigARM_logging.log", level=logging.DEBUG, format = log_format)
logger = logging.getLogger()
app.logger.handlers = logger.handlers

app.secret_key = os.urandom(24)
app.config['SECRET_KEY'] = app.secret_key
app.config.update(
	MONGO_URI='mongodb://201902alan:a145803PolyU@bigarm-storage.comp.polyu.edu.hk/bigARM')
mongo = PyMongo(app)

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
	def __init__(self, username, password,accesslevel):
		self.id = username
		self.username = username
		self.password = password


@login_manager.user_loader
def load_user(username):
	db_users = mongo.db['bigarm_remote_access_user']
	permitted_user = db_users.find_one({'Name': username})
	if not permitted_user:
		 return None
	return User(permitted_user['Name'], permitted_user['Password'],permitted_user['Level'])

@login_manager.unauthorized_handler
def unauthorized_callback():
    return render_template('login.html')

@app.route("/testing")
#@login_required
def testing():
	return '<h1>Testing Web OK</h1>'

@app.route('/')
def index():
	logger.info("Client access to BigARM from %s", request.remote_addr)
	return render_template('login.html')

@app.route('/bigarm')
@login_required
def bigarm():
	if admin_access:
		return render_template('index.html', admin_access = True)
	else:
		return render_template('index.html', admin_access = False)

def is_allow_extension(filename):
	if filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
		return True
	else:
		return False

@app.route('/upload_file', methods=['GET','POST'])
def upload_file():
	upload_date = modifydate.strftime('%d-%b-%Y')
	logger.info("Date of upload custom current plan : %s", upload_date)
	try:
		file = request.files['file']
		if file and is_allow_extension(file.filename):
			logger.info("User uploaded " + file.filename + " to server")
			upload_filename = upload_date +"-Current-Plan.csv"
			df_cf_result = cf.changeBigARMformat(upload_filename, file)
			df_cf_result.to_csv("/var/www/Bigarm/patrick_bigarm/data/" + upload_filename, index=False)
			#file.save(os.path.join(app.config['UPLOAD_FOLDER'], upload_filename))
			logger.info("File changed name to " + upload_filename + " and save to server.")
			logger.info("File Upload Completed.")

		elif is_allow_extension(file.filename) == False:
			logger.info("File extension not correct")

	except Exception as e:
		return json.dumps({'error': str(e)})

        details = []
        for i in range(len(df_cf_result)):
            flight = df_cf_result.iloc[i]
            # print(flight)
            f_json = {
                # "AircraftType": flight['AircraftType'],
                # "Stand": flight['Stand'],
                "Flight_no": flight['FLIGHT_ID_IATA_PREFERRED'],
                "STA":       flight['SCH_START'],
                "Load":      str(flight['load']),
                "ETO_start": flight['SCH_START'],
                "ETO_end":   flight['SCH_END'],
                "ID":        flight['FLIGHT_ID'],
                "Allocation": str(flight['dyn_belt'])
                # ,"First_carousel_no": str(flight['origin_belt'])
                # ,"test": "here"
            }
            details.append(f_json)
        return_json = {
            'Flight_count': len(df_cf_result),
            'Details':      details,
            'Error':        True,
        }
	return json.dumps(return_json)
	
@app.route('/login', methods=['GET', 'POST'])
def login():
	global admin_access
	db_users = mongo.db['bigarm_remote_access_user']
	username = request.form['username']
	password = request.form['pass']
	target_user = []
	target_user = db_users.find_one({'Name': username})
	if target_user:
		if password == target_user['Password']:
			level = target_user['Level']
			user = User(username, password,level )
			login_user(user)
			#Define user access right
			user_level = target_user['Level']
			if user_level == 1:
				logger.info('%s has Admin Permission', username)
				admin_access = True
				session['admin_access'] = True
			else:
				logger.info('%s has User Permission', username)
				admin_access = False
				session['admin_access'] = False

			session['username'] = True
			session['username'] = request.form['username']
			logger.info('%s has logged in successfully from %s', username, request.remote_addr)
			# is_safe_url should check if the url is safe for redirects.
			# See http://flask.pocoo.org/snippets/62/ for an example.
			return redirect(url_for('bigarm'))
	logger.warning('User entered Invalid username/password')
	return '<h1>Invalid username/password combination</h1>'

@app.route('/logout')
@login_required
def logout():
	logger.info('User %s has logged out successfully', session['username'])
	flash('You Have Been Logged Out')
	logout_user()
	return redirect('/')

@app.route('/disablecarousel', methods=['POST'])
def disablecarousel():
	logger.info("Start Process disable carousel")
	try:
		db_belt = mongo.db['belt_status']
		# query_date_str = request.form['query_time']
		# query_date = datetime.strptime(query_date_str, '%Y-%m-%d')
		#factors = (60, 1)
		carousel_list = []
		carousels = request.form.getlist('disable_carousel[]')
		dt_s = request.form.getlist('disabletime_S[]')
		dt_e = request.form.getlist('disabletime_E[]')
		for i in xrange(0, len(carousels)):
		##Changing Time to minutes.
		# for i in xrange(0, len(carousels)):
		# 	t1 = sum(i*j for i, j in zip(map(int, dt_s[i].split(':')), factors))
		# 	t2 = sum(i*j for i, j in zip(map(int, dt_e[i].split(':')), factors))
		# 	if t1 < 180:
		# 		 t1 += 24 * 60
		# 	if t2 < 180:
		# 		t2 += 24 * 60
			carousel_list.append([int(carousels[i]), dt_s[i], dt_e[i]])
			logger.info("User submited maintanence schedule.")
			insertTodb = {'createdtime':datetime.now(), 'belt':carousels[i], 'start':dt_s[i],'end':dt_e[i],'account':session['username']}
			db_belt.update_one({'start':dt_s[i],'belt':carousels[i]},{'$set': insertTodb},upsert=True) #Write to DB without duplicate record
			logger.info("Scheduled belt %s Mantenance from %s - %s.", int(carousels[i])+5, dt_s[i], dt_e[i])
		
		# details=[]
		# disable_process_start = datetime.now()
		# df_maintenancecarousel = bcm_new.generate_carousel_maintenance_initial_plan(query_date, carousel_list)
		# disable_process_end = datetime.now()
		# duration = disable_process_end - disable_process_start
		# logger.info('Disable carousel process completed. Duration : %s',duration)
		# for i in xrange(len(df_maintenancecarousel)):
		# 	flight = df_maintenancecarousel.iloc[i]
		# 	f_json = {
		# 		"Flight_no": flight['FLIGHT_ID_IATA_PREFERRED'], "STA": flight['SCH_START'],
		# 		"Load": flight['load'],
		# 		"Chock_time": flight['SCH_START'],
		# 		"ETO_end": flight['EST_END'],
		# 		"ID": flight['FLIGHT_ID'],
		# 		"Allocation": flight['dyn_belt']
		# 		#"First_carousel_no": flight['First_carousel_no']
		# 	}
		# 	details.append(f_json)
		# return_json = {
		# 	'Flight_count': len(df_maintenancecarousel),
		# 	'Details': details,
		# 	'Return': carousel_list,
		# 	'Error': False,
		# }
	except Exception as e:
		return json.dumps({'error': str(e)})

	return  json.dumps(carousel_list)

	#df_pass_result = bca.get_init_plan_for_plot(df_maintenancecarousel)
	#return df_maintenancecarousel
	#return render_template('result.html',data=df_maintenancecarousel.to_html())
	#return render_template('pass.html',data=df_maintenancecarousel.to_html(),dt=today,cn=disable_carousel,st=t1, et=t2)

@app.route('/viewmaintenance', methods=['POST'])
def viewmaintenance():
	try:
		logger.info("Scheduled maintenance loaded.")
		for x in db_belt.find({"end":{ "$gt":endtime}}):
			return(x)			
	except Exception as e:
		return json.dumps({'error': str(e)})

	return json.dumps(carousel_list)

# Get data from DB
# @app.route('/get_plan', methods=['POST'])
# @app.route('/init_plan', methods=['POST'])
# def get_init_plan():
	#####--- save_result_plot=False, save_csv=True)
	# global modifydate
	# date_str = request.form['date']
	# date = parser.parse(date_str)
	# modifydate = parser.parse(date_str)
	

    #####--- Database reading related part
	# logger.info('Date selected: %s, start processing data', date)
	# process_start = datetime.now()
	# a = bca.get_init_plan_for_plot(date)
	# process_end = datetime.now()
	# duration = process_end - process_start
	# logger.info('Data Process Completed. Duration: %s .', duration)
	# return a

# Get data from CSV
@app.route('/get_plan', methods=['POST'])
@app.route('/init_plan', methods=['POST'])
def get_init_plan():
	date_str = request.form['date']
	date = parser.parse(date_str)
	df_initial_plan=pd.read_csv('/var/www/Bigarm/Bigarm/data/'+date.strftime("%d-%b-%Y")+'.csv')
	return bca.get_init_plan_for_plot(df_initial_plan)  




# get simulation
@app.route('/get_simulation', methods=['POST'])
def get_simulation():
	date_str = request.form['date'][0:10]
	timestamp = request.form['date']
	load = request.form.getlist('load')
	loop_no = request.form['loopno']

	#date_str = str(datetime(2019,10,16))
	#timestamp = pd.Timestamp('2019-10-16 12:45:00')
	#load = 1
	#loop_no = 1
	
	logger.info('Simultaion process start.')
	return_json=bca.get_realtime_for_update(date_str,timestamp,load,loop_no)
	logger.info('Simultaion process completed.')
	return json.dumps(return_json)
#Demo
#sudo python -c 'import __init__; print __init__.get_simulation()'
#python __init__.py.get_simulation()

# get realtime
@app.route('/get_realtime', methods=['POST'])
def get_realtime():
    date_str = request.form['date'][0:10]
    timestamp = request.form['date']
    starttime = request.form['starttime']
    load = request.form.getlist('load')
    loop_no = request.form['loopno']
    return_json=bca.get_realtime_for_update_not_simulation(date_str,timestamp,starttime,load,loop_no)
    return json.dumps(return_json)

# update simulation
@app.route('/update_simulation', methods=['POST'])
def update_simulation():
    date = request.form['date']
    updateList = js.loads(request.form['updateList'])
    return_json= bca.update_dynamic_CSV(date,updateList)
    logger.info(len(return_json))
    return json.dumps(return_json)

# update realtime
@app.route('/update_realtime', methods=['POST'])
def update_realtime():
    date = request.form['date']
    updateList = js.loads(request.form['updateList'])
    return_json= bca.update_dynamic_CSV_not_simulation(date,updateList)
    return json.dumps(return_json)

# update initplan to database?
@app.route('/update_initplan', methods=['POST'])
def update_initplan():
    date = request.form['date']
    updateList = js.loads(request.form['updateList'])
    return_json= bca.update_initplan(date,updateList)
    return json.dumps(return_json) # transfer python to json

@app.route('/get_fig', methods=['POST'])
def get_figure():
    date_str = request.form['date']
    date = parser.parse(date_str)
    db_data = get_database_data(date)
    url = get_figure_url(db_data, date)
    return_json = {
        "Error": False,
        "Figure_url": url,
    }
    return json.dumps(return_json)

if __name__ == '__main__':
	app.run(host="0.0.0.0", port=5002,debug = True)
