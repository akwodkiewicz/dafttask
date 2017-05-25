import asyncio
import aiohttp
import plotly as pl
from flask import render_template, request, Response
from datetime import timedelta, date, datetime
from sys import stderr
from time import sleep

from app import app, mongo
from .models import ( 
    Previous, CurrencyForm,
    URL,
    TABLE_TYPE, 
    START_DATE,
    END_DATE,
    DELTA,
    CURRENCY_DICT,
    CURRENCY_LIST,
    SLEEP_TIME,
    TIMEOUT
)

### Global mutable objects
previous = Previous(date.today() - timedelta(days=7), date.today(), 'usd')
wrong_responses_counter = 0
inserted_records_counter = 0


def default_action():
    """
    Default function called by the main page and 2 subpages
    Returns all the data necessary to render a page
    """
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
    if e > date.today():
        e = date.today()
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
    Sets (start, end, currency) values basing on previously used values
    inside the form fields (for the user to see) and returns them 
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

    # Setting proper (start, end, currency) values
    if form.currency.data == 'None' or invalidated == True:
        (start, end, currency) = process_from_previous(form)
    else:
        (start, end) = validate_dates(form.from_date.data, form.to_date.data)
        currency = form.currency.data
        previous.update(start, end, currency)

    # Find all the docs from 'start' till the 'end'
    result = mongo.db[currency].find({"$and":[
        {"effectiveDate": { "$gte": start.strftime("%Y-%m-%d") }},
        {"effectiveDate": { "$lte": end.strftime("%Y-%m-%d") }}
        ]}).sort("effectiveDate", -1)

    # Prepare data for the table (and for a new graph)
    data=[]
    for doc in result:
        data.append(doc)

    # Try to find an existing graph for this set of values
    graph_record = mongo.db['graphs'].find_one({
        "start":start.strftime("%Y-%m-%d"),
        "end":end.strftime("%Y-%m-%d"),
        "currency":currency
        })

    # If it doesn't exist - make a new one
    if graph_record is None: 
        graph_record = make_and_get_graph_record(currency, start, end, data) 
    # If we had previously less data about this period,
    # delete the old graph and make a new one
    elif len(graph_record["data"]) < len(data):
        mongo.db["graphs"].delete_one(graph_record)
        graph_record = make_and_get_graph_record(currency, start, end, data)
    # Else - the data inside a graph_record is either equal to the data from
    # [currency] collection or even more detalied
    else:
        data = graph_record["data"]
        print("--- Using cached graph and data", file=stderr, flush=True)

    return (start, end, graph_record["graph"], data)


def make_and_get_graph_record(currency, start, end, data):
    """
    Makes a new graph, adds it to the database 
    and returns a whole record (a dictionary)
    """
    dates = [row['effectiveDate'] for row in data]
    mids = [row['mid'] for row in data]
    graph_obj = [pl.graph_objs.Scatter(x=dates, y=mids)]
    layout = pl.graph_objs.Layout(
                            title=CURRENCY_DICT[currency],
                            xaxis={"title":"Date"},
                            yaxis={"title":"Exchange rate"},
                            height=580,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)'
                            )
    graph = pl.offline.plot({"data":graph_obj, "layout":layout}, 
                            output_type="div")
    record = {
        "start":start.strftime("%Y-%m-%d"),
        "end":end.strftime("%Y-%m-%d"),
        "currency":currency,
        "graph":graph,
        "data":data
        }
    mongo.db['graphs'].insert_one(record)
    return record


def update_db():
    """
    Updates the database with all the missing records 
    using asyncio event loop. 
    Returns no. of inserted records and wrong responses
    """
    global wrong_responses_counter, inserted_records_counter
    wrong_responses_counter = 0
    inserted_records_counter = 0

    empty_record_dates = find_empty_record_dates()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(prepare_and_start_futures(empty_record_dates))
    print("--- Inserted records: {}\n--- Wrong responses: {}".format(
        inserted_records_counter,
        wrong_responses_counter
        ), file=stderr, flush=True
    )
    return (inserted_records_counter, wrong_responses_counter)


def find_empty_record_dates():
    """
    Finds all the missing chunks of records in the database and for each 
    currency in CURRENCY_DICT returns its list of chunks' start dates.
    Example return:
    empty_record_dates = {
        'usd': [date(2005, 5, 7),
                date(2005, 8, 9),
                date(2005, 11, 11),
                date.today()-timedelta(days=DELTA)],
        'jpy': [date(2007, 12, 3)],
                date.today()-timedelta(days=DELTA)],
        'chf': [],
        ... etc. ...
    }
    """
    empty_record_dates = {}
    for cur in CURRENCY_DICT.keys():
        empty_record_dates[cur] = []
        current_date = START_DATE
        # Find all the DELTA-long chunks 
        while current_date <= END_DATE:
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
            # Added some sleeping to decrease the number of wrong responses
            # received from the NBP API
            sleep(SLEEP_TIME)

        if len(futures) != 0:
            await asyncio.wait(futures)
                

async def get_from_nbp(session, currency, start_date, end_date):
    """Sends one GET request and inserts the response into database"""
    global wrong_responses_counter, inserted_records_counter
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
                    timeout=TIMEOUT
                    ) as response:

            try:
                json = await response.json()    
                record_list = json['rates']
                for rec in record_list:
                    if mongo.db[currency].find_one(rec) is None:
                        mongo.db[currency].insert_one(rec)      
                        inserted_records_counter += 1

            except aiohttp.ClientResponseError as e:
                wrong_responses_counter += 1
                print("-!- Wrong response from:{}\n-!- {}"\
                    .format(url, e), file=stderr)

    except aiohttp.ClientConnectionError as e:
        wrong_responses_counter += 1
        print("-!- ConnectionError for:{}\n-!- {}"\
            .format(url, e), file=stderr)

    except asyncio.TimeoutError as e:
        wrong_responses_counter += 1
        print("-!- Timeout for {}".format(url), file=stderr)

    except Exception as e:
        wrong_responses_counter += 1
        print("-!- Unkown exception when sending a request: {}"\
            .format(e), file=stderr)

    stderr.flush()
