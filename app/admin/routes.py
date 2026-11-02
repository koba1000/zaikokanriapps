"""店長（owner）専用。ブループリント内の全ルートが OWNER 限定。"""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import select

from app import audit, crypto
from app.admin.forms import EmployeeForm, SaleForm, UserForm
from app.auth.passwords import hash_password, validate_password
from app.authz import OWNER, roles_required
from app.extensions import db
from app.models import AuditLog, Employee, Sale, User

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users", methods=["GET", "POST"])
@roles_required(OWNER)
def users():  # type: ignore[no-untyped-def]
    form = UserForm()
    if form.validate_on_submit():
        problem = validate_password(form.initial_password.data, form.username.data)
        exists = db.session.scalar(select(User).filter_by(username=form.username.data))
        if problem:
            flash(problem, "error")
        elif exists:
            flash("そのIDは使用済みです", "error")
        else:
            db.session.add(
                User(
                    username=form.username.data,
                    role=form.role.data,
                    password_hash=hash_password(form.initial_password.data),
                    must_change_password=True,
                )
            )
            audit.record("user_create", form.username.data)
            db.session.commit()
            return redirect(url_for("admin.users"))
    all_users = db.session.scalars(select(User).order_by(User.username)).all()
    return render_template("admin/users.html", form=form, users=all_users)


@bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@roles_required(OWNER)
def deactivate_user(user_id: int):  # type: ignore[no-untyped-def]
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash("自分自身は無効化できません", "error")
    else:
        user.active = False
        user.session_version += 1
        audit.record("user_deactivate", str(user.id))
        db.session.commit()
    return redirect(url_for("admin.users"))


@bp.route("/employees", methods=["GET", "POST"])
@roles_required(OWNER)
def employees():  # type: ignore[no-untyped-def]
    form = EmployeeForm()
    if form.validate_on_submit():
        db.session.add(
            Employee(
                name=form.name.data,
                address_encrypted=crypto.encrypt(form.address.data),
            )
        )
        db.session.flush()
        audit.record("employee_create")
        db.session.commit()
        return redirect(url_for("admin.employees"))
    rows = db.session.scalars(select(Employee).order_by(Employee.name)).all()
    return render_template("admin/employees.html", form=form, employees=rows)


@bp.route("/employees/<int:employee_id>")
@roles_required(OWNER)
def employee_detail(employee_id: int):  # type: ignore[no-untyped-def]
    employee = db.session.get(Employee, employee_id)
    if employee is None:
        abort(404)
    audit.record("employee_address_view", str(employee.id))
    db.session.commit()
    address = crypto.decrypt(employee.address_encrypted)
    return render_template("admin/employee_detail.html", employee=employee, address=address)


@bp.route("/sales", methods=["GET", "POST"])
@roles_required(OWNER)
def sales():  # type: ignore[no-untyped-def]
    form = SaleForm()
    if form.validate_on_submit():
        sale = db.session.scalar(select(Sale).filter_by(day=form.day.data))
        if sale is None:
            db.session.add(Sale(day=form.day.data, amount=form.amount.data))
        else:
            sale.amount = form.amount.data
        audit.record("sale_upsert", str(form.day.data))
        db.session.commit()
        return redirect(url_for("admin.sales"))
    audit.record("sales_view")
    db.session.commit()
    rows = db.session.scalars(select(Sale).order_by(Sale.day.desc()).limit(60)).all()
    return render_template("admin/sales.html", form=form, sales=rows)


@bp.route("/audit")
@roles_required(OWNER)
def audit_log():  # type: ignore[no-untyped-def]
    rows = db.session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200)).all()
    return render_template("admin/audit.html", logs=rows)
