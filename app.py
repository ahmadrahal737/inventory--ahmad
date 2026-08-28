import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image
import io
import os

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

# --- واجهة الموقع ---
st.set_page_config(page_title="نظام إدارة المخزون", layout="wide")
st.title("📦 نظام إدارة المخزون (Inventory Management)")

# القائمة الجانبية للتنقل
menu = ["عرض المخزون", "إضافة منتج جديد", "تصدير البيانات (CSV)"]
choice = st.sidebar.selectbox("القائمة الرئيسية", menu)

# --- 1. عرض المخزون ---
if choice == "عرض المخزون":
    st.subheader("جدول المنتجات الحالية")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id, name, quantity, price FROM products", conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # عرض صور المنتجات
        st.subheader("📷 صور المنتجات")
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
        st.info("لا توجد منتجات مسجلة حتى الآن.")
    conn.close()

# --- 2. إضافة منتج جديد ---
elif choice == "إضافة منتج جديد":
    st.subheader("إضافة منتج إلى قاعدة البيانات")
    
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
                st.success(f"تمت إضافة المنتج '{name}' بنجاح!")

# --- 3. تصدير البيانات ---
elif choice == "تصدير البيانات (CSV)":
    st.subheader("تصدير ملف Excel / CSV")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id, name, quantity, price FROM products", conn)
    conn.close()
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 تحميل ملف CSV",
            data=csv,
            file_name='inventory_report.csv',
            mime='text/csv',
        )
    else:
        st.warning("لا توجد بيانات لتصديرها.")
