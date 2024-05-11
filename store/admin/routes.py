import secrets
import b2sdk.v2 as b2

from flask import render_template, redirect, url_for, request, abort
from werkzeug.utils import secure_filename
from flask_login import current_user
from functools import wraps

from store.models import Product, User
from store import APP_KEY, APP_KEY_ID, app, db, login_manager

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