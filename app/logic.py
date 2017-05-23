import requests
import plotly as pl
from datetime import timedelta, date
from sys import stderr

from app import app, mongo

URL = 'http://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{startDate}/{endDate}/'
TABLE_TYPE = 'A'
START_DATE = date(2002, 1, 1)
END_DATE = date(2017, 1, 1)
DELTA = 92

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
    if (s < START_DATE):
        start = START_DATE
        if (e - start) > timedelta(days=DELTA):
            end = start + timedelta(days=DELTA)
        else:
            end = e
    else:
        start = s
        end = e
    return (start, end)

def process(form):
    currency = form.currency.data  
    (start, end) = validate_dates(form.from_date.data, form.to_date.data)
    print("Start:{}, End:{}".format(start,end), file=stderr)

    check_db(start, end, currency)
    
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
    layout = pl.graph_objs.Layout(autosize=True, width=600, height=500)
    graph = pl.offline.plot({"data":graph_obj, "layout":layout}, output_type="div")
    return (start, end, graph, data)
