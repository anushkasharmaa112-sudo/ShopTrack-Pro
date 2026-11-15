"""
Reports and Stock Analytics View for Inventory & Shop Management System.
Uses high-contrast standard widgets for 100% visibility across macOS (Light & Dark), Windows, and Linux.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from services import ReportService, ProductService
from utils import (
    COLORS, FONTS, format_currency,
    create_card, create_label
)


class ReportsFrame(tk.Frame):
    def __init__(self, parent, on_data_changed=None):
        super().__init__(parent, bg=COLORS["bg_light"])
        self.on_data_changed = on_data_changed

        self._build_ui()
        self.refresh_all_reports()

    def _build_ui(self):
        container = tk.Frame(self, bg=COLORS["bg_light"], padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Header Bar
        header = tk.Frame(container, bg=COLORS["bg_light"])
        header.pack(fill=tk.X, pady=(0, 12))

        create_label(
            header,
            text="📊 Analytics & Stock Reports",
            font_key="heading",
            fg_key="text_dark",
            bg_key="bg_light"
        ).pack(side=tk.LEFT)

        ttk.Button(
            header,
            text="🔄 Refresh Reports",
            command=self.refresh_all_reports
        ).pack(side=tk.RIGHT)

        # Notebook
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # Tab 1: Low Stock & Restock
        # ----------------------------------------------------
        self.tab_low_stock = tk.Frame(self.notebook, bg=COLORS["bg_light"], padx=12, pady=12)
        self.notebook.add(self.tab_low_stock, text="🚨 Low Stock & Restock")

        low_top = create_card(self.tab_low_stock, padx=14, pady=10)
        low_top.pack(fill=tk.X, pady=(0, 10))

        self.low_count_lbl = create_label(low_top, text="Inspecting stock...", font_key="body_bold", fg_key="text_dark", bg_key="card_bg")
        self.low_count_lbl.pack(side=tk.LEFT)

        ttk.Button(
            low_top,
            text="📦 Quick Restock Selected Item",
            command=self._handle_quick_restock
        ).pack(side=tk.RIGHT)

        low_tree_card = create_card(self.tab_low_stock, padx=2, pady=2)
        low_tree_card.pack(fill=tk.BOTH, expand=True)

        low_cols = ("id", "name", "category", "price", "stock", "threshold", "deficit")
        self.low_tree = ttk.Treeview(low_tree_card, columns=low_cols, show="headings", selectmode="browse")

        self.low_tree.heading("id", text="ID")
        self.low_tree.heading("name", text="Product Name")
        self.low_tree.heading("category", text="Category")
        self.low_tree.heading("price", text="Price")
        self.low_tree.heading("stock", text="Current Stock")
        self.low_tree.heading("threshold", text="Threshold")
        self.low_tree.heading("deficit", text="Restock Deficit")

        self.low_tree.column("id", width=50, anchor=tk.CENTER)
        self.low_tree.column("name", width=200, anchor=tk.W)
        self.low_tree.column("category", width=110, anchor=tk.W)
        self.low_tree.column("price", width=80, anchor=tk.E)
        self.low_tree.column("stock", width=95, anchor=tk.CENTER)
        self.low_tree.column("threshold", width=105, anchor=tk.CENTER)
        self.low_tree.column("deficit", width=115, anchor=tk.CENTER)

        low_vsb = ttk.Scrollbar(low_tree_card, orient=tk.VERTICAL, command=self.low_tree.yview)
        self.low_tree.configure(yscrollcommand=low_vsb.set)
        self.low_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        low_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ----------------------------------------------------
        # Tab 2: Top Selling Leaderboard
        # ----------------------------------------------------
        self.tab_top_selling = tk.Frame(self.notebook, bg=COLORS["bg_light"], padx=12, pady=12)
        self.notebook.add(self.tab_top_selling, text="🏆 Top Selling Items")

        top_tree_card = create_card(self.tab_top_selling, padx=2, pady=2)
        top_tree_card.pack(fill=tk.BOTH, expand=True)

        top_cols = ("rank", "name", "units_sold", "revenue")
        self.top_tree = ttk.Treeview(top_tree_card, columns=top_cols, show="headings", selectmode="browse")

        self.top_tree.heading("rank", text="Rank")
        self.top_tree.heading("name", text="Product Name")
        self.top_tree.heading("units_sold", text="Units Sold")
        self.top_tree.heading("revenue", text="Total Sales Revenue")

        self.top_tree.column("rank", width=60, anchor=tk.CENTER)
        self.top_tree.column("name", width=250, anchor=tk.W)
        self.top_tree.column("units_sold", width=120, anchor=tk.CENTER)
        self.top_tree.column("revenue", width=140, anchor=tk.E)

        top_vsb = ttk.Scrollbar(top_tree_card, orient=tk.VERTICAL, command=self.top_tree.yview)
        self.top_tree.configure(yscrollcommand=top_vsb.set)
        self.top_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        top_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ----------------------------------------------------
        # Tab 3: Category Valuation
        # ----------------------------------------------------
        self.tab_valuation = tk.Frame(self.notebook, bg=COLORS["bg_light"], padx=12, pady=12)
        self.notebook.add(self.tab_valuation, text="💰 Valuation Breakdown")

        val_card = create_card(self.tab_valuation, padx=2, pady=2)
        val_card.pack(fill=tk.BOTH, expand=True)

        val_cols = ("category", "items_count", "total_units", "total_val")
        self.val_tree = ttk.Treeview(val_card, columns=val_cols, show="headings")

        self.val_tree.heading("category", text="Category")
        self.val_tree.heading("items_count", text="Active Products")
        self.val_tree.heading("total_units", text="Total Stock Units")
        self.val_tree.heading("total_val", text="Inventory Valuation")

        self.val_tree.column("category", width=180, anchor=tk.W)
        self.val_tree.column("items_count", width=130, anchor=tk.CENTER)
        self.val_tree.column("total_units", width=140, anchor=tk.CENTER)
        self.val_tree.column("total_val", width=160, anchor=tk.E)

        val_vsb = ttk.Scrollbar(val_card, orient=tk.VERTICAL, command=self.val_tree.yview)
        self.val_tree.configure(yscrollcommand=val_vsb.set)
        self.val_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        val_vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_all_reports(self):
        self._load_low_stock()
        self._load_top_selling()
        self._load_valuation()

    def _load_low_stock(self):
        for it in self.low_tree.get_children():
            self.low_tree.delete(it)

        low_rows = ReportService.get_low_stock_products()
        count = len(low_rows)

        if count == 0:
            self.low_count_lbl.config(
                text="✅ All products are well stocked above their alert thresholds!",
                fg=COLORS["success"]
            )
        else:
            self.low_count_lbl.config(
                text=f"⚠️ {count} product(s) are low on stock and need restocking.",
                fg=COLORS["danger"]
            )

        for r in low_rows:
            stock = r["quantity"]
            thresh = r["low_stock"]
            deficit = max(0, thresh - stock)
            self.low_tree.insert("", tk.END, values=(
                r["id"],
                r["name"],
                r["category"],
                format_currency(r["price_minor"]),
                stock,
                thresh,
                f"+{deficit} units" if deficit > 0 else "At threshold"
            ))

    def _load_top_selling(self):
        for it in self.top_tree.get_children():
            self.top_tree.delete(it)

        top_rows = ReportService.get_top_selling_products(limit=10)
        for idx, r in enumerate(top_rows, 1):
            self.top_tree.insert("", tk.END, values=(
                f"#{idx}",
                r["product_name"],
                r["total_sold"],
                format_currency(r["total_revenue_minor"])
            ))

    def _load_valuation(self):
        for it in self.val_tree.get_children():
            self.val_tree.delete(it)

        val_rows = ReportService.get_category_valuation()
        for r in val_rows:
            self.val_tree.insert("", tk.END, values=(
                r["category"],
                r["items_count"],
                r["total_units"] or 0,
                format_currency(r["valuation_minor"] or 0)
            ))

    def _handle_quick_restock(self):
        selected = self.low_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a product from the low stock list.")
            return

        values = self.low_tree.item(selected[0], "values")
        prod_id = int(values[0])
        prod_name = values[1]
        curr_stock = values[4]

        qty_str = simpledialog.askstring(
            "Quick Restock",
            f"Product: {prod_name}\nCurrent Stock: {curr_stock}\n\nEnter number of units to add:"
        )
        if qty_str is None:
            return

        try:
            add_qty = int(qty_str)
            if add_qty <= 0:
                messagebox.showerror("Invalid Input", "Restock quantity must be a positive whole number.")
                return

            ProductService.quick_restock(prod_id, add_qty)
            messagebox.showinfo("Restocked", f"Added {add_qty} units to '{prod_name}'.")

            self.refresh_all_reports()
            if self.on_data_changed:
                self.on_data_changed()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid whole number.")
