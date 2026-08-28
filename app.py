import streamlit as st
import sqlite3
from PIL import Image
import io
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta

# =========================================================
# ENGINEER AHMAD - INVENTORY MANAGER
# =========================================================

DB_NAME = "inventory.db"
SESSION_DAYS = 30

st.set_page_config(
    page_title="Engineer Ahmad | Inventory Manager",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# LIGHT MOBILE UI
# =========================================================

st.markdown("""
<style>

.stApp {
    background: #F5F7FA;
}

.block-container {
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 1400px;
}

h1, h2, h3 {
    color: #17324D !important;
}

div.stButton > button,
div.stFormSubmitButton > button {
    min-height: 48px;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 600;
}

div.stButton > button:hover,
div.stFormSubmitButton > button:hover {
    transform: translateY(-1px);
}

input, textarea {
    border-radius: 10px !important;
}

[data-testid="stMetric"] {
    background: white;
    border-radius: 14px;
    padding: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
}

.product-card {
    background: white;
    border-radius: 16px;
    padding: 14px;
    margin-bottom: 15px;
    box-shadow: 0 3px 14px rgba(0,0,0,0.07);
}

.product-name {
    font-size: 21px;
    font-weight: 700;
    color: #17324D;
}

.product-info {
    font-size: 15px;
    margin-top: 5px;
}

.low-stock {
    color: #C53030;
    font-weight: bold;
}

.good-stock {
    color: #2F855A;
    font-weight: bold;
}

.admin-box {
    background: white;
    padding: 18px;
    border-radius: 16px;
    box-shadow: 0 3px 14px rgba(0,0,0,0.07);
}

@media (max-width: 768px) {
    .block-container {
        padding-left: 0.6rem;
        padding-right: 0.6rem;
    }

    h1 {
        font-size: 28px !important;
    }

    h2 {
        font-size: 23px !important;
    }

    div.stButton > button {
        min-height: 52px;
    }
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def column_exists(table, column):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cur.fetchall()]
    conn.close()
    return column in columns


def add_column(table, column, definition):
    if not column_exists(table, column):
        conn = get_connection()
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )
        conn.commit()
        conn.close()


def init_db():

    conn = get_connection()
    cur = conn.cursor()

    # USERS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            is_approved INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            session_token TEXT,
            token_expiry TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # PRODUCTS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT,
            category TEXT,
            color TEXT,
            quantity INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            link TEXT,
            image BLOB,
            low_stock_limit INTEGER DEFAULT 5,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # LOGS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            action TEXT,
            product_id INTEGER,
            details TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    # Compatibility with old database
    add_column("users", "password_hash", "TEXT")
    add_column("users", "is_admin", "INTEGER DEFAULT 0")
    add_column("users", "is_active", "INTEGER DEFAULT 1")
    add_column("users", "session_token", "TEXT")
    add_column("users", "token_expiry", "TEXT")

    add_column("products", "sku", "TEXT")
    add_column("products", "category", "TEXT")
    add_column("products", "low_stock_limit", "INTEGER DEFAULT 5")
    add_column("products", "created_at", "TEXT")
    add_column("products", "updated_at", "TEXT")


init_db()


# =========================================================
# PASSWORD SECURITY
# =========================================================

def hash_password(password):
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        120000
    )

    return salt.hex() + ":" + key.hex()


def verify_password(password, stored_hash):

    try:
        salt_hex, key_hex = stored_hash.split(":")

        salt = bytes.fromhex(salt_hex)

        new_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            120000
        )

        return hmac.compare_digest(
            new_key.hex(),
            key_hex
        )

    except Exception:
        return False


# =========================================================
# USER FUNCTIONS
# =========================================================

def user_count():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")

    result = cur.fetchone()[0]

    conn.close()

    return result


def create_user(email, password):

    conn = get_connection()

    cur = conn.cursor()

    first_user = user_count() == 0

    password_hash = hash_password(password)

    cur.execute("""
        INSERT INTO users
        (email, password_hash, is_approved, is_admin, is_active)
        VALUES (?, ?, ?, ?, 1)
    """, (
        email.lower().strip(),
        password_hash,
        1 if first_user else 0,
        1 if first_user else 0
    ))

    conn.commit()
    conn.close()

    return first_user


def authenticate_user(email, password):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT email, password_hash,
               is_approved, is_admin, is_active
        FROM users
        WHERE email=?
    """, (email.lower().strip(),))

    user = cur.fetchone()

    conn.close()

    if not user:
        return None

    email, password_hash, approved, admin, active = user

    if not active:
        return "disabled"

    if not verify_password(password, password_hash):
        return None

    if not approved:
        return "pending"

    return {
        "email": email,
        "is_admin": bool(admin)
    }


# =========================================================
# SESSION TOKEN
# =========================================================

def create_session(email):

    token = secrets.token_urlsafe(48)

    expiry = datetime.now() + timedelta(days=SESSION_DAYS)

    conn = get_connection()

    conn.execute("""
        UPDATE users
        SET session_token=?, token_expiry=?
        WHERE email=?
    """, (
        token,
        expiry.isoformat(),
        email
    ))

    conn.commit()
    conn.close()

    return token


def validate_session(token):

    if not token:
        return None

    conn = get_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT email, token_expiry, is_admin
        FROM users
        WHERE session_token=?
        AND is_approved=1
        AND is_active=1
    """, (token,))

    row = cur.fetchone()

    conn.close()

    if not row:
        return None

    email, expiry, is_admin = row

    try:
        if datetime.fromisoformat(expiry) > datetime.now():
            return {
                "email": email,
                "is_admin": bool(is_admin)
            }
    except:
        pass

    return None


def logout():

    email = st.session_state.get("user_email")

    if email:

        conn = get_connection()

        conn.execute("""
            UPDATE users
            SET session_token=NULL,
                token_expiry=NULL
            WHERE email=?
        """, (email,))

        conn.commit()
        conn.close()

    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.is_admin = False

    st.query_params.clear()

    st.rerun()


# =========================================================
# LOGGING
# =========================================================

def log_action(action, product_id=None, details=""):

    email = st.session_state.get("user_email", "")

    conn = get_connection()

    conn.execute("""
        INSERT INTO logs
        (user_email, action, product_id, details)
        VALUES (?, ?, ?, ?)
    """, (
        email,
        action,
        product_id,
        details
    ))

    conn.commit()
    conn.close()


# =========================================================
# SESSION START
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


# Check saved session
saved_token = st.query_params.get("session")

if not st.session_state.logged_in and saved_token:

    session = validate_session(saved_token)

    if session:

        st.session_state.logged_in = True
        st.session_state.user_email = session["email"]
        st.session_state.is_admin = session["is_admin"]

        st.query_params.clear()

        st.rerun()


# =========================================================
# LOGIN / REGISTER
# =========================================================

if not st.session_state.logged_in:

    st.markdown(
        "<h1 style='text-align:center;'>📦 Engineer Ahmad</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center;'>Inventory Manager</p>",
        unsafe_allow_html=True
    )

    login_tab, register_tab = st.tabs([
        "🔐 Login",
        "➕ Create Account"
    ])

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    with login_tab:

        st.subheader("Welcome Back")

        email = st.text_input(
            "Email",
            placeholder="example@email.com"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        remember = st.checkbox(
            "Keep me signed in",
            value=True
        )

        if st.button(
            "🔐 Login",
            type="primary",
            use_container_width=True
        ):

            if not email or not password:

                st.warning("Please enter your email and password.")

            else:

                result = authenticate_user(
                    email,
                    password
                )

                if result == "pending":

                    st.warning(
                        "Your account is waiting for administrator approval."
                    )

                elif result == "disabled":

                    st.error(
                        "Your account has been disabled."
                    )

                elif result:

                    st.session_state.logged_in = True
                    st.session_state.user_email = result["email"]
                    st.session_state.is_admin = result["is_admin"]

                    if remember:

                        token = create_session(
                            result["email"]
                        )

                        st.query_params["session"] = token

                    st.rerun()

                else:

                    st.error(
                        "Invalid email or password."
                    )

    # -----------------------------------------------------
    # REGISTER
    # -----------------------------------------------------

    with register_tab:

        st.subheader("Create New Account")

        if user_count() == 0:

            st.info(
                "This is the first account. "
                "It will automatically become the Super Admin."
            )

        else:

            st.info(
                "New accounts require administrator approval."
            )

        new_email = st.text_input(
            "Email",
            key="register_email"
        )

        new_password = st.text_input(
            "Password",
            type="password",
            key="register_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password"
        )

        if st.button(
            "➕ Create Account",
            type="primary",
            use_container_width=True
        ):

            email_clean = new_email.lower().strip()

            if not email_clean or not new_password:

                st.warning(
                    "Please complete all required fields."
                )

            elif new_password != confirm_password:

                st.error(
                    "Passwords do not match."
                )

            elif len(new_password) < 6:

                st.error(
                    "Password must contain at least 6 characters."
                )

            else:

                try:

                    is_first = create_user(
                        email_clean,
                        new_password
                    )

                    if is_first:

                        st.success(
                            "Account created successfully. "
                            "You are the Super Admin."
                        )

                    else:

                        st.success(
                            "Account created successfully. "
                            "Please wait for administrator approval."
                        )

                except sqlite3.IntegrityError:

                    st.error(
                        "This email is already registered."
                    )

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("📦 Engineer Ahmad")

st.sidebar.caption(
    "Inventory Manager"
)

st.sidebar.write(
    f"👤 {st.session_state.user_email}"
)

if st.session_state.is_admin:

    st.sidebar.success("👑 Super Admin")

else:

    st.sidebar.info("👤 User")


# =========================================================
# DASHBOARD STATISTICS
# =========================================================

conn = get_connection()
cur = conn.cursor()

cur.execute("""
    SELECT
        COUNT(*),
        COALESCE(SUM(quantity),0),
        COALESCE(SUM(quantity * price),0)
    FROM products
""")

total_products, total_quantity, inventory_value = cur.fetchone()

cur.execute("""
    SELECT COUNT(*)
    FROM products
    WHERE quantity <= low_stock_limit
""")

low_stock = cur.fetchone()[0]

conn.close()


# =========================================================
# SIDEBAR MENU
# =========================================================

page = st.sidebar.radio(
    "Menu",
    [
        "🏠 Dashboard",
        "📦 Products",
        "➕ Add Product",
        "📋 Inventory History"
    ] + (
        ["👑 Admin Panel"]
        if st.session_state.is_admin
        else []
    )
)


if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True
):

    logout()


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    st.title("🏠 Dashboard")

    st.caption(
        "Welcome to Engineer Ahmad Inventory Manager"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "📦 Products",
        total_products
    )

    c2.metric(
        "🔢 Total Stock",
        total_quantity
    )

    c3.metric(
        "⚠️ Low Stock",
        low_stock
    )

    c4.metric(
        "💰 Inventory Value",
        f"${inventory_value:,.2f}"
    )

    st.divider()

    st.subheader("Quick Actions")

    q1, q2, q3 = st.columns(3)

    if q1.button(
        "📦 View Products",
        use_container_width=True
    ):
        st.info("Open Products from the menu.")

    if q2.button(
        "➕ Add Product",
        use_container_width=True
    ):
        st.info("Open Add Product from the menu.")

    if q3.button(
        "📋 Inventory History",
        use_container_width=True
    ):
        st.info("Open Inventory History from the menu.")


# =========================================================
# PRODUCTS
# =========================================================

elif page == "📦 Products":

    st.title("📦 Products")

    search = st.text_input(
        "🔍 Search",
        placeholder="Search by name, SKU, category or color..."
    )

    conn = get_connection()
    cur = conn.cursor()

    if search:

        pattern = f"%{search}%"

        cur.execute("""
            SELECT
                id, name, sku, category,
                color, quantity, price,
                link, image, low_stock_limit
            FROM products
            WHERE name LIKE ?
               OR sku LIKE ?
               OR category LIKE ?
               OR color LIKE ?
            ORDER BY name COLLATE NOCASE ASC
        """, (
            pattern,
            pattern,
            pattern,
            pattern
        ))

    else:

        cur.execute("""
            SELECT
                id, name, sku, category,
                color, quantity, price,
                link, image, low_stock_limit
            FROM products
            ORDER BY name COLLATE NOCASE ASC
        """)

    products = cur.fetchall()

    conn.close()

    if not products:

        st.info("No products found.")

    else:

        st.caption(
            f"{len(products)} product(s) found"
        )

        for product in products:

            (
                p_id,
                name,
                sku,
                category,
                color,
                qty,
                price,
                link,
                image_data,
                low_limit
            ) = product

            with st.container(border=True):

                col_image, col_info, col_actions = st.columns(
                    [1, 2, 1]
                )

                with col_image:

                    if image_data:

                        try:

                            img = Image.open(
                                io.BytesIO(image_data)
                            )

                            st.image(
                                img,
                                use_container_width=True
                            )

                        except:

                            st.write("🖼️ Image error")

                    else:

                        st.write("🖼️ No image")

                with col_info:

                    st.markdown(
                        f"<div class='product-name'>{name}</div>",
                        unsafe_allow_html=True
                    )

                    if sku:
                        st.write(f"SKU: {sku}")

                    if category:
                        st.write(
                            f"Category: {category}"
                        )

                    if color:
                        st.write(
                            f"Color: {color}"
                        )

                    if qty <= low_limit:

                        st.markdown(
                            f"<div class='low-stock'>"
                            f"Stock: {qty} ⚠️ LOW STOCK"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                    else:

                        st.markdown(
                            f"<div class='good-stock'>"
                            f"Stock: {qty} ✓"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                    st.write(
                        f"Price: ${price:,.2f}"
                    )

                    st.write(
                        f"Inventory Value: "
                        f"${qty * price:,.2f}"
                    )

                    if link:

                        st.link_button(
                            "🌐 Product Link",
                            link,
                            use_container_width=True
                        )

                with col_actions:

                    st.write("Stock")

                    minus, plus = st.columns(2)

                    if minus.button(
                        "−1",
                        key=f"minus_{p_id}",
                        use_container_width=True
                    ):

                        if qty > 0:

                            conn = get_connection()

                            conn.execute("""
                                UPDATE products
                                SET quantity=quantity-1,
                                    updated_at=CURRENT_TIMESTAMP
                                WHERE id=?
                            """, (p_id,))

                            conn.commit()
                            conn.close()

                            log_action(
                                "Stock Out",
                                p_id,
                                f"Removed 1 from {name}"
                            )

                            st.rerun()

                        else:

                            st.warning(
                                "Stock is already 0."
                            )

                    if plus.button(
                        "+1",
                        key=f"plus_{p_id}",
                        use_container_width=True
                    ):

                        conn = get_connection()

                        conn.execute("""
                            UPDATE products
                            SET quantity=quantity+1,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (p_id,))

                        conn.commit()
                        conn.close()

                        log_action(
                            "Stock In",
                            p_id,
                            f"Added 1 to {name}"
                        )

                        st.rerun()

                    st.divider()

                    edit_key = f"edit_{p_id}"

                    if st.button(
                        "✏️ Edit",
                        key=edit_key,
                        use_container_width=True
                    ):

                        st.session_state[
                            "editing_product"
                        ] = p_id

                        st.rerun()

                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_{p_id}",
                        use_container_width=True
                    ):

                        st.session_state[
                            "delete_product"
                        ] = p_id

                        st.rerun()


# =========================================================
# EDIT PRODUCT
# =========================================================

if "editing_product" in st.session_state:

    edit_id = st.session_state.editing_product

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name, sku, category, color,
               quantity, price, link,
               image, low_stock_limit
        FROM products
        WHERE id=?
    """, (edit_id,))

    product = cur.fetchone()

    conn.close()

    if product:

        st.divider()

        st.header("✏️ Edit Product")

        (
            old_name,
            old_sku,
            old_category,
            old_color,
            old_qty,
            old_price,
            old_link,
            old_image,
            old_limit
        ) = product

        with st.form("edit_product_form"):

            name = st.text_input(
                "Product Name",
                value=old_name
            )

            sku = st.text_input(
                "SKU",
                value=old_sku or ""
            )

            category = st.text_input(
                "Category",
                value=old_category or ""
            )

            color = st.text_input(
                "Color",
                value=old_color or ""
            )

            quantity = st.number_input(
                "Quantity",
                min_value=0,
                value=old_qty
            )

            price = st.number_input(
                "Price",
                min_value=0.0,
                value=float(old_price),
                step=0.5
            )

            low_limit = st.number_input(
                "Low Stock Alert",
                min_value=0,
                value=old_limit or 5
            )

            link = st.text_input(
                "Product Link",
                value=old_link or ""
            )

            new_image = st.file_uploader(
                "Replace Image",
                type=["jpg", "jpeg", "png"]
            )

            save = st.form_submit_button(
                "💾 Save Changes",
                use_container_width=True
            )

            cancel = st.form_submit_button(
                "Cancel",
                use_container_width=True
            )

            if cancel:

                del st.session_state[
                    "editing_product"
                ]

                st.rerun()

            if save:

                image_data = (
                    new_image.read()
                    if new_image
                    else old_image
                )

                conn = get_connection()

                conn.execute("""
                    UPDATE products
                    SET name=?,
                        sku=?,
                        category=?,
                        color=?,
                        quantity=?,
                        price=?,
                        link=?,
                        image=?,
                        low_stock_limit=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (
                    name,
                    sku,
                    category,
                    color,
                    quantity,
                    price,
                    link,
                    image_data,
                    low_limit,
                    edit_id
                ))

                conn.commit()
                conn.close()

                log_action(
                    "Edit Product",
                    edit_id,
                    f"Updated product: {name}"
                )

                del st.session_state[
                    "editing_product"
                ]

                st.success(
                    "Product updated successfully."
                )

                st.rerun()


# =========================================================
# DELETE CONFIRMATION
# =========================================================

if "delete_product" in st.session_state:

    delete_id = st.session_state.delete_product

    st.warning(
        "⚠️ Are you sure you want to permanently delete this product?"
    )

    yes, no = st.columns(2)

    if yes.button(
        "Yes, Delete",
        type="primary",
        use_container_width=True
    ):

        conn = get_connection()

        cur = conn.cursor()

        cur.execute(
            "SELECT name FROM products WHERE id=?",
            (delete_id,)
        )

        row = cur.fetchone()

        product_name = row[0] if row else "Unknown"

        cur.execute(
            "DELETE FROM products WHERE id=?",
            (delete_id,)
        )

        conn.commit()
        conn.close()

        log_action(
            "Delete Product",
            delete_id,
            f"Deleted product: {product_name}"
        )

        del st.session_state[
            "delete_product"
        ]

        st.success(
            "Product deleted successfully."
        )

        st.rerun()

    if no.button(
        "Cancel",
        use_container_width=True
    ):

        del st.session_state[
            "delete_product"
        ]

        st.rerun()


# =========================================================
# ADD PRODUCT
# =========================================================

elif page == "➕ Add Product":

    st.title("➕ Add New Product")

    with st.form(
        "add_product",
        clear_on_submit=True
    ):

        name = st.text_input(
            "Product Name *"
        )

        sku = st.text_input(
            "SKU / Product Code"
        )

        category = st.text_input(
            "Category"
        )

        color = st.text_input(
            "Color"
        )

        quantity = st.number_input(
            "Initial Quantity",
            min_value=0,
            value=0,
            step=1
        )

        price = st.number_input(
            "Price",
            min_value=0.0,
            value=0.0,
            step=0.5
        )

        low_limit = st.number_input(
            "Low Stock Alert",
            min_value=0,
            value=5,
            step=1
        )

        link = st.text_input(
            "Product Link (optional)"
        )

        image_file = st.file_uploader(
            "Product Image",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp"
            ]
        )

        if image_file:

            st.image(
                image_file,
                caption="Image Preview",
                width=220
            )

        submit = st.form_submit_button(
            "💾 Save Product",
            type="primary",
            use_container_width=True
        )

        if submit:

            if not name.strip():

                st.error(
                    "Product Name is required."
                )

            else:

                image_data = (
                    image_file.read()
                    if image_file
                    else None
                )

                conn = get_connection()

                cur = conn.cursor()

                cur.execute("""
                    INSERT INTO products
                    (
                        name,
                        sku,
                        category,
                        color,
                        quantity,
                        price,
                        link,
                        image,
                        low_stock_limit
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name.strip(),
                    sku.strip(),
                    category.strip(),
                    color.strip(),
                    quantity,
                    price,
                    link.strip(),
                    image_data,
                    low_limit
                ))

                product_id = cur.lastrowid

                conn.commit()
                conn.close()

                log_action(
                    "Add Product",
                    product_id,
                    f"Added {name}, quantity={quantity}"
                )

                st.success(
                    f"Product '{name}' added successfully."
                )


# =========================================================
# INVENTORY HISTORY
# =========================================================

elif page == "📋 Inventory History":

    st.title("📋 Inventory History")

    conn = get_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT
            user_email,
            action,
            details,
            timestamp
        FROM logs
        ORDER BY id DESC
        LIMIT 200
    """)

    logs = cur.fetchall()

    conn.close()

    if not logs:

        st.info(
            "No inventory activity yet."
        )

    else:

        for email, action, details, timestamp in logs:

            with st.container(border=True):

                st.write(
                    f"**{action}**"
                )

                st.caption(
                    f"{email} • {timestamp}"
                )

                st.write(details)


# =========================================================
# ADMIN PANEL
# =========================================================

elif page == "👑 Admin Panel":

    if not st.session_state.is_admin:

        st.error(
            "Access denied."
        )

        st.stop()

    st.title("👑 Admin Panel")

    st.info(
        "Only the Super Admin can access this panel."
    )

    conn = get_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT
            email,
            is_approved,
            is_admin,
            is_active,
            created_at
        FROM users
        ORDER BY created_at ASC
    """)

    users = cur.fetchall()

    conn.close()

    for email, approved, admin, active, created in users:

        with st.container(border=True):

            c1, c2, c3, c4 = st.columns(
                [3, 1, 1, 1]
            )

            with c1:

                st.write(
                    f"**{email}**"
                )

                if admin:

                    st.caption(
                        "👑 Super Admin"
                    )

                elif not approved:

                    st.caption(
                        "⏳ Pending Approval"
                    )

                elif not active:

                    st.caption(
                        "🚫 Disabled"
                    )

                else:

                    st.caption(
                        "✅ Approved User"
                    )

            with c2:

                if not approved and active:

                    if st.button(
                        "Approve",
                        key=f"approve_{email}",
                        use_container_width=True
                    ):

                        conn = get_connection()

                        conn.execute("""
                            UPDATE users
                            SET is_approved=1
                            WHERE email=?
                        """, (email,))

                        conn.commit()
                        conn.close()

                        st.success(
                            "User approved."
                        )

                        st.rerun()

            with c3:

                if active and not admin:

                    if st.button(
                        "Disable",
                        key=f"disable_{email}",
                        use_container_width=True
                    ):

                        conn = get_connection()

                        conn.execute("""
                            UPDATE users
                            SET is_active=0
                            WHERE email=?
                        """, (email,))

                        conn.commit()
                        conn.close()

                        st.rerun()

                elif not active and not admin:

                    if st.button(
                        "Enable",
                        key=f"enable_{email}",
                        use_container_width=True
                    ):

                        conn = get_connection()

                        conn.execute("""
                            UPDATE users
                            SET is_active=1
                            WHERE email=?
                        """, (email,))

                        conn.commit()
                        conn.close()

                        st.rerun()

            with c4:

                if not admin:

                    if st.button(
                        "Delete",
                        key=f"user_delete_{email}",
                        use_container_width=True
                    ):

                        conn = get_connection()

                        conn.execute(
                            "DELETE FROM users WHERE email=?",
                            (email,)
                        )

                        conn.commit()
                        conn.close()

                        st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <hr>
    <div style='text-align:center;color:#718096;font-size:13px;'>
        Engineer Ahmad • Inventory Manager
    </div>
    """,
    unsafe_allow_html=True
)
