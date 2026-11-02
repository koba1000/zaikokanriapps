import csv
import io

from flask import Blueprint, Response, abort, flash, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import select

from app import audit
from app.authz import OWNER, ROLES, roles_required
from app.extensions import db
from app.inventory.forms import ItemForm, StockForm
from app.models import Item, StockLog, utcnow

bp = Blueprint("inventory", __name__)


def _csv_safe(value: str) -> str:
    """Excel等で数式として実行される先頭文字（CSVインジェクション）を無害化。"""
    return "'" + value if value.startswith(("=", "+", "-", "@")) else value


def _get_item(item_id: int) -> Item:
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    return item


@bp.route("/")
@roles_required(*ROLES)
def dashboard():  # type: ignore[no-untyped-def]
    items = db.session.scalars(select(Item).order_by(Item.name)).all()
    return render_template(
        "inventory/dashboard.html",
        items=items,
        form=StockForm(),
        low_count=sum(1 for i in items if i.needs_order),
    )


@bp.route("/items/<int:item_id>/stock", methods=["POST"])
@roles_required(*ROLES)
def update_stock(item_id: int):  # type: ignore[no-untyped-def]
    item = _get_item(item_id)
    form = StockForm()
    if form.validate_on_submit():
        db.session.add(
            StockLog(
                item_id=item.id,
                user_id=current_user.id,
                before=item.quantity,
                after=form.quantity.data,
            )
        )
        item.quantity = form.quantity.data
        audit.record("stock_update", str(item.id))
        db.session.commit()
    else:
        flash("数量が正しくありません", "error")
    return redirect(url_for("inventory.dashboard"))


@bp.route("/items/new", methods=["GET", "POST"])
@roles_required(OWNER)
def create_item():  # type: ignore[no-untyped-def]
    form = ItemForm()
    if form.validate_on_submit():
        item = Item()
        form.populate_obj(item)
        db.session.add(item)
        audit.record("item_create", form.name.data)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("登録できませんでした（品名が重複している可能性があります）", "error")
            return render_template("inventory/item_form.html", form=form, title="品目追加")
        return redirect(url_for("inventory.dashboard"))
    return render_template("inventory/item_form.html", form=form, title="品目追加")


@bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@roles_required(OWNER)
def edit_item(item_id: int):  # type: ignore[no-untyped-def]
    item = _get_item(item_id)
    form = ItemForm(obj=item)
    if form.validate_on_submit():
        form.populate_obj(item)
        audit.record("item_update", str(item.id))
        db.session.commit()
        return redirect(url_for("inventory.dashboard"))
    return render_template("inventory/item_form.html", form=form, title="品目編集")


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
@roles_required(OWNER)
def delete_item(item_id: int):  # type: ignore[no-untyped-def]
    item = _get_item(item_id)
    db.session.execute(StockLog.__table__.delete().where(StockLog.item_id == item.id))
    db.session.delete(item)
    audit.record("item_delete", str(item_id))
    db.session.commit()
    return redirect(url_for("inventory.dashboard"))


def _order_candidates() -> list[Item]:
    items = db.session.scalars(select(Item).order_by(Item.supplier, Item.name)).all()
    return [i for i in items if i.needs_order]


@bp.route("/orders")
@roles_required(*ROLES)
def orders():  # type: ignore[no-untyped-def]
    by_supplier: dict[str, list[Item]] = {}
    for item in _order_candidates():
        by_supplier.setdefault(item.supplier or "（仕入先未設定）", []).append(item)
    return render_template("inventory/orders.html", by_supplier=by_supplier)


@bp.route("/orders.csv")
@roles_required(*ROLES)
def orders_csv():  # type: ignore[no-untyped-def]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["仕入先", "品名", "発注量", "単位"])
    for item in _order_candidates():
        writer.writerow(
            [_csv_safe(item.supplier), _csv_safe(item.name), item.order_quantity, item.unit]
        )
    audit.record("orders_csv_export")
    db.session.commit()
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"},
    )


@bp.route("/orders/<int:item_id>/ordered", methods=["POST"])
@roles_required(*ROLES)
def mark_ordered(item_id: int):  # type: ignore[no-untyped-def]
    item = _get_item(item_id)
    item.last_ordered_at = utcnow()
    audit.record("order_marked", str(item.id))
    db.session.commit()
    return redirect(url_for("inventory.orders"))
