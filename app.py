import streamlit as st
import sqlite3

# ضبط إعدادات الصفحة وجعلها تدعم ميزة التثبيت كـ PWA
st.set_page_config(
    page_title="تطبيق إدارة المخزون",
    page_icon="📦",
    layout="wide"
)

# ---------------------------------------------------------
# 1. إعداد قاعدة بيانات المستخدمين (SQLite)
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 2. نظام تسجيل الدخول والموافقات
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""

# إذا لم يكن المستخدم مسجلاً، اظهر صفحة الدخول والتسجيل فقط
if not st.session_state['logged_in']:
    st.title("🔐 تسجيل الدخول إلى النظام")
    
    tab_login, tab_register = st.tabs(["تسجيل الدخول", "حساب جديد"])

    # --- تبويب تسجيل الدخول ---
    with tab_login:
        email = st.text_input("البريد الإلكتروني", key="login_email")
        password = st.text_input("كلمة السر", type="password", key="login_pass")
        
        if st.button("تسجيل الدخول", type="primary"):
            if email and password:
                conn = sqlite3.connect('users.db')
                cursor = conn.cursor()
                cursor.execute("SELECT is_approved FROM users WHERE email=? AND password=?", (email, password))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    if user[0] == 1:
                        st.session_state['logged_in'] = True
                        st.session_state['user_email'] = email
                        st.success("تم الدخول بنجاح!")
                        st.rerun()
                    else:
                        st.warning("⏳ حسابك مسجل ولكنه بانتظار موافقة الأدمن.")
                else:
                    st.error("❌ البريد الإلكتروني أو كلمة السر غير صحيحة.")
            else:
                st.warning("يرجى ملء كافة الحقول.")

    # --- تبويب حساب جديد ---
    with tab_register:
        new_email = st.text_input("البريد الإلكتروني الجديد", key="reg_email")
        new_pass = st.text_input("كلمة السر الجديدة", type="password", key="reg_pass")
        
        if st.button("إنشاء الحساب"):
            if new_email and new_pass:
                try:
                    conn = sqlite3.connect('users.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (email, password, is_approved) VALUES (?, ?, 0)", (new_email, new_pass))
                    conn.commit()
                    conn.close()
                    st.success("✅ تم إنشاء الحساب بنجاح! انتظر تفعيل الحساب من الأدمن للدخول.")
                except sqlite3.IntegrityError:
                    st.error("⚠️ هذا البريد الإلكتروني مسجل بالفعل.")
            else:
                st.warning("يرجى إدخال البريد وكلمة السر.")

    # إيقاف تنفيذ باقي الكود حتى يسجل الدخول
    st.stop()

# ---------------------------------------------------------
# 3. القائمة الجانبية (شريط الأدمن وإمكانية الخروج)
# ---------------------------------------------------------
st.sidebar.write(f"👤 مرحباً: **{st.session_state['user_email']}**")

if st.sidebar.button("تسجيل الخروج"):
    st.session_state['logged_in'] = False
    st.session_state['user_email'] = ""
    st.rerun()

# --- لوحة الأدمن الخاصة بك فقط لتفعيل الحسابات ---
with st.sidebar.expander("🔑 لوحة موافقة الأدمن"):
    admin_key = st.text_input("كلمة سر الأدمن", type="password")
    if admin_key == "admin123":  # يمكنك تغيير كلمة السر الخاصة بك من هنا
        st.subheader("إدارة حسابات المستخدمين")
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT email, is_approved FROM users")
        all_users = cursor.fetchall()
        
        for u in all_users:
            col1, col2 = st.columns([2, 1])
            status_text = "✅ مفعل" if u[1] == 1 else "⏳ معلق"
            col1.write(f"{u[0]} ({status_text})")
            
            if u[1] == 0:
                if col2.button("سماح", key=f"btn_{u[0]}"):
                    cursor.execute("UPDATE users SET is_approved=1 WHERE email=?", (u[0],))
                    conn.commit()
                    st.success(f"تم تفعيل {u[0]}")
                    st.rerun()
        conn.close()

# ---------------------------------------------------------
# 4. كود برنامجك الأصلي (إدارة المنتجات والمخزون)
# ---------------------------------------------------------
st.title("📦 نظام إدارة المنتجات والمخزون")

# (هنا يوضع كود عرض المنتجات والإضافة الخاص بك)
st.info("مرحباً بك في النظام. يمكنك الآن التفاعل مع البيانات بأمان.")

# يمكنك استكمال بقية كود عرض الجداول والمنتجات هنا...
