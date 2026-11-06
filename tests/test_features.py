from decimal import Decimal

from app import crypto
from app.extensions import db
from app.models import AuditLog, Employee, Item, PurchaseOrder, StockLog
from tests.conftest import login


def test_low_stock_highlighted_and_ordered(owner):
    html = owner.get("/").get_data(as_text=True)
    assert "要発注" in html
    orders = owner.get("/orders").get_data(as_text=True)
    assert "コーヒー豆" in orders and "牛乳" not in orders


def test_staff_updates_stock_with_history(app, staff):
    with app.app_context():
        item_id = db.session.scalar(db.select(Item.id).filter_by(name="コーヒー豆"))
    assert staff.post(f"/items/{item_id}/stock", data={"quantity": "8"}).status_code == 302
    with app.app_context():
        assert db.session.get(Item, item_id).quantity == Decimal("8")
        log = db.session.scalar(db.select(StockLog))
        assert log.before == Decimal("1") and log.after == Decimal("8")
    assert "コーヒー豆" not in staff.get("/orders").get_data(as_text=True)


def test_zero_stock_is_accepted(app, staff):
    staff.post("/items/1/stock", data={"quantity": "0"})
    with app.app_context():
        assert db.session.get(Item, 1).quantity == Decimal("0")


def test_negative_or_invalid_quantity_rejected(app, staff):
    for bad in ("-1", "abc", "999999999"):
        staff.post("/items/1/stock", data={"quantity": bad})
    with app.app_context():
        assert db.session.get(Item, 1).quantity == Decimal("1")


def test_staff_cannot_create_or_delete_items(staff):
    assert staff.post("/items/new", data={"name": "x"}).status_code == 403
    assert staff.post("/items/1/delete").status_code == 403


def test_owner_creates_item(app, owner):
    resp = owner.post(
        "/items/new",
        data={
            "name": "砂糖",
            "unit": "kg",
            "quantity": "3",
            "reorder_point": "1",
            "order_quantity": "2",
            "supplier": "C",
        },
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.scalar(db.select(Item).filter_by(name="砂糖")) is not None


def test_item_name_is_escaped(app, owner):
    owner.post(
        "/items/new",
        data={
            "name": "<script>alert(1)</script>",
            "unit": "個",
            "quantity": "1",
            "reorder_point": "0",
            "order_quantity": "1",
            "supplier": "",
        },
    )
    html = owner.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_unknown_item_404(owner):
    assert owner.post("/items/9999/stock", data={"quantity": "1"}).status_code == 404


def test_address_encrypted_at_rest_and_view_audited(app, owner, employee_id):
    with app.app_context():
        raw = db.session.get(Employee, employee_id).address_encrypted
        assert "千代田".encode() not in raw
    assert "東京都千代田区1-1" in owner.get(f"/admin/employees/{employee_id}").get_data(
        as_text=True
    )
    with app.app_context():
        actions = [entry.action for entry in db.session.scalars(db.select(AuditLog))]
        assert "employee_address_view" in actions


def test_address_not_in_employee_list(owner, employee_id):
    owner.get(f"/admin/employees/{employee_id}")
    assert "千代田" not in owner.get("/admin/employees").get_data(as_text=True)


def test_crypto_roundtrip_and_tamper(app):
    import pytest

    with app.app_context():
        token = crypto.encrypt("秘密")
        assert crypto.decrypt(token) == "秘密"
        with pytest.raises(crypto.DecryptionError):
            crypto.decrypt(token[:-1] + bytes([token[-1] ^ 1]))


def test_owner_sales_and_user_management(app, owner):
    assert (
        owner.post("/admin/sales", data={"day": "2026-11-01", "amount": "50000"}).status_code == 302
    )
    sales_page = owner.get("/admin/sales").get_data(as_text=True)
    assert "50,000" in sales_page
    assert "日別合計" in sales_page and "会計・税計算・返金には対応していません" in sales_page
    weak = owner.post(
        "/admin/users", data={"username": "new1", "role": "staff", "initial_password": "short"}
    )
    assert "12文字以上" in weak.get_data(as_text=True)
    ok = owner.post(
        "/admin/users",
        data={"username": "new1", "role": "staff", "initial_password": "Initial-Pass-2026"},
    )
    assert ok.status_code == 302
    assert "new1" in owner.get("/admin/users").get_data(as_text=True)
    assert owner.get("/admin/audit").status_code == 200


def test_deactivated_user_session_revoked(app, owner):
    staff_client = app.test_client()
    login(staff_client, "staff1")
    with app.app_context():
        from app.models import User

        sid = db.session.scalar(db.select(User.id).filter_by(username="staff1"))
    owner.post(f"/admin/users/{sid}/deactivate")
    assert staff_client.get("/").status_code == 302


def test_order_record_stops_duplicate_candidates_until_received(app, staff):
    with app.app_context():
        item = db.session.scalar(db.select(Item).filter_by(name="コーヒー豆"))
        item_id = item.id
        initial_quantity = item.quantity

    assert staff.post(f"/orders/{item_id}/ordered").status_code == 302
    assert staff.post(f"/orders/{item_id}/ordered").status_code == 302
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(PurchaseOrder.id))) == 1
    page = staff.get("/orders").get_data(as_text=True)
    candidates = page.split("新たな発注候補", 1)[1]
    assert "コーヒー豆" not in candidates
    assert page.count("コーヒー豆") == 2
    assert "発注中" in page
    assert "入荷済みにしても在庫数は自動で変わりません" in page

    with app.app_context():
        order = db.session.scalar(db.select(PurchaseOrder))
        order_id = order.id
        assert order.quantity == Decimal("5")
        assert order.item_name == "コーヒー豆"
        assert order.supplier == "A商店"
        assert order.unit == "kg"

    assert staff.post(f"/orders/{order_id}/receive").status_code == 302
    with app.app_context():
        assert db.session.get(Item, item_id).quantity == initial_quantity
        assert db.session.get(PurchaseOrder, order_id).status == "received"
    history = staff.get("/orders").get_data(as_text=True)
    assert "コーヒー豆" in history
    assert "入荷済み" in history


def test_cancelling_order_returns_item_to_candidates(app, owner):
    with app.app_context():
        item_id = db.session.scalar(db.select(Item.id).filter_by(name="コーヒー豆"))
    owner.post(f"/orders/{item_id}/ordered")

    with app.app_context():
        order_id = db.session.scalar(db.select(PurchaseOrder.id))
    assert owner.post(f"/orders/{order_id}/cancel").status_code == 302
    with app.app_context():
        assert db.session.get(PurchaseOrder, order_id).status == "cancelled"
    assert "コーヒー豆" in owner.get("/orders").get_data(as_text=True)


def test_order_transition_rejects_unknown_order(owner):
    assert owner.post("/orders/9999/receive").status_code == 404


def test_item_with_order_history_cannot_be_deleted(app, owner):
    with app.app_context():
        item_id = db.session.scalar(db.select(Item.id).filter_by(name="コーヒー豆"))
    assert owner.post(f"/orders/{item_id}/ordered").status_code == 302

    assert owner.post(f"/items/{item_id}/delete").status_code == 302
    with app.app_context():
        assert db.session.get(Item, item_id) is not None
