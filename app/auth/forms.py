from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length


class LoginForm(FlaskForm):
    username = StringField("ID", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("パスワード", validators=[DataRequired(), Length(max=128)])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "現在のパスワード", validators=[DataRequired(), Length(max=128)]
    )
    new_password = PasswordField("新しいパスワード", validators=[DataRequired(), Length(max=128)])
    confirm = PasswordField(
        "新しいパスワード（確認）",
        validators=[DataRequired(), EqualTo("new_password", message="一致しません")],
    )
