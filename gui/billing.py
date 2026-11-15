"""
Point of Sale (POS) and Billing view for Inventory & Shop Management System.
Uses high-contrast standard widgets for 100% visibility across macOS (Light & Dark), Windows, and Linux.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from services import ProductService, BillingService
from utils import (
    COLORS, FONTS, format_currency, paise_to_rupees_str,
    validate_bill_item_qty, create_card, create_label, create_entry
)


class BillingFrame(tk.Frame):
    def __init__(self, parent, on_sale_completed=None):
        super().__init__(parent, bg=COLORS["bg_light"])
        self.on_sale_completed = on_sale_completed

        self.cart = []
        self.products_lookup = {}

        self._build_ui()
        self.refresh_products_list()

    def _build_ui(self):
        container = tk.Frame(self, bg=COLORS["bg_light"], padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Header Bar
        header = tk.Frame(container, bg=COLORS["bg_light"])
        header.pack(fill=tk.X, pady=(0, 12))

        create_label(
            header,
            text="🛒 Point of Sale & Billing",
            font_key="heading",
            fg_key="text_dark",
            bg_key="bg_light"
        ).pack(side=tk.LEFT)

        today_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
        create_label(
            header,
            text=f"Terminal Session: {today_str}",
            font_key="body",
            fg_key="text_muted",
            bg_key="bg_light"
        ).pack(side=tk.RIGHT)

        # Split Layout
        split_frame = tk.Frame(container, bg=COLORS["bg_light"])
        split_frame.pack(fill=tk.BOTH, expand=True)

        # Left Panel (Add Box + Cart Table)
        left_panel = tk.Frame(split_frame, bg=COLORS["bg_light"])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        # Add to Cart Box
        add_box = create_card(left_panel, padx=16, pady=12)
        add_box.pack(fill=tk.X, pady=(0, 12))

        # Row 1: Customer
        row_cust = tk.Frame(add_box, bg=COLORS["card_bg"])
        row_cust.pack(fill=tk.X, pady=(0, 10))

        create_label(row_cust, text="Customer Name:", font_key="body_bold", fg_key="text_dark", bg_key="card_bg").pack(side=tk.LEFT, padx=(0, 10))
        self.customer_var = tk.StringVar(value="Walk-in Customer")
        self.customer_entry = create_entry(
            row_cust,
            textvariable=self.customer_var,
            width=28
        )
        self.customer_entry.pack(side=tk.LEFT, ipady=3)

        # Row 2: Product & Qty
        row_prod = tk.Frame(add_box, bg=COLORS["card_bg"])
        row_prod.pack(fill=tk.X, pady=(0, 8))

        create_label(row_prod, text="Select Product:", font_key="body_bold", fg_key="text_dark", bg_key="card_bg").pack(side=tk.LEFT, padx=(0, 10))
        self.selected_prod_str = tk.StringVar()
        self.product_cb = ttk.Combobox(row_prod, textvariable=self.selected_prod_str, font=FONTS["body"], width=32, state="readonly")
        self.product_cb.pack(side=tk.LEFT, padx=(0, 12), ipady=2)
        self.product_cb.bind("<<ComboboxSelected>>", self._on_product_selected)

        create_label(row_prod, text="Qty:", font_key="body_bold", fg_key="text_dark", bg_key="card_bg").pack(side=tk.LEFT, padx=(0, 5))
        self.qty_var = tk.StringVar(value="1")
        self.qty_spinbox = ttk.Spinbox(row_prod, from_=1, to=9999, textvariable=self.qty_var, width=5, font=FONTS["body"])
        self.qty_spinbox.pack(side=tk.LEFT, padx=(0, 12), ipady=2)
        self.qty_spinbox.bind("<Return>", lambda e: self._add_item_to_cart())

        self.add_cart_btn = ttk.Button(
            row_prod,
            text="➕ Add to Cart",
            command=self._add_item_to_cart
        )
        self.add_cart_btn.pack(side=tk.LEFT)

        # Info Label
        self.info_lbl = create_label(
            add_box,
            text="Select an active catalog item to check availability",
            font_key="small",
            fg_key="text_muted",
            bg_key="card_bg"
        )
        self.info_lbl.pack(anchor=tk.W)

        # Cart Table Card
        cart_card = create_card(left_panel, padx=2, pady=2)
        cart_card.pack(fill=tk.BOTH, expand=True)

        cols = ("pid", "name", "price", "qty", "total")
        self.cart_tree = ttk.Treeview(cart_card, columns=cols, show="headings", selectmode="browse")

        self.cart_tree.heading("pid", text="ID")
        self.cart_tree.heading("name", text="Product Item")
        self.cart_tree.heading("price", text="Unit Price")
        self.cart_tree.heading("qty", text="Quantity")
        self.cart_tree.heading("total", text="Line Total")

        self.cart_tree.column("pid", width=40, anchor=tk.CENTER)
        self.cart_tree.column("name", width=220, anchor=tk.W)
        self.cart_tree.column("price", width=90, anchor=tk.E)
        self.cart_tree.column("qty", width=70, anchor=tk.CENTER)
        self.cart_tree.column("total", width=100, anchor=tk.E)

        vsb = ttk.Scrollbar(cart_card, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=vsb.set)

        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Cart Actions Footer
        cart_actions = tk.Frame(left_panel, bg=COLORS["bg_light"], pady=6)
        cart_actions.pack(fill=tk.X)

        ttk.Button(
            cart_actions,
            text="❌ Remove Selected Item",
            command=self._remove_selected_cart_item
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            cart_actions,
            text="🧹 Clear Entire Cart",
            command=self._clear_cart
        ).pack(side=tk.LEFT)

        # Right Panel: Invoice Summary Card
        checkout_card = create_card(split_frame, padx=16, pady=16, width=310)
        checkout_card.pack(side=tk.RIGHT, fill=tk.Y)
        checkout_card.pack_propagate(False)

        create_label(
            checkout_card,
            text="🧾 Bill Summary",
            font_key="heading",
            fg_key="text_dark",
            bg_key="card_bg"
        ).pack(anchor=tk.W, pady=(0, 12))

        self.total_items_lbl = create_label(
            checkout_card,
            text="Items in Cart: 0",
            font_key="body",
            fg_key="text_muted",
            bg_key="card_bg"
        )
        self.total_items_lbl.pack(anchor=tk.W, pady=(0, 8))

        subtotal_frame = tk.Frame(checkout_card, bg=COLORS["card_bg"])
        subtotal_frame.pack(fill=tk.X, pady=(0, 8))
        create_label(subtotal_frame, text="Subtotal:", font_key="body_bold", fg_key="text_dark", bg_key="card_bg").pack(side=tk.LEFT)
        self.subtotal_lbl = create_label(subtotal_frame, text="₹0.00", font_key="body_bold", fg_key="text_dark", bg_key="card_bg")
        self.subtotal_lbl.pack(side=tk.RIGHT)

        ttk.Separator(checkout_card, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        create_label(
            checkout_card,
            text="TOTAL PAYABLE",
            font_key="body_bold",
            fg_key="text_muted",
            bg_key="card_bg"
        ).pack(anchor=tk.W)

        self.grand_total_lbl = create_label(
            checkout_card,
            text="₹0.00",
            font_key="stat_num",
            fg_key="accent",
            bg_key="card_bg"
        )
        self.grand_total_lbl.pack(anchor=tk.W, pady=(2, 20))

        # Checkout Button
        self.checkout_btn = ttk.Button(
            checkout_card,
            text="💳 Complete Sale & Print",
            command=self._handle_checkout
        )
        self.checkout_btn.pack(fill=tk.X, pady=(0, 10), ipady=6)

    def refresh_products_list(self):
        rows = ProductService.get_products(include_inactive=False)
        self.products_lookup.clear()
        cb_values = []

        for r in rows:
            self.products_lookup[r["id"]] = r
            status_text = f"Stock: {r['quantity']}" if r["quantity"] > 0 else "OUT OF STOCK"
            cb_values.append(f"#{r['id']} - {r['name']} ({format_currency(r['price_minor'])}) [{status_text}]")

        self.product_cb["values"] = cb_values
        if cb_values:
            self.product_cb.current(0)
            self._on_product_selected()

    def _on_product_selected(self, event=None):
        selected_str = self.selected_prod_str.get()
        if not selected_str or not selected_str.startswith("#"):
            return

        try:
            prod_id = int(selected_str.split(" - ")[0].replace("#", ""))
            prod = self.products_lookup.get(prod_id)
            if prod:
                qty = prod["quantity"]
                price_minor = prod["price_minor"]
                if qty <= 0:
                    self.info_lbl.config(
                        text=f"⚠️ {prod['name']} is OUT OF STOCK. Cannot bill.",
                        fg=COLORS["danger"]
                    )
                else:
                    self.info_lbl.config(
                        text=f"Price: {format_currency(price_minor)}  |  Available: {qty} units",
                        fg=COLORS["text_muted"]
                    )
        except Exception:
            pass

    def _add_item_to_cart(self):
        selected_str = self.selected_prod_str.get()
        if not selected_str or not selected_str.startswith("#"):
            messagebox.showwarning("Selection Required", "Please select a product from the dropdown.")
            return

        prod_id = int(selected_str.split(" - ")[0].replace("#", ""))
        prod = self.products_lookup.get(prod_id)
        if not prod:
            messagebox.showerror("Error", "Product not found in active catalog.")
            return

        avail_stock = prod["quantity"]
        if avail_stock <= 0:
            messagebox.showerror("Out of Stock", f"'{prod['name']}' has zero available stock.")
            return

        already = next((i for i in self.cart if i["product_id"] == prod_id), None)
        existing_qty = already["quantity"] if already else 0

        ok, err, req_qty = validate_bill_item_qty(avail_stock - existing_qty, self.qty_var.get())
        if not ok:
            messagebox.showerror("Stock Limit Reached", err)
            return

        if already:
            already["quantity"] += req_qty
            already["line_total_minor"] = already["quantity"] * already["unit_price_minor"]
        else:
            self.cart.append({
                "product_id": prod["id"],
                "name": prod["name"],
                "unit_price_minor": prod["price_minor"],
                "quantity": req_qty,
                "line_total_minor": req_qty * prod["price_minor"],
                "max_stock": avail_stock
            })

        self.qty_var.set("1")
        self._refresh_cart_view()

    def _remove_selected_cart_item(self):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select an item from the cart table to remove.")
            return

        idx = self.cart_tree.index(selected[0])
        del self.cart[idx]
        self._refresh_cart_view()

    def _clear_cart(self):
        if not self.cart:
            return
        if messagebox.askyesno("Clear Cart", "Are you sure you want to remove all items from the cart?"):
            self.cart.clear()
            self._refresh_cart_view()

    def _refresh_cart_view(self):
        for it in self.cart_tree.get_children():
            self.cart_tree.delete(it)

        subtotal_minor = 0
        total_qty = 0

        for it in self.cart:
            subtotal_minor += it["line_total_minor"]
            total_qty += it["quantity"]
            self.cart_tree.insert("", tk.END, values=(
                it["product_id"],
                it["name"],
                format_currency(it["unit_price_minor"]),
                it["quantity"],
                format_currency(it["line_total_minor"])
            ))

        self.total_items_lbl.config(text=f"Items in Cart: {total_qty} ({len(self.cart)} distinct)")
        self.subtotal_lbl.config(text=format_currency(subtotal_minor))
        self.grand_total_lbl.config(text=format_currency(subtotal_minor))

    def _handle_checkout(self):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Cannot checkout an empty cart. Please add products first.")
            return

        customer = self.customer_var.get().strip() or "Walk-in Customer"
        total_minor = sum(it["line_total_minor"] for it in self.cart)

        confirm = messagebox.askyesno(
            "Confirm Checkout",
            f"Generate invoice for {customer}?\n"
            f"Total: {format_currency(total_minor)}\n\n"
            "This will record the transaction and deduct inventory stock.",
            icon="question"
        )
        if not confirm:
            return

        self.checkout_btn.config(state=tk.DISABLED)
        self.update_idletasks()

        try:
            bill_id, final_total_minor = BillingService.process_checkout(customer, self.cart)

            self._show_receipt_dialog(bill_id, customer, list(self.cart), final_total_minor)

            self.cart.clear()
            self.customer_var.set("Walk-in Customer")
            self._refresh_cart_view()
            self.refresh_products_list()

            if self.on_sale_completed:
                self.on_sale_completed()

        except Exception as e:
            messagebox.showerror(
                "Checkout Aborted",
                f"Checkout could not be completed:\n\n{e}\n\n"
                "Your cart has been preserved so you can adjust quantities and retry."
            )
        finally:
            self.checkout_btn.config(state=tk.NORMAL)

    def _show_receipt_dialog(self, bill_id, customer, items, total_minor):
        dialog = tk.Toplevel(self)
        dialog.title(f"Receipt - Bill #{bill_id}")
        dialog.geometry("450x550")
        dialog.configure(bg=COLORS["bg_light"])
        dialog.grab_set()

        create_label(
            dialog,
            text="🏪 STORE INVOICE RECEIPT",
            font_key="heading",
            fg_key="text_dark",
            bg_key="bg_light"
        ).pack(pady=(15, 4))

        create_label(
            dialog,
            text="Thank you for your business!",
            font_key="small",
            fg_key="text_muted",
            bg_key="bg_light"
        ).pack(pady=(0, 10))

        receipt_box = tk.Text(
            dialog,
            font=("Courier", 10),
            fg=COLORS["text_dark"],
            bg=COLORS["card_bg"],
            relief=tk.SOLID,
            bd=1,
            padx=12,
            pady=10
        )
        receipt_box.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=" * 44,
            f"INVOICE NUMBER: #{bill_id}",
            f"DATE & TIME   : {now_str}",
            f"CUSTOMER NAME : {customer}",
            "=" * 44,
            f"{'ITEM':<20} {'QTY':>4} {'PRICE':>8} {'TOTAL':>9}",
            "-" * 44
        ]

        for it in items:
            pname = it["name"][:18]
            uprice_str = paise_to_rupees_str(it["unit_price_minor"])
            ltotal_str = paise_to_rupees_str(it["line_total_minor"])
            lines.append(f"{pname:<20} {it['quantity']:>4} {uprice_str:>8} {ltotal_str:>9}")

        lines.extend([
            "-" * 44,
            f"{'GRAND TOTAL':<25} : {format_currency(total_minor):>16}",
            "=" * 44,
            "",
            "   Goods once sold are subject to store policy.",
            "              HAVE A GREAT DAY!"
        ])

        receipt_text = "\n".join(lines)
        receipt_box.insert(tk.END, receipt_text)
        receipt_box.config(state=tk.DISABLED)

        btn_bar = tk.Frame(dialog, bg=COLORS["bg_light"], padx=20, pady=10)
        btn_bar.pack(fill=tk.X)

        def save_txt():
            fp = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                initialfile=f"receipt_{bill_id}.txt"
            )
            if fp:
                try:
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(receipt_text)
                    messagebox.showinfo("Saved", f"Receipt saved to:\n{fp}")
                except Exception as ex:
                    messagebox.showerror("Error", f"Failed to save file: {ex}")

        ttk.Button(
            btn_bar,
            text="💾 Save Receipt (.txt)",
            command=save_txt
        ).pack(side=tk.LEFT)

        ttk.Button(
            btn_bar,
            text="Close",
            command=dialog.destroy
        ).pack(side=tk.RIGHT)
