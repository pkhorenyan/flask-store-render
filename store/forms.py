from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email

class UserLoginForm(FlaskForm):
    email = StringField(label='Email:', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password:', validators=[DataRequired(), Length(min=3)])
    submit = SubmitField(label='Log In')

class RegisterForm(FlaskForm):
    name = StringField(label="Name:", validators=[DataRequired()])
    email = StringField(label="Email address:", validators=[DataRequired(), Email()])
    password = PasswordField(label="Password:", validators=[DataRequired(), Length(min=3)])
    submit = SubmitField(label="Register")