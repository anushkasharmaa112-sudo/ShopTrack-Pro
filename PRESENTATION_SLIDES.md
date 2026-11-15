# 📊 Presentation Slides & Demo Script (15 Marks)

**Project Title:** ShopTrack Pro — Store & Inventory Management System  
**Team Members:** Member 1, Member 2, Member 3  
**Technology:** Python, Tkinter (GUI), SQLite (Backend)  
**Evaluation Date:** 06/11/2026

---

## 🖥️ Slide-by-Slide Content

### Slide 1: Title Slide
- **Title:** ShopTrack Pro: Desktop Store & Inventory Management System
- **Subtitle:** An Enterprise-Grade Python Tkinter & SQLite Application
- **Course / Subject:** GUI & Database Application Development (15 Marks)
- **Team Members:**
  - [Member 1 Name] — Frontend Layout & Authentication Lead
  - [Member 2 Name] — Database & Inventory Architecture Lead
  - [Member 3 Name] — Point of Sale (POS), Transactions & Analytics Lead
- **Speaker:** Member 1

---

### Slide 2: Problem Statement & Motivation
- **The Problem:**
  - Small retail businesses struggle with manual logbooks and spreadsheet rounding errors.
  - Floating-point calculations cause accounting discrepancies over time.
  - Deleting sold products often corrupts historical customer invoices.
- **The Solution:**
  - Lightweight, responsive desktop system requiring **zero external dependencies**.
  - **Integer Minor Units:** Money stored strictly as integer minor units (paise/cents) to eliminate float rounding errors.
  - **Soft Deactivation:** Obsolete items can be archived without breaking past invoices.
  - **Atomic Transactions:** Multi-item billing checkouts decrement stock and create invoices synchronously.
- **Speaker:** Member 1

---

### Slide 3: System Architecture & 3-Tier Layering
- **Layer 1: Presentation (GUI):** Modular Tkinter/ttk frames (`login_frame.py`, `dashboard.py`, `products.py`, `billing.py`, etc.).
- **Layer 2: Business Logic (`services.py`):**
  - Isolates UI from SQL statements.
  - Encapsulates `ProductService`, `BillingService`, and `ReportService`.
- **Layer 3: Data Access & Security (`database.py` & `auth.py`):**
  - Connection context manager enforcing `PRAGMA foreign_keys = ON`.
  - Salted PBKDF2-HMAC-SHA256 hashing with constant-time `hmac.compare_digest`.
- **Speaker:** Member 2

---

### Slide 4: Database Schema & Integrity Guarantees
- **Key Tables:**
  1. `users` — Stores username, salted hash, and role with first-run auto-setup.
  2. `products` — Tracks `price_minor INTEGER`, `quantity`, `low_stock`, and `active` flag.
  3. `bills` — Header records storing `total_minor INTEGER` and customer info.
  4. `bill_items` — Snapshotted line items linked by Foreign Keys (`ON DELETE CASCADE` from bills, `ON DELETE RESTRICT` from products).
- **Integrity Safeguards:**
  - Parameterized queries (`?`) throughout for total SQL injection immunity.
  - Database file location resolved relative to application directory (`__file__`).
- **Speaker:** Member 2

---

### Slide 5: Point of Sale & Defensive Billing
- **Concurrency & Stock Defense:**
  - Re-reads live stock and active status from SQLite inside transaction.
  - Conditional atomic update: `UPDATE products SET quantity = quantity - ? WHERE id = ? AND active = 1 AND quantity >= ?`.
  - Verifies `cursor.rowcount == 1`. If stock changed or was insufficient, transaction rolls back automatically.
- **Defensive Cart Preservation:**
  - If a checkout fails due to stock limits, **the cart remains completely intact** so the cashier only has to adjust quantities rather than starting over.
  - Checkout button disabled during processing to block accidental double-clicks.
- **Speaker:** Member 3

---

### Slide 6: Inventory Analytics & Error-Proofing
- **Real-Time Dashboard:**
  - Live KPI cards: Active Catalog Items, Total Asset Worth, Low-Stock Alerts, and Today's Sales.
- **Analytics & Restock:**
  - Low-stock report table with a 1-click **Quick Restock** modal dialog.
  - Sales leaderboard tracking units sold and revenue per item.
  - Category valuation breakdown.
  - Full CSV export for products and sales history.
- **Speaker:** Member 3

---

### Slide 7: Live Demonstration Flow (3–4 Minutes)
1. **Launch & Login:** Show clean card UI; login with administrator account.
2. **Dashboard Overview:** Point out live KPI cards and low-stock warning banners.
3. **Product Management:** Add a new item, show integer minor-unit conversion, soft-archive an item.
4. **Billing / POS:** Add items to cart; attempt to oversell stock to demonstrate defensive rollback; complete valid sale and inspect receipt popup.
5. **Stock Decrement & History:** Show stock decremented immediately in catalog and view line items in Sales History.
6. **Reports & Quick Restock:** Restock the low-stock item in 1 click and verify dashboard updates.
7. **Speaker:** Shared across all 3 members

---

### Slide 8: Summary & Technical Highlights
- **Engineering Accomplishments:**
  - Zero external pip dependencies (runs everywhere Python 3 is installed).
  - Floating point drift eliminated via integer minor units.
  - Soft deactivation preserving relational historical data.
  - 100% automated test suite passing in under 1 second (`test_app.py`).
- **Future Scope:**
  - Barcode scanner integration.
  - PDF receipt generation with company logo.
- **Speaker:** Member 1

---

## 🎯 Evaluator Demo Script (Who Speaks When)

- **Member 1 (0:00 - 1:15):**
  > "Respected Evaluators, our project is 'ShopTrack Pro', a desktop retail management system developed using Python Tkinter and SQLite. We designed it around defensive engineering principles. If the system is started fresh, our First-Run Setup Wizard guides the administrator to create their credentials. Once signed in, our Dashboard displays real-time store metrics computed from SQLite, including live inventory valuation and low-stock warnings."

- **Member 2 (1:15 - 2:30):**
  > "I will demonstrate the Product Catalog and Data Layer. Notice that all monetary prices are stored internally as integer minor units (paise) to prevent floating-point rounding errors. We also implemented soft deactivation: when a product is discontinued, setting it to inactive removes it from new billing dropdowns without breaking historical records in past customer invoices. All interactions pass through our decoupled `services.py` layer with parameterized SQL."

- **Member 3 (2:30 - 3:45):**
  > "Now for our Point of Sale and Billing system. When we build a cart, our service checks live stock levels inside an atomic database transaction. If we attempt to sell more units than are currently on the shelf, our conditional update detects it and rolls back immediately, while keeping our cart completely intact so the cashier doesn't lose entered items. Upon completing a valid checkout, stock decrements atomically, a formatted receipt is produced, and our Reports tab immediately reflects the updated sales leaderboard and 1-click restock utility."
