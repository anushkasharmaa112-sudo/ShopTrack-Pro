"""
Utility functions, currency conversion, validation logic, and UI constants.
High-contrast professional styling engineered for crisp text visibility on macOS.
"""

import re
import tkinter as tk
from tkinter import ttk
from typing import Tuple, Optional


# ==========================================
# UI Theme & Color Palette (High-Contrast Clean Theme)
# ==========================================
COLORS = {
    "primary": "#1E293B",        # Slate dark (header, sidebar)
    "primary_hover": "#334155",  # Hover for primary nav
    "accent": "#2563EB",         # Royal blue for action buttons
    "accent_hover": "#1D4ED8",   # Darker royal blue
    "success": "#16A34A",        # Emerald green for save/complete/in-stock
    "success_hover": "#15803D",
    "danger": "#DC2626",         # Crimson red
    "danger_hover": "#B91C1C",
    "warning": "#D97706",        # Amber for low-stock warnings
    "bg_light": "#F8FAFC",       # Clean light slate canvas background
    "card_bg": "#FFFFFF",        # White for cards & panels
    "input_bg": "#FFFFFF",       # Input fields background (White)
    "input_fg": "#0F172A",       # Input fields text: Deep dark black/slate!
    "border": "#CBD5E1",         # Crisp slate border
    "text_dark": "#0F172A",      # Primary text: Deep black / dark slate (High Contrast!)
    "text_muted": "#475569",     # Secondary text: Slate dark gray (High Contrast!)
    "white": "#FFFFFF",
}

FONTS = {
    "title": ("Helvetica", 18, "bold"),
    "subtitle": ("Helvetica", 14, "bold"),
    "heading": ("Helvetica", 12, "bold"),
    "body": ("Helvetica", 11),
    "body_bold": ("Helvetica", 11, "bold"),
    "small": ("Helvetica", 9),
    "stat_num": ("Helvetica", 22, "bold"),
}

CURRENCY_SYMBOL = "₹"


# ==========================================
# Robust UI Widget Factories (Dark/Light Mode Immune)
# ==========================================
def create_card(parent, **kwargs):
    """Creates a standard white elevated card with a crisp border."""
    bg = kwargs.pop("bg", COLORS["card_bg"])
    border = kwargs.pop("highlightbackground", COLORS["border"])
    thickness = kwargs.pop("highlightthickness", 1)
    return tk.Frame(parent, bg=bg, highlightbackground=border, highlightthickness=thickness, **kwargs)


def create_label(parent, text="", font_key="body", fg_key="text_dark", bg_key="card_bg", **kwargs):
    """Creates an explicit high-contrast tk.Label immune to macOS Cocoa dark mode bugs."""
    font = FONTS.get(font_key, FONTS["body"]) if isinstance(font_key, str) else font_key
    fg = COLORS.get(fg_key, fg_key) if isinstance(fg_key, str) and fg_key in COLORS else fg_key
    bg = COLORS.get(bg_key, bg_key) if isinstance(bg_key, str) and bg_key in COLORS else bg_key
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kwargs)


def create_entry(parent, textvariable=None, font_key="body", **kwargs):
    """Creates a high-contrast standard tk.Entry with visible border and cursor."""
    font = FONTS.get(font_key, FONTS["body"]) if isinstance(font_key, str) else font_key
    return tk.Entry(
        parent,
        textvariable=textvariable,
        font=font,
        fg=COLORS["text_dark"],
        bg=COLORS["input_bg"],
        relief=tk.SOLID,
        bd=1,
        insertbackground=COLORS["text_dark"],
        highlightcolor=COLORS["accent"],
        highlightthickness=1,
        **kwargs
    )


def configure_treeview_styles(style: ttk.Style):
    """Ensures Treeview and Headings have explicit high-contrast styling."""
    style.configure(
        "Treeview",
        background="#FFFFFF",
        foreground="#0F172A",
        fieldbackground="#FFFFFF",
        rowheight=28,
        font=FONTS["body"]
    )
    style.configure(
        "Treeview.Heading",
        background="#E2E8F0",
        foreground="#0F172A",
        font=FONTS["body_bold"],
        padding=(6, 6)
    )
    style.map(
        "Treeview",
        background=[("selected", "#2563EB")],
        foreground=[("selected", "#FFFFFF")]
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#CBD5E1")]
    )


# ==========================================
# Money & Minor Units Conversions
# ==========================================
def rupees_to_paise(amount_str: str) -> Tuple[bool, str, int]:
    clean_str = (amount_str or "").strip().replace(",", "")
    if not clean_str:
        return False, "Price cannot be empty.", 0

    match = re.match(r"^(\d+)(?:\.(\d{1,2}))?$", clean_str)
    if not match:
        return False, "Please enter a valid price (e.g. 199 or 199.50).", 0

    whole_part = int(match.group(1))
    fraction_str = (match.group(2) or "").ljust(2, "0")
    fraction_part = int(fraction_str)

    if whole_part > 10_000_000:
        return False, "Price exceeds allowed store limits.", 0

    total_paise = whole_part * 100 + fraction_part
    return True, "", total_paise


def paise_to_rupees_str(paise: int) -> str:
    try:
        paise = int(paise)
        whole = paise // 100
        frac = paise % 100
        return f"{whole}.{frac:02d}"
    except (ValueError, TypeError):
        return "0.00"


def format_currency(paise: int) -> str:
    try:
        paise = int(paise)
        whole = paise // 100
        frac = paise % 100
        return f"{CURRENCY_SYMBOL}{whole:,}.{frac:02d}"
    except (ValueError, TypeError):
        return f"{CURRENCY_SYMBOL}0.00"


def format_date(date_str: Optional[str]) -> str:
    if not date_str:
        return "N/A"
    return str(date_str)


# ==========================================
# Input Validators
# ==========================================
def validate_product_data(
    name: str,
    category: str,
    price_str: str,
    quantity_str: str,
    low_stock_str: str = "10"
) -> Tuple[bool, str, Optional[dict]]:
    name = (name or "").strip()
    category = (category or "").strip()

    if not name or len(name) < 2:
        return False, "Product name must be at least 2 characters long.", None
    if len(name) > 100:
        return False, "Product name cannot exceed 100 characters.", None

    if not category:
        category = "General"

    ok, err, price_minor = rupees_to_paise(price_str)
    if not ok:
        return False, err, None

    try:
        quantity = int(quantity_str)
        if quantity < 0:
            return False, "Stock quantity cannot be negative.", None
        if quantity > 1_000_000:
            return False, "Stock quantity is too large.", None
    except (ValueError, TypeError):
        return False, "Stock quantity must be a non-negative whole number.", None

    try:
        low_stock = int(low_stock_str) if low_stock_str else 10
        if low_stock < 0:
            return False, "Low stock threshold cannot be negative.", None
    except (ValueError, TypeError):
        return False, "Low stock threshold must be an integer.", None

    cleaned = {
        "name": name,
        "category": category,
        "price_minor": price_minor,
        "quantity": quantity,
        "low_stock": low_stock
    }
    return True, "", cleaned


def validate_user_credentials(username: str, password: str) -> Tuple[bool, str]:
    u = (username or "").strip()
    p = (password or "").strip()

    if not u or len(u) < 3:
        return False, "Username must be at least 3 characters long."
    if len(u) > 50:
        return False, "Username cannot exceed 50 characters."
    if not p or len(p) < 4:
        return False, "Password must be at least 4 characters long."

    return True, ""


def validate_bill_item_qty(available_stock: int, requested_qty_str: str) -> Tuple[bool, str, int]:
    try:
        qty = int(requested_qty_str)
        if qty <= 0:
            return False, "Quantity must be greater than zero.", 0
        if qty > available_stock:
            return False, f"Insufficient stock! Available: {available_stock}, Requested: {qty}", 0
        return True, "", qty
    except (ValueError, TypeError):
        return False, "Please enter a valid whole number for quantity.", 0
