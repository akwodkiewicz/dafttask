import requests
import asyncio
import aiohttp
import plotly as pl
from datetime import timedelta, date, datetime
from sys import stderr

from app import app, mongo

URL = 'http://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{startDate}/{endDate}/'
TABLE_TYPE = 'A'
START_DATE = date(2002, 1, 1)
END_DATE = date.today()
DELTA = 93

def make_graph(currency, from_time, to_time):
    pass

def make_table(data):
    pass

#TODO: Change the order of data source
def check_db(start, end, currency):
    req = requests.get(URL.format(
                table=TABLE_TYPE,
                code=currency,
                startDate=start,
                endDate=end
                ),
                params={'format': 'json'},
            )
    json = req.json()
    record_list = json['rates']
    for rec in record_list:
        if mongo.db[currency].find_one(rec) is None:
            print(rec, file=stderr)
            mongo.db[currency].insert_one(rec)


def validate_dates(s, e):
    if s is None or s > e:
        start = date.today() - timedelta(days=7)
        end = date.today()
    elif (e - s) > timedelta(days=DELTA):
        start = s
        end = start + timedelta(days=DELTA)
    else:
        start = s
        end = e
    if (s < START_DATE):
        start = START_DATE
        if (e - start) > timedelta(days=DELTA):
            end = start + timedelta(days=DELTA)
        else:
            end = e

    return (start, end)


def process(form):
    currency = form.currency.data  
    (start, end) = validate_dates(form.from_date.data, form.to_date.data)
    print("Start:{}, End:{}".format(start,end), file=stderr)

    #check_db(start, end, currency)
    
    dates=[]
    mids=[]
    data=[]
    result = mongo.db[currency].find({"$and":
        [
        {"effectiveDate": { "$gte": start.strftime("%Y-%m-%d") }},
        {"effectiveDate": { "$lte": end.strftime("%Y-%m-%d") }}
        ]
        }).sort("effectiveDate")
    for row in result:
        dates.append(row['effectiveDate'])
        mids.append(row['mid'])
        data.append(row)
    graph_obj = [pl.graph_objs.Scatter(x=dates, y=mids)]
    layout = pl.graph_objs.Layout(autosize=True)
    graph = pl.offline.plot({"data":graph_obj, "layout":layout}, output_type="div")
    return (start, end, graph, data)


async def populate_db(last_update):
    currency = 'usd'
    current_date = last_update
    if last_update is None:
        current_date = START_DATE
    futures = []
    async with aiohttp.ClientSession() as session:
        while current_date <= END_DATE:
            if current_date + timedelta(days=DELTA) <= END_DATE:
                end_date = current_date+timedelta(days=DELTA)
            else:
                end_date = END_DATE

            futures.append(get_from_nbp(session, currency, current_date, end_date))
            current_date += timedelta(days=DELTA+1)

        result, _ = await asyncio.wait(futures)    
    
    print("Total requests for [{}]: {}".format(currency, len(result)), file=stderr)
            
async def get_from_nbp(session, currency, start_date, end_date):
    url = URL.format(
        table=TABLE_TYPE,
        code=currency,
        startDate=start_date,
        endDate=end_date
        )
    async with session.get(url, params={'format': 'json'}) as response:
        json = await response.json()
        record_list = json['rates']
        for rec in record_list:
            if mongo.db[currency].find_one(rec) is None:
                print(rec, file=stderr)
                mongo.db[currency].insert_one(rec)

def restart_db():
    last_record_cursor = mongo.db['usd'].find().sort("effectiveDate",-1)
    if last_record_cursor.count() != 0:
        last_record = last_record_cursor[0]
        last_date = datetime.strptime(last_record["effectiveDate"], "%Y-%m-%d").date()
    else:
        last_date = START_DATE
    loop = asyncio.get_event_loop()
    loop.run_until_complete(populate_db(last_date))
    loop.close()
