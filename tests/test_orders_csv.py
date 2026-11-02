import csv
import io

from app.extensions import db
from app.models import AuditLog, Item


def _rows(resp):
    return list(csv.reader(io.StringIO(resp.get_data(as_text=True))))


def test_orders_csv_contains_only_low_stock_items(staff):
    resp = staff.get("/orders.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    rows = _rows(resp)
    assert rows[0] == ["仕入先", "品名", "発注量", "単位"]
    assert rows[1:] == [["A商店", "コーヒー豆", "5.00", "kg"]]


def test_orders_csv_neutralizes_formula_injection(app, owner):
    with app.app_context():
        db.session.add(
            Item(
                name="=HYPERLINK(1)",
                unit="個",
                quantity=0,
                reorder_point=1,
                order_quantity=1,
                supplier="+cmd",
            )
        )
        db.session.commit()
    cells = [c for row in _rows(owner.get("/orders.csv"))[1:] for c in row]
    assert "'=HYPERLINK(1)" in cells
    assert "'+cmd" in cells
    assert not any(c.startswith(("=", "+", "-", "@")) for c in cells)


def test_orders_csv_export_is_audited(app, staff):
    staff.get("/orders.csv")
    with app.app_context():
        actions = [entry.action for entry in db.session.scalars(db.select(AuditLog))]
        assert "orders_csv_export" in actions
