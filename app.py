import json
import os
import secrets
import stripe
import b2sdk.v2 as b2

from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, session, flash, abort, current_app
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_msearch import Search
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_uploads import IMAGES, UploadSet, configure_uploads
from functools import wraps


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


class UserLoginForm(FlaskForm):
    email = StringField(label='Email:', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password:', validators=[DataRequired(), Length(min=3)])
    submit = SubmitField(label='Log In')

class RegisterForm(FlaskForm):
    name = StringField(label="Name:", validators=[DataRequired()])
    email = StringField(label="Email address:", validators=[DataRequired(), Email()])
    password = PasswordField(label="Password:", validators=[DataRequired(), Length(min=3)])
    submit = SubmitField(label="Register")


@app.route("/", methods=['GET', 'POST'])
def home():
    session.permanent = True
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", default=8, type=int)

    sort = request.args.get("sort", None, type=str)
    if sort:
        if sort == "Price: Low to High":
            all_products = Product.query.order_by(Product.price).paginate(page=page, per_page=per_page)
        elif sort == "Price: High to Low":
            all_products = Product.query.order_by(Product.price.desc()).paginate(page=page, per_page=per_page)
        elif sort == "Newest Arrivals":
            all_products = Product.query.order_by(Product.id.desc()).paginate(page=page, per_page=per_page)
        elif sort == "Out of Stock":
            all_products = Product.query.filter(Product.stock<1).paginate(page=page, per_page=per_page)
        return render_template("index.html", products=all_products, page=page, per_page=per_page, sort=sort)

    all_products = Product.query.order_by(Product.stock.desc()).paginate(page=page, per_page=per_page)

    return render_template("index.html", products=all_products, page=page, per_page=per_page, sort=sort)


login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def admin_only(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return function(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = UserLoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data
        user_name = User.query.filter_by(email=email).first()
        if not user_name:
            flash("Email does not exist.")
        elif not check_password_hash(user_name.password,password):
            flash("Password is incorrect.")
        else:
            login_user(user_name)
            return render_template('authsuccess.html'), {"Refresh": "2; url='/'"}
            # return redirect(url_for('home'))

    return render_template("login.html", form=login_form)

@app.route('/register', methods=["GET", "POST"])
def register():
    register_user_form = RegisterForm()
    if register_user_form.validate_on_submit():
        email = register_user_form.email.data
        user_name = User.query.filter_by(email=email).first()
        if user_name:
            flash(f"Please login with your email: {email}")
            return redirect(url_for('login'))
        else:
            password = generate_password_hash(register_user_form.password.data, method='pbkdf2:sha256', salt_length=8)

            new_user = User(name = register_user_form.name.data,
                            email = register_user_form.email.data,
                            password = password,
                            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))

    return render_template("register.html", form=register_user_form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/result")
def result():
    keyword = request.args.get("q")
    products = Product.query.msearch(keyword, fields=['name','description','pid'], limit=1000)
    return render_template("result.html", products=products, keyword=keyword)

@app.route("/product/<int:id>")
def show_product(id):
    requested_product = Product.query.get(id)
    return render_template("product.html", product=requested_product)

@app.route("/remove", methods=['GET', 'POST'])
@admin_only
def remove_product():
    product_id = request.args.get("id")
    requested_product = Product.query.get(product_id)
    if request.method == 'POST':
        db.session.delete(requested_product)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("delete.html", product=requested_product)

def upload_to_b2():
    file = str(secure_filename(request.files.get("img").filename))
    request.files.get("img").save(file)

    # Authenticate with Backblaze B2
    info = b2.InMemoryAccountInfo()
    b2_api = b2.B2Api(info)
    b2_api.authorize_account("production", APP_KEY_ID, APP_KEY)
    bucket_name = "render-com"
    bucket = b2_api.get_bucket_by_name(bucket_name)

    # Upload the file to Backblaze B2
    with open(file, "rb") as data:
        bucket.upload_bytes(data.read(), file)
    url = f'{b2_api.get_download_url_for_file_name(bucket_name, file)}'
    return url


@app.route("/edit_product", methods=['GET', 'POST'])
@admin_only
def edit_product():
    product_id = request.args.get("id")
    requested_product = Product.query.get(product_id)
    if request.method == 'POST':
        requested_product.name = request.form.get("name")
        requested_product.pid = request.form.get("pid")
        requested_product.description = request.form.get("description")
        requested_product.price = request.form.get("price")
        requested_product.stock = request.form.get("quantity")
        if request.files.get("img"):
            requested_product.img = upload_to_b2()

        db.session.commit()
        return render_template("product.html", product=requested_product)

    return render_template("edit.html", product=requested_product)

@app.route("/add_product", methods=['GET', 'POST'])
@admin_only
def add_product():
    if request.method == 'POST':
        if request.files.get("img"):
            img_path = upload_to_b2()

        new_product = Product(pid=request.form.get("pid"),name=request.form.get("name"), description=request.form.get("description"),
                              price=float(request.form.get("price")),
                              img=img_path, stock=request.form.get("quantity"))
        db.session.add(new_product)
        db.session.commit()
        product_id = new_product.id
        requested_product = Product.query.get(product_id)
        return render_template("product.html", product=requested_product)
    pid = secrets.randbits(30)
    return render_template("addproduct.html", pid=pid)


def merge_dicts(dict1,dict2):
    if isinstance(dict1,list) and isinstance(dict2, list):
        return dict1+dict2
    elif isinstance(dict1,dict) and isinstance(dict2,dict):
        return dict(list(dict1.items())+list(dict2.items()))
    return False

@app.route("/add-to-cart", methods=['POST'])
def add_to_cart():
    product_id = request.form.get("product_id")
    quantity = request.form.get("quantity")
    if product_id and quantity and request.method == 'POST':
        requested_product = Product.query.get(product_id)
        shopping_cart_items = {
            product_id: {
                "name": requested_product.name,
                "product_price": requested_product.price,
                "quantity": quantity,
                "img": requested_product.img,
                "pid": requested_product.pid,
            }
        }
        if 'ShoppingCart' in session:

            if product_id in session['ShoppingCart']:
                flash("This product is already in your cart", "error")
            else:
                session['ShoppingCart'] = merge_dicts(session['ShoppingCart'], shopping_cart_items)
            print(session['ShoppingCart'])
            return redirect(request.referrer)
        else:
            session['ShoppingCart'] = shopping_cart_items
            print(session['ShoppingCart'])
            return redirect(request.referrer)

@app.route("/cart", methods=['GET', 'POST'])
def cart():
    if 'ShoppingCart' not in session:
        return redirect(request.referrer)
    grandtotal = 0
    for key, product in session['ShoppingCart'].items():
        grandtotal += float(product['product_price'])*int(product['quantity'])
    grandtotal = "%.2f" % grandtotal
    return render_template('cart.html', grandtotal=grandtotal)

@app.route("/update_cart/<int:code>", methods=['POST'])
def update_cart(code):
    if 'ShoppingCart' not in session and len(session['ShoppingCart'])<=0:
        return redirect(url_for('home'))
    if request.method == "POST":
        quantity = request.form.get('quantity')
        try:
            session.modified = True
            for key, item in session['ShoppingCart'].items():
                if int(key) == code:
                    prd_id = Product.query.get(key)
                    if int(quantity) > prd_id.stock:
                        item['quantity'] = prd_id.stock
                        flash("This is a maximum amount of items in stock")
                    else:
                        item['quantity'] = quantity
                        flash("Item is updated")
                    return redirect(url_for("cart"))

        except Exception as e:
            print(e)
            return redirect(url_for("cart"))

@app.route("/delete_item/<int:id>", methods=['POST'])
def delete_item(id):
    if 'ShoppingCart' not in session and len(session['ShoppingCart'])<=0:
        return redirect(url_for('home'))
    try:
        session.modified = True
        for key, item in session['ShoppingCart'].items():
            if int(key) == id:
                session['ShoppingCart'].pop(key, None)
                return redirect(url_for("cart"))
    except Exception as e:
        print(e)
        return redirect(url_for("cart"))

@app.route("/information", methods=['POST'])
def information():
    if 'ShoppingCart' not in session and len(session['ShoppingCart'])<=0:
        return redirect(url_for('home'))

    return render_template("information.html")

@app.route("/checkout", methods=['POST'])
def checkout():

    invoice = secrets.token_hex(9)

    if 'ShoppingCart' not in session and len(session['ShoppingCart'])<=0:
        return redirect(url_for('home'))

    name = request.form.get('name')
    city = request.form.get('city')
    address = request.form.get('address')
    zipcode = request.form.get('zipcode')
    email = request.form.get('email')

    customer = {
        "name": name,
        "city": city,
        "address": address,
        "zipcode": zipcode,
        "email": email,
    }
    grandtotal = 0
    for key, item in session['ShoppingCart'].items():
        grandtotal += float(item['product_price']) * int(item['quantity'])
    grandtotal = "%.2f" % grandtotal

    new_order = CustomerOrder(invoice=invoice,
                              status='Pending',
                              orders=session['ShoppingCart'],
                              customer=customer,
                              date_created=datetime.now(),
                             )
    db.session.add(new_order)
    db.session.commit()

    return render_template("checkout.html", order=new_order, grandtotal=grandtotal)

@app.route("/clearcart")
def clear_cart():
    try:
        # session.clear()
        session.pop('ShoppingCart', None)
        return redirect(url_for('home'))
    except Exception as e:
        print(e)


@app.route("/create-checkout-session", methods=['GET','POST'])
def create_checkout_session():
    session = stripe.checkout.Session.create(
                line_items=[{
                  'price_data': {
                    'currency': 'usd',
                    'product_data': {
                      'name': 'Purchase',
                    },
                    'unit_amount': request.form.get('price'),
                  },
                  'quantity': 1,
                }],
                mode='payment',
                success_url='http://127.0.0.1:5000/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='https://example.com/cancel',
                )

    invoice = request.form.get('invoice')
    completed_order = CustomerOrder.query.filter_by(invoice=invoice).first()
    completed_order.status = 'Paid'
    db.session.commit()

    return redirect(session.url, code=303)

@app.route("/success")
def success():
    session.pop('ShoppingCart', None)
    session_stripe = stripe.checkout.Session.retrieve(request.args.get('session_id'))
    customer = stripe.Customer.retrieve(session_stripe.customer)
    return render_template("success.html", customer=customer), {"Refresh": "4; url='/'"}




if __name__ == '__main__':
    app.run(debug=True)


