from flask import render_template, request, Response
from flask_pymongo import PyMongo
from datetime import datetime, timedelta, date
import requests
from sys import stderr


from app import app, mongo
from .models import CurrencyForm, currency_list
from .logic import ( validate_dates, process, update_db )


def default_action():
    start = date.today()-timedelta(days=7)
    end = date.today()
    graph = None
    data = None
    form = CurrencyForm(request.form)
    if request.method == 'GET':
        form.from_date.data = start
        form.to_date.data = end
        form.currency.data = 'usd'
        (start, end, graph, data) = process(form)
    if request.method == 'POST':
        if form.validate():
            (start, end, graph, data) = process(form)
    return (start, end, graph, data, form)


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
    update_db()
    return render_template('delete.html')


@app.route('/mongo')
def mongo_debug():
    cursor = mongo.db.collections()
    file = ""
    for doc in cursor:
        file += str(doc)
        file += '\n'
    return Response(file, mimetype='text')
