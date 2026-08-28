import streamlit as st
import sqlite3
from PIL import Image
import io

# إعدادات الصفحة وجعل الشريط الجانبي مفتوحاً دائماً
st.set_page_config(
    page_title="إدارة المخزون والمنتجات",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. إعداد قاعدة البيانات
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            is_approved INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            image BLOB
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# 2. إدارة الجلسة والدخول
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""

if not st.session_state['logged_in']:
    st.title("🔐 نظام إدارة المخزون - التسجيل والدخول")
    
    tab_login, tab_register, tab_admin = st.tabs(["تسجيل الدخول", "حساب جديد", "🔑 تفعيل الأدمن"])

    # --- تسجيل الدخول ---
    with tab_login:
        email = st.text_input("البريد الإلكتروني", key="login_email")
        password = st.text_input("كلمة السر", type="password", key="login_pass")
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
                    st.rerun()
                else:
                    st.warning("⏳ حسابك مسجل وبانتظار موافقة المسؤول من تبويب (تفعيل الأدمن).")
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
                    st.success("✅ تم إنشاء الحساب بنجاح! اذهب إلى تبويب (تفعيل الأدمن) لتفعيل الحساب.")
                except:
                    st.error("⚠️ هذا البريد مسجل بالفعل.")

    # --- لوحة الأدمن لتفعيل الحسابات من المنتصف مباشرة ---
    with tab_admin:
        st.subheader("لوحة موافقة المسؤول على الحسابات")
        admin_key = st.text_input("رمز سر الأدمن للتفعيل", type="password", key="admin_tab_key")
        if admin_key == "admin123":
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
        elif admin_key:
            st.error("رمز الأدمن غير صحيح.")

    st.stop()

# ---------------------------------------------------------
# 3. القائمة الجانبية بعد الدخول
# ---------------------------------------------------------
st.sidebar.title("📌 القائمة الجانبية")
st.sidebar.write(f"👤 المستخدم: **{st.session_state['user_email']}**")

if st.sidebar.button("تسجيل الخروج"):
    st.session_state['logged_in'] = False
    st.session_state['user_email'] = ""
    st.rerun()

# ---------------------------------------------------------
# 4. واجهة إضافة وعرض المنتجات
# ---------------------------------------------------------
st.title("📦 نظام إدارة المنتجات والمخزون")

tab_view, tab_add = st.tabs(["عرض المنتجات", "➕ إضافة منتج جديد"])

with tab_add:
    st.subheader("إضافة منتج جديد")
    with st.form("add_product_form", clear_on_submit=True):
        p_name = st.text_input("اسم المنتج")
        p_color = st.text_input("اللون (مثال: أحمر، أسود، أزرق)")
        p_quantity = st.number_input("الكمية المتاحة", min_value=1, step=1)
        p_price = st.number_input("السعر", min_value=0.0, step=0.5)
        p_image = st.file_uploader("صورة المنتج", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("حفظ المنتج")
        if submitted:
            if p_name and p_color:
                img_bytes = p_image.read() if p_image else None
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (name, color, quantity, price, image) VALUES (?, ?, ?, ?, ?)",
                               (p_name, p_color, p_quantity, p_price, img_bytes))
                conn.commit()
                conn.close()
                st.success(f"✅ تم إضافة المنتج '{p_name}' بنجاح!")
            else:
                st.error("يرجى ملء كافة البيانات المطلوبة.")

with tab_view:
    st.subheader("قائمة المنتجات المسجلة")
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, color, quantity, price, image FROM products")
    products = cursor.fetchall()
    conn.close()

    if not products:
        st.info("لا توجد منتجات مسجلة حتى الآن.")
    else:
        cols = st.columns(3)
        for idx, prod in enumerate(products):
            p_id, name, color, qty, price, img_data = prod
            with cols[idx % 3]:
                with st.container(border=True):
                    if img_data:
                        image = Image.open(io.BytesIO(img_data))
                        st.image(image, use_container_width=True)
                    else:
                        st.write("🖼️ *لا توجد صورة*")
                    st.markdown(f"### {name}")
                    st.write(f"🎨 **اللون:** {color}")
                    st.write(f"🔢 **الكمية:** {qty}")
                    st.write(f"💰 **السعر:** {price}$")
                    
                    if st.button("حذف المنتج", key=f"del_{p_id}"):
                        conn = sqlite3.connect('inventory.db')
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM products WHERE id=?", (p_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()
