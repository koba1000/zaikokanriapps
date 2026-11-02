from flask import current_app
from flask_login import current_user

from app.extensions import db
from app.models import AuditLog


def record(action: str, target: str = "", user_id: int | None = None) -> None:
    """監査ログ。呼び出し側の db.session.commit() と同一トランザクションで保存される。"""
    if user_id is None and current_user and current_user.is_authenticated:
        user_id = current_user.id
    db.session.add(AuditLog(user_id=user_id, action=action, target=str(target)))
    current_app.logger.info("audit action=%s target=%s user_id=%s", action, target, user_id)
