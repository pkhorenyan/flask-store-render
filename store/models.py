import json
from store import db, UserMixin
from datetime import datetime, timedelta

class JsonEncodedDict(db.TypeDecorator):
    impl = db.Text
    def process_bind_param(self,value,dialect):
        if value is None:
            return '{}'
        else:
            return json.dumps(value)
    def process_result_value(self,value,dialect):
        if value is None:
            return {}
        else:
            return json.loads(value)
class Product(db.Model):
    __searchable__ = ['name','description','pid']
    id = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(2650))
    price = db.Column(db.Float(), nullable=False)
    img = db.Column(db.String(250), nullable=False)
    stock = db.Column(db.Integer, nullable=False)


class CustomerOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice = db.Column(db.String(30), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now(), nullable=False)
    customer = db.Column(JsonEncodedDict)
    orders = db.Column(JsonEncodedDict)
# db.create_all()

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
# db.create_all()