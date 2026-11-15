"""
Main Application Entry Point for Inventory & Shop Management System.
Built with high-contrast styling engineered for 100% macOS, Windows, and Linux compatibility.
"""

import os
import sys

# Silence macOS deprecation notice
os.environ["TK_SILENCE_DEPRECATION"] = "1"

import tkinter as tk
from tkinter import ttk, messagebox
import database
import auth
from utils import (
    COLORS, FONTS, configure_treeview_styles,
    create_card, create_label
)
from gui.login_frame import LoginFrame
from gui.dashboard import DashboardFrame
from gui.products import ProductsFrame
from gui.billing import BillingFrame
from gui.sales import SalesFrame
from gui.reports import ReportsFrame


class ShopManagementApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ShopTrack — Inventory & Billing Management System")
        self.geometry("1180x740")
        self.minsize(1020, 650)
        self.configure(bg=COLORS["bg_light"])

        # Center window on screen
        self._center_window(1180, 740)

        # Bring window to front on launch
        self.lift()
        self.attributes('-topmost', True)
        self.after(200, lambda: self.attributes('-topmost', False))

        # Initialize SQLite database
        database.init_db()

        # Configure styles
        self._configure_styles()

        # State
        self.current_view = None
        self.nav_buttons = {}

        # Show Login Screen initially
        self.show_login_screen()

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, int((screen_width - width) / 2))
        y = max(0, int((screen_height - height) / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _configure_styles(self):
        style = ttk.Style(self)
        if sys.platform != "darwin":
            try:
                style.theme_use("clam")
            except Exception:
                pass

        # Central Treeview styling
        configure_treeview_styles(style)

        # Notebook tabs styling
        style.configure(
            "TNotebook",
            background=COLORS["bg_light"]
        )
        style.configure(
            "TNotebook.Tab",
            font=FONTS["body_bold"],
            padding=(15, 6)
        )

    # ============================================================
    # Screen Switching: Login vs Main App Layout
    # ============================================================
    def show_login_screen(self):
        """Clear window and show the login card."""
        for widget in self.winfo_children():
            widget.destroy()

        self.login_view = LoginFrame(self, on_login_success=self.on_login_success)
        self.login_view.pack(fill=tk.BOTH, expand=True)

    def on_login_success(self, user_dict):
        """Called upon successful user authentication."""
        auth.Session.login(user_dict)
        self.login_view.destroy()
        self._build_main_layout()
        self.navigate_to("dashboard")

    def _build_main_layout(self):
        # 1. Header Bar (Deep Slate Navy, Crisp White Text)
        header = tk.Frame(self, bg=COLORS["primary"], padx=20, pady=12)
        header.pack(side=tk.TOP, fill=tk.X)

        # Left branding
        create_label(
            header,
            text="🏪  ShopTrack Pro",
            font_key="title",
            fg_key="white",
            bg_key="primary"
        ).pack(side=tk.LEFT)

        # Right User profile & Logout
        right_header = tk.Frame(header, bg=COLORS["primary"])
        right_header.pack(side=tk.RIGHT)

        username = auth.Session.get_username()
        role = "Admin"
        if auth.Session.current_user and isinstance(auth.Session.current_user, dict):
            role = auth.Session.current_user.get("role", "admin").capitalize()

        create_label(
            right_header,
            text=f"👤 Logged in as: {username.capitalize()} ({role})",
            font_key="body",
            fg_key="#E2E8F0",
            bg_key="primary"
        ).pack(side=tk.LEFT, padx=(0, 15))

        logout_btn = ttk.Button(
            right_header,
            text="Logout ➔",
            command=self._handle_logout
        )
        logout_btn.pack(side=tk.LEFT)

        # 2. Bottom Status Bar
        status_bar = tk.Frame(self, bg="#E2E8F0", padx=15, pady=6)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = create_label(
            status_bar,
            text="● System Ready | SQLite DB: shop.db | Concurrency Safe (v2)",
            font_key="small",
            fg_key="#334155",
            bg_key="#E2E8F0"
        )
        self.status_label.pack(side=tk.LEFT)

        # 3. Main Center Workspace (Sidebar Left + Content Area Right)
        workspace = tk.Frame(self, bg=COLORS["bg_light"])
        workspace.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar Card
        self.sidebar = create_card(workspace, padx=12, pady=15, width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 6), pady=(8, 8))
        self.sidebar.pack_propagate(False)

        create_label(
            self.sidebar,
            text="MAIN MENU",
            font_key="small",
            fg_key="text_muted",
            bg_key="card_bg"
        ).pack(anchor=tk.W, padx=4, pady=(0, 10))

        # Navigation Buttons
        nav_items = [
            ("dashboard", "📊 Dashboard"),
            ("products", "📦 Products Catalog"),
            ("billing", "🛒 Point of Sale"),
            ("sales", "📜 Sales History"),
            ("reports", "📈 Reports & Restock"),
        ]

        self.nav_buttons.clear()
        for key, label in nav_items:
            btn = ttk.Button(
                self.sidebar,
                text=label,
                command=lambda k=key: self.navigate_to(k)
            )
            btn.pack(fill=tk.X, pady=(0, 8), ipady=3)
            self.nav_buttons[key] = btn

        # Content Area Container
        self.content_area = tk.Frame(workspace, bg=COLORS["bg_light"])
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 12), pady=(8, 8))

        # Pre-instantiate frames for fast switching
        self.frames = {
            "dashboard": DashboardFrame(self.content_area, navigate_callback=self.navigate_to),
            "products": ProductsFrame(self.content_area, on_data_changed=self._on_inventory_changed),
            "billing": BillingFrame(self.content_area, on_sale_completed=self._on_sale_made),
            "sales": SalesFrame(self.content_area),
            "reports": ReportsFrame(self.content_area, on_data_changed=self._on_inventory_changed)
        }

    def navigate_to(self, view_name: str):
        if view_name not in self.frames:
            return

        if self.current_view and self.current_view in self.frames:
            self.frames[self.current_view].pack_forget()

        target_frame = self.frames[view_name]
        target_frame.pack(fill=tk.BOTH, expand=True)
        self.current_view = view_name

        if hasattr(target_frame, "refresh_data"):
            target_frame.refresh_data()
        elif hasattr(target_frame, "load_products"):
            target_frame.load_products()
        elif hasattr(target_frame, "refresh_products_list"):
            target_frame.refresh_products_list()
        elif hasattr(target_frame, "load_bills"):
            target_frame.load_bills()
        elif hasattr(target_frame, "refresh_all_reports"):
            target_frame.refresh_all_reports()

        self.status_label.config(text=f"● Viewing: {view_name.capitalize()} | Database Active")

    def _on_inventory_changed(self):
        if "dashboard" in self.frames:
            self.frames["dashboard"].refresh_data()
        if "billing" in self.frames:
            self.frames["billing"].refresh_products_list()
        if "reports" in self.frames:
            self.frames["reports"].refresh_all_reports()

    def _on_sale_made(self):
        if "dashboard" in self.frames:
            self.frames["dashboard"].refresh_data()
        if "sales" in self.frames:
            self.frames["sales"].load_bills()
        if "reports" in self.frames:
            self.frames["reports"].refresh_all_reports()
        if "products" in self.frames:
            self.frames["products"].load_products()

    def _handle_logout(self):
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to log out?"):
            auth.Session.logout()
            self.show_login_screen()


def main():
    app = ShopManagementApp()
    app.mainloop()


if __name__ == "__main__":
    main()
