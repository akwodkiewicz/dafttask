import asyncio
from datetime import datetime
from sys import stderr
from flask import Flask
from flask_pymongo import PyMongo

app = Flask(__name__)

app.config['WTF_CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = 'this-shouldnt-be-publicly-visible'
app.config['MONGO_DBNAME'] = 'main_db'
app.config['MONGO_URI'] = 'mongodb://database/main_db'

mongo = PyMongo(app)

from app import views, logic

with app.app_context():
    last_record = mongo.db['usd'].find().sort("effectiveDate",-1)[0]
    last_date = datetime.strptime(last_record["effectiveDate"], "%Y-%m-%d").date()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(logic.populate_db(last_date))
    loop.close()

