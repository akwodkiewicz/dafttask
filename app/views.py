from flask import render_template, request, Response, redirect, url_for
from flask_pymongo import PyMongo
from datetime import datetime, timedelta, date
import requests
from pprint import pprint
from sys import stderr


from app import app, mongo
from .logic import (
    update_db, 
    default_action, 
    find_empty_record_dates
    )


@app.route('/', methods=['GET', 'POST'])
def index():
    (start, end, graph, data, form) = default_action()
    return render_template('home.html', form=form, graph=graph, 
                            data=data, start=start, end=end)


@app.route('/table', methods=['GET', 'POST'])
def table():
    (start, end, graph, data, form) = default_action()
    return render_template('table.html', form=form, data=data, 
                            start=start, end=end)


@app.route('/graph', methods=['GET', 'POST'])
def graph():
    (start, end, graph, data, form) = default_action()
    return render_template('graph.html', form=form, graph=graph,
                            start=start, end=end)


@app.route('/delete', methods=['GET', 'POST'])
def delete():
    if request.method == 'POST':
        # Pressing a button on delete.html page generates a value
        # inside the 'form' dictionary, under the key=='task'
        val = request.form.get('task', None)
        if val == 'update':
            update_db()    
        elif val == 'delete':
            for col in mongo.db.collection_names():
                mongo.db[col].drop()

    return render_template('delete.html')


@app.route('/mongo')
def mongo_debug():
    rec = mongo.db.usd.find_one()
    mongo.db.usd.delete_one(rec)
    print(rec, file=stderr)
    return "Check console"
