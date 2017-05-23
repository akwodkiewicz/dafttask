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
    logic.update_db()
