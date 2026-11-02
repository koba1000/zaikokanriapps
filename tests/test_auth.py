from app.extensions import db
from app.models import AuditLog, User
from tests.conftest import PASSWORD, login, make_app


def test_login_success_and_dashboard(client):
    resp = login(client, "owner1")
    assert resp.status_code == 302
    assert "毎朝の在庫確認" in client.get("/").get_data(as_text=True)


def test_login_failure_is_generic(client):
    a = login(client, "owner1", "wrong-password-xx").get_data(as_text=True)
    b = login(client, "nobody", "wrong-password-xx").get_data(as_text=True)
    assert "IDまたはパスワードが正しくありません" in a
    assert "IDまたはパスワードが正しくありません" in b


def test_lockout_after_repeated_failures(app, client):
    for _ in range(5):
        login(client, "staff1", "bad-password-123")
    assert login(client, "staff1", PASSWORD).status_code == 200  # ロック中は正しいPWでも失敗


def test_open_redirect_ignored(client):
    resp = client.post(
        "/login?next=https://evil.example", data={"username": "owner1", "password": PASSWORD}
    )
    assert "evil.example" not in resp.headers["Location"]


def test_must_change_password_is_forced(client):
    login(client, "newbie")
    resp = client.get("/")
    assert resp.status_code == 302 and "/password" in resp.headers["Location"]


def test_password_change_policy_and_session_revocation(app):
    c1, c2 = app.test_client(), app.test_client()
    login(c1, "staff1")
    login(c2, "staff1")
    weak = c1.post(
        "/password",
        data={"current_password": PASSWORD, "new_password": "short", "confirm": "short"},
    )
    assert "12文字以上" in weak.get_data(as_text=True)
    ok = c1.post(
        "/password",
        data={
            "current_password": PASSWORD,
            "new_password": "Another-Strong-Pw-77",
            "confirm": "Another-Strong-Pw-77",
        },
    )
    assert ok.status_code == 302
    assert c2.get("/").status_code == 302  # 他セッションは失効


def test_password_is_hashed_with_argon2(app):
    with app.app_context():
        u = db.session.scalar(db.select(User).filter_by(username="owner1"))
        assert u.password_hash.startswith("$argon2")


def test_login_is_audited_without_password(app, client):
    login(client, "owner1")
    with app.app_context():
        logs = db.session.scalars(db.select(AuditLog)).all()
        assert any(entry.action == "login_ok" for entry in logs)
        assert all(PASSWORD not in (entry.target or "") for entry in logs)


def test_csrf_enforced():
    app = make_app(csrf=True)
    resp = app.test_client().post("/login", data={"username": "owner1", "password": PASSWORD})
    assert resp.status_code == 400


def test_security_headers(client):
    resp = client.get("/login")
    assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Cache-Control"] == "no-store"


def test_healthz_public(client):
    assert client.get("/healthz").get_data(as_text=True) == "ok"
