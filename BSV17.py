import csv
import os
import webbrowser
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, font as tkfont
import uuid
import logging
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
# ---------- Config ----------
PRODUCTS_CSV = "products.csv"
CUSTOMERS_CSV = "customers.csv"
INVOICES_DIR = "invoices"
INVOICES_ARCHIVE_DIR = os.path.join(INVOICES_DIR, "archive")
CHARTS_DIR = "charts"
GST_DEFAULT = Decimal("18.0") # percent
CURRENCY_QUANT = Decimal("0.01")
SHOP_NAME = "Serenia Ltd."
PASSWORD = "1515"
ADMIN_PASSWORD = "1234"
GST_NUMBER = "GSTIN: 27ABCDE1234F1Z5" # Default GST Number
PROMOTION_TEXT = "No current promotions."
# ----------------------------
# Configure logging
logging.basicConfig(filename='billing.log', level=logging.WARNING)
def money(d: Decimal) -> str:
    return f"{d.quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)}"
def read_products(path=PRODUCTS_CSV):
    products = {}
    if not os.path.exists(path):
        with open(path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
            writer.writerow(["P001", "Sample Product 1", "10.00", "5.00", "100", "10", "General"])
            writer.writerow(["P002", "Sample Product 2", "20.00", "10.00", "50", "10", "General"])
            writer.writerow(["P003", "Sample Product 3", "15.75", "7.00", "75", "10", "General"])
        messagebox.showinfo("Created", f"Sample {path} created. Please edit it and reload.")
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        expected_headers = ["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"]
        if not all(h in reader.fieldnames for h in ["code", "name", "price", "stock"]):
            messagebox.showerror("Error", f"Invalid headers in {path}. Expected at least: code, name, price, stock")
            return {}
        for r in reader:
            code = r.get("code") or r.get("id") or r.get("sku")
            name = r.get("name") or r.get("product") or ""
            price = r.get("price") or "0"
            cost_price = r.get("cost_price") or "0"
            stock = r.get("stock") or "0"
            low_threshold = r.get("low_stock_threshold") or "10"
            category = r.get("category") or "General"
            if not code:
                continue
            try:
                price_d = Decimal(price)
                cost_price_d = Decimal(cost_price)
                stock_i = int(stock)
                threshold_i = int(low_threshold)
            except:
                price_d = Decimal("0")
                cost_price_d = Decimal("0")
                stock_i = 0
                threshold_i = 10
            products[code] = {"name": name, "price": price_d, "cost_price": cost_price_d, "stock": stock_i, "low_stock_threshold": threshold_i, "category": category}
    return products
def read_customers(path=CUSTOMERS_CSV):
    customers = {}
    if not os.path.exists(path):
        with open(path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "phone", "loyalty_points"])
            writer.writerow(["C001", "Sample Customer", "1234567890", "0"])
        messagebox.showinfo("Created", f"Sample {path} created. Please edit it and reload.")
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not all(h in reader.fieldnames for h in ["id", "name", "phone"]):
            messagebox.showerror("Error", f"Invalid headers in {path}. Expected: id, name, phone")
            return {}
        for r in reader:
            id_ = r.get("id")
            name = r.get("name") or ""
            phone = r.get("phone") or ""
            points = r.get("loyalty_points") or "0"
            if not id_:
                continue
            try:
                points_i = int(points)
            except:
                points_i = 0
            customers[id_] = {"name": name, "phone": phone, "loyalty_points": points_i}
    return customers
def ensure_invoices_dir():
    os.makedirs(INVOICES_DIR, exist_ok=True)
    os.makedirs(INVOICES_ARCHIVE_DIR, exist_ok=True)
def ensure_charts_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)
def next_invoice_number():
    ensure_invoices_dir()
    nums = []
    for fname in os.listdir(INVOICES_DIR):
        if fname.startswith("invoice_") and fname.endswith(".csv"):
            try:
                n = int(fname[len("invoice_"):-len(".csv")])
                nums.append(n)
            except ValueError:
                logging.warning(f"Invalid invoice filename: {fname}")
    return max(nums + [0]) + 1
def save_invoice_csv(inv_number, invoice_data, filename=None):
    ensure_invoices_dir()
    if filename is None:
        filename = os.path.join(INVOICES_DIR, f"invoice_{inv_number}.csv")
    with open(filename, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["shop_name", SHOP_NAME])
        writer.writerow(["gst_number", GST_NUMBER])
        writer.writerow(["invoice_number", inv_number])
        writer.writerow(["date", invoice_data["date"]])
        writer.writerow(["customer_name", invoice_data.get("customer_name", "")])
        writer.writerow(["customer_phone", invoice_data.get("customer_phone", "")])
        writer.writerow(["total_item_count", invoice_data["total_item_count"]])
        writer.writerow([])
        writer.writerow(["code", "name", "price", "qty", "total"])
        for row in invoice_data["items"]:
            writer.writerow([row["code"], row["name"], money(row["price"]), row["qty"], money(row["line_total"])])
        writer.writerow([])
        writer.writerow(["subtotal", money(invoice_data["subtotal"])])
        writer.writerow(["discount_percent", str(invoice_data["discount_percent"])])
        writer.writerow(["discount_amount", money(invoice_data["discount_amount"])])
        writer.writerow(["subtotal_after_discount", money(invoice_data["subtotal_after_discount"])])
        writer.writerow(["gst_percent", str(invoice_data["gst_percent"])])
        writer.writerow(["gst_total", money(invoice_data["gst_total"])])
        writer.writerow(["cgst", money(invoice_data["cgst"])])
        writer.writerow(["sgst", money(invoice_data["sgst"])])
        writer.writerow(["grand_total", money(invoice_data["grand_total"])])
        writer.writerow(["points_awarded", invoice_data.get("points_awarded", 0)])
        writer.writerow(["payment_status", invoice_data.get("payment_status", "pending")])
    return filename
def save_invoice_html(inv_number, invoice_data, filename=None):
    ensure_invoices_dir()
    if filename is None:
        filename = os.path.join(INVOICES_DIR, f"invoice_{inv_number}.html")
    rows_html = ""
    for row in invoice_data["items"]:
        rows_html += f"<tr><td>{row['code']}</td><td>{row['name']}</td><td align='right'>{money(row['price'])}</td><td align='center'>{row['qty']}</td><td align='right'>{money(row['line_total'])}</td></tr>\n"
    html = f"""
    <html>
    <head><meta charset="utf-8"><title>Invoice {inv_number}</title></head>
    <body>
    <h1>{SHOP_NAME}</h1>
    <p>GST Number: {GST_NUMBER}</p>
    <h2>Invoice #{inv_number}</h2>
    <p>Date: {invoice_data['date']}</p>
    <p>Customer: {invoice_data.get('customer_name', '-')} ({invoice_data.get('customer_phone', '-')})</p>
    <p>Total Item Count: {invoice_data['total_item_count']}</p>
    <p>Payment Status: {invoice_data.get('payment_status', 'pending').capitalize()}</p>
    <table border="1" cellspacing="0" cellpadding="6" width="80%">
      <thead>
        <tr><th>Code</th><th>Item</th><th>Price</th><th>Qty</th><th>Line Total</th></tr>
      </thead>
      <tbody>
      {rows_html}
      </tbody>
    </table>
    <p>Subtotal: <b>{money(invoice_data['subtotal'])}</b></p>
    <p>Discount ({invoice_data['discount_percent']}%): <b>{money(invoice_data['discount_amount'])}</b></p>
    <p>Subtotal after discount: <b>{money(invoice_data['subtotal_after_discount'])}</b></p>
    <p>GST ({invoice_data['gst_percent']}%): <b>{money(invoice_data['gst_total'])}</b> (CGST {money(invoice_data['cgst'])} + SGST {money(invoice_data['sgst'])})</p>
    <h3>Grand Total: {money(invoice_data['grand_total'])}</h3>
    <p>Points Awarded: {invoice_data.get('points_awarded', 0)}</p>
    <hr>
    <p>Thank you for your business!</p>
    </body>
    </html>
    """
    with open(filename, "w", encoding='utf-8') as f:
        f.write(html)
    return filename
def save_invoice_pdf(inv_number, invoice_data, filename=None):
    ensure_invoices_dir()
    if filename is None:
        filename = os.path.join(INVOICES_DIR, f"invoice_{inv_number}.pdf")
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
   
    elements.append(Paragraph(SHOP_NAME, styles['Title']))
    elements.append(Paragraph(f"GST Number: {GST_NUMBER}", styles['Normal']))
    elements.append(Paragraph(f"Invoice #{inv_number}", styles['Heading2']))
    elements.append(Paragraph(f"Date: {invoice_data['date']}", styles['Normal']))
    elements.append(Paragraph(f"Customer: {invoice_data.get('customer_name', '-')} ({invoice_data.get('customer_phone', '-')})", styles['Normal']))
    elements.append(Paragraph(f"Total Item Count: {invoice_data['total_item_count']}", styles['Normal']))
    elements.append(Paragraph(f"Payment Status: {invoice_data.get('payment_status', 'pending').capitalize()}", styles['Normal']))
    elements.append(Spacer(1, 12))
   
    data = [["Code", "Item", "Price", "Qty", "Line Total"]]
    for row in invoice_data["items"]:
        data.append([row["code"], row["name"], money(row["price"]), str(row["qty"]), money(row["line_total"])])
   
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
   
    elements.append(Paragraph(f"Subtotal: {money(invoice_data['subtotal'])}", styles['Normal']))
    elements.append(Paragraph(f"Discount ({invoice_data['discount_percent']}%): {money(invoice_data['discount_amount'])}", styles['Normal']))
    elements.append(Paragraph(f"Subtotal after discount: {money(invoice_data['subtotal_after_discount'])}", styles['Normal']))
    elements.append(Paragraph(f"GST ({invoice_data['gst_percent']}%): {money(invoice_data['gst_total'])} (CGST {money(invoice_data['cgst'])} + SGST {money(invoice_data['sgst'])})", styles['Normal']))
    elements.append(Paragraph(f"<b>Grand Total: {money(invoice_data['grand_total'])}</b>", styles['Heading3']))
    elements.append(Paragraph(f"Points Awarded: {invoice_data.get('points_awarded', 0)}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Thank you for your business!", styles['Normal']))
   
    doc.build(elements)
    return filename
def save_sales_chart(dates, totals, filename=None):
    ensure_charts_dir()
    if filename is None:
        filename = os.path.join(CHARTS_DIR, f"sales_chart_{uuid.uuid4()}.html")
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Sales Trend</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h2>Sales Trend</h2>
        <canvas id="salesChart" width="800" height="400"></canvas>
        <script>
            const ctx = document.getElementById('salesChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {dates},
                    datasets: [{{
                        label: 'Total Sales',
                        data: {totals},
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.2)',
                        fill: true
                    }}]
                }},
                options: {{
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{ display: true, text: 'Total Amount' }}
                        }},
                        x: {{
                            title: {{ display: true, text: 'Date' }}
                        }}
                    }},
                    plugins: {{
                        title: {{ display: true, text: 'Sales Trend' }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    with open(filename, "w", encoding='utf-8') as f:
        f.write(html)
    return filename
def plot_sales_trend():
    win = tk.Toplevel()
    win.title("Select Date Range")
    tk.Label(win, text="Start Date (YYYY-MM-DD):").pack()
    start_var = tk.StringVar()
    tk.Entry(win, textvariable=start_var).pack()
    tk.Label(win, text="End Date (YYYY-MM-DD):").pack()
    end_var = tk.StringVar()
    tk.Entry(win, textvariable=end_var).pack()
    def generate_chart():
        start_date = start_var.get() or "1900-01-01"
        end_date = end_var.get() or "9999-12-31"
        sales_by_date = {}
        for fname in sorted(os.listdir(INVOICES_DIR)):
            if fname.startswith("invoice_") and fname.endswith(".csv"):
                try:
                    with open(os.path.join(INVOICES_DIR, fname), newline='', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        data = list(reader)
                        date = data[3][1].split()[0] if len(data) > 3 and len(data[3]) > 1 else ""
                        total = float(data[-3][1]) if data[-3][0] == "grand_total" and len(data[-3]) > 1 else 0
                        if date and total and start_date <= date <= end_date:
                            sales_by_date[date] = sales_by_date.get(date, 0) + total
                except Exception as e:
                    logging.warning(f"Error reading {fname}: {e}")
                    continue
        if not sales_by_date:
            messagebox.showwarning("No data", "No valid invoices found for the selected date range.")
            return
        dates = list(sales_by_date.keys())
        totals = list(sales_by_date.values())
        chart_file = save_sales_chart(dates, totals)
        webbrowser.open_new_tab(os.path.abspath(chart_file))
        win.destroy()
    tk.Button(win, text="Generate Chart", command=generate_chart).pack(pady=5)
class LandingPage(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Serenia India Ltd - Welcome")
        self.geometry("1800x1000")
        self.configure(bg="#EDE8D0")
        # Define colors for each letter
        colors = [
            "red", "blue", "green", "purple", "orange",
            "darkcyan", "magenta", "darkgreen", "navy",
            "violet", "teal", "crimson", "darkorange",
            "indigo", "lime", "maroon"
        ]
       
        # Create a frame to center the content
        self.frame = tk.Frame(self, bg="#EDE8D0")
        self.frame.place(relx=0.5, rely=0.3, anchor="center") # Start higher for drop animation
        # Display "SERENIA INDIA LTD" with colorful letters
        self.label_frame = tk.Frame(self.frame, bg="#EDE8D0")
        self.label_frame.pack(pady=20)
        text = "SERENIA INDIA LTD"
        for i, char in enumerate(text):
            color = colors[i % len(colors)] # Cycle through colors
            tk.Label(
                self.label_frame,
                text=char,
                font=("Krungthep", 100, "bold"),
                fg=color,
                bg="#EDE8D0"
            ).pack(side=tk.LEFT)
        # Welcome message with initial small font for pop-in
        self.welcome_font = tkfont.Font(family="Silom", size=4)
        self.welcome_label = tk.Label(
            self.frame,
            text="WELCOME TO SERENIA INDIA LTD BILLING SOFTWARE BY HARSHIL SANDIP KHANDHAR ",
            font=self.welcome_font,
            bg="#EDE8D0"
        )
        self.welcome_label.pack(pady=10)
        # Top left buttons: Restock and Sales Chart
        top_left_frame = tk.Frame(self, bg="#EDE8D0")
        top_left_frame.place(relx=0.01, rely=0.01, anchor="nw")
        tk.Button(
            top_left_frame,
            text="Restock",
            font=("Silom", 18, "bold"),
            bg="#FFC107",
            fg="black",
            width=15,
            command=self.enter_restock
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            top_left_frame,
            text="Sales Chart",
            font=("Silom", 18, "bold"),
            bg="#2196F3",
            fg="black",
            width=15,
            command=plot_sales_trend
        ).pack(side=tk.LEFT, padx=5)
        # Button frame for main buttons
        button_frame = tk.Frame(self.frame, bg="#EDE8D0")
        button_frame.pack(pady=20)
        tk.Button(
            button_frame,
            text="BILLING SOFTWARE",
            font=("Silom", 18, "bold"),
            bg="#4CAF50",
            fg="black",
            width=15,
            command=self.enter_billing
        ).pack(side=tk.LEFT, padx=10)
        tk.Button(
            button_frame,
            text="QUICK SALE",
            font=("Silom", 18, "bold"),
            bg="#FF9800",
            fg="black",
            width=15,
            command=self.quick_sale
        ).pack(side=tk.LEFT, padx=10)
        tk.Button(
            button_frame,
            text="INVENTORY",
            font=("Silom", 18, "bold"),
            bg="#2196F3",
            fg="black",
            width=10,
            command=self.enter_inventory
        ).pack(side=tk.LEFT, padx=10)
        tk.Button(
            button_frame,
            text="EXIT SOFTWARE",
            font=("Silom", 18, "bold"),
            bg="#F44336",
            fg="black",
            width=15,
            command=self.destroy
        ).pack(side=tk.LEFT, padx=10)
        tk.Button(
            button_frame,
            text="PROMOTION",
            font=("Silom", 18, "bold"),
            bg="#9E9E9E",
            fg="black",
            width=15,
            command=self.manage_promotion
        ).pack(side=tk.LEFT, padx=10)
        # Bottom right: About Us and Help buttons
        about_frame = tk.Frame(self, bg="#EDE8D0")
        about_frame.place(relx=0.99, rely=0.99, anchor="se")
        tk.Button(
            about_frame,
            text="About Us",
            font=("Silom", 18, "bold"),
            bg="#9C27B0",
            fg="black",
            width=15,
            command=self.show_about_us
        ).pack(side=tk.RIGHT, padx=5, pady=5)
        tk.Button(
            about_frame,
            text="Help",
            font=("Silom", 18, "bold"),
            bg="#607D8B",
            fg="black",
            width=15,
            command=self.show_help
        ).pack(side=tk.RIGHT, padx=5, pady=5)
        # Bottom left: Customers and Invoices buttons
        bottom_left_frame = tk.Frame(self, bg="#EDE8D0")
        bottom_left_frame.place(relx=0.01, rely=0.99, anchor="sw")
        tk.Button(
            bottom_left_frame,
            text="Customers",
            font=("Silom", 18, "bold"),
            bg="#FFC107",
            fg="black",
            width=15,
            command=self.enter_customers
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            bottom_left_frame,
            text="Invoices",
            font=("Silom", 18, "bold"),
            bg="#2196F3",
            fg="black",
            width=15,
            command=self.enter_invoices
        ).pack(side=tk.LEFT, padx=5)
        # Start animations
        self.after(100, self.animate_drop)
    def animate_drop(self):
        current_rely = float(self.frame.place_info()['rely'])
        if current_rely < 0.5:
            new_rely = current_rely + 0.02
            self.frame.place(relx=0.5, rely=new_rely, anchor="center")
            self.after(20, self.animate_drop)
        else:
            self.animate_pop_in()
    def animate_pop_in(self):
        current_size = self.welcome_font.actual()['size']
        if current_size < 16:
            self.welcome_font.config(size=current_size + 1)
            self.after(30, self.animate_pop_in)
    def enter_billing(self):
        password = simpledialog.askstring("Password", "Enter password:", show="*")
        if password != PASSWORD:
            messagebox.showerror("Error", "Incorrect password")
            return
        self.destroy() # Close the landing page
        app = BillingApp() # Start the billing app
        app.mainloop()
    def enter_restock(self):
        password = simpledialog.askstring("Password", "Enter password for Restock:", show="*")
        if password != PASSWORD:
            messagebox.showerror("Error", "Incorrect password")
            return
        self.restock_goods()
    def enter_inventory(self):
        password = simpledialog.askstring("Password", "Enter password for Inventory:", show="*")
        if password != PASSWORD:
            messagebox.showerror("Error", "Incorrect password")
            return
        self.show_inventory()
    def enter_customers(self):
        password = simpledialog.askstring("Password", "Enter password for Customers:", show="*")
        if password != PASSWORD:
            messagebox.showerror("Error", "Incorrect password")
            return
        self.open_customers()
    def enter_invoices(self):
        password = simpledialog.askstring("Password", "Enter password for Invoices:", show="*")
        if password != PASSWORD:
            messagebox.showerror("Error", "Incorrect password")
            return
        self.open_invoices()
    def quick_sale(self):
        win = tk.Toplevel(self)
        win.title("Quick Sale")
        win.geometry("400x300")
        tk.Label(win, text="Product Code:").pack()
        code_var = tk.StringVar()
        tk.Entry(win, textvariable=code_var).pack()
        tk.Label(win, text="Quantity:").pack()
        qty_var = tk.StringVar(value="1")
        tk.Entry(win, textvariable=qty_var).pack()
        tk.Label(win, text="Customer Name:").pack()
        cust_var = tk.StringVar()
        tk.Entry(win, textvariable=cust_var).pack()
        def process_sale():
            products = read_products()
            code = code_var.get()
            prod = products.get(code)
            if not prod:
                messagebox.showerror("Error", "Product not found.")
                return
            try:
                qty = int(qty_var.get())
            except:
                messagebox.showerror("Error", "Invalid quantity.")
                return
            if prod["stock"] < qty:
                messagebox.showerror("Error", "Insufficient stock.")
                return
            subtotal = prod["price"] * Decimal(qty)
            gst_total = subtotal * GST_DEFAULT / Decimal("100")
            grand_total = subtotal + gst_total
            inv_num = next_invoice_number()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            invoice_data = {
                "date": now,
                "customer_name": cust_var.get() or "Anonymous",
                "customer_phone": "",
                "items": [{"code": code, "name": prod["name"], "price": prod["price"], "qty": qty, "line_total": subtotal}],
                "subtotal": subtotal,
                "discount_percent": Decimal("0"),
                "discount_amount": Decimal("0"),
                "subtotal_after_discount": subtotal,
                "gst_percent": GST_DEFAULT,
                "gst_total": gst_total,
                "cgst": gst_total / 2,
                "sgst": gst_total / 2,
                "grand_total": grand_total,
                "points_awarded": 0,
                "payment_status": "paid",
                "total_item_count": qty
            }
            save_invoice_csv(inv_num, invoice_data)
            save_invoice_html(inv_num, invoice_data)
            save_invoice_pdf(inv_num, invoice_data)
            prod["stock"] -= qty
            with open(PRODUCTS_CSV, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
                for c, p in products.items():
                    writer.writerow([c, p["name"], str(p["price"]), str(p["cost_price"]), p["stock"], p["low_stock_threshold"], p["category"]])
            messagebox.showinfo("Success", f"Quick sale #{inv_num} processed for {grand_total}.")
            win.destroy()
        tk.Button(win, text="Process Sale", command=process_sale).pack(pady=10)
    def manage_promotion(self):
        global PROMOTION_TEXT
        text = simpledialog.askstring("Promotion", f"Current Promotion:\n{PROMOTION_TEXT}\n\nEnter new promotion text:", initialvalue=PROMOTION_TEXT)
        if text:
            PROMOTION_TEXT = text
            messagebox.showinfo("Updated", f"Promotion updated: {PROMOTION_TEXT}")
    def show_inventory(self):
        products = read_products()
        if not products:
            messagebox.showinfo("No Products", "No products available.")
            return
        win = tk.Toplevel(self)
        win.title("Inventory")
        win.geometry("600x400")
        cols = ("code", "name", "price", "stock")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.capitalize())
            tree.column(c, anchor="center")
        tree.pack(fill=tk.BOTH, expand=True)
        for code, p in sorted(products.items()):
            tree.insert("", tk.END, values=(code, p["name"], money(p["price"]), p["stock"]))
    def restock_goods(self):
        products = read_products()
        if not products:
            messagebox.showinfo("No Products", "No products available to restock.")
            return
        win = tk.Toplevel(self)
        win.title("Restock Goods")
        win.geometry("800x500")
        # Create a frame with scrollbar
        canvas = tk.Canvas(win)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        cols = ("code", "name", "current_stock", "restock_qty")
        tree = ttk.Treeview(scrollable_frame, columns=cols, show="headings", height=15)
        for c in cols:
            tree.heading(c, text=c.replace("_", " ").title())
            tree.column(c, anchor="center", width=150)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Dictionary to hold StringVars for restock quantities
        restock_vars = {}
        for code, p in sorted(products.items()):
            tree.insert("", tk.END, values=(code, p["name"], p["stock"], "0"))
            restock_vars[code] = tk.StringVar(value="0")
        # Bind double-click to edit restock qty
        tree.bind("<Double-Button-1>", lambda e: self.edit_restock_qty(tree, restock_vars, products))
        def apply_restock():
            updated = False
            for code, var in restock_vars.items():
                try:
                    add_stock = int(var.get())
                    if add_stock > 0:
                        products[code]["stock"] += add_stock
                        updated = True
                except ValueError:
                    pass
            if updated:
                with open(PRODUCTS_CSV, "w", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
                    for c, p in products.items():
                        writer.writerow([c, p["name"], str(p["price"]), str(p["cost_price"]), p["stock"], p["low_stock_threshold"], p["category"]])
                messagebox.showinfo("Success", "Stock updated and saved to products.csv.")
            else:
                messagebox.showinfo("No Changes", "No restock amounts entered.")
            win.destroy()
        tk.Button(scrollable_frame, text="Apply Restock", command=apply_restock, font=("Arial", 12, "bold")).pack(pady=10)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    def edit_restock_qty(self, tree, restock_vars, products):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        code = vals[0]
        new_val = simpledialog.askinteger("Restock", f"Enter restock units for {code}:", initialvalue=int(vals[3]), minvalue=0)
        if new_val is not None:
            restock_vars[code].set(str(new_val))
            # Update the tree display
            tree.item(sel[0], values=(vals[0], vals[1], vals[2], new_val))
    def show_about_us(self):
        info = (
            "Software name: SERENIA INDIA LTD\n"
            "Version: BS 17 Exclusive\n"
            "Developer's name: Harshil Sandip Khandhar\n"
            "Made in INDIA"
        )
        messagebox.showinfo("About Us", info)
    def show_help(self):
        help_text = (
            "Welcome to Serenia India Ltd Billing Software!\n\n"
            "Key Features:\n"
            "- Billing: Generate invoices with GST and discounts.\n"
            "- Inventory: View and manage stock levels.\n"
            "- Restock: Add stock to products.\n"
            "- Customers: Manage customer data and loyalty points.\n"
            "- Invoices: View and archive invoices.\n"
            "- Quick Sale: Fast single-item sales.\n"
            "- Reports: Profit, sales trends, and more in Billing.\n"
            "- Admin Mode: Change settings (password required).\n\n"
            "Shortcuts in Billing:\n"
            "- Enter: Generate Invoice\n"
            "- Ctrl+P: Print Invoice\n"
            "- Shift+C: Calculator\n"
            "- Ctrl+C: Clear Cart\n\n"
            "Contact support for issues."
        )
        messagebox.showinfo("Help", help_text)
    def open_customers(self):
        path = os.path.abspath(CUSTOMERS_CSV)
        if os.name == 'nt':
            os.startfile(path)
        else:
            try:
                webbrowser.open("file://" + path)
            except:
                messagebox.showinfo("Customers file", path)
    def open_invoices(self):
        ensure_invoices_dir()
        path = os.path.abspath(INVOICES_DIR)
        if os.name == 'nt':
            os.startfile(path)
        else:
            try:
                webbrowser.open("file://" + path)
            except:
                messagebox.showinfo("Invoices folder", path)
class BillingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Billing Software By Serenia Ltd")
        self.geometry("1800x1000")
        self.products = read_products()
        self.customers = read_customers()
        if not self.products:
            messagebox.showinfo("No products", f"No products found in {PRODUCTS_CSV}. Please create the file and restart.")
        self.cart = []
        self.gst_percent = GST_DEFAULT
        self.discount_percent = Decimal("0")
        self.latest_invoice = None
        self.is_dark = False
        self.create_ui()
        self.refresh_product_list()
        self.update_totals()
        self.bind("<Return>", lambda e: self.generate_invoice())
        self.bind("<Command-9>" if os.name == "posix" else "<Control-9>", lambda e: self.print_invoice())
        self.tree.bind("<w>", lambda e: self.adjust_quantity(1))
        self.tree.bind("<s>", lambda e: self.adjust_quantity(-1))
        self.bind("<Control-n>", lambda e: self.add_new_customer())
        self.bind("<Control-m>", lambda e: self.open_admin_mode())
        self.bind("<Control-p>", lambda e: self.print_invoice() if self.latest_invoice else messagebox.showwarning("No invoice", "Generate an invoice first."))
        self.bind("<Control-c>", lambda e: self.clear_cart())
        self.bind("<Control-r>", lambda e: self.remove_selected())
        self.bind("<Shift-C>", lambda e: self.open_calculator())
    def create_ui(self):
        left = tk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        tk.Label(left, text="Category:").pack(anchor="w")
        self.category_var = tk.StringVar(value="All")
        categories = ["All"] + sorted(set(p["category"] for p in self.products.values()))
        self.category_combo = ttk.Combobox(left, textvariable=self.category_var, values=categories)
        self.category_combo.pack(anchor="w", fill=tk.X)
        self.category_var.trace("w", self.filter_products)
        tk.Label(left, text="Search Products:").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_products)
        tk.Entry(left, textvariable=self.search_var).pack(anchor="w", fill=tk.X)
        tk.Label(left, text="Products").pack(anchor="w", pady=(10, 0))
        self.product_listbox = tk.Listbox(left, width=40, height=20)
        self.product_listbox.pack()
        self.product_listbox.bind("<Double-Button-1>", lambda e: self.add_selected_product())
        qty_frame = tk.Frame(left)
        qty_frame.pack(pady=6, anchor="w")
        tk.Label(qty_frame, text="Qty:").pack(side=tk.LEFT)
        self.qty_var = tk.StringVar(value="1")
        vcmd_qty = (self.register(self.validate_qty), '%P')
        tk.Entry(qty_frame, textvariable=self.qty_var, width=5, validate="key", validatecommand=vcmd_qty).pack(side=tk.LEFT, padx=6)
        tk.Button(qty_frame, text="Add to Cart", command=self.add_selected_product).pack(side=tk.LEFT)
        tk.Button(left, text="Add Custom Item", command=self.add_custom_item).pack(pady=6, anchor="w")
        tk.Button(left, text="Load products CSV", command=self.load_products_csv).pack(pady=6, anchor="w")
        tk.Button(left, text="Admin Mode", command=self.open_admin_mode).pack(pady=6, anchor="w")
        tk.Button(left, text="Home", command=self.go_home).pack(pady=6, anchor="w")
        tk.Button(left, text="Reset Invoices", command=self.reset_invoices).pack(pady=6, anchor="w")
        right = tk.Frame(self)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        topright = tk.Frame(right)
        topright.pack(fill=tk.X)
        tk.Label(topright, text="Cart").pack(anchor="w")
        cols = ("code", "name", "price", "qty", "total")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Delete>", lambda e: self.remove_selected())
        btns = tk.Frame(right)
        btns.pack(fill=tk.X, pady=6)
        tk.Button(btns, text="Remove selected", command=self.remove_selected).pack(side=tk.LEFT)
        tk.Button(btns, text="Clear cart", command=self.clear_cart).pack(side=tk.LEFT, padx=6)
        bottom = tk.Frame(right)
        bottom.pack(fill=tk.X, pady=8)
        tk.Label(bottom, text="Customer:").grid(row=0, column=0, sticky="e")
        self.customer_var = tk.StringVar()
        self.customer_entry = ttk.Combobox(bottom, textvariable=self.customer_var, values=[c["name"] for c in self.customers.values()])
        self.customer_entry.grid(row=0, column=1, sticky="w")
        self.customer_entry.bind("<KeyRelease>", self.filter_customers)
        self.customer_entry.bind("<<ComboboxSelected>>", self.update_customer_info)
        tk.Button(bottom, text="Add New", command=self.add_new_customer).grid(row=0, column=2, sticky="w", padx=5)
        tk.Label(bottom, text="Phone:").grid(row=0, column=3, sticky="e")
        self.phone_label = tk.Label(bottom, text="")
        self.phone_label.grid(row=0, column=4, sticky="w")
        tk.Label(bottom, text="Loyalty Points:").grid(row=0, column=5, sticky="e")
        self.loyalty_label = tk.Label(bottom, text="")
        self.loyalty_label.grid(row=0, column=6, sticky="w")
        tk.Label(bottom, text="GST %:").grid(row=1, column=0, sticky="e")
        self.gst_var = tk.StringVar(value=str(self.gst_percent))
        vcmd_gst = (self.register(self.validate_percent_gst), '%P')
        gst_entry = tk.Entry(bottom, textvariable=self.gst_var, width=8, validate="key", validatecommand=vcmd_gst)
        gst_entry.grid(row=1, column=1, sticky="w")
        gst_entry.bind("<KeyRelease>", lambda e: self.update_totals())
        tk.Label(bottom, text="Discount %:").grid(row=1, column=3, sticky="e")
        self.discount_var = tk.StringVar(value="0")
        vcmd_discount = (self.register(self.validate_percent_discount), '%P')
        discount_entry = tk.Entry(bottom, textvariable=self.discount_var, width=8, validate="key", validatecommand=vcmd_discount)
        discount_entry.grid(row=1, column=4, sticky="w")
        discount_entry.bind("<KeyRelease>", lambda e: self.update_totals())
        self.subtotal_label = tk.Label(bottom, text="Subtotal: 0.00")
        self.subtotal_label.grid(row=2, column=0, columnspan=7, sticky="w")
        self.gst_label = tk.Label(bottom, text="GST: 0.00 (CGST 0.00 + SGST 0.00)")
        self.gst_label.grid(row=3, column=0, columnspan=7, sticky="w")
        self.item_count_label = tk.Label(bottom, text="Total Items: 0")
        self.item_count_label.grid(row=4, column=0, columnspan=7, sticky="w")
        self.grand_label = tk.Label(bottom, text="Grand Total: 0.00", font=("Arial", 14, "bold"))
        self.grand_label.grid(row=5, column=0, columnspan=7, sticky="w", pady=6)
        actions = tk.Frame(right)
        actions.pack(fill=tk.X)
        tk.Button(actions, text="Generate Invoice", command=self.generate_invoice).pack(side=tk.LEFT)
        tk.Button(actions, text="Export cart CSV", command=self.export_cart_csv).pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="Export Invoice Summary", command=self.export_invoice_summary).pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="Open invoices folder", command=self.open_invoices_folder).pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="View Invoices", command=self.show_invoice_history).pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="Calculator", command=self.open_calculator).pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="Profit Report", command=self.profit_report).pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="Process Return", command=self.process_return).pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="Toggle Theme", command=self.toggle_theme).pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="Advanced Reports", command=self.advanced_reports).pack(side=tk.LEFT, padx=6)
    def validate_qty(self, value):
        if value == "":
            return True
        try:
            qty = int(value)
            return qty > 0
        except ValueError:
            return False
    def validate_percent_gst(self, value):
        if value == "":
            return True
        try:
            perc = Decimal(value)
            return perc >= 0
        except:
            return False
    def validate_percent_discount(self, value):
        if value == "":
            return True
        try:
            perc = Decimal(value)
            return 0 <= perc <= 100
        except:
            return False
    def filter_products(self, *args):
        search = self.search_var.get().lower()
        category = self.category_var.get()
        self.product_listbox.delete(0, tk.END)
        for code, p in sorted(self.products.items()):
            if (category == "All" or p["category"] == category) and (search in code.lower() or search in p["name"].lower()):
                low_stock = " (LOW STOCK)" if p["stock"] < p["low_stock_threshold"] else ""
                self.product_listbox.insert(tk.END, f"{code} | {p['name']} | {money(p['price'])} | Stock: {p['stock']}{low_stock}")
    def refresh_product_list(self):
        self.product_listbox.delete(0, tk.END)
        for code, p in sorted(self.products.items()):
            low_stock = " (LOW STOCK)" if p["stock"] < p["low_stock_threshold"] else ""
            self.product_listbox.insert(tk.END, f"{code} | {p['name']} | {money(p['price'])} | Stock: {p['stock']}{low_stock}")
    def filter_customers(self, event):
        search = self.customer_var.get().lower()
        if not search:
            self.customer_entry['values'] = [c["name"] for c in self.customers.values()]
        else:
            filtered = [c["name"] for c in self.customers.values() if search in c["name"].lower()]
            self.customer_entry['values'] = filtered
        self.customer_entry.event_generate("<Down>")
    def add_selected_product(self):
        sel = self.product_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select product", "Please select a product from the list (double-click works).")
            return
        idx = sel[0]
        line = self.product_listbox.get(idx)
        code = line.split("|")[0].strip()
        prod = self.products.get(code)
        if not prod:
            return
        try:
            qty = int(self.qty_var.get())
        except ValueError:
            messagebox.showwarning("Quantity", "Enter a valid quantity >= 1")
            return
        if qty <= 0:
            messagebox.showwarning("Quantity", "Enter quantity >= 1")
            return
        if prod["stock"] < qty:
            messagebox.showwarning("Stock", f"Only {prod['stock']} units of {prod['name']} available.")
            return
        price = prod["price"]
        line_total = (price * Decimal(qty)).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
        found = False
        for item in self.cart:
            if item["code"] == code:
                new_qty = item["qty"] + qty
                if new_qty > prod["stock"]:
                    messagebox.showwarning("Stock", f"Cannot add {new_qty} units of {prod['name']}. Only {prod['stock']} available.")
                    return
                item["qty"] = new_qty
                item["line_total"] = (item["price"] * Decimal(item["qty"])).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
                found = True
                break
        if not found:
            self.cart.append({"code": code, "name": prod["name"], "price": price, "qty": qty, "line_total": line_total})
        self.refresh_cart()
        self.update_totals()
    def add_custom_item(self):
        name = simpledialog.askstring("Custom Item", "Enter item name:")
        if not name:
            return
        price_str = simpledialog.askstring("Custom Item", "Enter price:")
        try:
            price = Decimal(price_str)
            if price <= 0:
                raise ValueError
        except:
            messagebox.showwarning("Invalid Price", "Enter a valid positive price.")
            return
        qty_str = simpledialog.askstring("Custom Item", "Enter quantity:", initialvalue="1")
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except:
            messagebox.showwarning("Invalid Quantity", "Enter a valid positive quantity.")
            return
        code = f"CUSTOM_{uuid.uuid4().hex[:8].upper()}" # Unique code for custom item
        line_total = (price * Decimal(qty)).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
        self.cart.append({"code": code, "name": name, "price": price, "qty": qty, "line_total": line_total})
        self.refresh_cart()
        self.update_totals()
    def refresh_cart(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for item in self.cart:
            self.tree.insert("", tk.END, values=(item["code"], item["name"], money(item["price"]), item["qty"], money(item["line_total"])))
    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        for s in sel:
            vals = self.tree.item(s, "values")
            code = vals[0]
            for i, it in enumerate(self.cart):
                if it["code"] == code:
                    del self.cart[i]
                    break
        self.refresh_cart()
        self.update_totals()
    def clear_cart(self):
        if messagebox.askyesno("Clear", "Clear the cart?"):
            self.cart = []
            self.refresh_cart()
            self.update_totals()
    def adjust_quantity(self, delta):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select item", "Please select a cart item to adjust quantity.")
            return
        vals = self.tree.item(sel[0], "values")
        code = vals[0]
        for item in self.cart:
            if item["code"] == code:
                new_qty = item["qty"] + delta
                if new_qty < 1:
                    messagebox.showwarning("Quantity", "Quantity cannot be less than 1.")
                    return
                if 'CUSTOM_' not in code and new_qty > self.products[code]["stock"]:
                    messagebox.showwarning("Stock", f"Cannot set {new_qty} units of {self.products[code]['name']}. Only {self.products[code]['stock']} available.")
                    return
                item["qty"] = new_qty
                item["line_total"] = (item["price"] * Decimal(new_qty)).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
                break
        self.refresh_cart()
        self.update_totals()
    def update_customer_info(self, event):
        customer_name = self.customer_var.get().strip()
        self.selected_customer_id = None
        self.customer_phone = ""
        self.customer_loyalty_points = 0
        self.phone_label.config(text="")
        self.loyalty_label.config(text="")
        for id_, c in self.customers.items():
            if c["name"] == customer_name:
                self.selected_customer_id = id_
                self.customer_phone = c["phone"]
                self.customer_loyalty_points = c["loyalty_points"]
                self.phone_label.config(text=self.customer_phone)
                self.loyalty_label.config(text=str(self.customer_loyalty_points))
                break
        self.update_totals()
    def update_totals(self):
        subtotal = Decimal("0")
        total_items = 0
        for it in self.cart:
            subtotal += it["line_total"]
            total_items += it["qty"]
        try:
            gst_percent = Decimal(self.gst_var.get())
            if gst_percent < 0:
                raise ValueError
        except:
            gst_percent = GST_DEFAULT
            self.gst_var.set(str(gst_percent))
        try:
            discount_percent = Decimal(self.discount_var.get())
            if discount_percent < 0 or discount_percent > 100:
                raise ValueError
        except:
            discount_percent = Decimal("0")
            self.discount_var.set("0")
        # Loyalty enhancement: 10% discount if points >= 100
        loyalty_discount = Decimal("0")
        if hasattr(self, 'customer_loyalty_points') and self.customer_loyalty_points >= 100:
            loyalty_discount = Decimal("10")
        total_discount_percent = discount_percent + loyalty_discount
        discount_amount = (subtotal * total_discount_percent / Decimal("100")).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
        subtotal_after_discount = (subtotal - discount_amount).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
        gst_total = (subtotal_after_discount * gst_percent / Decimal("100")).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
        cgst = (gst_total / 2).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
        sgst = (gst_total - cgst).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
        grand_total = (subtotal_after_discount + gst_total).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
        self.subtotal = subtotal
        self.discount_amount = discount_amount
        self.subtotal_after_discount = subtotal_after_discount
        self.gst_total = gst_total
        self.cgst = cgst
        self.sgst = sgst
        self.grand_total = grand_total
        self.total_item_count = total_items
        self.subtotal_label.config(text=f"Subtotal: {money(subtotal)} (Discount: {money(discount_amount)})")
        self.gst_label.config(text=f"GST ({gst_percent}%): {money(gst_total)} (CGST {money(cgst)} + SGST {money(sgst)})")
        self.item_count_label.config(text=f"Total Items: {total_items}")
        self.grand_label.config(text=f"Grand Total: {money(grand_total)}")
    def generate_invoice(self):
        if not self.cart:
            messagebox.showwarning("Empty cart", "Add items before generating an invoice.")
            return
        inv_num = next_invoice_number()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        customer_name = self.customer_var.get().strip() or "Anonymous"
        customer_phone = getattr(self, "customer_phone", "")
        points_awarded = 0
        if hasattr(self, "selected_customer_id") and self.selected_customer_id:
            points_awarded = int(self.grand_total // Decimal(10))
            self.customers[self.selected_customer_id]["loyalty_points"] += points_awarded
            self.save_customers()
            self.loyalty_label.config(text=str(self.customers[self.selected_customer_id]["loyalty_points"]))
        invoice_data = {
            "date": now,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "items": self.cart,
            "subtotal": self.subtotal,
            "discount_percent": Decimal(self.discount_var.get()),
            "discount_amount": self.discount_amount,
            "subtotal_after_discount": self.subtotal_after_discount,
            "gst_percent": Decimal(self.gst_var.get()),
            "gst_total": self.gst_total,
            "cgst": self.cgst,
            "sgst": self.sgst,
            "grand_total": self.grand_total,
            "points_awarded": points_awarded,
            "payment_status": "pending",
            "total_item_count": self.total_item_count
        }
        low_stock_alerts = []
        for item in self.cart:
            if "CUSTOM_" in item["code"]:
                continue # No stock for custom items
            code = item["code"]
            self.products[code]["stock"] -= item["qty"]
            if self.products[code]["stock"] < self.products[code]["low_stock_threshold"]:
                low_stock_alerts.append(f"{self.products[code]['name']} (Code: {code}) is low on stock: {self.products[code]['stock']} left.")
        with open(PRODUCTS_CSV, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
            for c, p in self.products.items():
                writer.writerow([c, p["name"], str(p["price"]), str(p["cost_price"]), p["stock"], p["low_stock_threshold"], p["category"]])
        self.refresh_product_list()
        if low_stock_alerts:
            messagebox.showwarning("Low Stock Alert", "\n".join(low_stock_alerts))
        csvfile = save_invoice_csv(inv_num, invoice_data)
        htmlfile = save_invoice_html(inv_num, invoice_data)
        pdffile = save_invoice_pdf(inv_num, invoice_data)
        self.latest_invoice = htmlfile
        messagebox.showinfo("Saved", f"Invoice #{inv_num} saved.\nCSV: {csvfile}\nHTML: {htmlfile}\nPDF: {pdffile}")
        webbrowser.open_new_tab(os.path.abspath(htmlfile))
        self.cart = []
        self.customer_var.set("")
        self.selected_customer_id = None
        self.customer_phone = ""
        self.phone_label.config(text="")
        self.loyalty_label.config(text="")
        self.refresh_cart()
        self.update_totals()
    def print_invoice(self):
        if not self.latest_invoice or not os.path.exists(self.latest_invoice):
            messagebox.showwarning("No invoice", "Generate an invoice first.")
            return
        webbrowser.open_new_tab(os.path.abspath(self.latest_invoice))
    def export_cart_csv(self):
        if not self.cart:
            messagebox.showwarning("Empty cart", "No items to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["code", "name", "price", "qty", "total"])
            for it in self.cart:
                writer.writerow([it["code"], it["name"], money(it["price"]), it["qty"], money(it["line_total"])])
        messagebox.showinfo("Exported", f"Cart exported to {path}")
    def export_invoice_summary(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Invoice #", "Date", "Customer", "Total", "Payment Status"])
            for fname in sorted(os.listdir(INVOICES_DIR)):
                if fname.startswith("invoice_") and fname.endswith(".csv"):
                    try:
                        with open(os.path.join(INVOICES_DIR, fname), newline='', encoding='utf-8') as f_csv:
                            reader = csv.reader(f_csv)
                            data = list(reader)
                            invoice_dict = dict(row for row in data if len(row) == 2 and row[0])
                            num = fname.split("_")[1].split(".")[0]
                            date = invoice_dict.get("date", "")
                            customer = invoice_dict.get("customer_name", "")
                            total = invoice_dict.get("grand_total", "0")
                            status = invoice_dict.get("payment_status", "pending")
                            writer.writerow([num, date, customer, total, status])
                    except Exception as e:
                        logging.warning(f"Error reading {fname}: {e}")
        messagebox.showinfo("Exported", f"Invoice summary exported to {path}")
    def open_invoices_folder(self):
        ensure_invoices_dir()
        path = os.path.abspath(INVOICES_DIR)
        if os.name == 'nt':
            os.startfile(path)
        else:
            try:
                webbrowser.open("file://" + path)
            except:
                messagebox.showinfo("Invoices folder", path)
    def load_products_csv(self):
        path = filedialog.askopenfilename(title="Select products CSV", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            with open(path, newline='', encoding='utf-8') as src:
                txt = src.read()
            with open(PRODUCTS_CSV, "w", newline='', encoding='utf-8') as dst:
                dst.write(txt)
            self.products = read_products()
            self.refresh_product_list()
            categories = ["All"] + sorted(set(p["category"] for p in self.products.values()))
            self.category_combo['values'] = categories
            messagebox.showinfo("Loaded", f"Products loaded from {path} into {PRODUCTS_CSV}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    def reset_invoices(self):
        if not messagebox.askyesno("Reset", "This will archive all invoice files to archive folder. Are you sure?"):
            return
        ensure_invoices_dir()
        for fname in os.listdir(INVOICES_DIR):
            if (fname.startswith("invoice_") or fname.startswith("return_")) and (fname.endswith(".csv") or fname.endswith(".html") or fname.endswith(".pdf")):
                src = os.path.join(INVOICES_DIR, fname)
                dst = os.path.join(INVOICES_ARCHIVE_DIR, fname)
                os.rename(src, dst)
        messagebox.showinfo("Reset", "Invoices archived. Next invoice number is 1.")
    def show_invoice_history(self, for_return=False):
        win = tk.Toplevel(self)
        win.title("Invoice History")
        win.geometry("700x400")
        cols = ("number", "date", "customer", "total", "status")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        tree.heading("number", text="Invoice #")
        tree.heading("date", text="Date")
        tree.heading("customer", text="Customer")
        tree.heading("total", text="Total")
        tree.heading("status", text="Payment Status")
        tree.pack(fill=tk.BOTH, expand=True)
        invoices = []
        for fname in os.listdir(INVOICES_DIR):
            if fname.startswith("invoice_") and fname.endswith(".csv"):
                try:
                    with open(os.path.join(INVOICES_DIR, fname), newline='', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        data = list(reader)
                        invoice_dict = dict(row for row in data if len(row) == 2 and row[0])
                        date = invoice_dict.get("date", "")
                        customer = invoice_dict.get("customer_name", "")
                        total = invoice_dict.get("grand_total", "")
                        status = invoice_dict.get("payment_status", "pending")
                        num = fname.split("_")[1].split(".")[0]
                        invoices.append((num, date, customer, total, status, fname))
                except Exception as e:
                    logging.warning(f"Error reading {fname}: {e}")
                    continue
        invoices.sort(key=lambda x: x[1] if x[1] else "0")
        for num, date, customer, total, status, _ in invoices:
            tree.insert("", tk.END, values=(num, date, customer, total, status))
        if not for_return:
            tree.bind("<Double-Button-1>", lambda e: self.open_selected_invoice(tree))
        def change_status():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select Invoice", "Please select an invoice to update status.")
                return
            vals = tree.item(sel[0], "values")
            num = vals[0]
            current_status = vals[4]
            new_status = simpledialog.askstring("Update Status", f"Enter new status for Invoice #{num} (e.g., paid, pending, overdue):", initialvalue=current_status)
            if new_status:
                csvfile = os.path.join(INVOICES_DIR, f"invoice_{num}.csv")
                if os.path.exists(csvfile):
                    with open(csvfile, newline='', encoding='utf-8') as f:
                        data = list(csv.reader(f))
                    for row in data:
                        if row and row[0] == "payment_status":
                            row[1] = new_status
                            break
                    with open(csvfile, "w", newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(data)
                    messagebox.showinfo("Updated", f"Payment status for Invoice #{num} updated to {new_status}.")
                    tree.item(sel[0], values=(num, vals[1], vals[2], vals[3], new_status))
        tk.Button(win, text="Change Payment Status", command=change_status).pack(pady=5)
        if for_return:
            def select_for_return():
                sel = tree.selection()
                if sel:
                    vals = tree.item(sel[0], "values")
                    num = vals[0]
                    fname = next((inv[5] for inv in invoices if inv[0] == num), None)
                    if fname:
                        self.show_return_items(os.path.join(INVOICES_DIR, fname))
                        win.destroy()
            tk.Button(win, text="Select for Return", command=select_for_return).pack(pady=5)
        return win
    def open_selected_invoice(self, tree):
        sel = tree.selection()
        if sel:
            num = tree.item(sel[0], "values")[0]
            htmlfile = os.path.join(INVOICES_DIR, f"invoice_{num}.html")
            if os.path.exists(htmlfile):
                webbrowser.open_new_tab(os.path.abspath(htmlfile))
    def open_admin_mode(self):
        password = simpledialog.askstring("Admin Login", "Enter password:", show="*")
        if password != ADMIN_PASSWORD:
            messagebox.showerror("Error", "Incorrect password")
            return
        win = tk.Toplevel(self)
        win.title("Admin Mode")
        win.geometry("700x700")
        win.resizable(True, True)
        # Create scrollable frame
        canvas = tk.Canvas(win)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        # GST Number Management at top left
        gst_frame = tk.LabelFrame(scrollable_frame, text="GST Number Management", font=("Arial", 12, "bold"))
        gst_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(gst_frame, text=f"Current GST Number: {GST_NUMBER}").pack(anchor="w")
        gst_var = tk.StringVar(value=GST_NUMBER)
        gst_entry = tk.Entry(gst_frame, textvariable=gst_var, width=50)
        gst_entry.pack(pady=5)
        def save_gst():
            global GST_NUMBER
            GST_NUMBER = gst_var.get()
            messagebox.showinfo("Success", "GST Number updated.")
        tk.Button(gst_frame, text="Update GST Number", command=save_gst).pack(pady=5)
        # Password Management
        pw_frame = tk.LabelFrame(scrollable_frame, text="Password Management", font=("Arial", 12, "bold"))
        pw_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(pw_frame, text=f"Current Main Password: {PASSWORD}").pack(anchor="w")
        pw_var = tk.StringVar(value=PASSWORD)
        pw_entry = tk.Entry(pw_frame, textvariable=pw_var, show="*", width=50)
        pw_entry.pack(pady=5)
        def save_pw():
            global PASSWORD
            PASSWORD = pw_var.get()
            messagebox.showinfo("Success", "Main Password updated.")
        tk.Button(pw_frame, text="Update Main Password", command=save_pw).pack(pady=5)
        tk.Label(pw_frame, text=f"Current Admin Password: {ADMIN_PASSWORD}").pack(anchor="w")
        admin_pw_var = tk.StringVar(value=ADMIN_PASSWORD)
        admin_pw_entry = tk.Entry(pw_frame, textvariable=admin_pw_var, show="*", width=50)
        admin_pw_entry.pack(pady=5)
        def save_admin_pw():
            global ADMIN_PASSWORD
            ADMIN_PASSWORD = admin_pw_var.get()
            messagebox.showinfo("Success", "Admin Password updated.")
        tk.Button(pw_frame, text="Update Admin Password", command=save_admin_pw).pack(pady=5)
        # Company Name Management
        company_frame = tk.LabelFrame(scrollable_frame, text="Company Name Management", font=("Arial", 12, "bold"))
        company_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(company_frame, text=f"Current Company Name: {SHOP_NAME}").pack(anchor="w")
        company_var = tk.StringVar(value=SHOP_NAME)
        company_entry = tk.Entry(company_frame, textvariable=company_var, width=50)
        company_entry.pack(pady=5)
        def save_company():
            global SHOP_NAME
            SHOP_NAME = company_var.get()
            messagebox.showinfo("Success", "Company Name updated. It will reflect in new invoices.")
        tk.Button(company_frame, text="Update Company Name", command=save_company).pack(pady=5)
        # Product Management
        prod_frame = tk.LabelFrame(scrollable_frame, text="Product Management", font=("Arial", 12, "bold"))
        prod_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(prod_frame, text="Code").pack()
        code_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=code_var).pack()
        tk.Label(prod_frame, text="Name").pack()
        name_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=name_var).pack()
        tk.Label(prod_frame, text="Price").pack()
        price_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=price_var).pack()
        tk.Label(prod_frame, text="Cost Price").pack()
        cost_price_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=cost_price_var).pack()
        tk.Label(prod_frame, text="Stock").pack()
        stock_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=stock_var).pack()
        tk.Label(prod_frame, text="Low Stock Threshold").pack()
        threshold_var = tk.StringVar(value="10")
        tk.Entry(prod_frame, textvariable=threshold_var).pack()
        tk.Label(prod_frame, text="Category").pack()
        category_var = tk.StringVar(value="General")
        tk.Entry(prod_frame, textvariable=category_var).pack()
        def save_product():
            code, name, price, cost_price, stock, threshold, category = code_var.get(), name_var.get(), price_var.get(), cost_price_var.get(), stock_var.get(), threshold_var.get(), category_var.get()
            if code and name and price and stock:
                try:
                    price_d = Decimal(price)
                    cost_price_d = Decimal(cost_price)
                    stock_i = int(stock)
                    threshold_i = int(threshold)
                    if stock_i < 0 or threshold_i < 0:
                        raise ValueError("Stock and threshold cannot be negative")
                    self.products[code] = {"name": name, "price": price_d, "cost_price": cost_price_d, "stock": stock_i, "low_stock_threshold": threshold_i, "category": category}
                    with open(PRODUCTS_CSV, "w", newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
                        for c, p in self.products.items():
                            writer.writerow([c, p["name"], str(p["price"]), str(p["cost_price"]), p["stock"], p["low_stock_threshold"], p["category"]])
                    self.refresh_product_list()
                    categories = ["All"] + sorted(set(p["category"] for p in self.products.values()))
                    self.category_combo['values'] = categories
                    messagebox.showinfo("Success", "Product saved")
                except Exception as e:
                    messagebox.showerror("Error", f"Invalid input: {e}")
        tk.Button(prod_frame, text="Save Product", command=save_product).pack(pady=5)
        tk.Label(prod_frame, text="Delete Product", font=("Arial", 10, "bold")).pack(pady=(10,0))
        tk.Label(prod_frame, text="Code to Delete").pack()
        delete_code_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=delete_code_var).pack()
        def delete_product():
            code = delete_code_var.get()
            if code in self.products:
                del self.products[code]
                with open(PRODUCTS_CSV, "w", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
                    for c, p in self.products.items():
                        writer.writerow([c, p["name"], str(p["price"]), str(p["cost_price"]), p["stock"], p["low_stock_threshold"], p["category"]])
                self.refresh_product_list()
                categories = ["All"] + sorted(set(p["category"] for p in self.products.values()))
                self.category_combo['values'] = categories
                messagebox.showinfo("Deleted", "Product deleted")
            else:
                messagebox.showerror("Error", "Product not found")
        tk.Button(prod_frame, text="Delete Product", command=delete_product).pack(pady=5)
        tk.Button(prod_frame, text="Import Products CSV", command=self.import_products_csv).pack(pady=5)
        tk.Button(prod_frame, text="Export Products CSV", command=self.export_products_csv).pack(pady=5)
        # Customer Management
        cust_frame = tk.LabelFrame(scrollable_frame, text="Customer Management", font=("Arial", 12, "bold"))
        cust_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(cust_frame, text="ID").pack()
        cust_id_var = tk.StringVar()
        tk.Entry(cust_frame, textvariable=cust_id_var).pack()
        tk.Label(cust_frame, text="Name").pack()
        cust_name_var = tk.StringVar()
        tk.Entry(cust_frame, textvariable=cust_name_var).pack()
        tk.Label(cust_frame, text="Phone").pack()
        cust_phone_var = tk.StringVar()
        tk.Entry(cust_frame, textvariable=cust_phone_var).pack()
        tk.Label(cust_frame, text="Loyalty Points").pack()
        cust_loyalty_var = tk.StringVar(value="0")
        tk.Entry(cust_frame, textvariable=cust_loyalty_var).pack()
        def save_customer():
            id_, name, phone, loyalty = cust_id_var.get(), cust_name_var.get(), cust_phone_var.get(), cust_loyalty_var.get()
            if id_ and name:
                try:
                    loyalty_i = int(loyalty)
                    if loyalty_i < 0:
                        raise ValueError("Loyalty points cannot be negative")
                    self.customers[id_] = {"name": name, "phone": phone, "loyalty_points": loyalty_i}
                    self.save_customers()
                    self.customer_entry['values'] = [c["name"] for c in self.customers.values()]
                    messagebox.showinfo("Success", "Customer saved")
                except Exception as e:
                    messagebox.showerror("Error", f"Invalid loyalty points: {e}")
        tk.Button(cust_frame, text="Save Customer", command=save_customer).pack(pady=5)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    def import_products_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                expected = ["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"]
                if not all(h in reader.fieldnames for h in ["code", "name", "price", "stock"]):
                    messagebox.showerror("Error", "Invalid CSV headers")
                    return
                for row in reader:
                    code = row["code"]
                    try:
                        price = Decimal(row["price"])
                        cost_price = Decimal(row.get("cost_price", "0"))
                        stock = int(row["stock"])
                        threshold = int(row.get("low_stock_threshold", "10"))
                        self.products[code] = {
                            "name": row["name"],
                            "price": price,
                            "cost_price": cost_price,
                            "stock": stock,
                            "low_stock_threshold": threshold,
                            "category": row.get("category", "General")
                        }
                    except Exception as e:
                        logging.warning(f"Error importing product {code}: {e}")
            self.save_products()
            self.refresh_product_list()
            self.category_combo['values'] = ["All"] + sorted(set(p["category"] for p in self.products.values()))
            messagebox.showinfo("Success", f"Products imported from {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import: {e}")
    def export_products_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
            for code, p in sorted(self.products.items()):
                writer.writerow([code, p["name"], str(p["price"]), str(p["cost_price"]), p["stock"], p["low_stock_threshold"], p["category"]])
        messagebox.showinfo("Exported", f"Products exported to {path}")
    def save_products(self):
        with open(PRODUCTS_CSV, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
            for code, p in self.products.items():
                writer.writerow([code, p["name"], str(p["price"]), str(p["cost_price"]), p["stock"], p["low_stock_threshold"], p["category"]])
    def add_new_customer(self):
        id_ = simpledialog.askstring("New Customer", "Enter ID:")
        if not id_ or id_ in self.customers:
            messagebox.showerror("Error", "Invalid or duplicate ID")
            return
        name = simpledialog.askstring("New Customer", "Enter Name:")
        if not name:
            return
        phone = simpledialog.askstring("New Customer", "Enter Phone:")
        points = simpledialog.askinteger("New Customer", "Enter Loyalty Points:", initialvalue=0)
        if points is None:
            return
        self.customers[id_] = {"name": name, "phone": phone, "loyalty_points": points}
        self.save_customers()
        self.customer_entry['values'] = [c["name"] for c in self.customers.values()]
        messagebox.showinfo("Added", "Customer added")
    def save_customers(self):
        with open(CUSTOMERS_CSV, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "phone", "loyalty_points"])
            for id_, c in self.customers.items():
                writer.writerow([id_, c["name"], c["phone"], c["loyalty_points"]])
    def toggle_theme(self):
        self.is_dark = not self.is_dark
        style = ttk.Style()
        if self.is_dark:
            self.configure(bg="#2C2C2C")
            style.configure("Treeview", background="#333333", foreground="#FFFFFF", fieldbackground="#333333")
            style.configure("Treeview.Heading", background="#555555", foreground="#FFFFFF")
            for widget in self.winfo_children():
                if isinstance(widget, tk.Frame):
                    widget.configure(bg="#2C2C2C")
                    for child in widget.winfo_children():
                        if isinstance(child, (tk.Label, tk.Button)):
                            child.configure(bg="#2C2C2C", fg="#FFFFFF")
                        elif isinstance(child, tk.Listbox):
                            child.configure(bg="#333333", fg="#FFFFFF")
                        elif isinstance(child, tk.Entry):
                            child.configure(bg="#333333", fg="#FFFFFF", insertbackground="#FFFFFF")
        else:
            self.configure(bg="SystemButtonFace")
            style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
            style.configure("Treeview.Heading", background="SystemButtonFace", foreground="black")
            for widget in self.winfo_children():
                if isinstance(widget, tk.Frame):
                    widget.configure(bg="SystemButtonFace")
                    for child in widget.winfo_children():
                        if isinstance(child, (tk.Label, tk.Button)):
                            child.configure(bg="SystemButtonFace", fg="black")
                        elif isinstance(child, tk.Listbox):
                            child.configure(bg="white", fg="black")
                        elif isinstance(child, tk.Entry):
                            child.configure(bg="white", fg="black", insertbackground="black")
    def profit_report(self):
        total_sales = Decimal("0")
        total_cost = Decimal("0")
        item_sales = {}
        for fname in os.listdir(INVOICES_DIR):
            if fname.startswith("invoice_") and fname.endswith(".csv"):
                try:
                    with open(os.path.join(INVOICES_DIR, fname), newline='', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        data = list(reader)
                        invoice_dict = dict(row for row in data if len(row) == 2 and row[0])
                        grand_total = Decimal(invoice_dict.get("grand_total", "0"))
                        total_sales += grand_total
                        items_start = False
                        for row in data:
                            if row == ["code", "name", "price", "qty", "total"]:
                                items_start = True
                                continue
                            if items_start:
                                if len(row) != 5:
                                    break
                                code, name, price, qty, _ = row
                                qty_i = int(qty)
                                cost = self.products.get(code, {}).get("cost_price", Decimal("0")) * Decimal(qty_i)
                                total_cost += cost
                                if code not in item_sales:
                                    item_sales[code] = {"units": 0, "name": name if "CUSTOM_" in code else self.products.get(code, {}).get("name", "Unknown")}
                                item_sales[code]["units"] += qty_i
                except Exception as e:
                    logging.warning(f"Error processing {fname} for profit: {e}")
        profit = total_sales - total_cost
        top_seller_code = max(item_sales, key=lambda c: item_sales[c]["units"]) if item_sales else "N/A"
        top_seller_name = item_sales[top_seller_code]["name"] if item_sales else "N/A"
        report = f"Total Sales: {money(total_sales)}\nTotal Cost: {money(total_cost)}\nProfit: {money(profit)}\nTop Seller: {top_seller_name} (Code: {top_seller_code}, Units Sold: {item_sales.get(top_seller_code, {'units': 0})['units']})"
        messagebox.showinfo("Profit Report", report)
        self.export_profit_report_pdf(total_sales, total_cost, profit, top_seller_name, top_seller_code, item_sales)
    def export_profit_report_pdf(self, total_sales, total_cost, profit, top_seller_name, top_seller_code, item_sales):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        doc = SimpleDocTemplate(path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"Profit Report - {SHOP_NAME}", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Total Sales: {money(total_sales)}", styles['Normal']))
        elements.append(Paragraph(f"Total Cost: {money(total_cost)}", styles['Normal']))
        elements.append(Paragraph(f"Profit: {money(profit)}", styles['Normal']))
        elements.append(Paragraph(f"Top Seller: {top_seller_name} (Code: {top_seller_code}, Units Sold: {item_sales.get(top_seller_code, {'units': 0})['units']})", styles['Normal']))
        elements.append(Spacer(1, 12))
        data = [["Code", "Name", "Units Sold"]]
        for code, d in sorted(item_sales.items(), key=lambda x: x[1]["units"], reverse=True)[:5]:
            data.append([code, d["name"], d["units"]])
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        doc.build(elements)
        messagebox.showinfo("Exported", f"Profit report saved to {path}")
    def advanced_reports(self):
        win = tk.Toplevel(self)
        win.title("Advanced Reports")
        win.geometry("400x300")
        tk.Button(win, text="Sales by Category", command=self.sales_by_category_report).pack(pady=5)
        tk.Button(win, text="Customer Purchase History", command=self.customer_purchase_history_report).pack(pady=5)
        tk.Button(win, text="Low Stock Summary", command=self.low_stock_summary_report).pack(pady=5)
    def sales_by_category_report(self):
        win = tk.Toplevel(self)
        win.title("Sales by Category")
        cols = ("category", "total_sales", "units_sold")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        tree.heading("category", text="Category")
        tree.heading("total_sales", text="Total Sales")
        tree.heading("units_sold", text="Units Sold")
        tree.pack(fill=tk.BOTH, expand=True)
       
        category_sales = {}
        for fname in os.listdir(INVOICES_DIR):
            if fname.startswith("invoice_") and fname.endswith(".csv"):
                try:
                    with open(os.path.join(INVOICES_DIR, fname), newline='', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        data = list(reader)
                        items_start = False
                        for row in data:
                            if row == ["code", "name", "price", "qty", "total"]:
                                items_start = True
                                continue
                            if items_start and len(row) == 5:
                                code, _, price, qty, _ = row
                                if "CUSTOM_" in code:
                                    category = "Custom"
                                else:
                                    category = self.products.get(code, {}).get("category", "Unknown")
                                qty_i = int(qty)
                                total = Decimal(price) * qty_i
                                if category not in category_sales:
                                    category_sales[category] = {"total": Decimal("0"), "units": 0}
                                category_sales[category]["total"] += total
                                category_sales[category]["units"] += qty_i
                except Exception as e:
                    logging.warning(f"Error processing {fname}: {e}")
        for cat, data in sorted(category_sales.items()):
            tree.insert("", tk.END, values=(cat, money(data["total"]), data["units"]))
        tk.Button(win, text="Export to PDF", command=lambda: self.export_report_to_pdf(tree, "Sales by Category")).pack(pady=5)
    def customer_purchase_history_report(self):
        win = tk.Toplevel(self)
        win.title("Customer Purchase History")
        tk.Label(win, text="Select Customer:").pack()
        customer_var = tk.StringVar()
        customer_combo = ttk.Combobox(win, textvariable=customer_var, values=[c["name"] for c in self.customers.values()])
        customer_combo.pack()
        def show_history():
            customer_name = customer_var.get()
            if not customer_name:
                return
            cols = ("invoice_number", "date", "total")
            tree = ttk.Treeview(win, columns=cols, show="headings")
            tree.heading("invoice_number", text="Invoice #")
            tree.heading("date", text="Date")
            tree.heading("total", text="Total")
            tree.pack(fill=tk.BOTH, expand=True)
            for fname in os.listdir(INVOICES_DIR):
                if fname.startswith("invoice_") and fname.endswith(".csv"):
                    try:
                        with open(os.path.join(INVOICES_DIR, fname), newline='', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            data = list(reader)
                            invoice_dict = dict(row for row in data if len(row) == 2 and row[0])
                            if invoice_dict.get("customer_name") == customer_name:
                                num = fname.split("_")[1].split(".")[0]
                                tree.insert("", tk.END, values=(num, invoice_dict.get("date", ""), money(Decimal(invoice_dict.get("grand_total", "0")))))
                    except Exception as e:
                        logging.warning(f"Error reading {fname}: {e}")
            tk.Button(win, text="Export to PDF", command=lambda: self.export_report_to_pdf(tree, "Customer Purchase History")).pack(pady=5)
        tk.Button(win, text="Show History", command=show_history).pack(pady=5)
    def low_stock_summary_report(self):
        win = tk.Toplevel(self)
        win.title("Low Stock Summary")
        cols = ("code", "name", "stock", "threshold")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        tree.heading("code", text="Code")
        tree.heading("name", text="Name")
        tree.heading("stock", text="Stock")
        tree.heading("threshold", text="Threshold")
        tree.pack(fill=tk.BOTH, expand=True)
        for code, p in sorted(self.products.items()):
            if p["stock"] < p["low_stock_threshold"]:
                tree.insert("", tk.END, values=(code, p["name"], p["stock"], p["low_stock_threshold"]))
        tk.Button(win, text="Export to PDF", command=lambda: self.export_report_to_pdf(tree, "Low Stock Summary")).pack(pady=5)
    def export_report_to_pdf(self, tree, title):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        doc = SimpleDocTemplate(path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"{title} - {SHOP_NAME}", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        data = [tree.heading(c)['text'] for c in tree['columns']]
        data = [data]
        for child in tree.get_children():
            data.append(tree.item(child, "values"))
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        doc.build(elements)
        messagebox.showinfo("Exported", f"Report saved to {path}")
    def process_return(self):
        self.show_invoice_history(for_return=True)
    def show_return_items(self, invoice_path):
        with open(invoice_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            data = list(reader)
            invoice_data = dict(row for row in data if len(row) == 2 and row[0])
            items = []
            items_start = False
            for row in data:
                if row == ["code", "name", "price", "qty", "total"]:
                    items_start = True
                    continue
                if items_start:
                    if len(row) != 5:
                        break
                    code, name, price, qty, total = row
                    items.append({"code": code, "name": name, "price": Decimal(price), "qty": int(qty), "line_total": Decimal(total)})
        win = tk.Toplevel(self)
        win.title("Select Items to Return")
        win.geometry("600x300")
        cols = ("code", "name", "price", "qty", "return_qty")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.capitalize())
            tree.column(c, anchor="center")
        tree.pack(fill=tk.BOTH, expand=True)
        return_cart = {}
        for item in items:
            tree.insert("", tk.END, values=(item["code"], item["name"], money(item["price"]), item["qty"], 0))
        tree.bind("<Double-Button-1>", lambda e: self.edit_return_qty(tree, items))
        def confirm_return():
            return_items = []
            points_deducted = 0
            for child in tree.get_children():
                vals = tree.item(child, "values")
                return_qty = int(vals[4])
                if return_qty > 0:
                    code = vals[0]
                    orig_qty = int(vals[3])
                    if return_qty > orig_qty:
                        messagebox.showwarning("Invalid", f"Cannot return more than {orig_qty} for {code}")
                        return
                    price = Decimal(vals[2])
                    line_total = price * Decimal(return_qty)
                    return_items.append({"code": code, "name": vals[1], "price": price, "qty": -return_qty, "line_total": -line_total})
                    if "CUSTOM_" not in code:
                        self.products[code]["stock"] += return_qty
            if not return_items:
                messagebox.showinfo("No Items", "No items selected for return.")
                win.destroy()
                return
            subtotal = sum(item["line_total"] for item in return_items)
            discount_percent = Decimal(invoice_data["discount_percent"])
            discount_amount = (subtotal * discount_percent / Decimal("100")).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
            subtotal_after_discount = (subtotal - discount_amount).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
            gst_percent = Decimal(invoice_data["gst_percent"])
            gst_total = (subtotal_after_discount * gst_percent / Decimal("100")).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
            cgst = (gst_total / 2).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
            sgst = (gst_total - cgst).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
            grand_total = (subtotal_after_discount + gst_total).quantize(CURRENCY_QUANT, rounding=ROUND_HALF_UP)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return_num = next_invoice_number()
            return_data = {
                "date": now,
                "customer_name": invoice_data["customer_name"],
                "customer_phone": invoice_data["customer_phone"],
                "items": return_items,
                "subtotal": subtotal,
                "discount_percent": discount_percent,
                "discount_amount": discount_amount,
                "subtotal_after_discount": subtotal_after_discount,
                "gst_percent": gst_percent,
                "gst_total": gst_total,
                "cgst": cgst,
                "sgst": sgst,
                "grand_total": grand_total,
                "points_awarded": points_deducted,
                "payment_status": "refunded",
                "original_invoice": invoice_data["invoice_number"]
            }
            if invoice_data.get("customer_name") != "Anonymous":
                for id_, c in self.customers.items():
                    if c["name"] == invoice_data["customer_name"]:
                        points_deducted = -int(abs(grand_total) // Decimal(10))
                        c["loyalty_points"] += points_deducted
                        self.save_customers()
                        break
            return_csv = os.path.join(INVOICES_DIR, f"return_{return_num}.csv")
            with open(return_csv, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["shop_name", SHOP_NAME])
                writer.writerow(["return_number", return_num])
                writer.writerow(["original_invoice", invoice_data["invoice_number"]])
                writer.writerow(["date", return_data["date"]])
                writer.writerow(["customer_name", return_data["customer_name"]])
                writer.writerow(["customer_phone", return_data["customer_phone"]])
                writer.writerow([])
                writer.writerow(["code", "name", "price", "qty", "total"])
                for row in return_data["items"]:
                    writer.writerow([row["code"], row["name"], money(row["price"]), row["qty"], money(row["line_total"])])
                writer.writerow([])
                writer.writerow(["subtotal", money(return_data["subtotal"])])
                writer.writerow(["discount_percent", str(return_data["discount_percent"])])
                writer.writerow(["discount_amount", money(return_data["discount_amount"])])
                writer.writerow(["subtotal_after_discount", money(return_data["subtotal_after_discount"])])
                writer.writerow(["gst_percent", str(return_data["gst_percent"])])
                writer.writerow(["gst_total", money(return_data["gst_total"])])
                writer.writerow(["cgst", money(return_data["cgst"])])
                writer.writerow(["sgst", money(return_data["sgst"])])
                writer.writerow(["grand_total", money(return_data["grand_total"])])
                writer.writerow(["points_deducted", points_deducted])
                writer.writerow(["payment_status", return_data["payment_status"]])
            orig_csv = invoice_path
            with open(orig_csv, newline='', encoding='utf-8') as f:
                orig_data = list(csv.reader(f))
            for row in orig_data:
                if row and row[0] == "payment_status":
                    row[1] = "partial/refunded"
                    break
            with open(orig_csv, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(orig_data)
            with open(PRODUCTS_CSV, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["code", "name", "price", "cost_price", "stock", "low_stock_threshold", "category"])
                for c, p in self.products.items():
                    writer.writerow([c, p["name"], str(p["price"]), str(p["cost_price"]), p["stock"], p["low_stock_threshold"], p["category"]])
            self.refresh_product_list()
            messagebox.showinfo("Return Processed", f"Return #{return_num} saved. Stock updated. Points deducted: {points_deducted}")
            win.destroy()
    def edit_return_qty(self, tree, items):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        code = vals[0]
        orig_qty = int(vals[3])
        new_qty = simpledialog.askinteger("Return Quantity", f"Enter return qty for {code} (max {orig_qty}):", minvalue=0, maxvalue=orig_qty)
        if new_qty is not None:
            tree.item(sel[0], values=(vals[0], vals[1], vals[2], vals[3], new_qty))
    def open_calculator(self):
        win = tk.Toplevel(self)
        win.title("Calculator")
        win.geometry("300x450")
        win.transient(self) # Make it float above the main window
        win.grab_set() # Make it modal
        # Position it relative to main window
        x = self.winfo_rootx() + 50
        y = self.winfo_rooty() + 50
        win.geometry(f"+{x}+{y}")
        # Modern styling
        win.configure(bg="#f0f0f0")
        entry_font = tkfont.Font(family="Arial", size=18, weight="bold")
        button_font = tkfont.Font(family="Arial", size=14)
        button_bg = "#e0e0e0"
        button_active_bg = "#d0d0d0"
        button_fg = "#333333"
        expression = tk.StringVar()
        display = tk.Entry(win, textvariable=expression, font=entry_font, justify="right", bg="white", bd=2, relief="solid")
        display.pack(fill=tk.X, padx=10, pady=10)
        # Button frame with grid
        buttons_frame = tk.Frame(win, bg="#f0f0f0")
        buttons_frame.pack(expand=True)
        # Button layout
        buttons = [
            [('C', 1, 0), ('±', 1, 1), ('%', 1, 2), ('÷', 1, 3)],
            [('7', 2, 0), ('8', 2, 1), ('9', 2, 2), ('×', 2, 3)],
            [('4', 3, 0), ('5', 3, 1), ('6', 3, 2), ('-', 3, 3)],
            [('1', 4, 0), ('2', 4, 1), ('3', 4, 2), ('+', 4, 3)],
            [('0', 5, 0, 2), ('.', 5, 2), ('=', 5, 3)]
        ]
        def add_to_expression(value):
            current = expression.get()
            expression.set(current + str(value))
        def calculate():
            try:
                result = eval(expression.get().replace('÷', '/').replace('×', '*').replace('±', '-'))
                expression.set(str(result))
            except Exception:
                expression.set("Error")
        def clear():
            expression.set("")
        def negate():
            current = expression.get()
            if current and current != "Error":
                if current.startswith('-'):
                    expression.set(current[1:])
                else:
                    expression.set('-' + current)
        def percent():
            current = expression.get()
            try:
                result = float(current) / 100
                expression.set(str(result))
            except:
                pass
        button_commands = {
            'C': clear,
            '±': negate,
            '%': percent,
            '=': calculate
        }
        for row_buttons in buttons:
            for btn_text, r, c, *span in row_buttons:
                if span:
                    colspan = span[0]
                else:
                    colspan = 1
                if btn_text in button_commands:
                    cmd = button_commands[btn_text]
                elif btn_text in ['÷', '×', '-', '+']:
                    cmd = lambda v=btn_text: add_to_expression(v)
                else:
                    cmd = lambda v=btn_text: add_to_expression(v)
                btn = tk.Button(buttons_frame, text=btn_text, font=button_font, bg=button_bg, fg=button_fg,
                                activebackground=button_active_bg, activeforeground=button_fg,
                                relief="raised", bd=2, command=cmd)
                btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2, columnspan=colspan)
        # Configure grid weights
        for i in range(6):
            buttons_frame.grid_rowconfigure(i, weight=1)
        for j in range(4):
            buttons_frame.grid_columnconfigure(j, weight=1)
        # Bind Enter to calculate
        display.bind("<Return>", lambda e: calculate())
        # Keyboard bindings
        def handle_key(event):
            char = event.char
            keysym = event.keysym
            if char in "0123456789.":
                add_to_expression(char)
            elif char in "+-*":
                add_to_expression(char)
            elif char == "/":
                add_to_expression("÷")
            elif char == "*":
                add_to_expression("×")
            elif char == "%":
                percent()
            elif keysym == "Return" or char == "=":
                calculate()
            elif keysym == "BackSpace":
                expression.set(expression.get()[:-1])
            elif char.lower() == "c":
                clear()
            elif char == "!": # Arbitrary for ±
                negate()
        win.bind("<Key>", handle_key)
        display.focus_set()
    def go_home(self):
        self.destroy()
        landing = LandingPage()
        landing.mainloop()
if __name__ == "__main__":
    landing = LandingPage()
    landing.mainloop()
