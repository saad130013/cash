if submitted:
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
        "تمت التسوية؟": settled  # تمت إضافة الفاصلة هنا
    }
    st.write("🚧 البيانات المُرسلة:")
    st.json(new_row)  # حذف القوس الإضافي
    
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)  # إصلاح الأقواس
    df.to_excel(EXCEL_PATH, index=False)
    st.success("✅ تم تسجيل العهدة بنجاح")
    st.rerun()
