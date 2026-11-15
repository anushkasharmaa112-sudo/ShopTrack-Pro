"""
Currency formatting and input validation for the web interface.
Mirrors utils.py without the Tkinter dependency so the web app runs on any server.
"""

import re
from typing import Optional, Tuple

CURRENCY_SYMBOL = "₹"


def rupees_to_paise(amount_str: str) -> Tuple[bool, str, int]:
    clean_str = (amount_str or "").strip().replace(",", "")
    if not clean_str:
        return False, "Price cannot be empty.", 0
    match = re.match(r"^(\d+)(?:\.(\d{1,2}))?$", clean_str)
    if not match:
        return False, "Please enter a valid price (e.g. 199 or 199.50).", 0
    whole_part = int(match.group(1))
    fraction_part = int((match.group(2) or "").ljust(2, "0"))
    if whole_part > 10_000_000:
        return False, "Price exceeds allowed store limits.", 0
    return True, "", whole_part * 100 + fraction_part


def paise_to_rupees_str(paise) -> str:
    try:
        paise = int(paise)
        return f"{paise // 100}.{paise % 100:02d}"
    except (ValueError, TypeError):
        return "0.00"


def format_currency(paise) -> str:
    try:
        paise = int(paise)
        return f"{CURRENCY_SYMBOL}{paise // 100:,}.{paise % 100:02d}"
    except (ValueError, TypeError):
        return f"{CURRENCY_SYMBOL}0.00"


def parse_int(value, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def validate_product_data(name, category, price_str, quantity_str, low_stock_str="10") -> Tuple[bool, str, Optional[dict]]:
    name = (name or "").strip()
    category = (category or "").strip() or "General"
    if len(name) < 2:
        return False, "Product name must be at least 2 characters long.", None
    if len(name) > 100:
        return False, "Product name cannot exceed 100 characters.", None

    ok, err, price_minor = rupees_to_paise(price_str)
    if not ok:
        return False, err, None

    quantity = parse_int(quantity_str)
    if quantity is None or quantity < 0:
        return False, "Stock quantity must be a non-negative whole number.", None
    if quantity > 1_000_000:
        return False, "Stock quantity is too large.", None

    low_stock = parse_int(low_stock_str, 10) if str(low_stock_str or "").strip() else 10
    if low_stock is None or low_stock < 0:
        return False, "Low stock threshold must be a non-negative whole number.", None

    return True, "", {
        "name": name,
        "category": category,
        "price_minor": price_minor,
        "quantity": quantity,
        "low_stock": low_stock,
    }


def validate_user_credentials(username: str, password: str) -> Tuple[bool, str]:
    u = (username or "").strip()
    p = (password or "").strip()
    if len(u) < 3:
        return False, "Username must be at least 3 characters long."
    if len(u) > 50:
        return False, "Username cannot exceed 50 characters."
    if len(p) < 4:
        return False, "Password must be at least 4 characters long."
    return True, ""
