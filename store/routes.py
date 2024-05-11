import secrets
import stripe
from datetime import datetime

from flask import render_template, redirect, url_for, request, session, flash

from store import app, db
from store.models import Product, CustomerOrder


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

@app.route("/result")
def result():
    keyword = request.args.get("q")
    products = Product.query.msearch(keyword, fields=['name','description','pid'], limit=1000)
    return render_template("result.html", products=products, keyword=keyword)

@app.route("/product/<int:id>")
def show_product(id):
    requested_product = Product.query.get(id)
    return render_template("product.html", product=requested_product)

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