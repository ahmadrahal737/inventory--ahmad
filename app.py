import streamlit as st
import sqlite3
from PIL import Image
import io
import secrets
import datetime

# ---------------------------------------------------------
# إعدادات الصفحة (تم تغيير العنوان والأيقونة)
# ---------------------------------------------------------
st.set_page_config(
    page_title="مخزن مهندس أحمد",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# CSS المخصص للهواتف والألوان
# ---------------------------------------------------------
st.markdown("""
<style>
    /* جعل الأزرار كبيرة ومناسبة للمس */
    div.stButton > button {
        font-size: 20px !important;
        padding: 10px 24px !important;
        border-radius: 12px !important;
        min-height: 50px !important;
        min-width: 50px !important;
        margin: 4px !important;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
    }
    /* ألوان خاصة لأزرار الزيادة والنقص */
    .stButton > button[kind="secondary"] {
        background-color: #38A169 !important;
        color: white !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #2F855A !important;
    }
    .stButton > button[kind="danger"] {
        background-color: #E53E3E !important;
        color: white !important;
    }
    .stButton > button[kind="danger"]:hover {
        background-color: #C53030 !important;
    }
    /* تحسين شكل البطاقات */
    .stContainer {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        padding: 16px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        margin-bottom: 16px !important;
    }
    /* تنسيق العناوين */
    h1, h2, h3 {
        color: #1A365D !important;
    }
    /* شريط البحث ثابت في الأعلى */
    .stTextInput > div > div > input {
        font-size: 18px !important;
        padding: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. إعداد قاعدة البيانات وتحديث الجداول (إضافة حقل token وسجل الحركات)
# ---------------------------------------------------------
def add_column_if_not_exists(table, column, col_type):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    # جدول المستخدمين مع إضافة token و صلاحيته
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            is_approved INTEGER DEFAULT 0,
            token TEXT,
            token_expiry DATETIME
        )
    ''')
    # جدول المنتجات (نفسه)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            link TEXT,
            image BLOB
        )
    ''')
    # جدول سجل الحركات (جديد)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            action TEXT,
            product_id INTEGER,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    # إضافة الأعمدة الجديدة إذا لم تكن موجودة (للتوافق مع القواعد القديمة)
    add_column_if_not_exists('users', 'token', 'TEXT')
    add_column_if_not_exists('users', 'token_expiry', 'DATETIME')

init_db()

ADMIN_SECRET_KEY = "admin123"
TOKEN_EXPIRY_DAYS = 7

# ---------------------------------------------------------
# 2. دوال مساعدة: إدارة التوكن والتسجيل
# ---------------------------------------------------------
def generate_token():
    return secrets.token_urlsafe(32)

def set_user_token(email):
    token = generate_token()
    expiry = datetime.datetime.now() + datetime.timedelta(days=TOKEN_EXPIRY_DAYS)
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET token=?, token_expiry=? WHERE email=?", (token, expiry, email))
    conn.commit()
    conn.close()
    return token

def clear_user_token(email):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET token=NULL, token_expiry=NULL WHERE email=?", (email,))
    conn.commit()
    conn.close()

def validate_token(token):
    if not token:
        return None
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, token_expiry FROM users WHERE token=? AND is_approved=1", (token,))
    row = cursor.fetchone()
    conn.close()
    if row:
        email, expiry_str = row
        expiry = datetime.datetime.fromisoformat(expiry_str) if expiry_str else None
        if expiry and expiry > datetime.datetime.now():
            return email
    return None

def log_action(user_email, action, product_id=None, details=""):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (user_email, action, product_id, details) VALUES (?, ?, ?, ?)",
                   (user_email, action, product_id, details))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 3. التحقق من التوكن عند بدء التشغيل (تسجيل دخول تلقائي)
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""

# قراءة التوكن من رابط الصفحة
query_params = st.query_params
token_from_url = query_params.get("token", None)

if not st.session_state['logged_in'] and token_from_url:
    email = validate_token(token_from_url)
    if email:
        st.session_state['logged_in'] = True
        st.session_state['user_email'] = email
        # نزيل التوكن من الرابط بعد استخدامه (كي لا يبقى ظاهراً)
        st.query_params.clear()
        st.rerun()

# ---------------------------------------------------------
# 4. واجهة التسجيل والدخول (لمن ليس مسجلاً)
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    st.title("🔐 نظام إدارة المخزون - التسجيل والدخول")
    
    tab_login, tab_register, tab_admin_access = st.tabs(["تسجيل الدخول", "حساب جديد", "🔑 دخول الأدمن"])

    # --- تسجيل الدخول ---
    with tab_login:
        email = st.text_input("البريد الإلكتروني", key="login_email")
        password = st.text_input("كلمة السر", type="password", key="login_pass")
        remember = st.checkbox("تذكرني (البقاء متصلاً)", value=True)
        if st.button("تسجيل الدخول", type="primary"):
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT is_approved FROM users WHERE email=? AND password=?", (email, password))
            user = cursor.fetchone()
            conn.close()
            if user:
                if user[0] == 1:
                    st.session_state['logged_in'] = True
                    st.session_state['user_email'] = email
                    # إنشاء توكن إذا اختار "تذكرني"
                    if remember:
                        token = set_user_token(email)
                        st.query_params["token"] = token
                    st.rerun()
                else:
                    st.warning("⏳ حسابك مسجل وبانتظار موافقة المسؤول.")
            else:
                st.error("❌ البريد أو كلمة السر غير صحيحة.")

    # --- إنشاء حساب جديد ---
    with tab_register:
        new_email = st.text_input("البريد الإلكتروني الجديد", key="reg_email")
        new_pass = st.text_input("كلمة السر الجديدة", type="password", key="reg_pass")
        if st.button("إنشاء حساب"):
            if new_email and new_pass:
                try:
                    conn = sqlite3.connect('inventory.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (email, password, is_approved) VALUES (?, ?, 0)", (new_email, new_pass))
                    conn.commit()
                    conn.close()
                    st.success("✅ تم إنشاء الحساب بنجاح! يرجى التواصل مع الأدمن للتفعيل.")
                except:
                    st.error("⚠️ هذا البريد مسجل بالفعل.")

    # --- لوحة الأدمن ---
    with tab_admin_access:
        st.subheader("لوحة تفعيل الحسابات (خاصة بالمسؤول فقط)")
        admin_key_input = st.text_input("أدخل رمز تفعيل الأدمن الخاص بك", type="password", key="auth_admin_key")
        if admin_key_input == ADMIN_SECRET_KEY:
            st.success("🔓 تم التحقق من الرمز بنجاح!")
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT email, is_approved FROM users")
            users_list = cursor.fetchall()
            if not users_list:
                st.info("لا يوجد مستخدمون مسجلون بعد.")
            else:
                for u in users_list:
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"📧 **{u[0]}** — ({'✅ مفعل' if u[1]==1 else '⏳ معلق'})")
                    if u[1] == 0:
                        if col2.button("سماح وتفعيل", key=f"tab_btn_{u[0]}"):
                            cursor.execute("UPDATE users SET is_approved=1 WHERE email=?", (u[0],))
                            conn.commit()
                            st.success(f"تم تفعيل {u[0]} بنجاح!")
                            st.rerun()
            conn.close()
        elif admin_key_input:
            st.error("❌ رمز التفعيل غير صحيح! هذه اللوحة مخصصة للأدمن فقط.")
    st.stop()

# ---------------------------------------------------------
# 5. القائمة الجانبية بعد الدخول (مع إحصائيات)
# ---------------------------------------------------------
st.sidebar.title("📌 مخزن مهندس أحمد")
st.sidebar.write(f"👤 المستخدم: **{st.session_state['user_email']}**")

# إحصائيات سريعة
conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*), SUM(quantity) FROM products")
total_products, total_qty = cursor.fetchone()
conn.close()
st.sidebar.metric("📦 إجمالي المنتجات", total_products)
st.sidebar.metric("🔢 إجمالي الكميات", total_qty if total_qty else 0)

if st.sidebar.button("🚪 تسجيل الخروج"):
    clear_user_token(st.session_state['user_email'])
    st.session_state['logged_in'] = False
    st.session_state['user_email'] = ""
    st.query_params.clear()
    st.rerun()

# ---------------------------------------------------------
# 6. واجهة إضافة وعرض المنتجات (مع التحسينات)
# ---------------------------------------------------------
st.title("📦 نظام إدارة المنتجات والمخزون - مهندس أحمد")

tab_view, tab_add = st.tabs(["عرض المنتجات", "➕ إضافة منتج جديد"])

# --- تبويب إضافة منتج جديد (مع معاينة الصورة) ---
with tab_add:
    st.subheader("إضافة منتج جديد")
    with st.form("add_product_form", clear_on_submit=True):
        p_name = st.text_input("اسم المنتج")
        p_color = st.text_input("اللون (مثال: أحمر، أسود، أزرق)")
        p_quantity = st.number_input("الكمية المتاحة", min_value=1, step=1)
        p_price = st.number_input("السعر", min_value=0.0, step=0.5)
        p_link = st.text_input("رابط الصفحة الخاصة بالمنتج (اختياري)", placeholder="https://example.com/product")
        p_image = st.file_uploader("صورة المنتج", type=["jpg", "jpeg", "png"])
        
        # معاينة الصورة
        if p_image:
            st.image(p_image, caption="معاينة الصورة", width=200)
        
        submitted = st.form_submit_button("💾 حفظ المنتج")
        if submitted:
            if p_name and p_color:
                img_bytes = p_image.read() if p_image else None
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (name, color, quantity, price, link, image) VALUES (?, ?, ?, ?, ?, ?)",
                               (p_name, p_color, p_quantity, p_price, p_link, img_bytes))
                product_id = cursor.lastrowid
                conn.commit()
                conn.close()
                # تسجيل الحركة
                log_action(st.session_state['user_email'], "إضافة منتج", product_id, f"الاسم: {p_name}, الكمية: {p_quantity}")
                st.success(f"✅ تم إضافة المنتج '{p_name}' بنجاح!")
            else:
                st.error("يرجى ملء كافة البيانات المطلوبة.")

# --- تبويب عرض المنتجات والبحث (مع تحسينات الأزرار) ---
with tab_view:
    st.subheader("قائمة المنتجات المسجلة")
    search_query = st.text_input("🔍 البحث عن منتج (بالاسم أو اللون):", key="search_box")
    
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    if search_query:
        cursor.execute("SELECT id, name, color, quantity, price, link, image FROM products WHERE name LIKE ? OR color LIKE ?", 
                       (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT id, name, color, quantity, price, link, image FROM products")
    products = cursor.fetchall()
    conn.close()

    if not products:
        st.info("لا توجد منتجات متطابقة مع البحث." if search_query else "لا توجد منتجات مسجلة حتى الآن.")
    else:
        cols = st.columns(3)
        for idx, prod in enumerate(products):
            p_id, name, color, qty, price, link, img_data = prod
            with cols[idx % 3]:
                with st.container(border=True):
                    # عرض الصورة
                    if img_data:
                        image = Image.open(io.BytesIO(img_data))
                        st.image(image, use_container_width=True)
                    else:
                        st.write("🖼️ *لا توجد صورة*")
                    
                    st.markdown(f"### {name}")
                    st.write(f"🎨 **اللون:** {color}")
                    
                    # عرض الكمية مع تنبيه إذا كانت منخفضة
                    if qty <= 5:
                        st.write(f"🔢 **الكمية المتاحة:** {qty} ⚠️ (منخفضة)")
                    else:
                        st.write(f"🔢 **الكمية المتاحة:** {qty}")
                    
                    st.write(f"💰 **السعر:** {price}$")
                    
                    if link:
                        st.link_button("🌐 زيارة المنتج", link, use_container_width=True)
                    
                    st.divider()
                    
                    # أزرار التحكم
                    col_minus, col_plus, col_del = st.columns([1, 1, 1])
                    
                    # نقص الكمية
                    if col_minus.button("➖", key=f"minus_{p_id}", type="secondary"):
                        if qty > 0:
                            conn = sqlite3.connect('inventory.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE products SET quantity = quantity - 1 WHERE id=?", (p_id,))
                            conn.commit()
                            conn.close()
                            log_action(st.session_state['user_email'], "نقص كمية", p_id, f"الكمية الجديدة: {qty-1}")
                            st.rerun()
                        else:
                            st.warning("الكمية بالفعل 0")
                    
                    # زيادة الكمية
                    if col_plus.button("➕", key=f"plus_{p_id}", type="secondary"):
                        conn = sqlite3.connect('inventory.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE products SET quantity = quantity + 1 WHERE id=?", (p_id,))
                        conn.commit()
                        conn.close()
                        log_action(st.session_state['user_email'], "زيادة كمية", p_id, f"الكمية الجديدة: {qty+1}")
                        st.rerun()
                    
                    # حذف المنتج مع تأكيد
                    delete_key = f"del_{p_id}"
                    confirm_key = f"confirm_{p_id}"
                    
                    # إذا كان هذا المنتج هو المطلوب تأكيد حذفه
                    if st.session_state.get("confirm_delete") == p_id:
                        st.warning("⚠️ هل أنت متأكد من حذف هذا المنتج نهائياً؟")
                        col_yes, col_no = st.columns(2)
                        if col_yes.button("نعم، احذف", key=f"yes_{p_id}", type="danger"):
                            conn = sqlite3.connect('inventory.db')
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM products WHERE id=?", (p_id,))
                            conn.commit()
                            conn.close()
                            log_action(st.session_state['user_email'], "حذف منتج", p_id, f"المنتج: {name}")
                            st.session_state["confirm_delete"] = None
                            st.rerun()
                        if col_no.button("لا", key=f"no_{p_id}"):
                            st.session_state["confirm_delete"] = None
                            st.rerun()
                    else:
                        if col_del.button("🗑️", key=delete_key, type="danger"):
                            st.session_state["confirm_delete"] = p_id
                            st.rerun()

# إضافة زر "عرض سجل الحركات" في الشريط الجانبي (ميزة إضافية)
with st.sidebar.expander("📋 عرض سجل الحركات"):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_email, action, details, timestamp FROM logs ORDER BY timestamp DESC LIMIT 20")
    logs = cursor.fetchall()
    conn.close()
    if logs:
        for log in logs:
            st.write(f"**{log[0]}** - {log[1]} : {log[2]}  \n*{log[3]}*")
    else:
        st.write("لا توجد حركات مسجلة.")
