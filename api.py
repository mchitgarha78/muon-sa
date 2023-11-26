from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import secrets
import os
import logging

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'users.db')

app.config['SECRET_KEY'] = secrets.token_bytes(32)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)


with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Function to add users to the database
def add_user(username, password, user_type):
    with app.app_context():
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            new_user = User(username=username, password=password, user_type=user_type)
            db.session.add(new_user)
            db.session.commit()
        else:
            print(f"User with username '{username}' already exists.")

def remove_user(username):
    with app.app_context():
        user_to_remove = User.query.filter_by(username=username).first()
        if user_to_remove:
            db.session.delete(user_to_remove)
            db.session.commit()
            print(f"User with username '{username}' has been removed.")
        else:
            print(f"User with username '{username}' not found.")



class LoginForm:
    def __init__(self, username, password):
        self.username = username
        self.password = password

class LoginResource(Resource):
    def post(self):
        data = request.get_json()
        form = LoginForm(username=data.get('username'), password=data.get('password'))
        user = User.query.filter_by(username=form.username, password=form.password).first()
        if user:
            login_user(user)
            return jsonify({'message': f'Welcome, {user.username}!'}), 200
        else:
            return jsonify({'message': 'Login failed. Please check your username and password.'}), 401

class AppDeployment(Resource):
    @login_required
    def get(self):
        if current_user.user_type in ['admin', 'deployer']:
            return jsonify({'message': f'App deployed successfully'}), 200
        else:
            return jsonify({'message': f'You don\'t have the right access to deploy an app.'}), 400

class SignParams(Resource):
    @login_required
    def get(self):
        if current_user.user_type in ['deployer', 'admin', 'regular']:
            return jsonify({'message': f'Params signed successfully'}), 200
        else:
            return jsonify({'message': f'You don\'t have the right access to deploy an app.'}), 400

class AlterUser(Resource):
    @login_required
    def get(self):
        if current_user.user_type in 'admin':
            data = request.get_json()
            form = LoginForm(username=data.get('username'), password=data.get('password'))
            user = User.query.filter_by(username=form.username, password=form.password).first()
            return jsonify({'message': f'Params signed successfully'}), 200
        else:
            return jsonify({'message': f'You don\'t have the right access to deploy an app.'}), 400
    
class LogoutResource(Resource):
    @login_required
    def get(self):
        logout_user()
        return jsonify({'message': 'You have been logged out.'})

api = Api(app)
api.add_resource(LoginResource, '/login')
api.add_resource(AppDeployment, '/deploy')
api.add_resource(SignParams, '/sign_params')
api.add_resource(LogoutResource, '/logout')

