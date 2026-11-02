"""認可（RBAC）の宣言。

全ルートは @public か @roles_required のどちらかを必ず宣言する。
宣言のないルートは app/__init__.py の before_request が 403 で拒否する（デフォルト拒否）。
"""

from collections.abc import Callable
from typing import Any

F = Callable[..., Any]

OWNER = "owner"
STAFF = "staff"
ROLES = (OWNER, STAFF)


def public(view: F) -> F:
    view.is_public = True  # type: ignore[attr-defined]
    return view


def roles_required(*roles: str) -> Callable[[F], F]:
    unknown = set(roles) - set(ROLES)
    if unknown or not roles:
        raise ValueError(f"invalid roles: {roles}")

    def decorator(view: F) -> F:
        view.allowed_roles = frozenset(roles)  # type: ignore[attr-defined]
        return view

    return decorator
