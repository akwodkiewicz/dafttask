import requests
import asyncio
import aiohttp
import plotly as pl
from flask import render_template, request, Response
from datetime import timedelta, date, datetime
from sys import stderr

from app import app, mongo
from .models import currency_list, currency_dict, Previous, CurrencyForm

URL = 'http://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{startDate}/{endDate}/'
TABLE_TYPE = 'A'
START_DATE = date(2002, 1, 1)
END_DATE = date.today()
DELTA = 93
previous = Previous(date.today() - timedelta(days=7), date.today(), 'usd')


def default_action():
    """Default function called by the main page and 2 subpages"""
    form = CurrencyForm(request.form)
    if request.method == 'GET':
        (start, end, graph, data) = process(form)
    if request.method == 'POST':
        if form.validate():
            (start, end, graph, data) = process(form)
        else:
            (start, end, graph, data) = process(form, invalidated=True)
    return (start, end, graph, data, form)


def validate_dates(s, e):
    """Date validation for making a proper request"""
    if s is None or s > e:
        start = date.today() - timedelta(days=7)
        end = date.today()
    elif (s < START_DATE):
        start = START_DATE
        end = e
    else:
        start = s
        end = e
    return (start, end)


def process_from_previous(form):
    """
    Returns (start, end, currency) tuple based on previously used values
    and sets those values inside proper form fields for the user to see
    """
    global previous
    start = previous.start
    end = previous.end
    currency = previous.currency
    form.from_date.data = start
    form.to_date.data = end
    form.currency.data = currency
    return (start, end, currency)


def process(form, invalidated=False):
    """Processes submitted form and prepares table data and a graph"""

    #Setting proper (start, end, currency) values
    if form.currency.data == 'None' or invalidated == True:
        (start, end, currency) = process_from_previous(form)
    else:
        (start, end) = validate_dates(form.from_date.data, form.to_date.data)
        currency = form.currency.data
        previous.update(start, end, currency)

    #Find all the docs from start 'till the end
    result = mongo.db[currency].find({"$and":[
        {"effectiveDate": { "$gte": start.strftime("%Y-%m-%d") }},
        {"effectiveDate": { "$lte": end.strftime("%Y-%m-%d") }}
        ]}).sort("effectiveDate", -1)

    #Prepare data for the table (and for a new graph)
    dates=[]
    mids=[]
    data=[]
    for doc in result:
        dates.append(doc['effectiveDate'])
        mids.append(doc['mid'])
        data.append(doc)

    #Try to find an existing graph for this set of values
    graph_record = mongo.db['graphs'].find_one({
        "start":start.strftime("%Y-%m-%d"),
        "end":end.strftime("%Y-%m-%d"),
        "currency":currency
        })

    #If it doesn't exist - make a new one
    if graph_record is None: 
        graph_record = make_and_get_graph(currency, start, end, dates, mids)
    #If we had previously less data about this period, 
    #delete the old graph and make a new one
    elif graph_record["points"] < len(data):
        mongo.db["graphs"].delete(graph_record)
        graph_record = make_and_get_graph(currency, start, end, dates, mids)
    #else continue
    else:
        print("USING GRAPH FROM DB", file=stderr)

    return (start, end, graph_record["graph"], data)


def make_and_get_graph(currency, start, end, dates, mids):
    """
    Makes a new graph, adds it to the database 
    and returns a whole record (a dictionary)
    """
    graph_obj = [pl.graph_objs.Scatter(x=dates, y=mids)]
    layout = pl.graph_objs.Layout(
                            title=currency_dict[currency],
                            xaxis={"title":"Date"},
                            yaxis={"title":"Exchange rate"},
                            height=600
                            )
    graph = pl.offline.plot({"data":graph_obj, "layout":layout}, output_type="div")
    record = {
        "start":start.strftime("%Y-%m-%d"),
        "end":end.strftime("%Y-%m-%d"),
        "currency":currency,
        "graph":graph,
        "points":len(dates)
        }
    mongo.db['graphs'].insert_one(record)
    return record


def update_db():
    """
    Updates the database from the latest record up to current day 
    using asyncio event loop.
    """
    latest_date = find_latest_record_date()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(prepare_and_start_futures(latest_date))
    #loop.close()


def find_latest_record_date():
    last_record_cursor = mongo.db['usd'].find().sort("effectiveDate",-1)
    if last_record_cursor.count() != 0:
        last_record = last_record_cursor[0]
        last_date = datetime.strptime(last_record["effectiveDate"], "%Y-%m-%d").date()
    else:
        last_date = START_DATE
    return last_date


async def prepare_and_start_futures(last_update):
    """Queues all the requests and starts them asynchronously"""
    futures = []
    async with aiohttp.ClientSession() as session:
        for (currency, _) in currency_list:
            current_date = last_update
            while current_date < END_DATE:
                if current_date + timedelta(days=DELTA) <= END_DATE:
                    end_date = current_date+timedelta(days=DELTA)
                else:
                    end_date = END_DATE

                futures.append(get_from_nbp(session, currency, current_date, end_date))
                current_date += timedelta(days=DELTA+1)
        if len(futures) != 0:
            await asyncio.wait(futures)

                
async def get_from_nbp(session, currency, start_date, end_date):
    """Sends one GET request and enters the result into database"""
    url = URL.format(
        table=TABLE_TYPE,
        code=currency,
        startDate=start_date,
        endDate=end_date
        )
    try:
        async with session.get(url, params={'format': 'json'}, timeout=30) as response:
            try:
                json = await response.json()
                record_list = json['rates']
                for rec in record_list:
                    if mongo.db[currency].find_one(rec) is None:
                        #print(rec, file=stderr)
                        mongo.db[currency].insert_one(rec)
            except aiohttp.ClientResponseError as e:
                print("--- Wrong response from:{}\n---{}".format(url, e),
                    file=stderr)
    except aiohttp.ClientConnectionError as e:
        print("--- ConnectionError when sending a request:\n--- {}".format(e),
            file=stderr)
    except asyncio.TimeoutError as e:
        print("--- Timeout when sending a request:\n--- {}".format(e),
            file=stderr)
    except Exception as e:
        print("--- Unkown exception when sending a request:\n--- {}".format(e),
            file=stderr)

