from flask import render_template, request
from flask_pymongo import PyMongo
from datetime import datetime, timedelta, date
import requests
from sys import stderr
import plotly as pl



from app import app
from .models import CurrencyForm, Record
from .logic import make_graph, make_table


URL = 'http://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{startDate}/{endDate}/'
TABLE_TYPE = 'A'
START_DATE = date(2002, 1, 1)
END_DATE = date(2017, 1, 1)
DELTA = 92


@app.route('/', methods=['GET', 'POST'])
def index():
    graph = None
    data = None
    start = None
    end = None
    if request.method == 'GET':
        form = CurrencyForm(request.form)
        if start is not None and end is not None:
            form.from_date.data = start
            form.to_date.data = end
    if request.method == 'POST':
        form = CurrencyForm()
        if form.submit.data and form.validate():
            if form.from_date.data is None:
                start = date.today() - timedelta(days=7)
                end = date.today()
            elif (form.to_date.data - form.from_date.data) > timedelta(days=DELTA):
                start = form.from_date.data 
                end = start + timedelta(days=DELTA)
            else:
                start = form.from_date.data
                end = form.to_date.data
            #graph = make_graph(form.currency, form.from_date, form.to_date)

            req = requests.get(URL.format(
                    table=TABLE_TYPE,
                    code=form.currency.data,
                    startDate=start,
                    endDate=end
                    ),
                    params={'format': 'json'},
                )
            print("StartDate={}, endDate={}".format(start, end), file=stderr)
            print(req, file=stderr)
            json = req.json()
            print(json, file=stderr)
            data = json['rates']
            dates = [x['effectiveDate'] for x in data]
            mids = [x['mid'] for x in data]
            graph_obj = [pl.graph_objs.Scatter(x=dates, y=mids)]
            layout = pl.graph_objs.Layout(autosize=False, width=800, height=500)
            graph = pl.offline.plot({"data":graph_obj, "layout":layout}, output_type="div")

    return render_template('home.html', form=form, graph=graph, data=data,
        start=start, end=end)

@app.route('/table', methods=['GET', 'POST'])
def table():
    form = CurrencyForm()
    return render_template('table.html', form=form)

@app.route('/graph', methods=['GET', 'POST'])
def graph():
    form = CurrencyForm()
    return render_template('graph.html', form=form)


@app.route('/delete')
def delete():
    return render_template('delete.html')