# NBP Exchange Rates

This is a Flask web application that presents exchange rates of 5 currency pairs: 
- USD/PLN
- EUR/PLN 
- CHF/PLN 
- GBP/PLN 
- JPY/PLN

using the data avaliable from [NBP API](http://api.nbp.pl/) in form of a table and a graph (using [Plotly](https://plot.ly/)).

# Installation
1. Install [Docker](https://www.docker.com/)
2. Clone this repository
3. In repository's main directory execute :
    ```
    $ docker-compose up
    ```
    This command will build any missing images and run 2 containers: one with the MongoDB server and one with the Flask sever.
4. Access the app from [http://localhost:5000](http://localhost:5000).

   If you have troubles with connection check the IP address of your docker-machine by running:
    ``` $ docker-machine ip ``` and use the shown IP instead of the 'localhost'

**Important!** The Flask server will not start until it finishes updating the database. 
Be patient, it shouldn't take longer than 1 minute.

# Features
- [x] On startup: USD/PLN graph and table with data from the last 7 days 
- [x] 5 currency pairs to choose from
- [x] Adjustable time period
- [x] 3 views: graph+table / graph only / table only
- [x] Caching exchange rate records in the database (MongoDB)
- [x] Caching generated graphs in the database
- [x] *Clear database* option

**Additionally:**
- [x] User's choice is remembered when changing the webpage between */home*, */graph* and */table*
- [x] *Manual update* option
- [x] Information about the success/failure of the *manual update* and *delete* operations visible on the */delete* page

**What could be changed/added:**
- [ ] Changing the style of WTForms
- [ ] Daily automatic updates from the NBP
- [ ] Asynchronous behaviour when making a *manual update*
- [ ] In case of any response errors **on startup**: as many tries as needed until the database contains ***all*** the records
- [ ] More currencies (perhaps downloading all the possible pairs from NBP API)


# Additional information
The app tries to download all the necessary data from NBP servers on the first run.
Because the received responses are sometimes in a wrong mimetype or the connection errors might occur 
there is an option to force-update the database on the */delete* subpage by pressing the right button.
The errors are occurring probably due to *flooding* the api server with too many requests at once.

You can try to induce **more** errors and test the behaviour of the app 
by changing the constants ```TIMEOUT``` and ```SLEEP_TIME``` in ```app/models.py```

# Used technologies
- [Docker](https://www.docker.com/)
- [Python 3](https://www.python.org/)
- [Flask](flask.pocoo.org/)
- [Jinja2](http://jinja.pocoo.org/)
- [WTForms](https://wtforms.readthedocs.io/) + [Flask-WTForms](https://flask-wtf.readthedocs.io/en/stable/)
- [Plotly](https://plot.ly/python/)
- [MongoDB](https://www.mongodb.com/) + [PyMongo](https://api.mongodb.com/python/current/)
- [Bootstrap](http://getbootstrap.com)
