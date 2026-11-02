from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, TextAreaField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange

from app.authz import ROLES


class UserForm(FlaskForm):
    username = StringField("ID", validators=[DataRequired(), Length(min=3, max=64)])
    role = SelectField("ロール", choices=[(r, r) for r in ROLES])
    initial_password = StringField("初期パスワード", validators=[DataRequired(), Length(max=128)])


class EmployeeForm(FlaskForm):
    name = StringField("氏名", validators=[DataRequired(), Length(max=100)])
    address = TextAreaField("住所", validators=[DataRequired(), Length(max=300)])


class SaleForm(FlaskForm):
    day = DateField("日付", validators=[DataRequired()])
    amount = IntegerField(
        "売上（円）", validators=[InputRequired(), NumberRange(min=0, max=100_000_000)]
    )
