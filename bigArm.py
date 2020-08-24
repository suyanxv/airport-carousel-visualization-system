from flask import Flask
from flask import request
from datetime import datetime, timedelta
from dateutil import parser
from basic import get_database_data, connect_db
from basic import get_plans, Net, get_figure_url
import pymongo
from bson.objectid import ObjectId
from flask import json
from flask import abort, redirect, url_for
import sys

app = Flask(__name__)

#@app.route('/')
#def index():
#    return redirect(url_for('static', filename='index.html'))


@app.route('/get_plan', methods=['POST'])
@app.route('/init_plan', methods=['POST'])
def get_init_plan():
    try:
        date_str = request.form['date']
        initialize = False if request.form['initialize'] == 'false' else True
        date = parser.parse(date_str)
        db_data = get_database_data(date)
        if db_data is None:
            raise Exception('No data on this date')
        plans = get_plans(db_data, initialize)

        details = []
        for i in range(len(db_data)):
            flight = db_data.iloc[i]
            f_json = {
                "Flight_no": flight['Flight_no'],
                "STA":       flight['STA'],
                "Load":      flight['Load'],
                "Chock_time": flight['Chock_time'],
                "ETO_end":   flight['ETO_end'],
                "ID":        str(flight['_id']),
                "Allocation":      plans[i]['Allocation']
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


@app.route('/update', methods=['POST'])
def manual_update():
    post_info = dict(request.json)
    file_id = post_info['ID']
    target_key = post_info['Update']['Item_name']
    target_value = post_info['Update']['New_value']
    if target_key == 'Allocation':
        target_value = int(target_value)
    db = connect_db()
    myquery = {'_id':ObjectId(file_id)}
    newvalues = { "$set": { target_key: target_value } }
    db.update_one(myquery, newvalues)
    date_str = post_info['Date']
    date = parser.parse(date_str)
    db_data = get_database_data(date)
    index = int(post_info['Index'])
    if post_info['Type'] == 'Plan':
        plans, n_diff = (db_data, False, True, index+1, plan_change)
        assert len(plans) == len(db_data)
        return_json = {
            "Error": False,
            "Update_plan": True,
            "Index": index,
            "Plan_count": len(plans),
            "Plans": plans,
            "N_diff": n_diff,
        }

    elif post_info['Type'] == 'Time':
        plans, n_diff = get_plans(db_data, False,  True, index, plan_change=False)
        if plans is not None:
            return_json = {
                "Error": False,
                "Update_plan": True,
                "Index": index,
                "Plan_count": len(plans),
                "Plans": plans,
                "N_diff": n_diff,
            }
        else:
            return_json = {
                "Error": False,
                "Update_plan": False,
                "Index": index,
                "N_diff": n_diff,
            }
    return json.dumps(return_json)


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
    is_debug = False
    if len(sys.argv) == 2:
        if sys.argv[1] == 'debug':
            is_debug = True
    app.run(host="0.0.0.0", port=80, debug=is_debug)
