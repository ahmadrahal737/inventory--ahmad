import streamlit as st
import sqlite3
from PIL import Image
import io
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta

try:
    from streamlit_cookies_controller import CookieController
except ImportError:
    st.error("Please install: pip install streamlit-cookies-controller")
    st.stop()


# ============================================================
# ENGINEER AHMAD - CAR KEY INVENTORY
# ============================================================

DB_NAME = "car_keys.db"
LOGIN_DAYS = 30
LOW_STOCK_DEFAULT = 5


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Engineer Ahmad | Car Key Inventory",
    page_icon="🔑",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# COLORS / UI
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
    --gray: #666666;
}

.stApp {
    background: #F4F4F4;
}

.block-container {
    max-width: 1250px;
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}

/* Main title */

.main-title {
    background: #111111;
    color: #FF9800;
    padding: 18px;
    border-radius: 15px;
    text-align: center;
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 20px;
}

/* Product card */

.key-card {
    background: #FFFFFF;
    border: 2px solid #EEEEEE;
    border-left: 7px solid #F57C00;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 15px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
}

/* Product name */

.key-name {
    color: #111111;
    font-size: 24px;
    font-weight: 800;
    margin-bottom: 8px;
}

/* Labels */

.field-label {
    color: #F57C00;
    font-weight: 800;
    font-size: 14px;
}

.field-value {
    color: #222222;
    font-size: 16px;
}

/* Stock */

.stock-good {
    color: #111111;
    font-size: 20px;
    font-weight: 800;
}

.stock-low {
    color: #D32F2F;
    font-size: 20px;
    font-weight: 800;
}

/* Login */

.login-box {
    background: white;
    border-top: 8px solid #F57C00;
    border-radius: 18px;
    padding: 25px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.10);
}

/* Buttons */

div.stButton > button,
div.stFormSubmitButton > button {
    min-height: 48px;
    border-radius: 11px;
    font-weight: 700;
    font-size: 16px;
}

/* Inputs */

input, textarea {
    border-radius: 10px !important;
}

/* Mobile */

@media (max-width: 768px) {

    .block-container {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }

    .main-title {
        font-size: 23px;
        padding: 14px;
    }

    .key-name {
        font-size: 21px;
    }

    div.stButton > button {
        min-height: 52px;
    }
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE
# ============================================================

def db():
    return sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )


def init_database():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            session_token TEXT,
            token_expiry TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    conn.close()


init_database()


# ============================================================
# PASSWORD SECURITY
# ============================================================

def hash_password(password):

    salt = secrets.token_bytes(16)

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        150000
    )

    return (
        salt.hex()
        + ":"
        + key.hex()
    )


def check_password(password, stored):

    try:

        salt_hex, key_hex = stored.split(":")

        salt = bytes.fromhex(
            salt_hex
        )

        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            150000
        )

        return hmac.compare_digest(
            key.hex(),
            key_hex
        )

    except Exception:

        return False


# ============================================================
# USERS
# ============================================================

def number_of_users():

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM users"
    )

    result = cur.fetchone()[0]

    conn.close()

    return result


def register_user(email, password):

    email = email.strip().lower()

    first_user = number_of_users() == 0

    conn = db()

    conn.execute("""
        INSERT INTO users
        (
            email,
            password_hash,
            is_admin,
            is_approved,
            is_active
        )
        VALUES (?, ?, ?, ?, 1)
    """, (
        email,
        hash_password(password),
        1 if first_user else 0,
        1 if first_user else 0
    ))

    conn.commit()
    conn.close()

    return first_user


def login_user(email, password):

    email = email.strip().lower()

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            email,
            password_hash,
            is_admin,
            is_approved,
            is_active
        FROM users
        WHERE email=?
    """, (email,))

    row = cur.fetchone()

    conn.close()

    if not row:
        return None

    email, password_hash, admin, approved, active = row

    if not active:
        return "disabled"

    if not check_password(
        password,
        password_hash
    ):
        return None

    if not approved:
        return "pending"

    return {
        "email": email,
        "admin": bool(admin)
    }


# ============================================================
# PERMANENT LOGIN COOKIE
# ============================================================

cookies = CookieController()


def create_login_session(email):

    token = secrets.token_urlsafe(64)

    expiry = datetime.now() + timedelta(
        days=LOGIN_DAYS
    )

    conn = db()

    conn.execute("""
        UPDATE users

        SET
            session_token=?,
            token_expiry=?

        WHERE email=?
    """, (
        token,
        expiry.isoformat(),
        email
    ))

    conn.commit()
    conn.close()

    cookies.set(
        "engineer_ahmad_login",
        token,
        max_age=LOGIN_DAYS * 24 * 60 * 60
    )


def validate_login_cookie():

    token = cookies.get(
        "engineer_ahmad_login"
    )

    if not token:
        return None

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            email,
            is_admin,
            token_expiry

        FROM users

        WHERE session_token=?
        AND is_approved=1
        AND is_active=1
    """, (token,))

    row = cur.fetchone()

    conn.close()

    if not row:
        return None

    email, admin, expiry = row

    try:

        if datetime.fromisoformat(
            expiry
        ) > datetime.now():

            return {
                "email": email,
                "admin": bool(admin)
            }

    except Exception:
        pass

    return None


def logout_user():

    email = st.session_state.get(
        "user_email"
    )

    if email:

        conn = db()

        conn.execute("""
            UPDATE users

            SET
                session_token=NULL,
                token_expiry=NULL

            WHERE email=?
        """, (email,))

        conn.commit()
        conn.close()

    try:
        cookies.remove(
            "engineer_ahmad_login"
        )
    except Exception:
        pass

    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.is_admin = False

    st.rerun()


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


# ============================================================
# AUTOMATIC LOGIN
# ============================================================

if not st.session_state.logged_in:

    saved_session = validate_login_cookie()

    if saved_session:

        st.session_state.logged_in = True

        st.session_state.user_email = \
            saved_session["email"]

        st.session_state.is_admin = \
            saved_session["admin"]


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

    login_tab, register_tab = st.tabs([
        "🔐 LOGIN",
        "➕ CREATE ACCOUNT"
    ])

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    with login_tab:

        st.subheader(
            "Login to your account"
        )

        email = st.text_input(
            "EMAIL",
            placeholder="Enter your email",
            key="login_email"
        )

        password = st.text_input(
            "PASSWORD",
            type="password",
            placeholder="Enter your password",
            key="login_password"
        )

        remember = st.checkbox(
            "KEEP ME SIGNED IN",
            value=True
        )

        if st.button(
            "🔐 LOGIN",
            type="primary",
            use_container_width=True
        ):

            if not email or not password:

                st.warning(
                    "Please enter your email and password."
                )

            else:

                result = login_user(
                    email,
                    password
                )

                if result == "pending":

                    st.warning(
                        "Your account is waiting for administrator approval."
                    )

                elif result == "disabled":

                    st.error(
                        "Your account is disabled."
                    )

                elif result:

                    st.session_state.logged_in = True

                    st.session_state.user_email = \
                        result["email"]

                    st.session_state.is_admin = \
                        result["admin"]

                    if remember:

                        create_login_session(
                            result["email"]
                        )

                    st.rerun()

                else:

                    st.error(
                        "Invalid email or password."
                    )

    # --------------------------------------------------------
    # REGISTER
    # --------------------------------------------------------

    with register_tab:

        st.subheader(
            "Create New Account"
        )

        if number_of_users() == 0:

            st.info(
                "This will be the first account and will automatically become the Super Admin."
            )

        else:

            st.info(
                "New accounts must be approved by the Super Admin."
            )

        new_email = st.text_input(
            "EMAIL",
            key="new_email"
        )

        new_password = st.text_input(
            "PASSWORD",
            type="password",
            key="new_password"
        )

        confirm_password = st.text_input(
            "CONFIRM PASSWORD",
            type="password"
        )

        if st.button(
            "➕ CREATE ACCOUNT",
            type="primary",
            use_container_width=True
        ):

            if not new_email or not new_password:

                st.warning(
                    "Please complete all fields."
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

                    first = register_user(
                        new_email,
                        new_password
                    )

                    if first:

                        st.success(
                            "Account created. You are the Super Admin."
                        )

                    else:

                        st.success(
                            "Account created. Please wait for Admin approval."
                        )

                except sqlite3.IntegrityError:

                    st.error(
                        "This email is already registered."
                    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    """
    <h2 style="color:#F57C00;">
    🔑 Engineer Ahmad
    </h2>
    """,
    unsafe_allow_html=True
)

st.sidebar.caption(
    "Car Key Inventory"
)

st.sidebar.write(
    f"👤 {st.session_state.user_email}"
)

if st.session_state.is_admin:

    st.sidebar.success(
        "👑 SUPER ADMIN"
    )

else:

    st.sidebar.info(
        "USER"
    )


# ============================================================
# SIDEBAR MENU
# ============================================================

menu_items = [
    "🏠 DASHBOARD",
    "🔑 CAR KEYS",
    "➕ ADD KEY",
    "📋 HISTORY"
]

if st.session_state.is_admin:

    menu_items.append(
        "👑 ADMIN PANEL"
    )

page = st.sidebar.radio(
    "MENU",
    menu_items
)

if st.sidebar.button(
    "🚪 LOGOUT",
    use_container_width=True
):

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

    total_keys, total_quantity, total_value = \
        cur.fetchone()

    cur.execute("""
        SELECT COUNT(*)
        FROM keys_inventory
        WHERE quantity <= low_stock_limit
    """)

    low_stock = cur.fetchone()[0]

    conn.close()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🔑 KEY TYPES",
        total_keys
    )

    c2.metric(
        "📦 TOTAL STOCK",
        total_quantity
    )

    c3.metric(
        "⚠️ LOW STOCK",
        low_stock
    )

    c4.metric(
        "💰 STOCK VALUE",
        f"${total_value:,.2f}"
    )

    st.divider()

    st.subheader(
        "Quick Search"
    )

    quick_search = st.text_input(
        "SEARCH CAR KEY",
        placeholder="Search by key name, part number, brand or model..."
    )

    if quick_search:

        conn = db()
        cur = conn.cursor()

        pattern = f"%{quick_search}%"

        cur.execute("""
            SELECT
                id,
                key_name,
                part_number,
                brand,
                car_model,
                quantity,
                price
            FROM keys_inventory

            WHERE key_name LIKE ?
               OR part_number LIKE ?
               OR brand LIKE ?
               OR car_model LIKE ?

            ORDER BY key_name COLLATE NOCASE ASC
        """, (
            pattern,
            pattern,
            pattern,
            pattern
        ))

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

    search = st.text_input(
        "🔍 SEARCH",
        placeholder="Key name / Part Number / Brand / Model / Year / Type..."
    )

    conn = db()
    cur = conn.cursor()

    if search:

        pattern = f"%{search}%"

        cur.execute("""
            SELECT
                id,
                key_name,
                part_number,
                brand,
                car_model,
                year,
                key_type,
                key_color,
                quantity,
                price,
                low_stock_limit,
                image,
                notes,
                link
            FROM keys_inventory

            WHERE key_name LIKE ?
               OR part_number LIKE ?
               OR brand LIKE ?
               OR car_model LIKE ?
               OR year LIKE ?
               OR key_type LIKE ?
               OR key_color LIKE ?

            ORDER BY key_name COLLATE NOCASE ASC
        """, (
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern
        ))

    else:

        cur.execute("""
            SELECT
                id,
                key_name,
                part_number,
                brand,
                car_model,
                year,
                key_type,
                key_color,
                quantity,
                price,
                low_stock_limit,
                image,
                notes,
                link
            FROM keys_inventory

            ORDER BY key_name COLLATE NOCASE ASC
        """)

    keys = cur.fetchall()

    conn.close()

    st.caption(
        f"{len(keys)} key(s) found"
    )

    # --------------------------------------------------------
    # VERTICAL PRODUCT LIST
    # --------------------------------------------------------

    for item in keys:

        (
            key_id,
            key_name,
            part_number,
            brand,
            car_model,
            year,
            key_type,
            key_color,
            quantity,
            price,
            low_limit,
            image_data,
            notes,
            link
        ) = item

        with st.container(border=True):

            image_col, info_col, action_col = st.columns(
                [1.2, 3, 1.4]
            )

            # IMAGE
            with image_col:

                if image_data:

                    try:

                        image = Image.open(
                            io.BytesIO(image_data)
                        )

                        st.image(
                            image,
                            use_container_width=True
                        )

                    except:

                        st.write(
                            "🖼️ Image unavailable"
                        )

                else:

                    st.markdown(
                        """
                        <div style="
                        height:130px;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        background:#EEEEEE;
                        border-radius:12px;
                        font-size:45px;">
                        🔑
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            # INFORMATION
            with info_col:

                st.markdown(
                    f"""
                    <div class="key-name">
                    {key_name}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if part_number:

                    st.write(
                        f"🔢 **PART NUMBER:** {part_number}"
                    )

                if brand:

                    st.write(
                        f"🚗 **BRAND:** {brand}"
                    )

                if car_model:

                    st.write(
                        f"🚘 **MODEL:** {car_model}"
                    )

                if year:

                    st.write(
                        f"📅 **YEAR:** {year}"
                    )

                if key_type:

                    st.write(
                        f"🔐 **KEY TYPE:** {key_type}"
                    )

                if key_color:

                    st.write(
                        f"🎨 **COLOR:** {key_color}"
                    )

                if quantity <= low_limit:

                    st.markdown(
                        f"""
                        <div class="stock-low">
                        📦 STOCK: {quantity} ⚠️ LOW STOCK
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                else:

                    st.markdown(
                        f"""
                        <div class="stock-good">
                        📦 STOCK: {quantity}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                st.write(
                    f"💰 **PRICE:** ${price:,.2f}"
                )

                if notes:

                    st.write(
                        f"📝 **NOTES:** {notes}"
                    )

                if link:

                    st.link_button(
                        "🌐 PRODUCT LINK",
                        link
                    )

            # ACTIONS
            with action_col:

                st.write(
                    "**STOCK**"
                )

                minus, plus = st.columns(2)

                if minus.button(
                    "−1",
                    key=f"minus_{key_id}",
                    use_container_width=True
                ):

                    if quantity > 0:

                        conn = db()

                        conn.execute("""
                            UPDATE keys_inventory

                            SET
                                quantity=quantity-1,
                                updated_at=CURRENT_TIMESTAMP

                            WHERE id=?
                        """, (key_id,))

                        conn.commit()
                        conn.close()

                        conn = db()

                        conn.execute("""
                            INSERT INTO inventory_logs
                            (
                                user_email,
                                action,
                                key_id,
                                quantity_change,
                                new_quantity,
                                details
                            )

                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            st.session_state.user_email,
                            "STOCK OUT",
                            key_id,
                            -1,
                            quantity - 1,
                            f"Removed 1 from {key_name}"
                        ))

                        conn.commit()
                        conn.close()

                        st.rerun()

                if plus.button(
                    "+1",
                    key=f"plus_{key_id}",
                    use_container_width=True
                ):

                    conn = db()

                    conn.execute("""
                        UPDATE keys_inventory

                        SET
                            quantity=quantity+1,
                            updated_at=CURRENT_TIMESTAMP

                        WHERE id=?
                    """, (key_id,))

                    conn.commit()
                    conn.close()

                    conn = db()

                    conn.execute("""
                        INSERT INTO inventory_logs
                        (
                            user_email,
                            action,
                            key_id,
                            quantity_change,
                            new_quantity,
                            details
                        )

                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        st.session_state.user_email,
                        "STOCK IN",
                        key_id,
                        1,
                        quantity + 1,
                        f"Added 1 to {key_name}"
                    ))

                    conn.commit()
                    conn.close()

                    st.rerun()

                st.divider()

                if st.button(
                    "✏️ EDIT",
                    key=f"edit_{key_id}",
                    use_container_width=True
                ):

                    st.session_state[
                        "edit_key_id"
                    ] = key_id

                    st.rerun()

                if st.button(
                    "🗑️ DELETE",
                    key=f"delete_{key_id}",
                    use_container_width=True
                ):

                    st.session_state[
                        "delete_key_id"
                    ] = key_id

                    st.rerun()


# ============================================================
# EDIT KEY
# ============================================================

if "edit_key_id" in st.session_state:

    edit_id = st.session_state.edit_key_id

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            key_name,
            part_number,
            brand,
            car_model,
            year,
            key_type,
            key_color,
            quantity,
            price,
            low_stock_limit,
            image,
            notes,
            link

        FROM keys_inventory

        WHERE id=?
    """, (edit_id,))

    old = cur.fetchone()

    conn.close()

    if old:

        st.divider()

        st.header(
            "✏️ EDIT CAR KEY"
        )

        (
            old_name,
            old_part,
            old_brand,
            old_model,
            old_year,
            old_type,
            old_color,
            old_quantity,
            old_price,
            old_low,
            old_image,
            old_notes,
            old_link
        ) = old

        with st.form(
            "edit_key_form"
        ):

            key_name = st.text_input(
                "KEY NAME",
                value=old_name or ""
            )

            part_number = st.text_input(
                "PART NUMBER",
                value=old_part or ""
            )

            brand = st.text_input(
                "BRAND",
                value=old_brand or ""
            )

            car_model = st.text_input(
                "CAR MODEL",
                value=old_model or ""
            )

            year = st.text_input(
                "YEAR",
                value=old_year or ""
            )

            key_type = st.text_input(
                "KEY TYPE",
                value=old_type or ""
            )

            key_color = st.text_input(
                "COLOR",
                value=old_color or ""
            )

            quantity = st.number_input(
                "QUANTITY",
                min_value=0,
                value=int(old_quantity)
            )

            price = st.number_input(
                "PRICE",
                min_value=0.0,
                value=float(old_price),
                step=0.5
            )

            low_limit = st.number_input(
                "LOW STOCK ALERT",
                min_value=0,
                value=int(old_low or 5)
            )

            notes = st.text_area(
                "NOTES",
                value=old_notes or ""
            )

            link = st.text_input(
                "PRODUCT LINK",
                value=old_link or ""
            )

            new_image = st.file_uploader(
                "REPLACE IMAGE",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp"
                ]
            )

            save = st.form_submit_button(
                "💾 SAVE CHANGES",
                use_container_width=True
            )

            cancel = st.form_submit_button(
                "CANCEL",
                use_container_width=True
            )

            if cancel:

                del st.session_state[
                    "edit_key_id"
                ]

                st.rerun()

            if save:

                image_data = (
                    new_image.read()
                    if new_image
                    else old_image
                )

                conn = db()

                conn.execute("""
                    UPDATE keys_inventory

                    SET
                        key_name=?,
                        part_number=?,
                        brand=?,
                        car_model=?,
                        year=?,
                        key_type=?,
                        key_color=?,
                        quantity=?,
                        price=?,
                        low_stock_limit=?,
                        image=?,
                        notes=?,
                        link=?,
                        updated_at=CURRENT_TIMESTAMP

                    WHERE id=?
                """, (
                    key_name,
                    part_number,
                    brand,
                    car_model,
                    year,
                    key_type,
                    key_color,
                    quantity,
                    price,
                    low_limit,
                    image_data,
                    notes,
                    link,
                    edit_id
                ))

                conn.commit()
                conn.close()

                conn = db()

                conn.execute("""
                    INSERT INTO inventory_logs
                    (
                        user_email,
                        action,
                        key_id,
                        quantity_change,
                        new_quantity,
                        details
                    )

                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state.user_email,
                    "EDIT KEY",
                    edit_id,
                    0,
                    quantity,
                    f"Updated {key_name}"
                ))

                conn.commit()
                conn.close()

                del st.session_state[
                    "edit_key_id"
                ]

                st.success(
                    "Car key updated successfully."
                )

                st.rerun()


# ============================================================
# DELETE
# ============================================================

if "delete_key_id" in st.session_state:

    delete_id = st.session_state.delete_key_id

    st.warning(
        "⚠️ DELETE THIS CAR KEY PERMANENTLY?"
    )

    yes, no = st.columns(2)

    if yes.button(
        "🗑️ YES, DELETE",
        use_container_width=True
    ):

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT key_name
            FROM keys_inventory
            WHERE id=?
        """, (delete_id,))

        row = cur.fetchone()

        key_name = row[0] if row else "Unknown"

        cur.execute("""
            DELETE FROM keys_inventory
            WHERE id=?
        """, (delete_id,))

        conn.commit()
        conn.close()

        conn = db()

        conn.execute("""
            INSERT INTO inventory_logs
            (
                user_email,
                action,
                key_id,
                quantity_change,
                new_quantity,
                details
            )

            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            st.session_state.user_email,
            "DELETE KEY",
            delete_id,
            0,
            0,
            f"Deleted {key_name}"
        ))

        conn.commit()
        conn.close()

        del st.session_state[
            "delete_key_id"
        ]

        st.rerun()

    if no.button(
        "CANCEL",
        use_container_width=True
    ):

        del st.session_state[
            "delete_key_id"
        ]

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

    with st.form(
        "add_key_form",
        clear_on_submit=True
    ):

        st.subheader(
            "Basic Information"
        )

        key_name = st.text_input(
            "KEY NAME *",
            placeholder="Example: Mercedes Smart Key"
        )

        part_number = st.text_input(
            "PART NUMBER",
            placeholder="Example: A000905..."
        )

        brand = st.text_input(
            "BRAND",
            placeholder="Example: Mercedes"
        )

        car_model = st.text_input(
            "CAR MODEL",
            placeholder="Example: W211"
        )

        year = st.text_input(
            "YEAR",
            placeholder="Example: 2003-2009"
        )

        key_type = st.text_input(
            "KEY TYPE",
            placeholder="Example: Smart Key / Remote / Blade"
        )

        key_color = st.text_input(
            "COLOR",
            placeholder="Example: Black"
        )

        st.subheader(
            "Stock & Price"
        )

        quantity = st.number_input(
            "QUANTITY",
            min_value=0,
            value=0,
            step=1
        )

        price = st.number_input(
            "PRICE",
            min_value=0.0,
            value=0.0,
            step=0.5
        )

        low_limit = st.number_input(
            "LOW STOCK ALERT",
            min_value=0,
            value=LOW_STOCK_DEFAULT,
            step=1
        )

        st.subheader(
            "Image & Notes"
        )

        image_file = st.file_uploader(
            "PRODUCT IMAGE",
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
                caption="IMAGE PREVIEW",
                width=250
            )

        notes = st.text_area(
            "NOTES",
            placeholder="Additional information..."
        )

        link = st.text_input(
            "PRODUCT LINK",
            placeholder="https://..."
        )

        save = st.form_submit_button(
            "💾 SAVE CAR KEY",
            type="primary",
            use_container_width=True
        )

        if save:

            if not key_name.strip():

                st.error(
                    "KEY NAME is required."
                )

            else:

                image_data = (
                    image_file.read()
                    if image_file
                    else None
                )

                conn = db()
                cur = conn.cursor()

                cur.execute("""
                    INSERT INTO keys_inventory
                    (
                        key_name,
                        part_number,
                        brand,
                        car_model,
                        year,
                        key_type,
                        key_color,
                        quantity,
                        price,
                        low_stock_limit,
                        image,
                        notes,
                        link
                    )

                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key_name.strip(),
                    part_number.strip(),
                    brand.strip(),
                    car_model.strip(),
                    year.strip(),
                    key_type.strip(),
                    key_color.strip(),
                    quantity,
                    price,
                    low_limit,
                    image_data,
                    notes.strip(),
                    link.strip()
                ))

                key_id = cur.lastrowid

                conn.commit()
                conn.close()

                conn = db()

                conn.execute("""
                    INSERT INTO inventory_logs
                    (
                        user_email,
                        action,
                        key_id,
                        quantity_change,
                        new_quantity,
                        details
                    )

                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state.user_email,
                    "ADD KEY",
                    key_id,
                    quantity,
                    quantity,
                    f"Added {key_name}"
                ))

                conn.commit()
                conn.close()

                st.success(
                    f"'{key_name}' added successfully."
                )


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
        SELECT
            user_email,
            action,
            details,
            quantity_change,
            new_quantity,
            created_at

        FROM inventory_logs

        ORDER BY id DESC

        LIMIT 300
    """)

    logs = cur.fetchall()

    conn.close()

    if not logs:

        st.info(
            "No inventory history yet."
        )

    else:

        for (
            email,
            action,
            details,
            change,
            new_qty,
            created
        ) in logs:

            with st.container(border=True):

                if change > 0:

                    icon = "🟧"

                elif change < 0:

                    icon = "🟥"

                else:

                    icon = "⬛"

                st.write(
                    f"{icon} **{action}**"
                )

                st.caption(
                    f"{email} • {created}"
                )

                st.write(details)

                if change != 0:

                    st.write(
                        f"Quantity Change: **{change:+}** "
                        f"| New Stock: **{new_qty}**"
                    )


# ============================================================
# ADMIN PANEL
# ============================================================

elif page == "👑 ADMIN PANEL":

    if not st.session_state.is_admin:

        st.error(
            "Access denied."
        )

        st.stop()

    st.markdown(
        """
        <div class="main-title">
            👑 SUPER ADMIN PANEL
        </div>
        """,
        unsafe_allow_html=True
    )

    st.info(
        "Only the first account (Super Admin) can access this page."
    )

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            email,
            is_admin,
            is_approved,
            is_active,
            created_at

        FROM users

        ORDER BY created_at ASC
    """)

    users = cur.fetchall()

    conn.close()

    for (
        email,
        admin,
        approved,
        active,
        created
    ) in users:

        with st.container(border=True):

            c1, c2, c3, c4 = st.columns(
                [3, 1.2, 1.2, 1.2]
            )

            with c1:

                st.write(
                    f"**{email}**"
                )

                if admin:

                    st.caption(
                        "👑 SUPER ADMIN"
                    )

                elif not approved:

                    st.caption(
                        "⏳ WAITING FOR APPROVAL"
                    )

                elif not active:

                    st.caption(
                        "🟥 DISABLED"
                    )

                else:

                    st.caption(
                        "✅ APPROVED USER"
                    )

            with c2:

                if not approved and active:

                    if st.button(
                        "APPROVE",
                        key=f"approve_{email}",
                        use_container_width=True
                    ):

                        conn = db()

                        conn.execute("""
                            UPDATE users
                            SET is_approved=1
                            WHERE email=?
                        """, (email,))

                        conn.commit()
                        conn.close()

                        st.rerun()

            with c3:

                if not admin:

                    if active:

                        if st.button(
                            "DISABLE",
                            key=f"disable_{email}",
                            use_container_width=True
                        ):

                            conn = db()

                            conn.execute("""
                                UPDATE users
                                SET is_active=0
                                WHERE email=?
                            """, (email,))

                            conn.commit()
                            conn.close()

                            st.rerun()

                    else:

                        if st.button(
                            "ENABLE",
                            key=f"enable_{email}",
                            use_container_width=True
                        ):

                            conn = db()

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
                        "DELETE",
                        key=f"user_delete_{email}",
                        use_container_width=True
                    ):

                        conn = db()

                        conn.execute(
                            "DELETE FROM users WHERE email=?",
                            (email,)
                        )

                        conn.commit()
                        conn.close()

                        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <hr>

    <div style="
        text-align:center;
        color:#777;
        font-size:13px;
        padding:10px;">
        🔑 Engineer Ahmad • Car Key Inventory
    </div>
    """,
    unsafe_allow_html=True
)
