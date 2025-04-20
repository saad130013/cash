import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import requests
import joblib
from sklearn.ensemble import IsolationForest

def send_telegram_alert(message):
    token = "8064722037:AAFjn6v_d8fGj0mBAfezOpndKHV4LBFd1HI"
    chat_id = "961480270"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            st.toast("📤 تم إرسال تنبيه عبر Telegram")
    except Exception as e:
        st.error(f"خطأ في إرسال التنبيه: {e}")

st.set_page_config(page_title="نظام تسجيل العهد", layout="wide")
st.title("📘 نظام تسجيل العُهد وتتبعها")

EXCEL_PATH = "دفتر_العهد_المنظم.xlsx"

@st.cache_data
def load_data():
    if os.path.exists(EXCEL_PATH):
        return pd.read_excel(EXCEL_PATH)
    else:
        return pd.DataFrame(columns=[
            "مرفق", "رقم اليومية", "التاريخ", "اسم المستفيد", 
            "نوع العهدة", "البيان", "المبلغ", 
            "نوع الحركة (مدين/دائن)", "تاريخ العودة", "تمت التسوية؟"
        ])

df = load_data()

# 🔍 تصفية حسب التاريخ
st.sidebar.header("🗂️ تصفية العهد حسب التاريخ")
start_date = st.sidebar.date_input("من تاريخ", value=datetime.today().replace(day=1))
end_date = st.sidebar.date_input("إلى تاريخ", value=datetime.today())
df = df[(pd.to_datetime(df["التاريخ"]) >= pd.to_datetime(start_date)) & 
        (pd.to_datetime(df["التاريخ"]) <= pd.to_datetime(end_date))]

# تحميل النماذج
text_model = joblib.load("text_classifier_model.joblib")
anomaly_model = IsolationForest(contamination=0.2, random_state=42)
sample_amounts = [[100], [150], [200], [180], [160], [250], [220], [190], [175], [130], [4000], [5000]]
anomaly_model.fit(sample_amounts)

# 📥 نموذج التسجيل
st.subheader("📥 تسجيل عهدة جديدة")
with st.form("form_entry"):
    col1, col2 = st.columns(2)
    with col1:
        daily_number = st.text_input("رقم اليومية")
        name = st.text_input("اسم المستفيد")
        ouda_type = st.selectbox("نوع العهدة", ["سلفة مستديمة", "سلفة مؤقتة", "عهدة تحت التحصيل", "اعتماد مستندي"])
        amount = st.number_input("المبلغ", min_value=0.0, step=0.5)
        settled = st.selectbox("تمت التسوية؟", ["لا", "نعم"])
    with col2:
        movement_type = st.selectbox("نوع الحركة", ["مدين", "دائن"])
        note = st.text_area("البيان")
        entry_date = st.date_input("تاريخ التسجيل", datetime.today().date())
        return_date = st.date_input("تاريخ العودة", datetime.today().date() + timedelta(days=30))
    
    submitted = st.form_submit_button("💾 تسجيل العهدة")

if submitted:
    attachment_path = ""
    if uploaded_file := st.file_uploader("اختيار المرفق", type=["pdf", "png", "jpg", "jpeg"]):
        filename = f"{daily_number}_{uploaded_file.name}"
        attachment_path = os.path.join("attachments", filename)
        with open(attachment_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    new_row = {
        "مرفق": attachment_path,
        "رقم اليومية": daily_number,
        "التاريخ": entry_date,
        "اسم المستفيد": name,
        "نوع العهدة": ouda_type,
        "البيان": note,
        "المبلغ": amount,
        "نوع الحركة (مدين/دائن)": movement_type,
        "تاريخ العودة": return_date,
        "تمت التسوية؟": settled,  # التصحيح هنا: إضافة فاصلة
    }
    
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(EXCEL_PATH, index=False)
    st.success("✅ تم التسجيل بنجاح")
    st.rerun()

# 🔔 التنبيهات والملخصات
st.subheader("⏰ العهد المتأخرة")
if all(col in df.columns for col in ["تمت التسوية؟", "تاريخ العودة"]):
    today = pd.to_datetime(datetime.today().date())
    overdue = df[(df["تمت التسوية؟"] == "لا") & (pd.to_datetime(df["تاريخ العودة"]) < today)]
    if not overdue.empty:
        st.warning(f"⚠️ عدد العهد المتأخرة: {len(overdue)}")
        st.dataframe(overdue)
        send_telegram_alert(f"تنبيه! {len(overdue)} عهدة متأخرة")
    else:
        st.success("✅ لا توجد عهدة متأخرة")
else:
    st.error("❌ الأعمدة المطلوبة غير موجودة")

st.subheader("📊 ملخص حسب النوع")
st.dataframe(df.groupby("نوع العهدة")["المبلغ"].sum().reset_index())

with st.expander("📄 عرض السجل الكامل"):
    st.dataframe(df)

st.subheader("💸 ملخص التسوية")
try:
    summary = df.groupby(["اسم المستفيد", "نوع الحركة (مدين/دائن)"])["المبلغ"].sum().unstack(fill_value=0)
    summary["المتبقي"] = summary["مدين"] - summary["دائن"]
    st.dataframe(summary)
    
    if not summary[summary["المتبقي"] > 0].empty:
        st.warning("🟠 موظفون لديهم أرصدة غير مسددة")
    else:
        st.success("✅ جميع الحسابات مسددة")
except KeyError:
    st.error("❌ بيانات الحركات غير مكتملة")
