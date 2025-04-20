# 📲 إرسال تنبيه عبر Telegram عند وجود عهد متأخرة
import requests

def send_telegram_alert(message):
    token = "8064722037:AAFjn6v_d8fGj0mBAfezOpndKHV4LBFd1HI"
    chat_id = "961480270"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            st.toast("📤 تم إرسال تنبيه عبر Telegram")
    except Exception as e:
        st.error(f"خطأ في إرسال التنبيه: {e}")


import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="نظام تسجيل العهد", layout="wide")
st.title("📘 نظام تسجيل العُهد وتتبعها")

EXCEL_PATH = "دفتر_العهد_المنظم.xlsx"

# تحميل البيانات من الملف
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

# ✅ نموذج إدخال جديد
# تحميل النماذج
import joblib
text_model = joblib.load("text_classifier_model.joblib")

from sklearn.ensemble import IsolationForest
# تدريب نموذج كشف الشذوذ مباشرة عند التشغيل
anomaly_model = IsolationForest(contamination=0.2, random_state=42)
sample_amounts = [[100], [150], [200], [180], [160], [250], [220], [190], [175], [130], [4000], [5000]]
anomaly_model.fit(sample_amounts)

# التصنيف وكشف الشذوذ
if "note" in locals() and note:
    predicted_type = text_model.predict([note])[0]
    st.info(f"📌 التصنيف المقترح: {predicted_type}")

if "amount" in locals() and amount > 0:
    anomaly_flag = anomaly_model.predict([[amount]])[0]
    if anomaly_flag == -1:
        st.warning("⚠️ المبلغ خارج النطاق الطبيعي!")

# 📤 رفع المرفقات
st.markdown("**📎 رفع مرفق (اختياري):**")
uploaded_file = st.file_uploader("اختيار الملف", type=["pdf", "png", "jpg", "jpeg"])

attachments_folder = "attachments"
if not os.path.exists(attachments_folder):
    os.makedirs(attachments_folder)

# 📥 نموذج التسجيل
st.subheader("تسجيل عهدة جديدة")
with st.form("entry_form"):
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
    
    submitted = st.form_submit_button("💾 حفظ")

    if submitted:
        # حفظ المرفق
        attachment_path = ""
        if uploaded_file:
            filename = f"{daily_number}_{uploaded_file.name}"
            attachment_path = os.path.join(attachments_folder, filename)
            with open(attachment_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        
        # إضافة الصف الجديد
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
            "تمت التسوية؟": settled
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(EXCEL_PATH, index=False)
        st.success("✅ تم الحفظ بنجاح")
        st.rerun()

# 🔔 التنبيهات
st.subheader("⏰ العهد المتأخرة")
if "تمت التسوية؟" in df.columns and "تاريخ العودة" in df.columns:
    today = pd.to_datetime(datetime.today().date())
    overdue = df[(df["تمت التسوية؟"] == "لا") & (pd.to_datetime(df["تاريخ العودة"]) < today)]
    if not overdue.empty:
        st.warning(f"⚠️ عدد العهد المتأخرة: {len(overdue)}")
        st.dataframe(overdue)
        send_telegram_alert(f"تنبيه! {len(overdue)} عهدة متأخرة")
    else:
        st.success("✅ لا توجد عهدة متأخرة")
else:
    st.info("ℹ️ البيانات المطلوبة غير متوفرة")

# 📊 الملخصات
st.subheader("📊 ملخص حسب النوع")
st.dataframe(df.groupby("نوع العهدة")["المبلغ"].sum().reset_index())

with st.expander("عرض السجل الكامل"):
    st.dataframe(df)

# 💸 تسوية الحسابات
st.subheader("ملخص التسوية")
summary = df.groupby(["اسم المستفيد", "نوع الحركة (مدين/دائن)"])["المبلغ"].sum().unstack(fill_value=0)
summary["المتبقي"] = summary["مدين"] - summary["دائن"]
st.dataframe(summary)

if not summary[summary["المتبقي"] > 0].empty:
    st.warning("🟠 موظفون لديهم أرصدة غير مسددة")
else:
    st.success("✅ جميع الحسابات مسددة")
