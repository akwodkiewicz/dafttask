from flask import Flask
from flask_pymongo import PyMongo

app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'main_db'
app.config['MONGO_URI'] = 'mongodb://database/main_db'

mongo = PyMongo(app)

from app import views


