import base64
import os

import pytest

from app import create_app
from app.auth.passwords import hash_password
from app.extensions import db
from app.models import Employee, Item, User

PASSWORD = "Correct-Horse-9"


def make_app(csrf: bool = False):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "ENCRYPTION_KEY": base64.b64encode(os.urandom(32)).decode(),
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": csrf,
            "RATELIMIT_ENABLED": False,
            "SESSION_COOKIE_SECURE": False,
        }
    )
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                User(
                    username="owner1",
                    role="owner",
                    password_hash=hash_password(PASSWORD),
                    must_change_password=False,
                ),
                User(
                    username="staff1",
                    role="staff",
                    password_hash=hash_password(PASSWORD),
                    must_change_password=False,
                ),
                User(
                    username="newbie",
                    role="staff",
                    password_hash=hash_password(PASSWORD),
                    must_change_password=True,
                ),
                Item(
                    name="コーヒー豆",
                    unit="kg",
                    quantity=1,
                    reorder_point=2,
                    order_quantity=5,
                    supplier="A商店",
                ),
                Item(
                    name="牛乳",
                    unit="本",
                    quantity=10,
                    reorder_point=3,
                    order_quantity=12,
                    supplier="B乳業",
                ),
            ]
        )
        db.session.commit()
    return app


@pytest.fixture()
def app():
    return make_app()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username, password=PASSWORD):
    return client.post("/login", data={"username": username, "password": password})


@pytest.fixture()
def owner(client):
    login(client, "owner1")
    return client


@pytest.fixture()
def staff(client):
    login(client, "staff1")
    return client


@pytest.fixture()
def employee_id(app):
    from app import crypto

    with app.app_context():
        e = Employee(name="山田", address_encrypted=crypto.encrypt("東京都千代田区1-1"))
        db.session.add(e)
        db.session.commit()
        return e.id
