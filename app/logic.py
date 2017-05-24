import requests
import asyncio
import aiohttp
import plotly as pl
from flask import render_template, request, Response
from datetime import timedelta, date, datetime
from sys import stderr

from app import app, mongo
from .models import ( 
    Previous, CurrencyForm,
    URL,
    TABLE_TYPE, 
    START_DATE,
    END_DATE,
    DELTA,
    CURRENCY_DICT,
    CURRENCY_LIST
)

### Global mutable objects
previous = Previous(date.today() - timedelta(days=7), date.today(), 'usd')
wrong_responses_counter = 0
correct_responses_counter = 0


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

    #Find all the docs from defined start 'till the end
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
        graph_record = make_and_get_graph_record(currency, start, end, dates, mids)
    #If we had previously less data about this period (possibly due to errors),
    #delete the old graph and make a new one
    elif graph_record["points"] < len(data):
        mongo.db["graphs"].delete_one(graph_record)
        graph_record = make_and_get_graph_record(currency, start, end, 
                                                dates, mids)
    #else continue
    else:
        print("USING GRAPH FROM DB", file=stderr)

    return (start, end, graph_record["graph"], data)


def make_and_get_graph_record(currency, start, end, dates, mids):
    """
    Makes a new graph, adds it to the database 
    and returns a whole record (a dictionary)
    """
    graph_obj = [pl.graph_objs.Scatter(x=dates, y=mids)]
    layout = pl.graph_objs.Layout(
                            title=CURRENCY_DICT[currency],
                            xaxis={"title":"Date"},
                            yaxis={"title":"Exchange rate"},
                            height=600
                            )
    graph = pl.offline.plot({"data":graph_obj, "layout":layout},
                            output_type="div")
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
    Updates the database with all the missing records 
    using asyncio event loop.
    """
    global wrong_responses_counter, correct_responses_counter
    wrong_responses_counter = 0
    correct_responses_counter = 0

    empty_record_dates = find_empty_record_dates()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(prepare_and_start_futures(empty_record_dates))
    print("Correct responses: {}\nWrong responses:{}".format(
        correct_responses_counter,
        wrong_responses_counter
        ), file=stderr
    )
    #loop.close()


def find_empty_record_dates():
    """
    Finds all the missing chunks of records in the database
    and for each currency in CURRENCY_DICT (in models.py)
    returns its list of 'start_dates'.
    Example return:
    empty_record_dates = {
        'usd': [datetime.date(2005, 5, 7),
                datetime.date(2005, 8, 9),
                datetime.date(2005, 11, 11)],
        'jpy': [datetime.date(2007, 12, 3)],
        'chf': [],

        ... etc. ...
    }
    """
    empty_record_dates = {}
    for cur in CURRENCY_DICT.keys():
        empty_record_dates[cur] = []
        current_date = START_DATE
        while current_date < END_DATE:
            end_date = current_date+timedelta(days=DELTA)
            result = mongo.db[cur].find_one({"$and":[
                {"effectiveDate":{"$gte": current_date.strftime("%Y-%m-%d")}},
                {"effectiveDate":{"$lte": end_date.strftime("%Y-%m-%d")}}
                ]})
            if result is None:
                empty_record_dates[cur].append(current_date)
            current_date += timedelta(days=DELTA+1)
    return empty_record_dates


async def prepare_and_start_futures(empty_record_dates):
    """Queues all the requests and starts them asynchronously"""
    futures = []
    async with aiohttp.ClientSession() as session:
        for (currency, date_list) in empty_record_dates.items():
            for date in date_list:
                current_date = date
                if current_date + timedelta(days=DELTA) <= END_DATE:
                    end_date = current_date+timedelta(days=DELTA)
                else:
                    end_date = END_DATE
                futures.append(
                    get_from_nbp(session, currency, current_date, end_date)
                )

        if len(futures) != 0:
            await asyncio.wait(futures)
                

async def get_from_nbp(session, currency, start_date, end_date):
    """Sends one GET request and enters the result into database"""
    global wrong_responses_counter, correct_responses_counter
    url = URL.format(
        table=TABLE_TYPE,
        code=currency,
        startDate=start_date,
        endDate=end_date
        )
    try:
        async with session.get(
            url, 
            headers={'Accept': 'application/json'}, 
            timeout=30
            ) as response:
            
            if response.content_type == 'application/json':
                correct_responses_counter += 1
            else:
                wrong_responses_counter += 1
            try:
                json = await response.json()    
                record_list = json['rates']
                for rec in record_list:
                    if mongo.db[currency].find_one(rec) is None:
                        #print(rec, file=stderr)
                        mongo.db[currency].insert_one(rec)
            except aiohttp.ClientResponseError as e:
                print("--- Wrong response from:{}\n---{}---"\
                    .format(response, e.message), file=stderr)
    except aiohttp.ClientConnectionError as e:
        print("--- ConnectionError when sending a request: {} ---"\
            .format(e), file=stderr)
    except asyncio.TimeoutError as e:
        print("--- Timeout when sending a request ---", file=stderr)
    except Exception as e:
        print("--- Unkown exception when sending a request: {} ---"\
            .format(e), file=stderr)

