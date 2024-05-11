import os
import stripe

from datetime import timedelta
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_msearch import Search
from flask_login import LoginManager
from flask_uploads import IMAGES, UploadSet, configure_uploads

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ["SECRET_KEY"]
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ["DATABASE_URL"].replace('postgres://', 'postgresql://')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

APP_KEY_ID = os.environ["APP_KEY_ID"]
APP_KEY = os.environ["APP_KEY"]

app.config['UPLOADED_PHOTOS_DEST'] = os.path.normpath(os.path.join(basedir, 'static/product_images/'))
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

stripe.api_key = os.environ["STRIPE"]

db = SQLAlchemy(app)
search = Search()
search.init_app(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

from admin import routes
from users import routes
from store import routes