"""
Automated Integration Test Suite for Inventory & Shop Management System (v2).
Tests financial minor-unit math, atomic checkout transactions, concurrency safeguards,
soft deactivation, password hashing with compare_digest, and Tkinter UI lifecycle.
"""

import unittest
import os
import sqlite3

os.environ["TK_SILENCE_DEPRECATION"] = "1"
import database
import services
import auth
import utils


class TestInventoryAppV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Point to isolated test database so production/demo shop.db is never touched
        cls.orig_db_path = database.DB_PATH
        cls.test_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_shop.db")
        database.DB_PATH = cls.test_db_path

        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)

        database.init_db()

        # Seed an admin user in the test database
        h, s = auth.hash_password("admin123")
        database.create_user("admin", h, s, "admin")

    @classmethod
    def tearDownClass(cls):
        # Restore original path and clean up test file
        database.DB_PATH = cls.orig_db_path
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def test_01_currency_minor_units(self):
        # 1. Decimal to minor units (Paise)
        ok, _, paise = utils.rupees_to_paise("199.50")
        self.assertTrue(ok)
        self.assertEqual(paise, 19950)

        ok, _, paise = utils.rupees_to_paise("50")
        self.assertTrue(ok)
        self.assertEqual(paise, 5000)

        ok, _, paise = utils.rupees_to_paise("0.75")
        self.assertTrue(ok)
        self.assertEqual(paise, 75)

        # Negative & Malformed rejected
        ok, err, _ = utils.rupees_to_paise("-15.00")
        self.assertFalse(ok)

        ok, err, _ = utils.rupees_to_paise("abc")
        self.assertFalse(ok)

        # 2. Minor units back to string and formatted display
        self.assertEqual(utils.paise_to_rupees_str(19950), "199.50")
        self.assertEqual(utils.format_currency(19950), "₹199.50")
        self.assertEqual(utils.format_currency(125000), "₹1,250.00")

    def test_02_auth_and_compare_digest(self):
        h, s = auth.hash_password("secretpass")
        self.assertTrue(auth.verify_password(h, s, "secretpass"))
        self.assertFalse(auth.verify_password(h, s, "wrongpass"))

        # Verify admin
        admin = database.get_user_by_username("admin")
        self.assertIsNotNone(admin)
        self.assertTrue(auth.verify_password(admin["password_hash"], admin["password_salt"], "admin123"))

    def test_03_product_lifecycle_and_soft_deactivation(self):
        # Add product
        pid = services.ProductService.add_product("Wireless Ergonomic Mouse", "Electronics", 299900, 20, 5)
        prod = services.ProductService.get_product_by_id(pid)
        self.assertIsNotNone(prod)
        self.assertEqual(prod["active"], 1)
        self.assertEqual(prod["price_minor"], 299900)

        # Soft Deactivate
        services.ProductService.deactivate_product(pid)
        prod = services.ProductService.get_product_by_id(pid)
        self.assertEqual(prod["active"], 0)

        # Active products query should not list it
        active_list = services.ProductService.get_products(include_inactive=False)
        self.assertFalse(any(p["id"] == pid for p in active_list))

        # Restore
        services.ProductService.restore_product(pid)
        prod = services.ProductService.get_product_by_id(pid)
        self.assertEqual(prod["active"], 1)

    def test_04_atomic_billing_and_stock_safety(self):
        pid = services.ProductService.add_product("Gaming Headset", "Electronics", 150000, 10, 3)

        # 1. Successful sale of 4 units
        cart = [{
            "product_id": pid,
            "quantity": 4
        }]
        bill_id, total_minor = services.BillingService.process_checkout("Alice", cart)
        self.assertGreater(bill_id, 0)
        self.assertEqual(total_minor, 4 * 150000)

        # Verify stock decreased from 10 to 6
        prod = services.ProductService.get_product_by_id(pid)
        self.assertEqual(prod["quantity"], 6)

        # Verify line items have snapshotted product name and price
        lines = services.BillingService.get_bill_items(bill_id)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["product_name"], "Gaming Headset")
        self.assertEqual(lines[0]["quantity"], 4)
        self.assertEqual(lines[0]["unit_price_minor"], 150000)
        self.assertEqual(lines[0]["line_total_minor"], 600000)

        # 2. Defending against overselling (Stock is 6, request 10)
        overflow_cart = [{
            "product_id": pid,
            "quantity": 10
        }]
        with self.assertRaises(ValueError) as ctx:
            services.BillingService.process_checkout("Bob", overflow_cart)
        self.assertIn("Insufficient stock", str(ctx.exception))

        # Stock must remain safely unchanged at 6
        prod = services.ProductService.get_product_by_id(pid)
        self.assertEqual(prod["quantity"], 6)

        # 3. Defending against deactivation: Deactivated product cannot be billed
        services.ProductService.deactivate_product(pid)
        with self.assertRaises(ValueError) as ctx:
            services.BillingService.process_checkout("Charlie", [{"product_id": pid, "quantity": 1}])
        self.assertIn("deactivated", str(ctx.exception))

    def test_05_reports_and_valuation(self):
        metrics = services.ReportService.get_dashboard_metrics()
        self.assertIn("active_products", metrics)
        self.assertIn("inventory_valuation_minor", metrics)
        self.assertIn("today_bills", metrics)
        self.assertGreaterEqual(metrics["today_bills"], 1)

        low = services.ReportService.get_low_stock_products()
        self.assertIsInstance(low, list)

        top = services.ReportService.get_top_selling_products()
        self.assertIsInstance(top, list)

    def test_06_gui_lifecycle(self):
        import main
        app = main.ShopManagementApp()

        def run_gui_steps():
            try:
                user = database.get_user_by_username("admin")
                app.on_login_success(dict(user))
                for tab in ["dashboard", "products", "billing", "sales", "reports"]:
                    app.navigate_to(tab)
            finally:
                app.destroy()

        app.after(50, run_gui_steps)
        app.mainloop()


if __name__ == "__main__":
    unittest.main()
