
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
            "رقم اليومية", "التاريخ", "اسم المستفيد", "نوع العهدة",
            "البيان", "المبلغ", "نوع الحركة (مدين/دائن)", "تاريخ العودة", "تمت التسوية؟"
        ])

df = load_data()

# 🔍 تصفية حسب التاريخ
st.sidebar.header("🗂️ تصفية العهد حسب التاريخ")
start_date = st.sidebar.date_input("من تاريخ", value=datetime.today().replace(day=1))
end_date = st.sidebar.date_input("إلى تاريخ", value=datetime.today())
df = df[(pd.to_datetime(df["التاريخ"]) >= pd.to_datetime(start_date)) & (pd.to_datetime(df["التاريخ"]) <= pd.to_datetime(end_date))]


# ✅ نموذج إدخال جديد

# تحميل النماذج
import joblib
text_model = joblib.load("text_classifier_model.joblib")

from sklearn.ensemble import IsolationForest
# تدريب نموذج كشف الشذوذ مباشرة عند التشغيل
anomaly_model = IsolationForest(contamination=0.2, random_state=42)
# بيانات تدريب مبسطة
sample_amounts = [[100], [150], [200], [180], [160], [250], [220], [190], [175], [130], [4000], [5000]]
anomaly_model.fit(sample_amounts)


# تصنيف البيان عند الإدخال
if "note" in locals() and note:
    predicted_type = text_model.predict([note])[0]
    st.info(f"📌 التصنيف المقترح للبيان: {predicted_type}")

# كشف الشذوذ في المبلغ
if "amount" in locals() and amount > 0:
    anomaly_flag = anomaly_model.predict([[amount]])[0]
    if anomaly_flag == -1:
        st.warning("⚠️ المبلغ المُدخل خارج النطاق المعتاد (قيمة شاذة). يُرجى التأكد.")

# 📤 رفع مرفق (اختياري)
st.markdown("**📎 يمكن رفع ملف مرفق لكل عهدة (PDF أو صورة):**")
uploaded_file = st.file_uploader("اختيار المرفق", type=["pdf", "png", "jpg", "jpeg"])

attachments_folder = "attachments"
if not os.path.exists(attachments_folder):
    os.makedirs(attachments_folder)

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
        today = datetime.today().date()
        entry_date = st.date_input("تاريخ التسجيل", value=today)
        return_date = st.date_input("تاريخ العودة", value=today + timedelta(days=30))

    submitted = st.form_submit_button("💾 تسجيل العهدة")

    
if submitted:
    # حفظ المرفق إن وُجد
    attachment_path = ""
    if uploaded_file is not None:
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
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(EXCEL_PATH, index=False)
        st.success("✅ تم تسجيل العهدة بنجاح")

        st.experimental_rerun()  # يعيد تحميل النموذج ويفرّغه بعد التسجيل

# 🔔 تنبيهات العهد المتأخرة
st.subheader("⏰ العهد المتأخرة عن التسوية")
today = pd.to_datetime(datetime.today().date())
if "تمت التسوية؟" in df.columns and "تاريخ العودة" in df.columns:
    overdue = df[(df["تمت التسوية؟"] == "لا") & (pd.to_datetime(df["تاريخ العودة"]) < today)]

if not overdue.empty:
    st.warning(f"⚠️ هناك {len(overdue)} عهدة/عُهد تجاوزت تاريخ العودة ولم تُسدد:")
    st.dataframe(overdue)
else:
    st.success("✅ لا توجد عهد متأخرة حالياً.")

# 📊 ملخص تحليلي
st.subheader("📊 ملخص العهد حسب النوع")
summary = df.groupby("نوع العهدة")["المبلغ"].sum().reset_index()
st.dataframe(summary)

# عرض كامل السجل
with st.expander("📄 عرض جميع العهد"):
    st.dataframe(df)

# 📉 تسوية العهد تلقائيًا
st.subheader("💸 ملخص التسوية حسب المستفيد")

# حساب الصرف (مدين) مقابل السداد (دائن)
summary_by_name = df.groupby(["اسم المستفيد", "نوع الحركة (مدين/دائن)"])["المبلغ"].sum().unstack(fill_value=0)
summary_by_name["المتبقي"] = summary_by_name.get("مدين", 0) - summary_by_name.get("دائن", 0)
summary_by_name = summary_by_name.reset_index()

st.dataframe(summary_by_name)

# قائمة الموظفين الذين لديهم مبالغ غير مسددة
unsettled = summary_by_name[summary_by_name["المتبقي"] > 0]
if not unsettled.empty:
    st.warning("🟠 الموظفون الذين لديهم عُهد غير مسددة:")
    st.dataframe(unsettled[["اسم المستفيد", "المتبقي"]])
else:
    st.success("✅ جميع العُهد تمت تسويتها.")
