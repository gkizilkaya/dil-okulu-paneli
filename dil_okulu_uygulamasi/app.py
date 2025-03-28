import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import tempfile
import os
import unicodedata

# Google Sheets'e bağlanmak için yetki
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
import json  # kodun başında olmalı
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gspread"], scope)

client = gspread.authorize(creds)

# Google Sheet ID (Paylaşılmış tabloya özel ID)
sheet_id = "1w7TuaR-K6jW1c-Kkue7lip6_b82ijnqytoyS4UErJJw"
df = pd.DataFrame(client.open_by_key(sheet_id).sheet1.get_all_records())

st.set_page_config(page_title="Dil Okulu Danışman Paneli")
st.title("📘 Öğrenciye Uygun Yaz Okulu Programı Bul")

# Kullanıcıdan bilgiler al
age = st.number_input("Öğrencinin Yaşı", min_value=5, max_value=99, step=1)
duration = st.selectbox("Program Süresi (Hafta)", options=["2", "3", "4", "6", "8+", "24 hafta"])
season = st.radio("Sezon Türü", options=["Standard", "High"])
student_name = st.text_input("Öğrenci Adı")
consultant_name = st.text_input("Danışman Adı")

# Yardımcı fonksiyonlar
def clean_text(text):
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")

def age_in_range(row, age):
    try:
        row = row.lower().strip()
        if "yeti" in row:
            return age >= 18
        elif "+" in row:
            base_age = int(row.replace("+", "").strip())
            return age >= base_age
        elif "|" in row:
            parts = row.split("|")
            return any(age_in_range(part.strip(), age) for part in parts)
        elif "-" in row:
            min_age, max_age = [int(x.strip()) for x in row.split("-")]
            return min_age <= age <= max_age
        else:
            return False
    except:
        return False

# Filtreleme
df["Yaş Aralığı"] = df["Yaş Aralığı"].astype(str)
filtered = df[df["Yaş Aralığı"].apply(lambda x: age_in_range(x, age))]
if duration != "8+":
    filtered = filtered[filtered["Süre (Ders/Hafta)"].astype(str).str.contains(duration, na=False)]

price_col = "Standard Season (€)" if season == "Standard" else "High Season (€)"

st.subheader("🎯 Uygun Programlar")

if filtered.empty:
    st.warning("Belirtilen kriterlere uygun program bulunamadı.")
else:
    st.dataframe(filtered[["Program Adı", "Yaş Aralığı", "Süre (Ders/Hafta)", price_col, "Sezon Tarihi", "Açıklama"]])

    if st.button("📄 PDF Teklifi Oluştur"):
        pdf = FPDF()
        pdf.add_page()

        # Başlık kutusu ve bilgiler
        pdf.set_fill_color(230, 230, 250)
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(190, 12, txt="Dil Okulu Teklif Ozeti", ln=True, align="C", fill=True)
        pdf.ln(5)

        pdf.set_font("Arial", size=11)
        pdf.set_text_color(0)
        if student_name:
            pdf.cell(190, 8, txt=f"Ogrenci: {clean_text(student_name)}", ln=True)
        if consultant_name:
            pdf.cell(190, 8, txt=f"Danisman: {clean_text(consultant_name)}", ln=True)
        pdf.ln(5)

        for index, row in filtered.iterrows():
            pdf.set_font("Arial", style="B", size=12)
            pdf.set_text_color(0)
            pdf.cell(200, 10, txt=f"Program: {clean_text(row['Program Adı'])}", ln=True)

            pdf.set_font("Arial", size=11)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(100, 8, txt=f"Yas Araligi: {clean_text(row['Yaş Aralığı'])}", ln=True)
            pdf.cell(100, 8, txt=f"Sure: {clean_text(row['Süre (Ders/Hafta)'])}", ln=True)
            pdf.cell(100, 8, txt=f"Fiyat: {clean_text(row[price_col])} EUR", ln=True)
            pdf.cell(100, 8, txt=f"Sezon: {clean_text(row['Sezon Tarihi'])}", ln=True)

            if row['Açıklama']:
                try:
                    pdf.set_text_color(100, 100, 100)
                    pdf.multi_cell(0, 8, txt=f"Not: {clean_text(row['Açıklama'])}")
                except:
                    pdf.multi_cell(0, 8, txt="Not: (Karakter gosterilemedi)")

            pdf.ln(6)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(6)

        pdf.set_font("Arial", size=10)
        pdf.set_text_color(150, 150, 150)
        pdf.ln(10)
        pdf.cell(200, 10, txt="Bu teklif danismaniniza ozeldir. Fiyatlar bilgilendirme amaclidir.", ln=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name, "F")
            tmp_file_path = tmp_file.name

        with open(tmp_file_path, "rb") as f:
            st.download_button(
                label="📥 PDF Teklifini Indir",
                data=f,
                file_name="ogrenci_teklif.pdf",
                mime="application/pdf"
            )

        os.remove(tmp_file_path)