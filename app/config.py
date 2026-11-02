import os
from datetime import timedelta
from typing import Any


def _database_uri() -> str:
    uri = os.environ.get("DATABASE_URL", "")
    # Neon は postgresql:// を返すので psycopg3 ドライバ指定に正規化
    if uri.startswith("postgres://"):
        uri = "postgresql://" + uri[len("postgres://") :]
    if uri.startswith("postgresql://"):
        uri = "postgresql+psycopg://" + uri[len("postgresql://") :]
    return uri


def load_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "SECRET_KEY": os.environ.get("SECRET_KEY", ""),
        "ENCRYPTION_KEY": os.environ.get("ENCRYPTION_KEY", ""),
        "SQLALCHEMY_DATABASE_URI": _database_uri(),
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=30),  # アイドル期限
        "ABSOLUTE_SESSION_LIFETIME": timedelta(hours=12),  # 絶対期限
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "LOGIN_MAX_FAILURES": 5,
        "LOGIN_LOCK_MINUTES": 15,
        "RATELIMIT_STORAGE_URI": "memory://",
        "TESTING": False,
    }
    if overrides:
        cfg.update(overrides)
    if not cfg["TESTING"]:
        missing = [
            k for k in ("SECRET_KEY", "ENCRYPTION_KEY", "SQLALCHEMY_DATABASE_URI") if not cfg[k]
        ]
        if missing:
            raise RuntimeError(f"missing required settings: {missing}")
    return cfg
