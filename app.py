from flask import Flask
import click
from flask_login import LoginManager, login_required
from flask_sqlalchemy import SQLAlchemy
import sys
import os

# init
app = Flask(__name__)
app.config['SECRET_KEY'] = 'thisisasecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = ('sqlite:///' if sys.platform.startswith(
    'win') else 'sqlite:////') + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# database

# authentication

# error handlers

# routes


@app.route('/')
def index():
    pass


@app.route('/submit')
@login_required
def submit():
    pass

@app.route('/detail/<int:model_id>')
# the detail page of a model
def detail():
    pass


@app.route('/submission/<int:submission_id>')
# the detail page of a single submission
def submission():
    pass


@app.route('/login', methods=['GET', 'POST'])
def login():
    pass


if __name__ == '__main__':
    app.run(debug=True)
