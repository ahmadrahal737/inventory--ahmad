import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image
import io

# --- إعداد قاعدة البيانات ---
DB_FILE = "inventory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, 
                  quantity INTEGER, 
                  price REAL, 
                  image BLOB)''')
    conn.commit()
    conn.close()

init_db()

# --- إعداد الصفحة والتصميم (CSS Custom Theme) ---
st.set_page_config(page_title="نظام أحمد رحال لإدارة المخزون", layout="wide")

st.markdown("""
    <style>
    /* ألوان الخلفيات والعناصر الرئيسية */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* الهيدر العلوي */
    .header-container {
        background: linear-gradient(135deg, #4f46e5, #06b6d4);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 20px rgba(79, 70, 229, 0.15);
        margin-bottom: 2rem;
    }
    
    .header-container h1 {
        color: white !important;
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    
    .developer-badge {
        background-color: rgba(255, 255, 255, 0.2);
        padding: 6px 16px;
        border-radius: 50px;
        font-size: 1rem;
        font-weight: 600;
        display: inline-block;
        backdrop-filter: blur(5px);
    }
    
    /* تخصيص القائمة الجانبية */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-left: 1px solid #e2e8f0;
    }
    
    /* تخصيص الأزرار */
    .stButton > button {
        background: linear-gradient(135deg, #4f46e5, #06b6d4);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(79, 70, 229, 0.3);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- الترويسة الرئيسية ---
st.markdown("""
    <div class="header-container">
        <h1>📦 نظام إدارة المخزون الذكي</h1>
        <div class="developer-badge">تطوير المطور: أحمد رحال ✨</div>
    </div>
""", unsafe_allow_html=True)

# القائمة الجانبية للتنقل
st.sidebar.markdown("### 👤 **أحمد رحال**")
st.sidebar.markdown("---")
menu = ["عرض المخزون", "إضافة منتج جديد", "تصدير البيانات (CSV)"]
choice = st.sidebar.radio("القائمة الرئيسية", menu)

# --- 1. عرض المخزون ---
if choice == "عرض المخزون":
    st.subheader("📊 جدول المنتجات الحالية")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id AS 'المعرف', name AS 'اسم المنتج', quantity AS 'الكمية', price AS 'السعر ($)' FROM products", conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # عرض صور المنتجات
        st.subheader("📷 معرض صور المنتجات")
        c = conn.cursor()
        c.execute("SELECT name, image FROM products WHERE image IS NOT NULL")
        rows = c.fetchall()
        
        cols = st.columns(3)
        for idx, (p_name, img_data) in enumerate(rows):
            if img_data:
                try:
                    image = Image.open(io.BytesIO(img_data))
                    with cols[idx % 3]:
                        st.image(image, caption=p_name, use_column_width=True)
                except Exception:
                    pass
    else:
        st.info("لا توجد منتجات مسجلة حتى الآن في النظام.")
    conn.close()

# --- 2. إضافة منتج جديد ---
elif choice == "إضافة منتج جديد":
    st.subheader("➕ إضافة منتج إلى قاعدة البيانات")
    
    with st.form("add_product_form", clear_on_submit=True):
        name = st.text_input("اسم المنتج")
        quantity = st.number_input("الكمية", min_value=0, step=1)
        price = st.number_input("السعر", min_value=0.0, step=0.5)
        uploaded_file = st.file_uploader("صورة المنتج (اختياري)", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("حفظ المنتج")
        
        if submitted:
            if name.strip() == "":
                st.error("يرجى إدخال اسم المنتج!")
            else:
                img_bytes = None
                if uploaded_file is not None:
                    img_bytes = uploaded_file.read()
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO products (name, quantity, price, image) VALUES (?, ?, ?, ?)",
                          (name, quantity, price, img_bytes))
                conn.commit()
                conn.close()
                st.success(f"تمت إضافة المنتج '{name}' بنجاح إلى نظام أحمد رحال!")

# --- 3. تصدير البيانات ---
elif choice == "تصدير البيانات (CSV)":
    st.subheader("📥 تصدير ملف البيانات")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id, name, quantity, price FROM products", conn)
    conn.close()
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 تحميل تقرير المخزون (CSV)",
            data=csv,
            file_name='inventory_report_ahmad_rahhal.csv',
            mime='text/csv',
        )
    else:
        st.warning("لا توجد بيانات متاحة للتصدير حالياً.")
import streamlit as st
import sqlite3

# إنشاء قاعدة بيانات الحسابات
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            is_approved INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# إدارة حالة الدخول
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# الشاشة قبل تسجيل الدخول
if not st.session_state['logged_in']:
    st.title("تسجيل الدخول / إنشاء حساب")
    tab1, tab2 = st.tabs(["تسجيل الدخول", "حساب جديد"])

    with tab1:
        email = st.text_input("البريد الإلكتروني", key="login_email")
        password = st.text_input("كلمة السر", type="password", key="login_pass")
        if st.button("دخول"):
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT is_approved FROM users WHERE email=? AND password=?", (email, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                if user[0] == 1:
                    st.session_state['logged_in'] = True
                    st.success("تم الدخول بنجاح!")
                    st.rerun()
                else:
                    st.warning("حسابك بانتظار موافقة المسؤول.")
            else:
                st.error("البريد أو كلمة السر غير صحيحة")

    with tab2:
        new_email = st.text_input("البريد الإلكتروني", key="reg_email")
        new_pass = st.text_input("كلمة السر", type="password", key="reg_pass")
        if st.button("إنشاء حساب"):
            try:
                conn = sqlite3.connect('users.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (email, password, is_approved) VALUES (?, ?, 0)", (new_email, new_pass))
                conn.commit()
                conn.close()
                st.info("تم إنشاء الحساب! يرجى الانتظار لحين موافقة المسؤول.")
            except:
                st.error("البريد الإلكتروني مستخدم بالفعل")

    st.stop() # يمنع عرض باقي التطبيق الأصلي حتى يتم الدخول

# --- ضع كود تطبيقك الأصلي هنا (سيعمل فقط بعد تسجيل الدخول) ---
    
    return jsonify({"message": f"تمت الموافقة على حساب {target_email} بنجاح!"})

if __name__ == '__main__':
    app.run(debug=True)
# لوحة تفعيل الحسابات (Admin)
with st.sidebar.expander("لوحة المسؤول (Admin)"):
    admin_pass = st.text_input("كلمة سر الأدمن", type="password")
    if admin_pass == "admin123": # يمكنك تغيير كلمة السر هذه
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT email, is_approved FROM users")
        users = cursor.fetchall()
        
        for u in users:
            col1, col2 = st.columns([2, 1])
            col1.write(f"{u[0]} ({'مفعل' if u[1]==1 else 'غير مفعل'})")
            if u[1] == 0:
                if col2.button("تفعيل", key=u[0]):
                    cursor.execute("UPDATE users SET is_approved=1 WHERE email=?", (u[0],))
                    conn.commit()
                    st.rerun()
        conn.close()
