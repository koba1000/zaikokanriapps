from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange

QTY = [InputRequired(), NumberRange(min=0, max=100000)]


class ItemForm(FlaskForm):
    name = StringField("品名", validators=[DataRequired(), Length(max=100)])
    unit = StringField("単位", validators=[DataRequired(), Length(max=16)])
    quantity = DecimalField("現在庫", places=2, validators=QTY)
    reorder_point = DecimalField("発注点", places=2, validators=QTY)
    order_quantity = DecimalField("標準発注量", places=2, validators=QTY)
    supplier = StringField("仕入先", validators=[Length(max=100)])


class StockForm(FlaskForm):
    quantity = DecimalField("現在庫", places=2, validators=QTY)
