import time
from typing import Any

from flask import Flask, abort, redirect, request, session, url_for
from flask_login import current_user, logout_user
from flask_talisman import Talisman

from app.authz import public
from app.config import load_config
from app.extensions import csrf, db, limiter, login_manager
from app.models import User


def create_app(overrides: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(load_config(overrides))
    testing = bool(app.config["TESTING"])

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    Talisman(
        app,
        force_https=not testing,
        session_cookie_secure=not testing,
        content_security_policy={"default-src": "'self'", "frame-ancestors": "'none'"},
        referrer_policy="same-origin",
    )

    @login_manager.user_loader
    def load_user(session_id: str) -> User | None:
        try:
            user_id, version = (int(p) for p in session_id.split(":"))
        except ValueError:
            return None
        user = db.session.get(User, user_id)
        if user is None or not user.active or user.session_version != version:
            return None
        return user

    from app.admin.routes import bp as admin_bp
    from app.auth.routes import bp as auth_bp
    from app.inventory.routes import bp as inventory_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(admin_bp)

    @app.route("/healthz")
    @public
    def healthz() -> str:
        return "ok"

    @app.before_request
    def enforce_access() -> Any:
        """デフォルト拒否。認証 → セッション期限 → ロール → パスワード変更強制 の順に検査。"""
        endpoint = request.endpoint
        if endpoint is None or endpoint == "static":
            return None
        view = app.view_functions[endpoint]
        if getattr(view, "is_public", False):
            return None
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        login_at = session.get("login_at")
        max_age = app.config["ABSOLUTE_SESSION_LIFETIME"].total_seconds()
        if login_at is None or time.time() - login_at > max_age:
            logout_user()
            session.clear()
            return redirect(url_for("auth.login"))
        roles = getattr(view, "allowed_roles", None)
        if not roles or current_user.role not in roles:
            abort(403)
        if current_user.must_change_password and endpoint not in (
            "auth.change_password",
            "auth.logout",
        ):
            return redirect(url_for("auth.change_password"))
        return None

    @app.after_request
    def no_store(response):  # type: ignore[no-untyped-def]
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(403)
    def forbidden(_e):  # type: ignore[no-untyped-def]
        return "403 権限がありません", 403

    from app.cli import register_cli

    register_cli(app)
    return app
