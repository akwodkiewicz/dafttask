from flask import render_template, request, Response, redirect, url_for
from flask_pymongo import PyMongo
from datetime import datetime, timedelta, date
import requests
from pprint import pprint
from sys import stderr


from app import app, mongo
from .models import CURRENCY_DICT
from .logic import (
    update_db, 
    default_action, 
    find_empty_record_dates
    )


@app.route('/', methods=['GET', 'POST'])
def index():
    (start, end, graph, data, form) = default_action()
    return render_template('home.html', form=form, graph=graph, 
                            data=data, start=start, end=end,
                            cur=CURRENCY_DICT[form.currency.data])


@app.route('/table', methods=['GET', 'POST'])
def table():
    (start, end, graph, data, form) = default_action()
    return render_template('table.html', form=form, data=data, 
                            start=start, end=end,
                            cur=CURRENCY_DICT[form.currency.data])


@app.route('/graph', methods=['GET', 'POST'])
def graph():
    (start, end, graph, data, form) = default_action()
    return render_template('graph.html', form=form, graph=graph,
                            start=start, end=end,
                            cur=CURRENCY_DICT[form.currency.data])


@app.route('/delete', methods=['GET', 'POST'])
def delete():
    wrong = -1
    correct = -1
    deleted = False
    if request.method == 'POST':
        # Pressing a button on delete.html page generates a value
        # inside the 'form' dictionary, under the key=='task'
        val = request.form.get('task', None)
        if val == 'update':
            (correct, wrong) = update_db()
        elif val == 'delete':
            for col in mongo.db.collection_names():
                mongo.db[col].drop()
            deleted = True

    return render_template('delete.html', wrong=wrong, correct=correct,
                            deleted=deleted)


@app.route('/mongo')
def mongo_debug():
    rec = mongo.db.usd.find_one({"effectiveDate":date.today()})
    mongo.db.usd.delete_one(rec)
    print(rec, file=stderr)
    return "Check console"
