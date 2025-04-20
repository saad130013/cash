# ... (الاستيرادات والإعدادات الأولية تبقى كما هي)

@st.cache_data
def load_data():
    try:
        if os.path.exists(EXCEL_PATH):
            df = pd.read_excel(EXCEL_PATH)
            # التحقق من وجود جميع الأعمدة المطلوبة
            required_columns = [
                "مرفق", "رقم اليومية", "التاريخ", "اسم المستفيد",
                "نوع العهدة", "البيان", "المبلغ",
                "نوع الحركة (مدين/دائن)", "تاريخ العودة", "تمت التسوية؟"
            ]
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None
            return df
        else:
            return pd.DataFrame(columns=required_columns)
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {str(e)}")
        return pd.DataFrame()

# ... (بقية الأكواد تبقى كما هي حتى قسم التسجيل)

if submitted:
    try:
        attachment_path = ""
        if uploaded_file is not None:
            # إنشاء مجلد المرفقات إذا لم يكن موجودًا
            os.makedirs(attachments_folder, exist_ok=True)
            filename = f"{daily_number}_{uploaded_file.name}"
            attachment_path = os.path.join(attachments_folder, filename)
            with open(attachment_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        new_row = {
            "مرفق": attachment_path,
            "رقم اليومية": daily_number,
            "التاريخ": pd.to_datetime(entry_date),  # تحويل التاريخ لتنسيق مناسب
            "اسم المستفيد": name,
            "نوع العهدة": ouda_type,
            "البيان": note,
            "المبلغ": amount,
            "نوع الحركة (مدين/دائن)": movement_type,
            "تاريخ العودة": pd.to_datetime(return_date),  # تحويل التاريخ
            "تمت التسوية؟": settled
        }

        # إضافة الصف الجديد وإعادة تحميل البيانات
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(EXCEL_PATH, index=False, engine='openpyxl')  # تحديد المحرك
        
        st.success("✅ تم الحفظ بنجاح")
        st.cache_data.clear()  # مسح الذاكرة المؤقتة لإعادة التحميل
        df = load_data()  # إعادة تحميل البيانات المحدثة
        
    except PermissionError:
        st.error("❌ لا يمكن الكتابة إلى الملف. يرجى إغلاق ملف Excel أولاً.")
    except Exception as e:
        st.error(f"❌ حدث خطأ غير متوقع: {str(e)}")
