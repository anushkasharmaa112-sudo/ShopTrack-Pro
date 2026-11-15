"""
Database layer for Inventory & Shop Management System.
Handles SQLite connections, schema initialization, corruption verification, and persistence.
All monetary amounts are strictly persisted as integer minor units (paise/cents).
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple

DB_FILENAME = "shop.db"
# Resolve path relative to this script directory to ensure immunity to working directory changes
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)


@contextmanager
def get_connection():
    """
    Context manager providing a transactional SQLite connection.
    Enforces foreign key checks, row_factory, auto-commit, and rollback on error.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_database_integrity():
    """
    Checks that the SQLite database file is not corrupted if it already exists.
    Raises RuntimeError if corrupted to prevent silent overwriting.
    """
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            conn.close()
            if not res or res[0] != "ok":
                raise RuntimeError(
                    f"CRITICAL: Database '{DB_PATH}' appears corrupt (PRAGMA integrity_check returned '{res}').\n"
                    "The file has been preserved for manual recovery. Please check your database file."
                )
        except sqlite3.DatabaseError as e:
            raise RuntimeError(
                f"CRITICAL: Failed to open database at '{DB_PATH}': {e}.\n"
                "The file has been preserved for manual recovery."
            )


def init_db():
    """
    Initializes database schema with foreign keys, checks, and indexes.
    Seeds sample catalog if database is fresh.
    """
    verify_database_integrity()

    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username       TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash  TEXT NOT NULL,
                password_salt  TEXT NOT NULL,
                role           TEXT NOT NULL DEFAULT 'admin',
                created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
        """)

        # 2. Products Table (Using price_minor INTEGER and active flag for soft deactivation)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL COLLATE NOCASE,
                category       TEXT NOT NULL DEFAULT 'General',
                price_minor    INTEGER NOT NULL CHECK(price_minor >= 0),
                quantity       INTEGER NOT NULL CHECK(quantity >= 0),
                low_stock      INTEGER NOT NULL DEFAULT 10 CHECK(low_stock >= 0),
                active         INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
                created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
        """)

        # 3. Bills Table (total_minor INTEGER)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                customer       TEXT NOT NULL DEFAULT 'Walk-in Customer',
                total_minor    INTEGER NOT NULL CHECK(total_minor >= 0),
                created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
        """)

        # 4. Bill Items Table (unit_price_minor & line_total_minor INTEGER)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bill_items (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id           INTEGER NOT NULL,
                product_id        INTEGER NOT NULL,
                product_name      TEXT NOT NULL,
                quantity          INTEGER NOT NULL CHECK(quantity > 0),
                unit_price_minor  INTEGER NOT NULL CHECK(unit_price_minor >= 0),
                line_total_minor  INTEGER NOT NULL CHECK(line_total_minor >= 0),
                FOREIGN KEY (bill_id)    REFERENCES bills(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
            );
        """)

        # Migration safeguards for existing databases
        cursor.execute("PRAGMA table_info(products);")
        existing_cols = {col["name"]: col for col in cursor.fetchall()}
        if existing_cols and "active" not in existing_cols:
            cursor.execute("ALTER TABLE products ADD COLUMN active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1));")
        if existing_cols and "price_minor" not in existing_cols:
            cursor.execute("ALTER TABLE products ADD COLUMN price_minor INTEGER NOT NULL DEFAULT 0 CHECK(price_minor >= 0);")
            if "price" in existing_cols:
                cursor.execute("UPDATE products SET price_minor = CAST(ROUND(price * 100) AS INTEGER);")

        cursor.execute("PRAGMA table_info(bills);")
        bill_cols = {col["name"]: col for col in cursor.fetchall()}
        if bill_cols and "total_minor" not in bill_cols:
            cursor.execute("ALTER TABLE bills ADD COLUMN total_minor INTEGER NOT NULL DEFAULT 0 CHECK(total_minor >= 0);")
            if "total" in bill_cols:
                cursor.execute("UPDATE bills SET total_minor = CAST(ROUND(total * 100) AS INTEGER);")

        cursor.execute("PRAGMA table_info(bill_items);")
        item_cols = {col["name"]: col for col in cursor.fetchall()}
        if item_cols and "unit_price_minor" not in item_cols:
            cursor.execute("ALTER TABLE bill_items ADD COLUMN unit_price_minor INTEGER NOT NULL DEFAULT 0 CHECK(unit_price_minor >= 0);")
            if "unit_price" in item_cols:
                cursor.execute("UPDATE bill_items SET unit_price_minor = CAST(ROUND(unit_price * 100) AS INTEGER);")
        if item_cols and "line_total_minor" not in item_cols:
            cursor.execute("ALTER TABLE bill_items ADD COLUMN line_total_minor INTEGER NOT NULL DEFAULT 0 CHECK(line_total_minor >= 0);")
            if "line_total" in item_cols:
                cursor.execute("UPDATE bill_items SET line_total_minor = CAST(ROUND(line_total * 100) AS INTEGER);")

        cursor.execute("PRAGMA table_info(users);")
        user_cols = {col["name"]: col for col in cursor.fetchall()}
        if user_cols and "password_salt" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN password_salt TEXT DEFAULT '';")
        if user_cols and "password_hash" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT '';")
            if "password" in user_cols:
                cursor.execute("UPDATE users SET password_hash = password;")

        # Create helpful indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_active ON products(active, name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bill_items_bill_id ON bill_items(bill_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_created_at ON bills(created_at);")

        # Seed sample store catalog if products table is empty
        cursor.execute("SELECT COUNT(*) as count FROM products;")
        if cursor.fetchone()["count"] == 0:
            sample_products = [
                ("Wireless Mouse", "Electronics", 49900, 45, 10, 1),
                ("Mechanical Keyboard", "Electronics", 249900, 18, 5, 1),
                ("USB-C Hub (4 Ports)", "Electronics", 89900, 6, 8, 1),     # Low stock
                ("Notebook A5 Ruled", "Stationery", 6000, 120, 20, 1),
                ("Gel Pen Blue (Pack of 5)", "Stationery", 5000, 80, 15, 1),
                ("Stapler Medium", "Stationery", 12000, 4, 10, 1),           # Low stock
                ("Arabica Coffee Powder 250g", "Groceries", 34000, 25, 10, 1),
                ("Green Tea Bags (Box 25)", "Groceries", 21000, 30, 8, 1),
                ("Digestive Biscuits 500g", "Snacks", 9500, 50, 12, 1),
                ("Dark Chocolate Bar 100g", "Snacks", 15000, 3, 10, 1),      # Low stock
            ]
            cursor.executemany(
                "INSERT INTO products (name, category, price_minor, quantity, low_stock, active) VALUES (?, ?, ?, ?, ?, ?);",
                sample_products
            )


# ============================================================
# User Repository
# ============================================================
def has_users() -> bool:
    """Returns True if at least one user is registered."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users;")
        return cursor.fetchone()["count"] > 0


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE;", (username.strip(),))
        return cursor.fetchone()


def create_user(username: str, password_hash: str, password_salt: str, role: str = "admin") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, password_salt, role) VALUES (?, ?, ?, ?);",
            (username.strip(), password_hash, password_salt, role)
        )
        return cursor.lastrowid
