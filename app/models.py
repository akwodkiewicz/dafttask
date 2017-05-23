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

class CurrencyForm(FlaskForm):
    currency = SelectField('Currency', choices=[('usd','USD/PLN'), ('eur','EUR/PLN')])
    from_date = DateField('Start Date', format='%Y-%m-%d', validators=(validators.Optional(),))
    to_date = DateField('End Date', format='%Y-%m-%d', validators=(validators.Optional(),))
    submit = SubmitField('Submit')

class Record(object):
    def __init__():
        self.no = None
        self.effectiveDate = None
        self.bid = None
        self.ask = None