"""認可ハーネス: 全ルートを列挙して、宣言漏れ・ロール逸脱を機械的に検出する。

AI が新しいルートを足しても、宣言がなければこのテストが落ちる。
"""

import pytest
from flask import url_for

from tests.conftest import login, make_app

SKIP = {"static"}


def _rules(app):
    return [r for r in app.url_map.iter_rules() if r.endpoint not in SKIP]


def _url(app, rule):
    with app.test_request_context():
        return url_for(rule.endpoint, **{a: 1 for a in rule.arguments})


def _methods(rule):
    return sorted(rule.methods - {"HEAD", "OPTIONS"})


def test_every_route_declares_access(app):
    for rule in _rules(app):
        view = app.view_functions[rule.endpoint]
        assert getattr(view, "is_public", False) or getattr(view, "allowed_roles", None), (
            f"{rule.endpoint} に @public / @roles_required の宣言がありません"
        )


def test_public_routes_are_allowlisted(app):
    public = {
        r.endpoint
        for r in _rules(app)
        if getattr(app.view_functions[r.endpoint], "is_public", False)
    }
    assert public == {"auth.login", "healthz"}


def test_anonymous_cannot_access_protected_routes(app):
    client = app.test_client()
    for rule in _rules(app):
        view = app.view_functions[rule.endpoint]
        if getattr(view, "is_public", False):
            continue
        for method in _methods(rule):
            resp = client.open(_url(app, rule), method=method)
            assert resp.status_code in (302, 401), f"{method} {rule.rule} -> {resp.status_code}"
            if resp.status_code == 302:
                assert "/login" in resp.headers["Location"]


def test_staff_forbidden_from_owner_only_routes(app, employee_id):
    client = app.test_client()
    login(client, "staff1")
    checked = 0
    for rule in _rules(app):
        roles = getattr(app.view_functions[rule.endpoint], "allowed_roles", None)
        if roles and "staff" not in roles:
            for method in _methods(rule):
                resp = client.open(_url(app, rule), method=method)
                assert resp.status_code == 403, f"{method} {rule.rule} -> {resp.status_code}"
                checked += 1
    assert checked >= 10


@pytest.mark.parametrize(
    "path", ["/admin/sales", "/admin/employees", "/admin/users", "/admin/audit"]
)
def test_staff_direct_url_is_403(staff, path):
    assert staff.get(path).status_code == 403


def test_undeclared_route_is_denied_by_default():
    app = make_app()

    @app.route("/oops")
    def oops():
        return "secret"

    client = app.test_client()
    login(client, "staff1")
    assert client.get("/oops").status_code == 403
