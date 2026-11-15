"""
Product Inventory Management View for Inventory & Shop Management System.
Uses high-contrast standard widgets for 100% visibility across macOS (Light & Dark), Windows, and Linux.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from services import ProductService
from utils import (
    COLORS, FONTS, format_currency, paise_to_rupees_str,
    validate_product_data, create_card, create_label, create_entry
)


class ProductsFrame(tk.Frame):
    def __init__(self, parent, on_data_changed=None):
        super().__init__(parent, bg=COLORS["bg_light"])
        self.on_data_changed = on_data_changed
        self.selected_product = None

        self._build_ui()
        self.load_categories()
        self.load_products()

    def _build_ui(self):
        container = tk.Frame(self, bg=COLORS["bg_light"], padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # Top Control Bar
        # ----------------------------------------------------
        top_bar = tk.Frame(container, bg=COLORS["bg_light"])
        top_bar.pack(fill=tk.X, pady=(0, 12))

        create_label(
            top_bar,
            text="📦 Product Catalog",
            font_key="heading",
            fg_key="text_dark",
            bg_key="bg_light"
        ).pack(side=tk.LEFT, padx=(0, 15))

        # Search Box
        create_label(top_bar, text="Search:", font_key="body_bold", fg_key="text_dark", bg_key="bg_light").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = create_entry(top_bar, textvariable=self.search_var, width=16)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=3)
        self.search_entry.bind("<Return>", lambda e: self.load_products())

        # Category Filter
        create_label(top_bar, text="Category:", font_key="body_bold", fg_key="text_dark", bg_key="bg_light").pack(side=tk.LEFT, padx=(0, 5))
        self.cat_filter_var = tk.StringVar(value="All")
        self.cat_filter_cb = ttk.Combobox(top_bar, textvariable=self.cat_filter_var, state="readonly", width=12, font=FONTS["body"])
        self.cat_filter_cb.pack(side=tk.LEFT, padx=(0, 10), ipady=2)
        self.cat_filter_cb.bind("<<ComboboxSelected>>", lambda e: self.load_products())

        # Show Inactive Checkbox
        self.show_inactive_var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(
            top_bar,
            text="Show Archived",
            variable=self.show_inactive_var,
            command=self.load_products,
            font=FONTS["body"],
            fg=COLORS["text_dark"],
            bg=COLORS["bg_light"],
            activebackground=COLORS["bg_light"],
            selectcolor=COLORS["card_bg"]
        )
        cb.pack(side=tk.LEFT, padx=(0, 10))

        # Filter & Reset Buttons
        ttk.Button(
            top_bar,
            text="🔍 Filter",
            command=self.load_products
        ).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(
            top_bar,
            text="Reset",
            command=self._reset_filters
        ).pack(side=tk.LEFT)

        # Export CSV Button
        ttk.Button(
            top_bar,
            text="📥 Export CSV",
            command=self._export_csv
        ).pack(side=tk.RIGHT)

        # ----------------------------------------------------
        # Main Layout (Split: Table Left, Form Right)
        # ----------------------------------------------------
        split_frame = tk.Frame(container, bg=COLORS["bg_light"])
        split_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Treeview in Card
        table_card = create_card(split_frame, padx=2, pady=2)
        table_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        cols = ("id", "name", "category", "price", "quantity", "low_stock", "status")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Product Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("price", text="Unit Price")
        self.tree.heading("quantity", text="Stock")
        self.tree.heading("low_stock", text="Threshold")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=45, anchor=tk.CENTER)
        self.tree.column("name", width=170, anchor=tk.W)
        self.tree.column("category", width=100, anchor=tk.W)
        self.tree.column("price", width=80, anchor=tk.E)
        self.tree.column("quantity", width=65, anchor=tk.CENTER)
        self.tree.column("low_stock", width=75, anchor=tk.CENTER)
        self.tree.column("status", width=95, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_card, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)

        # Right: Product Form Card
        form_card = create_card(split_frame, padx=16, pady=16, width=340)
        form_card.pack(side=tk.RIGHT, fill=tk.Y)
        form_card.pack_propagate(False)

        create_label(
            form_card,
            text="📝 Product Editor",
            font_key="heading",
            fg_key="text_dark",
            bg_key="card_bg"
        ).pack(anchor=tk.W, pady=(0, 4))

        self.id_lbl_var = tk.StringVar(value="Status: Adding New Product")
        self.status_header_lbl = create_label(
            form_card,
            text=self.id_lbl_var.get(),
            font_key="small",
            fg_key="text_muted",
            bg_key="card_bg"
        )
        self.status_header_lbl.pack(anchor=tk.W, pady=(0, 8))

        # Form Entries
        self.name_var = tk.StringVar()
        self._create_field(form_card, "Product Name *", self.name_var)

        create_label(form_card, text="Category *", font_key="body_bold", fg_key="text_dark", bg_key="card_bg").pack(anchor=tk.W, pady=(6, 2))
        self.category_var = tk.StringVar()
        self.category_cb = ttk.Combobox(form_card, textvariable=self.category_var, font=FONTS["body"])
        self.category_cb.pack(fill=tk.X, pady=(0, 4), ipady=2)

        self.price_var = tk.StringVar()
        self._create_field(form_card, "Price in ₹ (e.g. 199.50) *", self.price_var)

        self.qty_var = tk.StringVar()
        self._create_field(form_card, "Stock Quantity *", self.qty_var)

        self.low_stock_var = tk.StringVar(value="10")
        self._create_field(form_card, "Low Stock Alert Level", self.low_stock_var)

        # Buttons
        btn_box = tk.Frame(form_card, bg=COLORS["card_bg"])
        btn_box.pack(fill=tk.X, pady=(15, 0))

        self.add_btn = ttk.Button(
            btn_box,
            text="➕ Add Product",
            command=self._handle_add
        )
        self.add_btn.pack(fill=tk.X, pady=(0, 6), ipady=3)

        self.update_btn = ttk.Button(
            btn_box,
            text="✏️ Update Selected",
            command=self._handle_update
        )
        self.update_btn.pack(fill=tk.X, pady=(0, 6), ipady=3)

        self.archive_btn = ttk.Button(
            btn_box,
            text="📦 Deactivate / Archive",
            command=self._handle_toggle_archive
        )
        self.archive_btn.pack(fill=tk.X, pady=(0, 6), ipady=3)

        self.clear_btn = ttk.Button(
            btn_box,
            text="🧹 Clear Form",
            command=self._clear_form
        )
        self.clear_btn.pack(fill=tk.X, ipady=3)

    def _create_field(self, parent, label_text, str_var):
        create_label(parent, text=label_text, font_key="body_bold", fg_key="text_dark", bg_key="card_bg").pack(anchor=tk.W, pady=(6, 2))
        entry = create_entry(
            parent,
            textvariable=str_var
        )
        entry.pack(fill=tk.X, pady=(0, 4), ipady=3)
        return entry

    def load_categories(self):
        cats = ProductService.get_categories()
        self.cat_filter_cb["values"] = ["All"] + cats
        self.category_cb["values"] = cats

    def load_products(self):
        search = self.search_var.get().strip()
        cat = self.cat_filter_var.get().strip()
        include_inactive = self.show_inactive_var.get()

        for it in self.tree.get_children():
            self.tree.delete(it)

        rows = ProductService.get_products(
            include_inactive=include_inactive,
            search_term=search,
            category=cat
        )

        for r in rows:
            qty = r["quantity"]
            alert_lvl = r["low_stock"]
            is_active = r["active"] == 1

            if not is_active:
                status = "Archived"
            elif qty == 0:
                status = "Out of Stock"
            elif qty <= alert_lvl:
                status = f"Low ({qty})"
            else:
                status = "In Stock"

            self.tree.insert("", tk.END, values=(
                r["id"],
                r["name"],
                r["category"],
                format_currency(r["price_minor"]),
                qty,
                alert_lvl,
                status
            ))

    def _on_row_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        if not values:
            return

        pid = int(values[0])
        prod = ProductService.get_product_by_id(pid)
        if not prod:
            return

        self.selected_product = prod
        active_status = "Active" if prod["active"] == 1 else "Archived"
        msg = f"Editing ID: #{prod['id']} ({active_status})"
        self.id_lbl_var.set(msg)
        self.status_header_lbl.config(text=msg)
        self.name_var.set(prod["name"])
        self.category_var.set(prod["category"])
        self.price_var.set(paise_to_rupees_str(prod["price_minor"]))
        self.qty_var.set(str(prod["quantity"]))
        self.low_stock_var.set(str(prod["low_stock"]))

        if prod["active"] == 1:
            self.archive_btn.config(text="📦 Deactivate / Archive")
        else:
            self.archive_btn.config(text="♻️ Restore to Active")

    def _clear_form(self):
        self.selected_product = None
        self.id_lbl_var.set("Status: Adding New Product")
        self.status_header_lbl.config(text="Status: Adding New Product")
        self.name_var.set("")
        self.category_var.set("")
        self.price_var.set("")
        self.qty_var.set("")
        self.low_stock_var.set("10")
        self.archive_btn.config(text="📦 Deactivate / Archive")
        self.tree.selection_remove(self.tree.selection())

    def _reset_filters(self):
        self.search_var.set("")
        self.cat_filter_var.set("All")
        self.show_inactive_var.set(False)
        self.load_products()

    def _handle_add(self):
        ok, err, data = validate_product_data(
            self.name_var.get(),
            self.category_var.get(),
            self.price_var.get(),
            self.qty_var.get(),
            self.low_stock_var.get()
        )
        if not ok:
            messagebox.showerror("Validation Error", err)
            return

        try:
            ProductService.add_product(
                data["name"],
                data["category"],
                data["price_minor"],
                data["quantity"],
                data["low_stock"]
            )
            messagebox.showinfo("Success", f"Product '{data['name']}' saved to catalog.")
            self._clear_form()
            self.load_categories()
            self.load_products()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add product: {e}")

    def _handle_update(self):
        if not self.selected_product:
            messagebox.showwarning("Select Product", "Please select a product from the table to update.")
            return

        ok, err, data = validate_product_data(
            self.name_var.get(),
            self.category_var.get(),
            self.price_var.get(),
            self.qty_var.get(),
            self.low_stock_var.get()
        )
        if not ok:
            messagebox.showerror("Validation Error", err)
            return

        try:
            ProductService.update_product(
                self.selected_product["id"],
                data["name"],
                data["category"],
                data["price_minor"],
                data["quantity"],
                data["low_stock"]
            )
            messagebox.showinfo("Updated", "Product updated successfully.")
            self._clear_form()
            self.load_categories()
            self.load_products()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update product: {e}")

    def _handle_toggle_archive(self):
        if not self.selected_product:
            messagebox.showwarning("Select Product", "Please select a product from the table.")
            return

        pid = self.selected_product["id"]
        pname = self.selected_product["name"]
        curr_active = self.selected_product["active"] == 1

        if curr_active:
            confirm = messagebox.askyesno(
                "Confirm Deactivation",
                f"Deactivate '{pname}'?\n\nIt will be hidden from new billing carts, while past sales history is preserved."
            )
            if not confirm:
                return
            ProductService.deactivate_product(pid)
            messagebox.showinfo("Archived", f"'{pname}' has been deactivated.")
        else:
            ProductService.restore_product(pid)
            messagebox.showinfo("Restored", f"'{pname}' has been restored to active status.")

        self._clear_form()
        self.load_products()
        if self.on_data_changed:
            self.on_data_changed()

    def _export_csv(self):
        rows = ProductService.get_products(
            include_inactive=self.show_inactive_var.get(),
            search_term=self.search_var.get().strip(),
            category=self.cat_filter_var.get().strip()
        )
        if not rows:
            messagebox.showinfo("Export", "No products available to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="products_export.csv"
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Name", "Category", "Price (Rupees)", "Quantity", "Low Stock Threshold", "Active"])
                for r in rows:
                    writer.writerow([
                        r["id"],
                        r["name"],
                        r["category"],
                        paise_to_rupees_str(r["price_minor"]),
                        r["quantity"],
                        r["low_stock"],
                        "Yes" if r["active"] == 1 else "Archived"
                    ])
            messagebox.showinfo("Export Successful", f"Saved {len(rows)} products to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not write CSV: {e}")
