# 🏪 ShopTrack Pro — Store & Inventory Management System (v2)

A desktop Graphical User Interface (GUI) application built with **Python**, **Tkinter**, and **SQLite**. Designed for retail shops and small businesses to manage catalog products, track real-time stock levels, generate customer invoices, view past sales records, and monitor inventory analytics.

---

## 🌟 Key Features & Engineering Safeguards

1. **Financial Precision (Minor Units)**
   - All prices and monetary amounts are stored as **integer minor units (paise/cents)** in SQLite.
   - Eliminates IEEE 754 floating-point rounding errors (e.g. `19.99 * 3 = 59.970000000000006`).
   - Clean decimal conversion at presentation boundary (`utils.py`).

2. **Decoupled Architecture (`services.py`)**
   - Clean 3-tier Layered Architecture: UI Frames (`gui/`) ➔ Business Services (`services.py`) ➔ Database Access (`database.py`).
   - UI components never execute raw SQL statements directly.

3. **Atomic Billing Transactions & Concurrency Safety**
   - Billing transactions query live database prices and stock levels inside the transaction.
   - Executes conditional updates: `UPDATE products SET quantity = quantity - ? WHERE id = ? AND active = 1 AND quantity >= ?`.
   - Confirms `rowcount == 1` per line item. If stock is insufficient or changed, rolls back the entire transaction.
   - **Defensive Cart Preservation:** If an error occurs, the customer's cart remains completely intact so the user only has to adjust quantities rather than starting over.
   - Prevents duplicate submissions by temporarily disabling the checkout button while processing.

4. **Soft Deactivation vs Hard Deletes**
   - Products feature an `active` flag (`active INTEGER DEFAULT 1`).
   - Archiving a product hides it from new billing dropdowns and active catalog lists without breaking foreign key relationships in historical sales invoices.

5. **First-Run Setup & Secure Authentication**
   - If the database contains no users on launch, a **First-Run Admin Setup Wizard** appears automatically.
   - Salted PBKDF2-HMAC-SHA256 password hashing with `hmac.compare_digest` constant-time verification.
   - Quick-fill button provided for evaluation convenience.

6. **Interactive Dashboard & Stock Reports**
   - Live KPI cards: Active Products, Total Asset Valuation, Low-Stock Warnings, and Today's Sales.
   - 1-Click **Quick Restock** utility for low-stock items.
   - Top-Selling Products leaderboard and Category Valuation breakdown.
   - Export both catalog and sales history to `.csv`.

---

## 📁 Project Architecture

```
ShopTrack-Pro/
├── main.py                 # Application entry point & sidebar navigation router
├── services.py             # Business layer: ProductService, BillingService, ReportService
├── database.py             # SQLite connection context, schema, corruption check
├── auth.py                 # PBKDF2-HMAC-SHA256 password hashing & session state
├── utils.py                # Money conversion (rupees <-> paise), validation, theme
├── test_app.py             # Automated unit & integration test suite (6 tests)
├── gui/
│   ├── __init__.py
│   ├── login_frame.py      # Login card & first-run setup wizard
│   ├── dashboard.py        # Real-time KPI cards & quick actions
│   ├── products.py         # Product CRUD, category filter, archival, CSV export
│   ├── billing.py          # POS cart, stock verification, atomic checkout, receipt modal
│   ├── sales.py            # Invoice history, line item drilldown, receipt reprint
│   └── reports.py          # Low stock alerts, 1-click restock, sales leaderboard
├── webapp/                 # Browser-based version (Flask) sharing the same services & database
│   ├── app.py              # Routes: login/setup, dashboard, products, billing, sales, reports, CSV export
│   ├── helpers.py          # Currency formatting & validation (Tkinter-free)
│   ├── requirements.txt
│   ├── templates/          # Jinja2 HTML pages
│   └── static/style.css
├── shop.db                 # Auto-seeded SQLite database
├── PRESENTATION_SLIDES.md  # 8-slide presentation deck & 3-member script
└── README.md
```

---

## 🚀 How to Run

### Prerequisites
- Python 3.8 or higher.
- Built-in `tkinter` and `sqlite3` (zero `pip install` dependencies required!).

### Running the App
```bash
cd ShopTrack-Pro
python3 main.py
```

### Running the Test Suite
```bash
python3 test_app.py
```

### Running the Web App
The web version uses the same `shop.db`, `services.py`, `database.py` and `auth.py`, so products, bills and users are shared with the desktop app.
```bash
pip install -r webapp/requirements.txt
python3 webapp/app.py
```
Then open http://localhost:5000 in your browser. Set `PORT` to change the port and `SHOPTRACK_SECRET_KEY` to keep logins valid across restarts.

---

## 🔑 Default Credentials

| Username | Password | Role |
| :--- | :--- | :--- |
| `admin` | `admin123` | Administrator |

*(If running with a fresh/empty database, the First-Run Setup Wizard allows entering these credentials or custom ones).*

---

## 👥 Team Work Division (3 Members)

| Member | Primary Focus Area | Modules Handled |
| :--- | :--- | :--- |
| **Member 1** | App Navigation, First-Run Setup & Dashboard | `main.py`, `auth.py`, `gui/login_frame.py`, `gui/dashboard.py` |
| **Member 2** | Database Layer & Inventory Catalog | `database.py`, `services.py` (ProductService), `gui/products.py` |
| **Member 3** | Point of Sale (POS), Transactions & Reports | `services.py` (BillingService, ReportService), `gui/billing.py`, `gui/sales.py`, `gui/reports.py`, `utils.py` |
