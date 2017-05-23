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


currency_dict = {
        'usd': 'USD/PLN',
        'eur': 'EUR/PLN',
        'chf': 'CHF/PLN',
        'gbp': 'GBP/PLN',
        'jpy': 'JPY/PLN'
        }

currency_list = [(k, v) for (k,v) in currency_dict.items()]

class CurrencyForm(FlaskForm):
    currency = SelectField('Currency', choices=currency_list)
    from_date = DateField('Start Date', format='%Y-%m-%d', validators=(validators.Optional(),))
    to_date = DateField('End Date', format='%Y-%m-%d', validators=(validators.Optional(),))
    #submit = SubmitField('Submit')

