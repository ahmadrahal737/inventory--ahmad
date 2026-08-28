import streamlit as st
import sqlite3
from PIL import Image
import io
import secrets
import hashlib
import hmac
import time

try:
    from streamlit_cookies_controller import CookieController
except ImportError:
    st.error("Please install: pip install streamlit-cookies-controller")
    st.stop()

# ============================================================
# ENGINEER AHMAD - CAR KEY INVENTORY (STABLE COOKIES)
# ============================================================

DB_NAME = "car_keys.db"
LOW_STOCK_DEFAULT = 5

DEFAULT_ADMIN_EMAIL = "ahmad@example.com"
DEFAULT_ADMIN_PASSWORD = "changeme123"

SECRET_KEY = "ahmad-car-keys-please-change-this-secret"
COOKIE_NAME = "ahmad_key_inventory_auth"
LOGIN_DAYS = 365

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Engineer Ahmad | Car Key Inventory",
    page_icon="🔑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CSS STYLING
# ============================================================

st.markdown("""
<style>
:root {
    --orange: #F57C00;
    --dark-orange: #E65100;
    --black: #111111;
    --red: #D32F2F;
    --light: #F5F5F5;
    --white: #FFFFFF;
    --gray: #555555;
}

.stApp {
    background: #ECEDEF;
}

.block-container {
    max-width: 1250px;
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}

.main-title {
    background: #111111;
    color: #FFA733;
    padding: 18px;
    border-radius: 15px;
    text-align: center;
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 20px;
}

p, span, label, li, div[data-testid="stMarkdownContainer"] {
    color: #1A1A1A;
}

.key-name {
    color: #111111;
    font-size: 24px;
    font-weight: 800;
    margin-bottom: 8px;
}

.stock-good {
    color: #1B5E20;
    font-size: 20px;
    font-weight: 800;
}

.stock-low {
    color: #C62828;
    font-size: 20px;
    font-weight: 800;
}

div.stButton > button,
div.stFormSubmitButton > button {
    min-height: 48px;
    border-radius: 11px;
    font-weight: 700;
    font-size: 16px;
    border: 1.5px solid #D8D8D8;
    color: #111111;
}

div.stButton > button[kind="primary"],
div.stFormSubmitButton > button[kind="primary"] {
    background: #F57C00;
    color: #FFFFFF;
    border: none;
}

div.stButton > button[kind="primary"]:hover,
div.stFormSubmitButton > button[kind="primary"]:hover {
    background: #E65100;
}

input, textarea {
    border-radius: 10px !important;
    color: #111111 !important;
}

section[data-testid="stSidebar"] {
    background: #161616;
}

section[data-testid="stSidebar"] * {
    color: #F1F1F1;
}

div[data-testid="stMetricValue"] {
    color: #111111;
    font-weight: 800;
}
div[data-testid="stMetricLabel"] {
    color: #444444;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE SETUP
# ============================================================

def db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_database():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_account (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS keys_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_name TEXT NOT NULL,
            part_number TEXT,
            brand TEXT,
            car_model TEXT,
            year TEXT,
            key_type TEXT,
            key_color TEXT,
            quantity INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            low_stock_limit INTEGER DEFAULT 5,
            image BLOB,
            notes TEXT,
            link TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            action TEXT,
            key_id INTEGER,
            quantity_change INTEGER DEFAULT 0,
            new_quantity INTEGER,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM admin_account WHERE id = 1")
    if cur.fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO admin_account (id, email, password_hash) VALUES (1, ?, ?)",
            (DEFAULT_ADMIN_EMAIL.strip().lower(), hash_password(DEFAULT_ADMIN_PASSWORD))
        )
        conn.commit()

    conn.close()

# ============================================================
# PASSWORD SECURITY
# ============================================================

def hash_password(password):
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 150000)
    return salt.hex() + ":" + key.hex()

def check_password(password, stored):
    try:
        salt_hex, key_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 150000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

init_database()

# ============================================================
# ADMIN ACCOUNT HELPERS
# ============================================================

def get_admin():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT email, password_hash FROM admin_account WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return row

def verify_admin_login(email, password):
    admin_email, admin_hash = get_admin()
    email = email.strip().lower()
    if email != admin_email:
        return False
    return check_password(password, admin_hash)

def update_admin_credentials(new_email, new_password):
    conn = db()
    conn.execute(
        "UPDATE admin_account SET email=?, password_hash=?, updated_at=CURRENT_TIMESTAMP WHERE id=1",
        (new_email.strip().lower(), hash_password(new_password))
    )
    conn.commit()
    conn.close()

# ============================================================
# COOKIE HELPERS & SESSION STATE (STABLE FIX)
# ============================================================

def make_token(email):
    sig = hmac.new(SECRET_KEY.encode(), email.encode(), hashlib.sha256).hexdigest()
    return f"{email}|{sig}"

def verify_token(token):
    try:
        email, sig = token.split("|")
        expected = hmac.new(SECRET_KEY.encode(), email.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected):
            admin_email, _ = get_admin()
            if email == admin_email:
                return email
    except Exception:
        pass
    return None

# تخزين الـ CookieController في الsession_state لضمان استقرار العمل وعدم تكراره
if "cookie_controller" not in st.session_state:
    st.session_state.cookie_controller = CookieController()

cookie_controller = st.session_state.cookie_controller

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "cookie_checked" not in st.session_state:
    st.session_state.cookie_checked = False

# التحقق من وجود الكوكي تلقائياً عند فتح الموقع
if not st.session_state.logged_in:
    try:
        cookies_dict = cookie_controller.getAll()
        saved_token = cookies_dict.get(COOKIE_NAME) if cookies_dict else None
    except Exception:
        saved_token = None

    if saved_token:
        restored_email = verify_token(saved_token)
        if restored_email:
            st.session_state.logged_in = True
            st.session_state.user_email = restored_email

    if not st.session_state.logged_in and not st.session_state.cookie_checked:
        st.session_state.cookie_checked = True
        time.sleep(0.2)
        st.rerun()

def logout_user():
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    try:
        cookie_controller.remove(COOKIE_NAME)
        time.sleep(0.1)
    except Exception:
        pass
    st.rerun()

# ============================================================
# LOGIN SCREEN
# ============================================================

if not st.session_state.logged_in:
    st.markdown(
        """
        <div class="main-title">
            🔑 ENGINEER AHMAD<br>
            CAR KEY INVENTORY
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("Login")
    email = st.text_input("EMAIL", placeholder="Enter your email", key="login_email")
    password = st.text_input("PASSWORD", type="password", placeholder="Enter your password", key="login_password")
    stay_signed_in = st.checkbox("Stay signed in on this device", value=True)

    if st.button("🔐 LOGIN", type="primary", use_container_width=True):
        if not email or not password:
            st.warning("Please enter your email and password.")
        elif verify_admin_login(email, password):
            admin_email, _ = get_admin()
            st.session_state.logged_in = True
            st.session_state.user_email = admin_email
            if stay_signed_in:
                try:
                    cookie_controller.set(
                        COOKIE_NAME,
                        make_token(admin_email),
                        max_age=LOGIN_DAYS * 24 * 60 * 60
                    )
                    time.sleep(0.2) # مهلة بسيطة لضمان حفظ الكوكي بالمتصفح قبل إعادة التحميل
                except Exception:
                    pass
            st.rerun()
        else:
            st.error("Invalid email or password.")

    st.stop()

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    """
    <h2 style="color:#FFA733;">🔑 Engineer Ahmad</h2>
    """,
    unsafe_allow_html=True
)

st.sidebar.caption("Car Key Inventory")
st.sidebar.write(f"👤 {st.session_state.user_email}")
st.sidebar.success("👑 ADMIN")

menu_items = [
    "🏠 DASHBOARD",
    "🔑 CAR KEYS",
    "➕ ADD KEY",
    "📋 HISTORY",
    "⚙ ACCOUNT"
]

page = st.sidebar.radio("MENU", menu_items)

if st.sidebar.button("🚪 LOGOUT", use_container_width=True):
    logout_user()

# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 DASHBOARD":
    st.markdown(
        """
        <div class="main-title">
            🔑 ENGINEER AHMAD<br>
            CAR KEY INVENTORY
        </div>
        """,
        unsafe_allow_html=True
    )

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*),
            COALESCE(SUM(quantity),0),
            COALESCE(SUM(quantity * price),0)
        FROM keys_inventory
    """)
    total_keys, total_quantity, total_value = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM keys_inventory WHERE quantity <= low_stock_limit")
    low_stock = cur.fetchone()[0]
    conn.close()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔑 KEY TYPES", total_keys)
    c2.metric("📦 TOTAL STOCK", total_quantity)
    c3.metric("⚠ LOW STOCK", low_stock)
    c4.metric("💰 STOCK VALUE", f"${total_value:,.2f}")

    st.divider()
    st.subheader("Quick Search")
    quick_search = st.text_input("SEARCH CAR KEY", placeholder="Search by key name, part number, brand or model...")

    if quick_search:
        conn = db()
        cur = conn.cursor()
        pattern = f"%{quick_search}%"
        cur.execute("""
            SELECT id, key_name, part_number, brand, car_model, quantity, price
            FROM keys_inventory
            WHERE key_name LIKE ? OR part_number LIKE ? OR brand LIKE ? OR car_model LIKE ?
            ORDER BY key_name COLLATE NOCASE ASC
        """, (pattern, pattern, pattern, pattern))
        results = cur.fetchall()
        conn.close()

        for row in results:
            st.write(
                f"🔑 **{row[1]}** | "
                f"Part: {row[2] or '-'} | "
                f"{row[3] or '-'} | "
                f"{row[4] or '-'} | "
                f"Stock: **{row[5]}** | "
                f"${row[6]:.2f}"
            )

    if low_stock:
        st.divider()
        st.subheader("⚠ Low Stock Items")
        conn = db()
        cur = conn.cursor()
        cur.execute("""
            SELECT key_name, quantity, low_stock_limit
            FROM keys_inventory
            WHERE quantity <= low_stock_limit
            ORDER BY quantity ASC
        """)
        low_items = cur.fetchall()
        conn.close()
        for name, qty, limit in low_items:
            st.write(f"🔴 **{name}** — {qty} left (alert at {limit})")

# ============================================================
# CAR KEYS
# ============================================================

elif page == "🔑 CAR KEYS":
    st.markdown(
        """
        <div class="main-title">
            🔑 CAR KEYS
        </div>
        """,
        unsafe_allow_html=True
    )

    search = st.text_input("🔍 SEARCH", placeholder="Key name / Part Number / Brand / Model / Year / Type...")
    show_low_only = st.checkbox("Show low stock only", value=False)

    conn = db()
    cur = conn.cursor()

    if search:
        pattern = f"%{search}%"
        cur.execute("""
            SELECT id, key_name, part_number, brand, car_model, year, key_type, key_color, quantity, price, low_stock_limit, image, notes, link
            FROM keys_inventory
            WHERE key_name LIKE ? OR part_number LIKE ? OR brand LIKE ? OR car_model LIKE ? OR year LIKE ? OR key_type LIKE ? OR key_color LIKE ?
            ORDER BY key_name COLLATE NOCASE ASC
        """, (pattern, pattern, pattern, pattern, pattern, pattern, pattern))
    else:
        cur.execute("""
            SELECT id, key_name, part_number, brand, car_model, year, key_type, key_color, quantity, price, low_stock_limit, image, notes, link
            FROM keys_inventory
            ORDER BY key_name COLLATE NOCASE ASC
        """)

    keys = cur.fetchall()
    conn.close()

    if show_low_only:
        keys = [item for item in keys if item[8] <= item[10]]

    st.caption(f"{len(keys)} key(s) found")

    for item in keys:
        (
            key_id, key_name, part_number, brand, car_model, year,
            key_type, key_color, quantity, price, low_limit,
            image_data, notes, link
        ) = item

        with st.container(border=True):
            image_col, info_col, action_col = st.columns([1.2, 3, 1.4])

            with image_col:
                if image_data:
                    try:
                        image = Image.open(io.BytesIO(image_data))
                        st.image(image, use_container_width=True)
                    except Exception:
                        st.write("🖼 Image unavailable")
                else:
                    st.markdown(
                        """
                        <div style="height:130px;display:flex;align-items:center;justify-content:center;background:#EEEEEE;border-radius:12px;font-size:45px;">
                        🔑
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            with info_col:
                st.markdown(f'<div class="key-name">{key_name}</div>', unsafe_allow_html=True)
                if part_number: st.write(f"🔢 **PART NUMBER:** {part_number}")
                if brand: st.write(f"🚗 **BRAND:** {brand}")
                if car_model: st.write(f"🚘 **MODEL:** {car_model}")
                if year: st.write(f"📅 **YEAR:** {year}")
                if key_type: st.write(f"🔐 **KEY TYPE:** {key_type}")
                if key_color: st.write(f"🎨 **COLOR:** {key_color}")

                if quantity <= low_limit:
                    st.markdown(f'<div class="stock-low">📦 STOCK: {quantity} ⚠ LOW STOCK</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="stock-good">📦 STOCK: {quantity}</div>', unsafe_allow_html=True)

                st.write(f"💰 **PRICE:** ${price:,.2f}")
                if notes: st.write(f"📝 **NOTES:** {notes}")
                if link: st.link_button("🌐 PRODUCT LINK", link)

            with action_col:
                st.write("**STOCK**")
                minus, plus = st.columns(2)

                if minus.button("−1", key=f"minus_{key_id}", use_container_width=True):
                    if quantity > 0:
                        conn = db()
                        conn.execute("UPDATE keys_inventory SET quantity=quantity-1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (key_id,))
                        conn.commit()
                        conn.execute("""
                            INSERT INTO inventory_logs (user_email, action, key_id, quantity_change, new_quantity, details)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (st.session_state.user_email, "STOCK OUT", key_id, -1, quantity - 1, f"Removed 1 from {key_name}"))
                        conn.commit()
                        conn.close()
                        st.rerun()

                if plus.button("+1", key=f"plus_{key_id}", use_container_width=True):
                    conn = db()
                    conn.execute("UPDATE keys_inventory SET quantity=quantity+1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (key_id,))
                    conn.commit()
                    conn.execute("""
                        INSERT INTO inventory_logs (user_email, action, key_id, quantity_change, new_quantity, details)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (st.session_state.user_email, "STOCK IN", key_id, 1, quantity + 1, f"Added 1 to {key_name}"))
                    conn.commit()
                    conn.close()
                    st.rerun()

                st.divider()

                if st.button("✏ EDIT", key=f"edit_{key_id}", use_container_width=True):
                    st.session_state["edit_key_id"] = key_id
                    st.rerun()

                if st.button("🗑 DELETE", key=f"delete_{key_id}", use_container_width=True):
                    st.session_state["delete_key_id"] = key_id
                    st.rerun()

    # ---- Edit form ----
    if "edit_key_id" in st.session_state:
        edit_id = st.session_state.edit_key_id
        conn = db()
        cur = conn.cursor()
        cur.execute("""
            SELECT key_name, part_number, brand, car_model, year, key_type, key_color, quantity, price, low_stock_limit, image, notes, link
            FROM keys_inventory WHERE id=?
        """, (edit_id,))
        old = cur.fetchone()
        conn.close()

        if old:
            st.divider()
            st.header("✏ EDIT CAR KEY")
            (
                old_name, old_part, old_brand, old_model, old_year,
                old_type, old_color, old_quantity, old_price, old_low,
                old_image, old_notes, old_link
            ) = old

            with st.form("edit_key_form"):
                key_name_e = st.text_input("KEY NAME", value=old_name or "")
                part_number_e = st.text_input("PART NUMBER", value=old_part or "")
                brand_e = st.text_input("BRAND", value=old_brand or "")
                car_model_e = st.text_input("CAR MODEL", value=old_model or "")
                year_e = st.text_input("YEAR", value=old_year or "")
                key_type_e = st.text_input("KEY TYPE", value=old_type or "")
                key_color_e = st.text_input("COLOR", value=old_color or "")
                quantity_e = st.number_input("QUANTITY", min_value=0, value=int(old_quantity))
                price_e = st.number_input("PRICE", min_value=0.0, value=float(old_price), step=0.5)
                low_limit_e = st.number_input("LOW STOCK ALERT", min_value=0, value=int(old_low or 5))
                notes_e = st.text_area("NOTES", value=old_notes or "")
                link_e = st.text_input("PRODUCT LINK", value=old_link or "")
                new_image = st.file_uploader("REPLACE IMAGE", type=["jpg", "jpeg", "png", "webp"])

                save = st.form_submit_button("💾 SAVE CHANGES", use_container_width=True)
                cancel = st.form_submit_button("CANCEL", use_container_width=True)

                if cancel:
                    del st.session_state["edit_key_id"]
                    st.rerun()

                if save:
                    image_data = new_image.read() if new_image else old_image
                    conn = db()
                    conn.execute("""
                        UPDATE keys_inventory
                        SET key_name=?, part_number=?, brand=?, car_model=?, year=?, key_type=?, key_color=?, quantity=?, price=?, low_stock_limit=?, image=?, notes=?, link=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (key_name_e, part_number_e, brand_e, car_model_e, year_e, key_type_e, key_color_e, quantity_e, price_e, low_limit_e, image_data, notes_e, link_e, edit_id))
                    conn.commit()
                    conn.execute("""
                        INSERT INTO inventory_logs (user_email, action, key_id, quantity_change, new_quantity, details)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (st.session_state.user_email, "EDIT KEY", edit_id, 0, quantity_e, f"Updated {key_name_e}"))
                    conn.commit()
                    conn.close()

                    del st.session_state["edit_key_id"]
                    st.success("Car key updated successfully.")
                    st.rerun()

    # ---- Delete confirmation ----
    if "delete_key_id" in st.session_state:
        delete_id = st.session_state.delete_key_id
        st.warning("⚠ DELETE THIS CAR KEY PERMANENTLY?")
        yes, no = st.columns(2)

        if yes.button("🗑 YES, DELETE", use_container_width=True):
            conn = db()
            cur = conn.cursor()
            cur.execute("SELECT key_name FROM keys_inventory WHERE id=?", (delete_id,))
            row = cur.fetchone()
            key_name_d = row[0] if row else "Unknown"

            cur.execute("DELETE FROM keys_inventory WHERE id=?", (delete_id,))
            conn.commit()
            conn.execute("""
                INSERT INTO inventory_logs (user_email, action, key_id, quantity_change, new_quantity, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (st.session_state.user_email, "DELETE KEY", delete_id, 0, 0, f"Deleted {key_name_d}"))
            conn.commit()
            conn.close()

            del st.session_state["delete_key_id"]
            st.rerun()

        if no.button("CANCEL", use_container_width=True):
            del st.session_state["delete_key_id"]
            st.rerun()

# ============================================================
# ADD KEY
# ============================================================

elif page == "➕ ADD KEY":
    st.markdown(
        """
        <div class="main-title">
            ➕ ADD NEW CAR KEY
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("add_key_form", clear_on_submit=True):
        st.subheader("Basic Information")
        key_name = st.text_input("KEY NAME *", placeholder="Example: Mercedes Smart Key")
        part_number = st.text_input("PART NUMBER", placeholder="Example: A000905...")
        brand = st.text_input("BRAND", placeholder="Example: Mercedes")
        car_model = st.text_input("CAR MODEL", placeholder="Example: W211")
        year = st.text_input("YEAR", placeholder="Example: 2003-2009")
        key_type = st.text_input("KEY TYPE", placeholder="Example: Smart Key / Remote / Blade")
        key_color = st.text_input("COLOR", placeholder="Example: Black")

        st.subheader("Stock & Price")
        quantity = st.number_input("QUANTITY", min_value=0, value=0, step=1)
        price = st.number_input("PRICE", min_value=0.0, value=0.0, step=0.5)
        low_limit = st.number_input("LOW STOCK ALERT", min_value=0, value=LOW_STOCK_DEFAULT, step=1)

        st.subheader("Image & Notes")
        image_file = st.file_uploader("PRODUCT IMAGE", type=["jpg", "jpeg", "png", "webp"])
        if image_file:
            st.image(image_file, caption="IMAGE PREVIEW", width=250)

        notes = st.text_area("NOTES", placeholder="Additional information...")
        link = st.text_input("PRODUCT LINK", placeholder="https://...")

        save = st.form_submit_button("💾 SAVE CAR KEY", type="primary", use_container_width=True)

        if save:
            if not key_name.strip():
                st.error("KEY NAME is required.")
            else:
                image_data = image_file.read() if image_file else None
                conn = db()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO keys_inventory (key_name, part_number, brand, car_model, year, key_type, key_color, quantity, price, low_stock_limit, image, notes, link)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key_name.strip(), part_number.strip(), brand.strip(),
                    car_model.strip(), year.strip(), key_type.strip(),
                    key_color.strip(), quantity, price, low_limit,
                    image_data, notes.strip(), link.strip()
                ))
                key_id = cur.lastrowid
                conn.commit()
                conn.execute("""
                    INSERT INTO inventory_logs (user_email, action, key_id, quantity_change, new_quantity, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (st.session_state.user_email, "ADD KEY", key_id, quantity, quantity, f"Added {key_name}"))
                conn.commit()
                conn.close()

                st.success(f"'{key_name}' added successfully.")

# ============================================================
# HISTORY
# ============================================================

elif page == "📋 HISTORY":
    st.markdown(
        """
        <div class="main-title">
            📋 INVENTORY HISTORY
        </div>
        """,
        unsafe_allow_html=True
    )

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_email, action, details, quantity_change, new_quantity, created_at
        FROM inventory_logs
        ORDER BY id DESC
        LIMIT 300
    """)
    logs = cur.fetchall()
    conn.close()

    if not logs:
        st.info("No inventory history yet.")
    else:
        for email, action, details, change, new_qty, created in logs:
            with st.container(border=True):
                if change > 0:
                    icon = "🟧"
                elif change < 0:
                    icon = "🟥"
                else:
                    icon = "⬛"

                st.write(f"{icon} **{action}**")
                st.caption(f"{email} • {created}")
                st.write(details)
                if change != 0:
                    st.write(f"Quantity Change: **{change:+}** | New Stock: **{new_qty}**")

# ============================================================
# ACCOUNT
# ============================================================

elif page == "⚙ ACCOUNT":
    st.markdown(
        """
        <div class="main-title">
            ⚙ ACCOUNT SETTINGS
        </div>
        """,
        unsafe_allow_html=True
    )

    admin_email, _ = get_admin()
    st.write(f"Current login email: **{admin_email}**")

    with st.form("change_credentials_form"):
        st.subheader("Change Email / Password")
        current_password = st.text_input("CURRENT PASSWORD", type="password")
        new_email = st.text_input("NEW EMAIL", value=admin_email)
        new_password = st.text_input("NEW PASSWORD (leave blank to keep current)", type="password")
        confirm_password = st.text_input("CONFIRM NEW PASSWORD", type="password")

        update = st.form_submit_button("💾 SAVE", type="primary", use_container_width=True)

        if update:
            if not check_password(current_password, get_admin()[1]):
                st.error("Current password is incorrect.")
            elif not new_email.strip():
                st.error("Email cannot be empty.")
            elif new_password and new_password != confirm_password:
                st.error("New passwords do not match.")
            elif new_password and len(new_password) < 6:
                st.error("New password must be at least 6 characters.")
            else:
                final_password = new_password if new_password else current_password
                update_admin_credentials(new_email, final_password)
                st.session_state.user_email = new_email.strip().lower()
                try:
                    cookie_controller.set(
                        COOKIE_NAME,
                        make_token(st.session_state.user_email),
                        max_age=LOGIN_DAYS * 24 * 60 * 60
                    )
                    time.sleep(0.2)
                except Exception:
                    pass
                st.success("Account updated successfully.")
                st.rerun()

# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <hr>
    <div style="text-align:center;color:#777;font-size:13px;padding:10px;">
        🔑 Engineer Ahmad • Car Key Inventory
    </div>
    """,
    unsafe_allow_html=True
)
