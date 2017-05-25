from datetime import timedelta, date
from flask_wtf import FlaskForm
from wtforms import (
    TextField, 
    BooleanField, 
    DecimalField, 
    SubmitField, 
    SelectField, 
    DateField,
    validators 
    )

### Constants
URL = 'http://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{startDate}/{endDate}/?format=json'
TABLE_TYPE = 'A'
START_DATE = date(2002, 1, 1)
END_DATE = date.today()
DELTA = 93
CURRENCY_DICT = {
        'usd': 'USD/PLN',
        'eur': 'EUR/PLN',
        'chf': 'CHF/PLN',
        'gbp': 'GBP/PLN',
        'jpy': 'JPY/PLN'
        }
CURRENCY_LIST = [(k, v) for (k,v) in CURRENCY_DICT.items()]
SLEEP_TIME = 1

class CurrencyForm(FlaskForm):
    currency = SelectField('Currency', choices=CURRENCY_LIST)
    from_date = DateField('Start Date', format='%Y-%m-%d', validators=(validators.Optional(),))
    to_date = DateField('End Date', format='%Y-%m-%d', validators=(validators.Optional(),))
    #submit = SubmitField('Submit')

class Previous(object):
    def __init__(self, start, end, currency):
        self.start = start
        self.end = end
        self.currency = currency
    def update(self, start, end, currency):
        self.start = start
        self.end = end
        self.currency = currency
