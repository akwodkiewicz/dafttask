from flask import render_template, request, Response, redirect, url_for
from flask_pymongo import PyMongo
from datetime import datetime, timedelta, date
import requests
from pprint import pprint
from sys import stderr


from app import app, mongo
from .logic import (update_db, default_action, find_empty_record_dates)


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
    for col in mongo.db.collection_names():
        mongo.db[col].drop()
    update_db()
    return render_template('delete.html', f=redirect(url_for('index')))


@app.route('/mongo')
def mongo_debug():
    result = find_empty_record_dates()
    pprint(result, stream=stderr)
    return "Check console"
