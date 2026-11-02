import click
from flask import Flask
from sqlalchemy import select

from app import crypto
from app.auth.passwords import hash_password, validate_password
from app.authz import OWNER
from app.extensions import db
from app.models import User


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        """テーブル作成（開発・初回用）。"""
        db.create_all()
        click.echo("tables created")

    @app.cli.command("create-owner")
    @click.argument("username")
    @click.password_option()
    def create_owner(username: str, password: str) -> None:
        """店長アカウントを作成（パスワードは対話入力。履歴・引数に残さない）。"""
        problem = validate_password(password, username)
        if problem:
            raise click.ClickException(problem)
        if db.session.scalar(select(User).filter_by(username=username)):
            raise click.ClickException("user already exists")
        db.session.add(
            User(
                username=username,
                role=OWNER,
                password_hash=hash_password(password),
                must_change_password=True,
            )
        )
        db.session.commit()
        click.echo("owner created")

    @app.cli.command("generate-key")
    def generate_key() -> None:
        """ENCRYPTION_KEY 用の鍵を生成して表示。"""
        click.echo(crypto.generate_key())
