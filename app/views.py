from flask import render_template, request, Response
from flask_pymongo import PyMongo
from datetime import datetime, timedelta, date
import requests
from sys import stderr


from app import app, mongo
from .models import CurrencyForm, currency_list
from .logic import ( validate_dates, process, update_db, previous, default_action)


@app.route('/', methods=['GET', 'POST'])
def index():
    (start, end, graph, data, form) = default_action()
    return render_template('home.html', form=form, graph=graph, data=data,
            start=start, end=end)


@app.route('/table', methods=['GET', 'POST'])
def table():
    (start, end, graph, data, form) = default_action()
    return render_template('table.html', form=form, data=data, start=start, end=end)


@app.route('/graph', methods=['GET', 'POST'])
def graph():
    (start, end, graph, data, form) = default_action()
    return render_template('graph.html', form=form, graph=graph, start=start, end=end)


@app.route('/delete')
def delete():
    for (cur,_) in currency_list:
        mongo.db[cur].drop()
    mongo.db['graphs'].drop()
    #update_db()
    return render_template('delete.html')


@app.route('/mongo')
def mongo_debug():
    return Response(mongo.db.collection_names(), mimetype='text')
