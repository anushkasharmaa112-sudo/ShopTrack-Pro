"""
Business logic and transaction boundary layer.
All database modifications, atomic billing checkouts, and reporting aggregates are handled here.
UI frames call services and never issue direct SQL statements.
"""

from typing import List, Dict, Any, Optional, Tuple
import database


class ProductService:
    @staticmethod
    def get_products(include_inactive: bool = False, search_term: Optional[str] = None, category: Optional[str] = None) -> List[dict]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM products WHERE 1=1"
            params = []

            if not include_inactive:
                query += " AND active = 1"

            if search_term:
                query += " AND (name LIKE ? OR category LIKE ?)"
                t = f"%{search_term.strip()}%"
                params.extend([t, t])

            if category and category.lower() != "all":
                query += " AND category = ?"
                params.append(category.strip())

            query += " ORDER BY active DESC, name ASC;"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_product_by_id(product_id: int) -> Optional[dict]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?;", (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_categories() -> List[str]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category ASC;")
            return [r["category"] for r in cursor.fetchall()]

    @staticmethod
    def add_product(name: str, category: str, price_minor: int, quantity: int, low_stock: int = 10) -> int:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name, category, price_minor, quantity, low_stock, active)
                VALUES (?, ?, ?, ?, ?, 1);
            """, (name.strip(), category.strip(), price_minor, quantity, low_stock))
            return cursor.lastrowid

    @staticmethod
    def update_product(product_id: int, name: str, category: str, price_minor: int, quantity: int, low_stock: int) -> bool:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products
                SET name = ?, category = ?, price_minor = ?, quantity = ?, low_stock = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?;
            """, (name.strip(), category.strip(), price_minor, quantity, low_stock, product_id))
            return cursor.rowcount > 0

    @staticmethod
    def deactivate_product(product_id: int) -> bool:
        """Soft-deactivates product so it cannot be billed while preserving historical records."""
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products
                SET active = 0, updated_at = datetime('now', 'localtime')
                WHERE id = ?;
            """, (product_id,))
            return cursor.rowcount > 0

    @staticmethod
    def restore_product(product_id: int) -> bool:
        """Restores a previously archived product back to active status."""
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products
                SET active = 1, updated_at = datetime('now', 'localtime')
                WHERE id = ?;
            """, (product_id,))
            return cursor.rowcount > 0

    @staticmethod
    def quick_restock(product_id: int, added_quantity: int) -> bool:
        if added_quantity <= 0:
            return False
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products
                SET quantity = quantity + ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?;
            """, (added_quantity, product_id))
            return cursor.rowcount > 0


class BillingService:
    @staticmethod
    def process_checkout(customer_name: str, cart_items: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Executes atomic checkout transaction.
        cart_items: list of dicts with: product_id, quantity, (optional requested name/price for validation)
        Verifies live DB stock and active status.
        Uses conditional decrement: UPDATE products SET quantity = quantity - ? WHERE id = ? AND active = 1 AND quantity >= ?
        Returns: (bill_id, total_minor)
        Raises: ValueError on validation or stock conflict with zero changes committed.
        """
        if not cart_items:
            raise ValueError("Cannot checkout an empty cart.")

        customer = customer_name.strip() if customer_name and customer_name.strip() else "Walk-in Customer"

        with database.get_connection() as conn:
            cursor = conn.cursor()

            verified_lines = []
            bill_total_minor = 0

            # Step 1: Verify each product against live database inside transaction
            for item in cart_items:
                pid = item["product_id"]
                req_qty = int(item["quantity"])

                cursor.execute("SELECT id, name, price_minor, quantity, active FROM products WHERE id = ?;", (pid,))
                prod = cursor.fetchone()
                if not prod:
                    raise ValueError(f"Product (ID #{pid}) was not found in catalog.")

                if prod["active"] != 1:
                    raise ValueError(f"Product '{prod['name']}' has been deactivated and cannot be sold.")

                curr_stock = prod["quantity"]
                if curr_stock < req_qty:
                    raise ValueError(
                        f"Insufficient stock for '{prod['name']}'!\n"
                        f"Current Store Stock: {curr_stock}, Requested: {req_qty}"
                    )

                unit_price = prod["price_minor"]
                line_total = req_qty * unit_price
                bill_total_minor += line_total

                verified_lines.append((pid, prod["name"], req_qty, unit_price, line_total))

            # Step 2: Conditional Stock Decrement (Guarantees atomic concurrency safety)
            for pid, pname, req_qty, unit_price, line_total in verified_lines:
                cursor.execute("""
                    UPDATE products
                    SET quantity = quantity - ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ? AND active = 1 AND quantity >= ?;
                """, (req_qty, pid, req_qty))

                if cursor.rowcount != 1:
                    raise ValueError(
                        f"Stock conflict encountered for '{pname}'. "
                        "Stock was modified concurrently. Checkout aborted without saving."
                    )

            # Step 3: Insert Bill Header
            cursor.execute(
                "INSERT INTO bills (customer, total_minor) VALUES (?, ?);",
                (customer, bill_total_minor)
            )
            bill_id = cursor.lastrowid

            # Step 4: Insert Snapshot Line Items
            for pid, pname, req_qty, unit_price, line_total in verified_lines:
                cursor.execute("""
                    INSERT INTO bill_items (bill_id, product_id, product_name, quantity, unit_price_minor, line_total_minor)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (bill_id, pid, pname, req_qty, unit_price, line_total))

            return bill_id, bill_total_minor

    @staticmethod
    def get_all_bills(search_term: Optional[str] = None) -> List[dict]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            if search_term:
                query = """
                    SELECT * FROM bills
                    WHERE id LIKE ? OR customer LIKE ?
                    ORDER BY id DESC;
                """
                t = f"%{search_term.strip()}%"
                cursor.execute(query, (t, t))
            else:
                cursor.execute("SELECT * FROM bills ORDER BY id DESC;")
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_bill_by_id(bill_id: int) -> Optional[dict]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bills WHERE id = ?;", (bill_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_bill_items(bill_id: int) -> List[dict]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bill_items WHERE bill_id = ? ORDER BY id ASC;", (bill_id,))
            return [dict(r) for r in cursor.fetchall()]


class ReportService:
    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        with database.get_connection() as conn:
            cursor = conn.cursor()

            # Active products count
            cursor.execute("SELECT COUNT(*) as cnt FROM products WHERE active = 1;")
            active_products = cursor.fetchone()["cnt"]

            # Inventory Asset Valuation (Sum of price_minor * quantity for active items)
            cursor.execute("SELECT COALESCE(SUM(price_minor * quantity), 0) as total_val FROM products WHERE active = 1;")
            inventory_val_minor = cursor.fetchone()["total_val"]

            # Low stock count for active items
            cursor.execute("SELECT COUNT(*) as low_cnt FROM products WHERE active = 1 AND quantity <= low_stock;")
            low_stock_count = cursor.fetchone()["low_cnt"]

            # Today's Sales
            cursor.execute("""
                SELECT COUNT(*) as bills_today, COALESCE(SUM(total_minor), 0) as rev_today
                FROM bills
                WHERE date(created_at) = date('now', 'localtime');
            """)
            today_row = cursor.fetchone()

            # Lifetime Sales
            cursor.execute("SELECT COUNT(*) as all_bills, COALESCE(SUM(total_minor), 0) as all_rev FROM bills;")
            lifetime_row = cursor.fetchone()

            return {
                "active_products": active_products,
                "inventory_valuation_minor": inventory_val_minor,
                "low_stock_count": low_stock_count,
                "today_bills": today_row["bills_today"],
                "today_revenue_minor": today_row["rev_today"],
                "lifetime_bills": lifetime_row["all_bills"],
                "lifetime_revenue_minor": lifetime_row["all_rev"]
            }

    @staticmethod
    def get_low_stock_products() -> List[dict]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM products
                WHERE active = 1 AND quantity <= low_stock
                ORDER BY quantity ASC, name ASC;
            """)
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_top_selling_products(limit: int = 10) -> List[dict]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_name,
                       SUM(quantity) as total_sold,
                       SUM(line_total_minor) as total_revenue_minor
                FROM bill_items
                GROUP BY product_id, product_name
                ORDER BY total_sold DESC
                LIMIT ?;
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_category_valuation() -> List[dict]:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category,
                       COUNT(*) as items_count,
                       COALESCE(SUM(quantity), 0) as total_units,
                       COALESCE(SUM(price_minor * quantity), 0) as valuation_minor
                FROM products
                WHERE active = 1
                GROUP BY category
                ORDER BY valuation_minor DESC;
            """)
            return [dict(r) for r in cursor.fetchall()]
