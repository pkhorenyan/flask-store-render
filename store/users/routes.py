from store.forms import UserLoginForm, RegisterForm
from store.models import User
from store import app, db

from flask import render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user


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