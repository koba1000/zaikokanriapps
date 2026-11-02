import time
from datetime import timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import select

from app import audit
from app.auth.forms import ChangePasswordForm, LoginForm
from app.auth.passwords import (
    DUMMY_HASH,
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)
from app.authz import ROLES, public, roles_required
from app.extensions import db, limiter
from app.models import User, utcnow

bp = Blueprint("auth", __name__)

GENERIC_ERROR = "IDまたはパスワードが正しくありません"


def _failed(user: User | None, max_failures: int, lock_minutes: int) -> None:
    if user is not None:
        user.failed_count += 1
        if user.failed_count >= max_failures:
            user.locked_until = utcnow() + timedelta(minutes=lock_minutes)
            user.failed_count = 0
        audit.record("login_failed", str(user.id), user_id=user.id)
    else:
        audit.record("login_failed", "unknown")
    db.session.commit()
    flash(GENERIC_ERROR, "error")


@bp.route("/login", methods=["GET", "POST"])
@public
@limiter.limit("10 per minute", methods=["POST"])
def login():  # type: ignore[no-untyped-def]
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            select(User).filter_by(username=form.username.data)
        ).scalar_one_or_none()
        cfg = current_app.config
        if user is None:
            verify_password(DUMMY_HASH, form.password.data)
            _failed(None, cfg["LOGIN_MAX_FAILURES"], cfg["LOGIN_LOCK_MINUTES"])
        elif not user.active or (user.locked_until and user.locked_until > utcnow()):
            verify_password(DUMMY_HASH, form.password.data)
            _failed(None, cfg["LOGIN_MAX_FAILURES"], cfg["LOGIN_LOCK_MINUTES"])
        elif not verify_password(user.password_hash, form.password.data):
            _failed(user, cfg["LOGIN_MAX_FAILURES"], cfg["LOGIN_LOCK_MINUTES"])
        else:
            if needs_rehash(user.password_hash):
                user.password_hash = hash_password(form.password.data)
            user.failed_count = 0
            user.locked_until = None
            session.clear()  # セッション固定化対策
            login_user(user)
            session.permanent = True
            session["login_at"] = time.time()
            audit.record("login_ok", str(user.id), user_id=user.id)
            db.session.commit()
            return redirect(url_for("inventory.dashboard"))
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@roles_required(*ROLES)
def logout():  # type: ignore[no-untyped-def]
    audit.record("logout")
    db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/password", methods=["GET", "POST"])
@roles_required(*ROLES)
def change_password():  # type: ignore[no-untyped-def]
    form = ChangePasswordForm()
    if form.validate_on_submit():
        problem = validate_password(form.new_password.data, current_user.username)
        if not verify_password(current_user.password_hash, form.current_password.data):
            flash("現在のパスワードが正しくありません", "error")
        elif problem:
            flash(problem, "error")
        elif form.new_password.data == form.current_password.data:
            flash("現在と異なるパスワードにしてください", "error")
        else:
            current_user.password_hash = hash_password(form.new_password.data)
            current_user.must_change_password = False
            current_user.session_version += 1  # 他の全セッションを失効
            audit.record("password_changed")
            db.session.commit()
            logout_user()
            session.clear()
            flash("パスワードを変更しました。再ログインしてください", "info")
            return redirect(url_for("auth.login"))
    return render_template("auth/change_password.html", form=form)
