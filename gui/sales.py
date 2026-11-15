"""
Sales History view for Inventory & Shop Management System.
Uses high-contrast standard widgets for 100% visibility across macOS (Light & Dark), Windows, and Linux.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from services import BillingService
from utils import (
    COLORS, FONTS, format_currency, paise_to_rupees_str,
    create_card, create_label, create_entry
)


class SalesFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_light"])
        self.selected_bill = None

        self._build_ui()
        self.load_bills()

    def _build_ui(self):
        container = tk.Frame(self, bg=COLORS["bg_light"], padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Top Bar
        top_bar = tk.Frame(container, bg=COLORS["bg_light"])
        top_bar.pack(fill=tk.X, pady=(0, 12))

        create_label(
            top_bar,
            text="📜 Sales History & Invoices",
            font_key="heading",
            fg_key="text_dark",
            bg_key="bg_light"
        ).pack(side=tk.LEFT, padx=(0, 15))

        create_label(top_bar, text="Search Bill / Customer:", font_key="body_bold", fg_key="text_dark", bg_key="bg_light").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = create_entry(
            top_bar,
            textvariable=self.search_var,
            width=18
        )
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=3)
        self.search_entry.bind("<Return>", lambda e: self.load_bills())

        ttk.Button(
            top_bar,
            text="🔍 Search",
            command=self.load_bills
        ).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(
            top_bar,
            text="Reset",
            command=self._reset_search
        ).pack(side=tk.LEFT)

        ttk.Button(
            top_bar,
            text="📥 Export Invoices (CSV)",
            command=self._export_csv
        ).pack(side=tk.RIGHT)

        # Main Split
        split = tk.Frame(container, bg=COLORS["bg_light"])
        split.pack(fill=tk.BOTH, expand=True)

        # Invoices Treeview Card
        table_card = create_card(split, padx=2, pady=2)
        table_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        cols = ("id", "date", "customer", "total")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("id", text="Bill #")
        self.tree.heading("date", text="Date & Time")
        self.tree.heading("customer", text="Customer")
        self.tree.heading("total", text="Total Paid")

        self.tree.column("id", width=60, anchor=tk.CENTER)
        self.tree.column("date", width=140, anchor=tk.W)
        self.tree.column("customer", width=150, anchor=tk.W)
        self.tree.column("total", width=95, anchor=tk.E)

        vsb = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_bill_selected)

        # Right Side: Detail Card
        self.detail_card = create_card(split, padx=16, pady=16, width=360)
        self.detail_card.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.detail_card.pack_propagate(False)

        create_label(
            self.detail_card,
            text="📑 Invoice Line Items",
            font_key="heading",
            fg_key="text_dark",
            bg_key="card_bg"
        ).pack(anchor=tk.W, pady=(0, 8))

        # Metadata Header Frame
        self.meta_frame = tk.Frame(self.detail_card, bg=COLORS["card_bg"])
        self.meta_frame.pack(fill=tk.X, pady=(0, 10))

        self.bill_no_lbl = create_label(self.meta_frame, text="Select an invoice from the table", font_key="body_bold", fg_key="text_dark", bg_key="card_bg")
        self.bill_no_lbl.pack(anchor=tk.W)

        self.cust_date_lbl = create_label(self.meta_frame, text="", font_key="small", fg_key="text_muted", bg_key="card_bg")
        self.cust_date_lbl.pack(anchor=tk.W)

        # Line Items Tree
        detail_cols = ("pname", "uprice", "qty", "line_total")
        self.detail_tree = ttk.Treeview(self.detail_card, columns=detail_cols, show="headings", height=8)

        self.detail_tree.heading("pname", text="Product")
        self.detail_tree.heading("uprice", text="Price")
        self.detail_tree.heading("qty", text="Qty")
        self.detail_tree.heading("line_total", text="Total")

        self.detail_tree.column("pname", width=140, anchor=tk.W)
        self.detail_tree.column("uprice", width=65, anchor=tk.E)
        self.detail_tree.column("qty", width=45, anchor=tk.CENTER)
        self.detail_tree.column("line_total", width=75, anchor=tk.E)

        detail_vsb = ttk.Scrollbar(self.detail_card, orient=tk.VERTICAL, command=self.detail_tree.yview)
        self.detail_tree.configure(yscrollcommand=detail_vsb.set)

        self.detail_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Total & Actions
        self.total_lbl = create_label(
            self.detail_card,
            text="Total: ₹0.00",
            font_key="subtitle",
            fg_key="accent",
            bg_key="card_bg"
        )
        self.total_lbl.pack(anchor=tk.E, pady=(0, 10))

        self.print_btn = ttk.Button(
            self.detail_card,
            text="🖨️ Re-print Receipt",
            command=self._reprint_receipt,
            state=tk.DISABLED
        )
        self.print_btn.pack(fill=tk.X, ipady=4)

    def load_bills(self):
        term = self.search_var.get().strip()
        for it in self.tree.get_children():
            self.tree.delete(it)

        bills = BillingService.get_all_bills(search_term=term)
        for b in bills:
            self.tree.insert("", tk.END, values=(
                f"#{b['id']}",
                b["created_at"],
                b["customer"],
                format_currency(b["total_minor"])
            ))

        self._clear_detail()

    def _reset_search(self):
        self.search_var.set("")
        self.load_bills()

    def _clear_detail(self):
        self.selected_bill = None
        self.bill_no_lbl.config(text="Select an invoice from the table")
        self.cust_date_lbl.config(text="")
        self.total_lbl.config(text="Total: ₹0.00")
        self.print_btn.config(state=tk.DISABLED)
        for it in self.detail_tree.get_children():
            self.detail_tree.delete(it)

    def _on_bill_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        if not values:
            return

        bill_id = int(values[0].replace("#", ""))
        bill = BillingService.get_bill_by_id(bill_id)
        if not bill:
            return

        self.selected_bill = bill
        items = BillingService.get_bill_items(bill_id)

        self.bill_no_lbl.config(text=f"Invoice #{bill['id']} — {bill['customer']}")
        self.cust_date_lbl.config(text=f"Issued: {bill['created_at']}")
        self.total_lbl.config(text=f"Grand Total: {format_currency(bill['total_minor'])}")
        self.print_btn.config(state=tk.NORMAL)

        for it in self.detail_tree.get_children():
            self.detail_tree.delete(it)

        for line in items:
            self.detail_tree.insert("", tk.END, values=(
                line["product_name"],
                format_currency(line["unit_price_minor"]),
                line["quantity"],
                format_currency(line["line_total_minor"])
            ))

    def _reprint_receipt(self):
        if not self.selected_bill:
            return

        bill = self.selected_bill
        items = BillingService.get_bill_items(bill["id"])

        lines = [
            "=" * 44,
            f"DUPLICATE INVOICE RECEIPT: #{bill['id']}",
            f"DATE & TIME : {bill['created_at']}",
            f"CUSTOMER    : {bill['customer']}",
            "=" * 44,
            f"{'ITEM':<20} {'QTY':>4} {'PRICE':>8} {'TOTAL':>9}",
            "-" * 44
        ]
        for it in items:
            pname = it["product_name"][:18]
            uprice_str = paise_to_rupees_str(it["unit_price_minor"])
            ltotal_str = paise_to_rupees_str(it["line_total_minor"])
            lines.append(f"{pname:<20} {it['quantity']:>4} {uprice_str:>8} {ltotal_str:>9}")

        lines.extend([
            "-" * 44,
            f"{'GRAND TOTAL':<25} : {format_currency(bill['total_minor']):>16}",
            "=" * 44,
            "",
            "   (Reprinted copy for records)",
            "         HAVE A GREAT DAY!"
        ])
        receipt_text = "\n".join(lines)

        dialog = tk.Toplevel(self)
        dialog.title(f"Receipt Preview - #{bill['id']}")
        dialog.geometry("450x520")
        dialog.configure(bg=COLORS["bg_light"])

        create_label(dialog, text="🏪 INVOICE RECEIPT COPY", font_key="heading", fg_key="text_dark", bg_key="bg_light").pack(pady=(15, 5))

        txt = tk.Text(
            dialog,
            font=("Courier", 10),
            fg=COLORS["text_dark"],
            bg=COLORS["card_bg"],
            relief=tk.SOLID,
            bd=1,
            padx=10,
            pady=10
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        txt.insert(tk.END, receipt_text)
        txt.config(state=tk.DISABLED)

        def save_file():
            fp = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                initialfile=f"reprint_bill_{bill['id']}.txt"
            )
            if fp:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(receipt_text)
                messagebox.showinfo("Saved", f"Receipt saved to:\n{fp}")

        bar = tk.Frame(dialog, bg=COLORS["bg_light"], padx=20, pady=10)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="💾 Save to File", command=save_file).pack(side=tk.LEFT)
        ttk.Button(bar, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)

    def _export_csv(self):
        bills = BillingService.get_all_bills()
        if not bills:
            messagebox.showinfo("Export", "No sales invoices available to export.")
            return

        fp = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="sales_history_export.csv"
        )
        if not fp:
            return

        try:
            with open(fp, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Bill ID", "Date Time", "Customer Name", "Total Paid (Rupees)"])
                for b in bills:
                    writer.writerow([b["id"], b["created_at"], b["customer"], paise_to_rupees_str(b["total_minor"])])
            messagebox.showinfo("Exported", f"Exported {len(bills)} bills to:\n{fp}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")
