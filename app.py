import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from pathlib import Path
from datetime import datetime
import sqlite3
import shutil
import csv

# ----------------- تحديد مسار حفظ آمن ودائم -----------------
APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "InventoryManagerApp"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_FILE = APP_DATA_DIR / "inventory.db"
IMAGE_DIR = APP_DATA_DIR / "product_images"
IMAGE_DIR.mkdir(exist_ok=True)

# ---------------- Database ----------------
conn = sqlite3.connect(DB_FILE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE,
    barcode TEXT UNIQUE,
    quantity INTEGER NOT NULL DEFAULT 0,
    min_stock INTEGER NOT NULL DEFAULT 0,
    image TEXT DEFAULT ''
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    old_quantity INTEGER NOT NULL,
    new_quantity INTEGER NOT NULL,
    date_time TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(id)
)
""")
conn.commit()

# ---------------- Helpers ----------------
def product_rows(search=""):
    search = search.strip()
    if search:
        return cur.execute("""
            SELECT * FROM products
            WHERE name LIKE ? OR barcode LIKE ?
            ORDER BY name COLLATE NOCASE ASC
        """, (f"%{search}%", f"%{search}%")).fetchall()
    return cur.execute("""
        SELECT * FROM products
        ORDER BY name COLLATE NOCASE ASC
    """).fetchall()

def stats():
    total_products = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_stock = cur.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]
    low_stock = cur.execute(
        "SELECT COUNT(*) FROM products WHERE quantity > 0 AND quantity <= min_stock"
    ).fetchone()[0]
    out_stock = cur.execute(
        "SELECT COUNT(*) FROM products WHERE quantity = 0"
    ).fetchone()[0]
    return total_products, total_stock, low_stock, out_stock

def add_movement(product_id, movement_type, amount, old_q, new_q):
    cur.execute("""
        INSERT INTO movements
        (product_id, movement_type, amount, old_quantity, new_quantity, date_time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        product_id, movement_type, amount, old_q, new_q,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

# ---------------- Main Window ----------------
root = tk.Tk()
root.title("Inventory Manager")
root.geometry("1200x750")
root.minsize(1000, 650)
root.configure(bg="#F4F6F9")

# ---------------- Dynamic Styles & Colors ----------------
COLOR_BG = "#F4F6F9"
COLOR_PRIMARY = "#2C3E50"      # dark blue-gray
COLOR_ACCENT = "#2980B9"       # bright blue
COLOR_TEXT_MAIN = "#1A252F"

style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass

# Root & Frame backgrounds
style.configure(".", background=COLOR_BG, font=("Segoe UI", 11))
style.configure("TFrame", background=COLOR_BG)
style.configure("TLabelFrame", background=COLOR_BG, font=("Segoe UI", 11, "bold"), foreground=COLOR_PRIMARY)
style.configure("TLabelFrame.Label", background=COLOR_BG, foreground=COLOR_PRIMARY)

# Header
style.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), foreground=COLOR_PRIMARY, background=COLOR_BG)

# General Labels
style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MAIN, font=("Segoe UI", 11))

# Buttons Styling
style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=8, background="#34495E", foreground="#FFFFFF")
style.map("TButton",
    background=[("active", "#2C3E50"), ("pressed", "#1A252F")],
    foreground=[("active", "#FFFFFF")]
)

style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), padding=8, background=COLOR_ACCENT, foreground="#FFFFFF")
style.map("Accent.TButton",
    background=[("active", "#1F618D"), ("pressed", "#154360")],
    foreground=[("active", "#FFFFFF")]
)

style.configure("Success.TButton", font=("Segoe UI", 11, "bold"), padding=8, background="#27AE60", foreground="#FFFFFF")
style.map("Success.TButton",
    background=[("active", "#1E8449")],
    foreground=[("active", "#FFFFFF")]
)

style.configure("Danger.TButton", font=("Segoe UI", 11, "bold"), padding=8, background="#E74C3C", foreground="#FFFFFF")
style.map("Danger.TButton",
    background=[("active", "#C0392B")],
    foreground=[("active", "#FFFFFF")]
)

# Treeview / Table Styling
style.configure("Treeview",
    font=("Segoe UI", 12),
    rowheight=32,
    background="#FFFFFF",
    fieldbackground="#FFFFFF",
    foreground="#2C3E50"
)
style.configure("Treeview.Heading",
    font=("Segoe UI", 12, "bold"),
    background="#EAECEE",
    foreground=COLOR_PRIMARY,
    padding=6
)
style.map("Treeview",
    background=[("selected", COLOR_ACCENT)],
    foreground=[("selected", "#FFFFFF")]
)

# Entry fields
style.configure("TEntry", font=("Segoe UI", 12), padding=6)

# ---------------- UI Layout ----------------

# Header
header = ttk.Frame(root, padding=(16, 16, 16, 8))
header.pack(fill="x")

ttk.Label(
    header, text="📦 Inventory Management System",
    style="Header.TLabel"
).pack(side="left")

# Dashboard Cards
dashboard = ttk.Frame(root, padding=(16, 0, 16, 10))
dashboard.pack(fill="x")

stat_vars = [tk.StringVar(value="0") for _ in range(4)]
stat_names = ["Total Products", "Total Stock", "Low Stock", "Out of Stock"]
card_colors = ["#2980B9", "#27AE60", "#F39C12", "#C0392B"]

for i, name in enumerate(stat_names):
    box = ttk.LabelFrame(dashboard, text=f"  {name}  ", padding=12)
    box.grid(row=0, column=i, sticky="ew", padx=6)
    dashboard.columnconfigure(i, weight=1)
    
    lbl = ttk.Label(
        box, textvariable=stat_vars[i],
        font=("Segoe UI", 22, "bold"),
        foreground=card_colors[i]
    )
    lbl.pack()

# Search Bar
search_frame = ttk.Frame(root, padding=(16, 5, 16, 10))
search_frame.pack(fill="x")

ttk.Label(search_frame, text="🔎 Search / Scan Barcode:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 8))
search_var = tk.StringVar()
search_entry = ttk.Entry(search_frame, textvariable=search_var)
search_entry.pack(side="left", fill="x", expand=True)

# Product Table
table_frame = ttk.Frame(root, padding=(16, 0, 16, 10))
table_frame.pack(fill="both", expand=True)

columns = ("name", "barcode", "quantity", "min_stock", "status")
tree = ttk.Treeview(table_frame, columns=columns, show="headings")

tree.heading("name", text="Product Name")
tree.heading("barcode", text="Barcode")
tree.heading("quantity", text="Quantity")
tree.heading("min_stock", text="Min. Stock")
tree.heading("status", text="Status")

tree.column("name", width=360)
tree.column("barcode", width=180)
tree.column("quantity", width=110, anchor="center")
tree.column("min_stock", width=110, anchor="center")
tree.column("status", width=150, anchor="center")

# Colored Tags for Table Rows
tree.tag_configure("instock", background="#E8F8F5")
tree.tag_configure("lowstock", background="#FEF9E7")
tree.tag_configure("outstock", background="#FDEDEC")

scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scroll.set)

tree.pack(side="left", fill="both", expand=True)
scroll.pack(side="right", fill="y")

# ---------------- Refresh Function ----------------
def refresh():
    for item in tree.get_children():
        tree.delete(item)

    for p in product_rows(search_var.get()):
        q = p["quantity"]
        minimum = p["min_stock"]

        if q == 0:
            status = "OUT OF STOCK"
            tag = "outstock"
        elif q <= minimum:
            status = "LOW STOCK"
            tag = "lowstock"
        else:
            status = "IN STOCK"
            tag = "instock"

        tree.insert(
            "", "end", iid=str(p["id"]),
            values=(p["name"], p["barcode"] or "", q, minimum, status),
            tags=(tag,)
        )

    values = stats()
    for var, value in zip(stat_vars, values):
        var.set(str(value))

def selected_product():
    selected = tree.selection()
    if not selected:
        return None
    return cur.execute(
        "SELECT * FROM products WHERE id=?", (int(selected[0]),)
    ).fetchone()

search_var.trace_add("write", lambda *_: refresh())

# ---------------- Add Product Window ----------------
def add_product():
    win = tk.Toplevel(root)
    win.title("Add Product")
    win.geometry("540x630")
    win.configure(bg=COLOR_BG)
    win.transient(root)
    win.grab_set()

    name_var = tk.StringVar()
    barcode_var = tk.StringVar()
    quantity_var = tk.StringVar(value="0")
    min_var = tk.StringVar(value="0")
    image_var = tk.StringVar()

    preview = ttk.Label(win, text="No Image Selected", anchor="center", font=("Segoe UI", 10, "italic"))
    preview.pack(pady=12)

    form = ttk.Frame(win, padding=20)
    form.pack(fill="x")

    def field(label, variable):
        ttk.Label(form, text=label, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Entry(form, textvariable=variable).pack(fill="x", pady=(3, 10))

    field("Product Name:", name_var)
    field("Barcode:", barcode_var)
    field("Initial Quantity:", quantity_var)
    field("Minimum Stock:", min_var)

    def choose_image():
        path = filedialog.askopenfilename(
            title="Select Product Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")]
        )
        if path:
            image_var.set(path)
            img = Image.open(path)
            img.thumbnail((190, 160))
            photo = ImageTk.PhotoImage(img)
            preview.configure(image=photo, text="")
            preview.image = photo

    ttk.Button(form, text="📷 Choose Product Image", command=choose_image).pack(fill="x", pady=5)

    def save():
        name = name_var.get().strip()
        barcode = barcode_var.get().strip() or None

        if not name:
            messagebox.showerror("Error", "Product name is required.", parent=win)
            return

        try:
            quantity = int(quantity_var.get())
            minimum = int(min_var.get())
            if quantity < 0 or minimum < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Error",
                "Quantity and Minimum Stock must be non-negative whole numbers.",
                parent=win
            )
            return

        try:
            cur.execute("""
                INSERT INTO products (name, barcode, quantity, min_stock)
                VALUES (?, ?, ?, ?)
            """, (name, barcode, quantity, minimum))
            product_id = cur.lastrowid

            source = image_var.get()
            if source:
                ext = Path(source).suffix.lower()
                filename = f"product_{product_id}{ext}"
                shutil.copy2(source, IMAGE_DIR / filename)
                cur.execute(
                    "UPDATE products SET image=? WHERE id=?",
                    (filename, product_id)
                )

            if quantity:
                add_movement(product_id, "STOCK IN", quantity, 0, quantity)

            conn.commit()
            refresh()
            win.destroy()

        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Duplicate Barcode",
                "This barcode is already assigned to another product.",
                parent=win
            )
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", str(e), parent=win)

    ttk.Button(form, text="Save Product", style="Success.TButton", command=save).pack(fill="x", pady=(15, 5))
    ttk.Button(form, text="Cancel", command=win.destroy).pack(fill="x")

# ---------------- Stock Movement Window ----------------
def change_stock(stock_in=True):
    product = selected_product()
    if not product:
        messagebox.showwarning("No Selection", "Please select a product first.")
        return

    win = tk.Toplevel(root)
    win.title("Stock In" if stock_in else "Stock Out")
    win.geometry("400x240")
    win.configure(bg=COLOR_BG)
    win.transient(root)
    win.grab_set()

    amount_var = tk.StringVar()

    title_color = "#27AE60" if stock_in else "#E74C3C"
    title_lbl = ttk.Label(
        win,
        text=f"{'Stock In' if stock_in else 'Stock Out'}: {product['name']}",
        font=("Segoe UI", 14, "bold"),
        foreground=title_color
    )
    title_lbl.pack(pady=18)

    ttk.Label(win, text="Quantity:", font=("Segoe UI", 11, "bold")).pack()
    entry = ttk.Entry(win, textvariable=amount_var)
    entry.pack(pady=6)
    entry.focus()

    def apply():
        try:
            amount = int(amount_var.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Quantity",
                "Enter a positive whole number.",
                parent=win
            )
            return

        old_q = product["quantity"]
        new_q = old_q + amount if stock_in else old_q - amount

        if new_q < 0:
            messagebox.showerror(
                "Not Enough Stock",
                f"Current stock is {old_q}.",
                parent=win
            )
            return

        cur.execute(
            "UPDATE products SET quantity=? WHERE id=?",
            (new_q, product["id"])
        )
        add_movement(
            product["id"],
            "STOCK IN" if stock_in else "STOCK OUT",
            amount, old_q, new_q
        )
        conn.commit()
        refresh()
        win.destroy()

    btn_style = "Success.TButton" if stock_in else "Danger.TButton"
    ttk.Button(
        win, text="Apply", style=btn_style,
        command=apply
    ).pack(fill="x", padx=50, pady=12)

# ---------------- Edit Product Window ----------------
def edit_product():
    product = selected_product()
    if not product:
        messagebox.showwarning("No Selection", "Please select a product first.")
        return

    win = tk.Toplevel(root)
    win.title("Edit Product")
    win.geometry("540x580")
    win.configure(bg=COLOR_BG)
    win.transient(root)
    win.grab_set()

    name_var = tk.StringVar(value=product["name"])
    barcode_var = tk.StringVar(value=product["barcode"] or "")
    min_var = tk.StringVar(value=str(product["min_stock"]))
    image_var = tk.StringVar()

    preview = ttk.Label(win, text="No Image Available", anchor="center", font=("Segoe UI", 10, "italic"))
    preview.pack(pady=12)

    if product["image"]:
        old_path = IMAGE_DIR / product["image"]
        if old_path.exists():
            try:
                img = Image.open(old_path)
                img.thumbnail((190, 160))
                photo = ImageTk.PhotoImage(img)
                preview.configure(image=photo, text="")
                preview.image = photo
            except Exception:
                pass

    form = ttk.Frame(win, padding=20)
    form.pack(fill="x")

    for label, variable in [
        ("Product Name:", name_var),
        ("Barcode:", barcode_var),
        ("Minimum Stock:", min_var)
    ]:
        ttk.Label(form, text=label, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Entry(form, textvariable=variable).pack(fill="x", pady=(3, 10))

    def choose_image():
        path = filedialog.askopenfilename(
            title="Select Product Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")]
        )
        if path:
            image_var.set(path)
            img = Image.open(path)
            img.thumbnail((190, 160))
            photo = ImageTk.PhotoImage(img)
            preview.configure(image=photo, text="")
            preview.image = photo

    ttk.Button(form, text="📷 Change Product Image", command=choose_image).pack(fill="x", pady=5)

    def save():
        name = name_var.get().strip()
        barcode = barcode_var.get().strip() or None

        try:
            minimum = int(min_var.get())
            if minimum < 0 or not name:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Error",
                "Enter a valid name and minimum stock.",
                parent=win
            )
            return

        try:
            cur.execute("""
                UPDATE products
                SET name=?, barcode=?, min_stock=?
                WHERE id=?
            """, (name, barcode, minimum, product["id"]))

            source = image_var.get()
            if source:
                ext = Path(source).suffix.lower()
                filename = f"product_{product['id']}{ext}"
                shutil.copy2(source, IMAGE_DIR / filename)
                cur.execute(
                    "UPDATE products SET image=? WHERE id=?",
                    (filename, product["id"])
                )

            conn.commit()
            refresh()
            win.destroy()

        except sqlite3.IntegrityError:
            conn.rollback()
            messagebox.showerror(
                "Duplicate Barcode",
                "This barcode is already assigned to another product.",
                parent=win
            )

    ttk.Button(form, text="Save Changes", style="Success.TButton", command=save).pack(fill="x", pady=(15, 5))
    ttk.Button(form, text="Cancel", command=win.destroy).pack(fill="x")

# ---------------- Delete Product ----------------
def delete_product():
    product = selected_product()
    if not product:
        messagebox.showwarning("No Selection", "Please select a product first.")
        return

    if not messagebox.askyesno(
        "Delete Product",
        f"Are you sure you want to delete '{product['name']}'?"
    ):
        return

    cur.execute("DELETE FROM movements WHERE product_id=?", (product["id"],))
    cur.execute("DELETE FROM products WHERE id=?", (product["id"],))
    conn.commit()
    refresh()

# ---------------- Movement History ----------------
def movement_history():
    product = selected_product()

    win = tk.Toplevel(root)
    win.title("Stock Movement History")
    win.geometry("950x520")
    win.configure(bg=COLOR_BG)

    columns = ("date", "product", "type", "amount", "old", "new")
    hist = ttk.Treeview(win, columns=columns, show="headings")

    labels = {
        "date": "Date & Time",
        "product": "Product",
        "type": "Movement",
        "amount": "Amount",
        "old": "Old Stock",
        "new": "New Stock"
    }

    for c in columns:
        hist.heading(c, text=labels[c])

    hist.column("date", width=170)
    hist.column("product", width=260)
    hist.column("type", width=130)
    hist.column("amount", width=100, anchor="center")
    hist.column("old", width=100, anchor="center")
    hist.column("new", width=100, anchor="center")

    sql = """
        SELECT m.*, p.name
        FROM movements m
        JOIN products p ON p.id=m.product_id
    """
    params = ()

    if product:
        sql += " WHERE m.product_id=?"
        params = (product["id"],)

    sql += " ORDER BY m.id DESC"

    for row in cur.execute(sql, params):
        hist.insert(
            "", "end",
            values=(
                row["date_time"], row["name"],
                row["movement_type"], row["amount"],
                row["old_quantity"], row["new_quantity"]
            )
        )

    hist.pack(fill="both", expand=True, padx=12, pady=12)

# ---------------- Show Image ----------------
def show_image():
    product = selected_product()
    if not product:
        messagebox.showwarning("No Selection", "Please select a product first.")
        return

    if not product["image"]:
        messagebox.showinfo("Product Image", "No image available.")
        return

    path = IMAGE_DIR / product["image"]
    if not path.exists():
        messagebox.showinfo("Product Image", "Image file not found.")
        return

    win = tk.Toplevel(root)
    win.title(product["name"])
    win.configure(bg=COLOR_BG)

    img = Image.open(path)
    img.thumbnail((700, 550))
    photo = ImageTk.PhotoImage(img)

    label = ttk.Label(win, image=photo)
    label.image = photo
    label.pack(padx=15, pady=15)

# ---------------- Export CSV ----------------
def export_csv():
    path = filedialog.asksaveasfilename(
        title="Export Inventory",
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")]
    )
    if not path:
        return

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Product Name", "Barcode", "Quantity", "Minimum Stock", "Status"])

        for p in product_rows():
            q = p["quantity"]
            status = "OUT OF STOCK" if q == 0 else (
                "LOW STOCK" if q <= p["min_stock"] else "IN STOCK"
            )
            writer.writerow([
                p["name"], p["barcode"] or "",
                q, p["min_stock"], status
            ])

    messagebox.showinfo("Export Complete", "Inventory exported successfully.")

# ---------------- Control Buttons ----------------
buttons = ttk.Frame(root, padding=(16, 5, 16, 16))
buttons.pack(fill="x")

ttk.Button(buttons, text="➕ Add Product", style="Accent.TButton", command=add_product).pack(side="left", padx=4)
ttk.Button(buttons, text="✏️ Edit", command=edit_product).pack(side="left", padx=4)
ttk.Button(buttons, text="🗑️ Delete", style="Danger.TButton", command=delete_product).pack(side="left", padx=4)

ttk.Separator(buttons, orient="vertical").pack(side="left", fill="y", padx=10)

ttk.Button(buttons, text="Stock In (+)", style="Success.TButton", command=lambda: change_stock(True)).pack(side="left", padx=4)
ttk.Button(buttons, text="Stock Out (-)", style="Danger.TButton", command=lambda: change_stock(False)).pack(side="left", padx=4)

ttk.Separator(buttons, orient="vertical").pack(side="left", fill="y", padx=10)

ttk.Button(buttons, text="🖼️ View Image", command=show_image).pack(side="left", padx=4)
ttk.Button(buttons, text="📜 Movement History", command=movement_history).pack(side="left", padx=4)
ttk.Button(buttons, text="📊 Export CSV", command=export_csv).pack(side="left", padx=4)

tree.bind("<Double-1>", lambda e: show_image())

def on_close():
    conn.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

refresh()
search_entry.focus()
root.mainloop()
