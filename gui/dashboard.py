"""
Dashboard view for Inventory & Shop Management System.
Uses high-contrast standard widgets for 100% visibility across macOS (Light & Dark), Windows, and Linux.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from services import ReportService, BillingService
import auth
from utils import (
    COLORS, FONTS, format_currency,
    create_card, create_label
)


class DashboardFrame(tk.Frame):
    def __init__(self, parent, navigate_callback):
        super().__init__(parent, bg=COLORS["bg_light"])
        self.navigate = navigate_callback

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        content = tk.Frame(self, bg=COLORS["bg_light"], padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)

        # Header Bar
        header = tk.Frame(content, bg=COLORS["bg_light"])
        header.pack(fill=tk.X, pady=(0, 15))

        title_box = tk.Frame(header, bg=COLORS["bg_light"])
        title_box.pack(side=tk.LEFT)

        self.welcome_label = create_label(
            title_box,
            text="Dashboard Overview",
            font_key="title",
            fg_key="text_dark",
            bg_key="bg_light"
        )
        self.welcome_label.pack(anchor=tk.W)

        today_str = datetime.now().strftime("%A, %d %B %Y")
        date_label = create_label(
            title_box,
            text=f"Live Store Status as of {today_str}",
            font_key="body",
            fg_key="text_muted",
            bg_key="bg_light"
        )
        date_label.pack(anchor=tk.W)

        refresh_btn = ttk.Button(
            header,
            text="🔄 Refresh Stats",
            command=self.refresh_data
        )
        refresh_btn.pack(side=tk.RIGHT)

        # Alert Banner
        self.alert_frame = tk.Frame(content, bg="#FEF3C7", highlightbackground="#F59E0B", highlightthickness=1, padx=15, pady=10)
        self.alert_label = create_label(
            self.alert_frame,
            text="",
            font_key="body_bold",
            fg_key="#92400E",
            bg_key="#FEF3C7"
        )
        self.alert_label.pack(side=tk.LEFT)

        alert_btn = ttk.Button(
            self.alert_frame,
            text="View Low Stock Items ➔",
            command=lambda: self.navigate("reports")
        )
        alert_btn.pack(side=tk.RIGHT)

        # KPI Metric Cards Grid
        self.cards_frame = tk.Frame(content, bg=COLORS["bg_light"])
        self.cards_frame.pack(fill=tk.X, pady=(0, 18))

        self.card_products = self._create_kpi_card(self.cards_frame, "📦 Active Products", "0", "Catalog items")
        self.card_value = self._create_kpi_card(self.cards_frame, "💰 Inventory Valuation", "₹0.00", "Total stock value")
        self.card_low = self._create_kpi_card(self.cards_frame, "⚠️ Low Stock Alerts", "0", "Below threshold")
        self.card_sales = self._create_kpi_card(self.cards_frame, "📈 Today's Sales", "₹0.00", "0 orders today")

        self.card_products.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.card_value.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.card_low.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.card_sales.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bottom Grid (Quick Actions + Recent Sales)
        bottom_grid = tk.Frame(content, bg=COLORS["bg_light"])
        bottom_grid.pack(fill=tk.BOTH, expand=True)

        # Quick Actions Card
        actions_card = create_card(bottom_grid, padx=16, pady=15)
        actions_card.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 15))

        create_label(
            actions_card,
            text="⚡ Quick Actions",
            font_key="heading",
            fg_key="text_dark",
            bg_key="card_bg"
        ).pack(anchor=tk.W, pady=(0, 12))

        self._create_action_btn(actions_card, "🛒 Point of Sale / Billing", lambda: self.navigate("billing"))
        self._create_action_btn(actions_card, "📦 Product Catalog", lambda: self.navigate("products"))
        self._create_action_btn(actions_card, "📋 Sales History", lambda: self.navigate("sales"))
        self._create_action_btn(actions_card, "🚨 Stock & Restock Reports", lambda: self.navigate("reports"))

        # Recent Sales Card
        sales_card = create_card(bottom_grid, padx=16, pady=12)
        sales_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        recent_header = tk.Frame(sales_card, bg=COLORS["card_bg"])
        recent_header.pack(fill=tk.X, pady=(0, 8))

        create_label(
            recent_header,
            text="🕒 Recent Invoices",
            font_key="heading",
            fg_key="text_dark",
            bg_key="card_bg"
        ).pack(side=tk.LEFT)

        view_all_btn = ttk.Button(
            recent_header,
            text="View All ➔",
            command=lambda: self.navigate("sales")
        )
        view_all_btn.pack(side=tk.RIGHT)

        cols = ("id", "date", "customer", "total")
        self.tree = ttk.Treeview(sales_card, columns=cols, show="headings", height=7)
        self.tree.heading("id", text="Bill #")
        self.tree.heading("date", text="Date & Time")
        self.tree.heading("customer", text="Customer")
        self.tree.heading("total", text="Total Paid")

        self.tree.column("id", width=60, anchor=tk.CENTER)
        self.tree.column("date", width=140, anchor=tk.W)
        self.tree.column("customer", width=150, anchor=tk.W)
        self.tree.column("total", width=90, anchor=tk.E)

        self.tree.pack(fill=tk.BOTH, expand=True)

    def _create_kpi_card(self, parent, title, initial_val, sub_text):
        card = create_card(parent, padx=15, pady=12)

        create_label(
            card,
            text=title,
            font_key="body_bold",
            fg_key="text_muted",
            bg_key="card_bg"
        ).pack(anchor=tk.W)

        val_lbl = create_label(
            card,
            text=initial_val,
            font_key="stat_num",
            fg_key="text_dark",
            bg_key="card_bg"
        )
        val_lbl.pack(anchor=tk.W, pady=(4, 2))

        sub_lbl = create_label(
            card,
            text=sub_text,
            font_key="small",
            fg_key="text_muted",
            bg_key="card_bg"
        )
        sub_lbl.pack(anchor=tk.W)

        card.val_lbl = val_lbl
        card.sub_lbl = sub_lbl
        return card

    def _create_action_btn(self, parent, text, cmd):
        btn = ttk.Button(
            parent,
            text=text,
            command=cmd
        )
        btn.pack(fill=tk.X, pady=(0, 8), ipady=3)

    def refresh_data(self):
        username = auth.Session.get_username()
        self.welcome_label.config(text=f"Welcome back, {username.capitalize()}!")

        metrics = ReportService.get_dashboard_metrics()

        self.card_products.val_lbl.config(text=str(metrics["active_products"]))
        self.card_products.sub_lbl.config(text=f"{metrics['active_products']} active catalog items")

        self.card_value.val_lbl.config(text=format_currency(metrics["inventory_valuation_minor"]))

        low_count = metrics["low_stock_count"]
        self.card_low.val_lbl.config(text=str(low_count))
        self.card_low.sub_lbl.config(text="Items ≤ alert threshold")

        today_rev = metrics["today_revenue_minor"]
        today_bills = metrics["today_bills"]
        self.card_sales.val_lbl.config(text=format_currency(today_rev))
        self.card_sales.sub_lbl.config(text=f"{today_bills} invoice(s) today")

        if low_count > 0:
            self.alert_label.config(text=f"Notice: {low_count} product(s) are low on stock and need restock!")
            self.alert_frame.pack(fill=tk.X, pady=(0, 15), before=self.cards_frame)
        else:
            self.alert_frame.pack_forget()

        for it in self.tree.get_children():
            self.tree.delete(it)

        recent_bills = BillingService.get_all_bills()[:7]
        for b in recent_bills:
            self.tree.insert("", tk.END, values=(
                f"#{b['id']}",
                b["created_at"],
                b["customer"],
                format_currency(b["total_minor"])
            ))
