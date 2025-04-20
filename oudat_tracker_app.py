
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import requests
import joblib
from sklearn.ensemble import IsolationForest

# إرسال تنبيه Telegram
def send_telegram_alert(message):
    token = "8064722037:AAFjn6v_d8fGj0mBAfezOpndKHV4LBFd1HI"
    chat_id = "961480270"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=payload)
    except Exception as e:
        st.error(f"Telegram Error: {e}")

st.set_page_config(page_title="نظام تسجيل العهد", layout="wide")
st.title("📘 نظام تسجيل العُهد وتتبعها")

EXCEL_PATH = "دفتر_العهد_المنظم.xlsx"

@st.cache_data
def load_data():
    if os.path.exists(EXCEL_PATH):
        return pd.read_excel(EXCEL_PATH)
    else:
        return pd.DataFrame(columns=[
            "مرفق", "رقم اليومية", "التاريخ", "اسم المستفيد", "نوع العهدة",
            "البيان", "المبلغ", "نوع الحركة (مدين/دائن)", "تاريخ العودة", "تمت التسوية؟"
        ])

df = load_data()

# التصفية
st.sidebar.header("🗂️ تصفية العهد حسب التاريخ")
start_date = st.sidebar.date_input("من تاريخ", value=datetime.today().replace(day=1))
end_date = st.sidebar.date_input("إلى تاريخ", value=datetime.today())
df = df[(pd.to_datetime(df["التاريخ"]) >= pd.to_datetime(start_date)) & (pd.to_datetime(df["التاريخ"]) <= pd.to_datetime(end_date))]

# النموذج الذكي
text_model = joblib.load("text_classifier_model.joblib")
anomaly_model = IsolationForest(contamination=0.2, random_state=42)
anomaly_model.fit([[100], [200], [300], [150], [4000], [5000]])

st.markdown("**📎 يمكن رفع مرفق:**")
uploaded_file = st.file_uploader("اختيار مرفق", type=["pdf", "png", "jpg", "jpeg"])
attachments_folder = "attachments"
os.makedirs(attachments_folder, exist_ok=True)

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
        entry_date = st.date_input("تاريخ التسجيل", value=datetime.today())
        return_date = st.date_input("تاريخ العودة", value=datetime.today() + timedelta(days=30))
    submitted = st.form_submit_button("💾 تسجيل العهدة")

if submitted:
    attachment_path = ""
    if uploaded_file:
        filename = f"{daily_number}_{uploaded_file.name}"
        attachment_path = os.path.join(attachments_folder, filename)
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
        "تمت التسوية؟": settled
    }

    st.write("🚧 البيانات المُرسلة:")
    st.json(new_row)

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(EXCEL_PATH, index=False)
    st.success("✅ تم تسجيل العهدة بنجاح")
    with st.expander("📌 العهدة المسجلة الآن:"):
        st.dataframe(pd.DataFrame([new_row]))

# تنبيهات العهد المتأخرة
st.subheader("⏰ العهد المتأخرة عن التسوية")
if "تمت التسوية؟" in df.columns and "تاريخ العودة" in df.columns:
    today = pd.to_datetime(datetime.today().date())
    overdue = df[(df["تمت التسوية؟"] == "لا") & (pd.to_datetime(df["تاريخ العودة"]) < today)]
    if not overdue.empty:
        st.warning(f"⚠️ يوجد {len(overdue)} عهدة متأخرة:")
        st.dataframe(overdue)
        send_telegram_alert(f"🚨 يوجد {len(overdue)} عهدة متأخرة لم يتم تسويتها!")
    else:
        st.success("✅ لا توجد عهد متأخرة حالياً.")

# ملخص حسب النوع
st.subheader("📊 ملخص العهد حسب النوع")
summary = df.groupby("نوع العهدة")["المبلغ"].sum().reset_index()
st.dataframe(summary)

# ملخص التسوية حسب المستفيد
st.subheader("💸 ملخص التسوية حسب المستفيد")
if "نوع الحركة (مدين/دائن)" in df.columns:
    summary_by_name = df.groupby(["اسم المستفيد", "نوع الحركة (مدين/دائن)"])["المبلغ"].sum().unstack(fill_value=0)
    summary_by_name["المتبقي"] = summary_by_name.get("مدين", 0) - summary_by_name.get("دائن", 0)
    summary_by_name = summary_by_name.reset_index()
    st.dataframe(summary_by_name)

    unsettled = summary_by_name[summary_by_name["المتبقي"] > 0]
    if not unsettled.empty:
        st.warning("🟠 الموظفون الذين لديهم عُهد غير مسددة:")
        st.dataframe(unsettled[["اسم المستفيد", "المتبقي"]])
    else:
        st.success("✅ جميع العهد تمت تسويتها.")
else:
    st.info("ℹ️ لا يمكن عرض ملخص التسوية لعدم وجود عمود 'نوع الحركة (مدين/دائن)'.")
