from flask import Flask, render_template
import click
from flask_login import LoginManager, UserMixin, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
import sys
import os

# init
app = Flask(__name__)
app.config['SECRET_KEY'] = 'thisisasecretkey' # TODO 暂时没有dotenv配置
app.config['SQLALCHEMY_DATABASE_URI'] = ('sqlite:///' if sys.platform.startswith(
    'win') else 'sqlite:////') + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# login_manager = LoginManager(app)
# login_manager.login_view = 'login'

# database

# class User(db.Model,UserMixin):
#     id=db.Column(db.Integer,primary_key=True)
#     name=db.Column(db.String(32))
#     password_hash=db.Column(db.String(32))
    
#     def set_password(self,password):
#         self.password_hash=generate_password_hash(password)
    
#     def validate_password(self,password):
#         return check_password_hash(self.password_hash,password) 
    
# class Model(db.Model):
#     id=db.Column(db.Integer,primary_key=True)
#     name=db.Column(db.String(32))
#     description=db.Column(db.String(128))
    
    
#     def add_submission(self,submission):
#         pass
    
    

# class Submission(db.Model):
#     pass
    

# authentication

# error handlers

# routes


@app.route('/')
def index():
    return render_template('index.html')


'''
提交后，更新该模型提交记录
'''
@app.route('/submit', methods=['GET', 'POST'])
# @login_required
def submit():
    return render_template('submit.html')



@app.route('/detail/<int:model_id>')
# the detail page of a model
def model():
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
