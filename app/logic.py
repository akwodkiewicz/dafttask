import requests
import asyncio
import aiohttp
import plotly as pl
from datetime import timedelta, date, datetime
from sys import stderr

from app import app, mongo
from .models import currency_list, currency_dict

URL = 'http://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{startDate}/{endDate}/'
TABLE_TYPE = 'A'
START_DATE = date(2002, 1, 1)
END_DATE = date.today()
DELTA = 93


def validate_dates(s, e):
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


def process(form):
    """Processes submitted form and prepares table data and a graph"""
    currency = form.currency.data  
    (start, end) = validate_dates(form.from_date.data, form.to_date.data)
    dates=[]
    mids=[]
    data=[]
    #Find all the docs from start 'till the end
    result = mongo.db[currency].find({"$and":[
        {"effectiveDate": { "$gte": start.strftime("%Y-%m-%d") }},
        {"effectiveDate": { "$lte": end.strftime("%Y-%m-%d") }}
        ]}).sort("effectiveDate")
    #Prepare data for the table (and for making a new graph)
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
    if graph_record is None:
        graph_record = make_and_get_graph(currency, start, end, dates, mids)
    return (start, end, graph_record["graph"], data)


def make_and_get_graph(currency, start, end, dates, mids):
    """Makes a new graph, adds it to the database and returns a record"""
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
        "graph":graph
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
    loop.close()


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
    async with session.get(url, params={'format': 'json'}) as response:
        try:
            json = await response.json()
            record_list = json['rates']
            for rec in record_list:
                if mongo.db[currency].find_one(rec) is None:
                    #print(rec, file=stderr)
                    mongo.db[currency].insert_one(rec)
        except aiohttp.errors.ClientResponseError as exc:
            print("EXCPTIN! Url:{}, code:{}".format(url, exc.code), file=stderr)
