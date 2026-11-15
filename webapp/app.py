"""
ShopTrack Pro — Web Interface (Flask).
Reuses the same database layer (database.py), business services (services.py)
and password hashing (auth.py) as the Tkinter desktop application.
"""

import csv
import io
import os
import secrets
import sys
from functools import wraps

from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import auth  # noqa: E402
import database  # noqa: E402
from services import BillingService, ProductService, ReportService  # noqa: E402

from helpers import (format_currency, paise_to_rupees_str, parse_int,  # noqa: E402
                     validate_product_data, validate_user_credentials)

app = Flask(__name__)
app.secret_key = os.environ.get("SHOPTRACK_SECRET_KEY") or secrets.token_hex(32)
app.jinja_env.filters["currency"] = format_currency
app.jinja_env.filters["rupees"] = paise_to_rupees_str

database.init_db()


# ============================================================
# Security helpers
# ============================================================
def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_forms():
    if request.method == "POST":
        token = request.form.get("_csrf", "")
        if not token or token != session.get("_csrf"):
            abort(400, "Invalid or missing form token. Please reload the page and try again.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not database.has_users():
            return redirect(url_for("setup"))
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"current_user": session.get("user"), "cart_count": len(session.get("cart", []))}


# ============================================================
# Authentication
# ============================================================
@app.route("/setup", methods=["GET", "POST"])
def setup():
    if database.has_users():
        return redirect(url_for("login"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        ok, err = validate_user_credentials(username, password)
        if ok and password != confirm:
            ok, err = False, "Passwords do not match."
        if not ok:
            flash(err, "error")
        else:
            pw_hash, salt = auth.hash_password(password)
            database.create_user(username, pw_hash, salt, "admin")
            flash("Administrator account created. Please sign in.", "success")
            return redirect(url_for("login"))
    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not database.has_users():
        return redirect(url_for("setup"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = database.get_user_by_username(username) if username else None
        if user and auth.verify_password(user["password_hash"], user["password_salt"], password):
            session.clear()
            session["user"] = {"id": user["id"], "username": user["username"], "role": user["role"]}
            session["cart"] = []
            next_url = request.args.get("next", "")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard")
            return redirect(next_url)
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


# ============================================================
# Dashboard
# ============================================================
@app.route("/")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        metrics=ReportService.get_dashboard_metrics(),
        low_stock=ReportService.get_low_stock_products(),
        top_selling=ReportService.get_top_selling_products(5),
        recent_bills=BillingService.get_all_bills()[:5],
    )


@app.route("/products/<int:product_id>/restock", methods=["POST"])
@login_required
def restock(product_id):
    qty = parse_int(request.form.get("quantity"), 0)
    if qty <= 0:
        flash("Restock quantity must be a positive whole number.", "error")
    elif ProductService.quick_restock(product_id, qty):
        flash(f"Added {qty} units to stock.", "success")
    else:
        flash("Product not found.", "error")
    return redirect(request.form.get("back") or url_for("dashboard"))


# ============================================================
# Products
# ============================================================
@app.route("/products")
@login_required
def products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "All")
    show_archived = request.args.get("archived") == "1"
    items = ProductService.get_products(include_inactive=show_archived, search_term=q or None, category=category)
    return render_template(
        "products.html",
        products=items,
        categories=ProductService.get_categories(),
        q=q,
        category=category,
        show_archived=show_archived,
    )


def _product_form(product=None):
    form = request.form
    if request.method == "POST":
        ok, err, data = validate_product_data(
            form.get("name"), form.get("category"), form.get("price"),
            form.get("quantity"), form.get("low_stock"),
        )
        if not ok:
            flash(err, "error")
        elif product:
            ProductService.update_product(product["id"], **data)
            flash(f"Updated '{data['name']}'.", "success")
            return redirect(url_for("products"))
        else:
            ProductService.add_product(**data)
            flash(f"Added '{data['name']}' to the catalog.", "success")
            return redirect(url_for("products"))
        values = form
    elif product:
        values = {
            "name": product["name"],
            "category": product["category"],
            "price": paise_to_rupees_str(product["price_minor"]),
            "quantity": product["quantity"],
            "low_stock": product["low_stock"],
        }
    else:
        values = {"low_stock": 10}
    return render_template("product_form.html", product=product, values=values,
                           categories=ProductService.get_categories())


@app.route("/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    return _product_form()


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(product_id):
    product = ProductService.get_product_by_id(product_id)
    if not product:
        abort(404)
    return _product_form(product)


@app.route("/products/<int:product_id>/archive", methods=["POST"])
@login_required
def product_archive(product_id):
    if ProductService.deactivate_product(product_id):
        flash("Product archived. It is hidden from billing but kept in sales history.", "success")
    return redirect(url_for("products"))


@app.route("/products/<int:product_id>/restore", methods=["POST"])
@login_required
def product_restore(product_id):
    if ProductService.restore_product(product_id):
        flash("Product restored to the active catalog.", "success")
    return redirect(url_for("products", archived=1))


# ============================================================
# Billing
# ============================================================
def _cart_lines():
    lines, total = [], 0
    for item in session.get("cart", []):
        product = ProductService.get_product_by_id(item["product_id"])
        if not product:
            continue
        line_total = product["price_minor"] * item["quantity"]
        total += line_total
        lines.append({"product": product, "quantity": item["quantity"], "line_total": line_total})
    return lines, total


@app.route("/billing")
@login_required
def billing():
    lines, total = _cart_lines()
    return render_template("billing.html", products=ProductService.get_products(),
                           lines=lines, total=total, customer=session.get("customer", ""))


@app.route("/billing/add", methods=["POST"])
@login_required
def billing_add():
    product = ProductService.get_product_by_id(parse_int(request.form.get("product_id"), 0))
    qty = parse_int(request.form.get("quantity"), 0)
    session["customer"] = request.form.get("customer", session.get("customer", "")).strip()
    if not product or not product["active"]:
        flash("Please select a valid product.", "error")
        return redirect(url_for("billing"))
    if qty <= 0:
        flash("Quantity must be greater than zero.", "error")
        return redirect(url_for("billing"))

    cart = session.get("cart", [])
    existing = next((c for c in cart if c["product_id"] == product["id"]), None)
    new_qty = qty + (existing["quantity"] if existing else 0)
    if new_qty > product["quantity"]:
        flash(f"Insufficient stock for '{product['name']}'. Available: {product['quantity']}, in cart: {new_qty}.", "error")
        return redirect(url_for("billing"))
    if existing:
        existing["quantity"] = new_qty
    else:
        cart.append({"product_id": product["id"], "quantity": qty})
    session["cart"] = cart
    return redirect(url_for("billing"))


@app.route("/billing/remove/<int:product_id>", methods=["POST"])
@login_required
def billing_remove(product_id):
    session["cart"] = [c for c in session.get("cart", []) if c["product_id"] != product_id]
    return redirect(url_for("billing"))


@app.route("/billing/clear", methods=["POST"])
@login_required
def billing_clear():
    session["cart"] = []
    session["customer"] = ""
    return redirect(url_for("billing"))


@app.route("/billing/checkout", methods=["POST"])
@login_required
def billing_checkout():
    customer = request.form.get("customer", "").strip()
    session["customer"] = customer
    try:
        bill_id, total = BillingService.process_checkout(customer, session.get("cart", []))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("billing"))
    session["cart"] = []
    session["customer"] = ""
    flash(f"Invoice #{bill_id} generated for {format_currency(total)}.", "success")
    return redirect(url_for("sale_detail", bill_id=bill_id))


# ============================================================
# Sales & Reports
# ============================================================
@app.route("/sales")
@login_required
def sales():
    q = request.args.get("q", "").strip()
    return render_template("sales.html", bills=BillingService.get_all_bills(q or None), q=q)


@app.route("/sales/<int:bill_id>")
@login_required
def sale_detail(bill_id):
    bill = BillingService.get_bill_by_id(bill_id)
    if not bill:
        abort(404)
    return render_template("invoice.html", bill=bill, items=BillingService.get_bill_items(bill_id))


@app.route("/reports")
@login_required
def reports():
    return render_template(
        "reports.html",
        metrics=ReportService.get_dashboard_metrics(),
        top_selling=ReportService.get_top_selling_products(10),
        categories=ReportService.get_category_valuation(),
        low_stock=ReportService.get_low_stock_products(),
    )


def _csv_response(filename, header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.route("/export/products.csv")
@login_required
def export_products():
    rows = [
        (p["id"], p["name"], p["category"], paise_to_rupees_str(p["price_minor"]), p["quantity"],
         p["low_stock"], "Active" if p["active"] else "Archived")
        for p in ProductService.get_products(include_inactive=True)
    ]
    return _csv_response("products.csv",
                         ["ID", "Name", "Category", "Price", "Quantity", "Low Stock Threshold", "Status"], rows)


@app.route("/export/sales.csv")
@login_required
def export_sales():
    rows = [(b["id"], b["customer"], paise_to_rupees_str(b["total_minor"]), b["created_at"])
            for b in BillingService.get_all_bills()]
    return _csv_response("sales.csv", ["Bill ID", "Customer", "Total", "Date"], rows)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
