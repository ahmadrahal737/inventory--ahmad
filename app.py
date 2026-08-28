import streamlit as st
import sqlite3
from PIL import Image
import io

# ---------------------------------------------------------
# إعدادات الصفحة المخصصة وتصميم متوافق مع الهاتف
# ---------------------------------------------------------
st.set_page_config(
    page_title="نظام المخزون | المهندس أحمد",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إضافة CSS لتحسين الألوان والواجهة على الهواتف الذكية
st.markdown("""
    <style>
    /* الألوان الأساسية والتنسيق العام */
    :root {
        --primary-color: #1e293b;
        --accent-color: #d97706;
        --bg-card: #ffffff;
    }
    
    /* جعل الأزرار أكبر وأكثر وضوحاً للمس على الهاتف */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease-in-out;
    }
    
    /* تحسين العناوين وشريط الهوية */
    .brand-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #ffffff;
        padding: 1.2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .brand-header h1 {
        color: #d97706;
        margin: 0;
        font-size: 1.6rem;
    }
    .brand-header p {
        margin: 5px 0 0 0;
        font-size: 0.95rem;
        opacity: 0.9;
    }
    
    /* بطاقة الإحصائيات السريعة */
    .stat-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
    }
    </style>
""", unsafe_allow_allow_html=True)

# ---------------------------------------------------------
# 1. إعداد قاعدة البيانات وتحديث الجداول
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
            link TEXT,
            image BLOB
        )
    ''')
    conn.commit()
    conn.close()

init_db()

ADMIN_SECRET_KEY = "admin123"

# Header الرئيسي
st.markdown("""
    <div class="brand-header">
        <h1>📦 نظام إدارة المخزون الذكي</h1>
        <p>إشراف وتطوير: <b>المهندس أحمد</b></p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. إدارة الجلسة والدخول
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""

if not st.session_state['logged_in']:
    tab_login, tab_register, tab_admin_access = st.tabs(["🔒 تسجيل الدخول", "📝 حساب جديد", "🔑 تفعيل الأدمن"])

    # --- تسجيل الدخول ---
    with tab_login:
        email = st.text_input("البريد الإلكتروني", key="login_email")
        password = st.text_input("كلمة السر", type="password", key="login_pass")
        if st.button("تسجيل الدخول", type="primary", use_container_width=True):
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
                    st.warning("⏳ حسابك مسجل وبانتظار موافقة المهندس أحمد.")
            else:
                st.error("❌ البريد أو كلمة السر غير صحيحة.")

    # --- إنشاء حساب جديد ---
    with tab_register:
        new_email = st.text_input("البريد الإلكتروني الجديد", key="reg_email")
        new_pass = st.text_input("كلمة السر الجديدة", type="password", key="reg_pass")
        if st.button("إنشاء حساب", use_container_width=True):
            if new_email and new_pass:
                try:
                    conn = sqlite3.connect('inventory.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (email, password, is_approved) VALUES (?, ?, 0)", (new_email, new_pass))
                    conn.commit()
                    conn.close()
                    st.success("✅ تم إنشاء الحساب بنجاح! يرجى الانتظار لحين التفعيل من الأدمن.")
                except:
                    st.error("⚠️ هذا البريد مسجل بالفعل.")

    # --- لوحة الأدمن ---
    with tab_admin_access:
        st.subheader("لوحة تفعيل الحسابات (المسؤول)")
        admin_key_input = st.text_input("أدخل رمز تفعيل الأدمن", type="password", key="auth_admin_key")
        
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
            st.error("❌ رمز التفعيل غير صحيح!")

    st.stop()

# ---------------------------------------------------------
# 3. القائمة الجانبية بعد الدخول
# ---------------------------------------------------------
st.sidebar.title("📱 التحكم والحساب")
st.sidebar.markdown(f"👤 المستخدم الحركي:\n**{st.session_state['user_email']}**")
st.sidebar.markdown("---")

if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state['logged_in'] = False
    st.session_state['user_email'] = ""
    st.rerun()

# ---------------------------------------------------------
# 4. واجهة إضافة وعرض المنتجات
# ---------------------------------------------------------
tab_view, tab_add = st.tabs(["📋 عرض والبحث عن المنتجات", "➕ إضافة منتج جديد"])

# --- تبويب إضافة منتج جديد ---
with tab_add:
    st.subheader("إضافة منتج جديد للمخزون")
    with st.form("add_product_form", clear_on_submit=True):
        p_name = st.text_input("اسم المنتج")
        p_color = st.text_input("اللون (مثال: أحمر، أسود، أزرق)")
        p_quantity = st.number_input("الكمية المتاحة", min_value=1, step=1)
        p_price = st.number_input("السعر ($)", min_value=0.0, step=0.5)
        p_link = st.text_input("رابط المنتج (اختياري)", placeholder="https://example.com/product")
        p_image = st.file_uploader("صورة المنتج", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("💾 حفظ المنتج", use_container_width=True)
        if submitted:
            if p_name and p_color:
                img_bytes = p_image.read() if p_image else None
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (name, color, quantity, price, link, image) VALUES (?, ?, ?, ?, ?, ?)",
                               (p_name, p_color, p_quantity, p_price, p_link, img_bytes))
                conn.commit()
                conn.close()
                st.success(f"✅ تم إضافة المنتج '{p_name}' بنجاح!")
            else:
                st.error("يرجى ملء كافة البيانات الأساسية المطلوبة.")

# --- تبويب عرض والبحث عن المنتجات ---
with tab_view:
    # 🔍 حقل البحث
    search_query = st.text_input("🔍 بحث عن منتج (الاسم أو اللون):", key="search_box")
    
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    
    if search_query:
        cursor.execute("SELECT id, name, color, quantity, price, link, image FROM products WHERE name LIKE ? OR color LIKE ?", 
                       (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT id, name, color, quantity, price, link, image FROM products")
        
    products = cursor.fetchall()
    
    # حساب ملخص إحصائيات المخزون
    cursor.execute("SELECT SUM(quantity), SUM(quantity * price) FROM products")
    stats = cursor.fetchone()
    total_qty = stats[0] if stats[0] else 0
    total_val = stats[1] if stats[1] else 0.0
    conn.close()

    # عرض الإحصائيات في شريط علوي
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='stat-card'>📦 إجمالي القطع المخزنة<br><b>{total_qty}</b></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-card'>💰 القيمة الإجمالية<br><b>{total_val:,.2f} $</b></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if not products:
        st.info("لا توجد منتجات مسجلة مطابقة للبحث." if search_query else "لا توجد منتجات في المخزون حالياً.")
    else:
        # ترتيب العرض بصورة تجاوبية (3 أعمدة للشاشات العريضة وتتحول لتناسب الهاتف)
        cols = st.columns([1, 1, 1])
        for idx, prod in enumerate(products):
            p_id, name, color, qty, price, link, img_data = prod
            with cols[idx % 3]:
                with st.container(border=True):
                    if img_data:
                        image = Image.open(io.BytesIO(img_data))
                        st.image(image, use_container_width=True)
                    else:
                        st.write("🖼️ *لا توجد صورة للمنتج*")
                    
                    st.markdown(f"### {name}")
                    st.write(f"🎨 **اللون:** {color}")
                    st.write(f"🔢 **الكمية:** {qty}")
                    st.write(f"💰 **السعر:** {price}$")
                    
                    if link:
                        st.link_button("🌐 رابط المنتج", link, use_container_width=True)
                    
                    st.divider()
                    
                    # أزرار التفاعل السريع
                    col_minus, col_plus, col_del = st.columns([1, 1, 1])
                    
                    if col_minus.button("➖", key=f"minus_{p_id}"):
                        if qty > 0:
                            conn = sqlite3.connect('inventory.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE products SET quantity = quantity - 1 WHERE id=?", (p_id,))
                            conn.commit()
                            conn.close()
                            st.rerun()
                        else:
                            st.warning("الكمية 0 بالفعل")
                            
                    if col_plus.button("➕", key=f"plus_{p_id}"):
                        conn = sqlite3.connect('inventory.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE products SET quantity = quantity + 1 WHERE id=?", (p_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()

                    if col_del.button("🗑️", key=f"del_{p_id}"):
                        conn = sqlite3.connect('inventory.db')
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM products WHERE id=?", (p_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()
