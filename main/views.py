from django.shortcuts import redirect, render, HttpResponse
from django.contrib.auth.decorators import login_required
import os
import tempfile
from django.urls import reverse_lazy
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract

import re
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
import datetime
from .models import KategoriSoal


# Load model sekali saat server start
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Cache embedding untuk mempercepat, optional tapi disarankan
embedding_cache = {}

def normalize_text(text):
    # Lowercase, remove multiple spaces, strip, remove some punctuation for better matching
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # hilangkan tanda baca
    text = re.sub(r'\s+', ' ', text)  # normalize spasi
    return text.strip()

def get_embedding(text):
    norm_text = normalize_text(text)
    if norm_text not in embedding_cache:
        embedding_cache[norm_text] = model.encode(norm_text, convert_to_tensor=True)
    return embedding_cache[norm_text]

def classify_similarity(score):
    # Skor similarity [0..1], ubah jadi klasifikasi teks dan skor 1-5
    if score < 0.3:
        return "Sangat Tidak Relevan", 1
    elif score < 0.5:
        return "Tidak Relevan", 2
    elif score < 0.7:
        return "Sedang", 3
    elif score < 0.85:
        return "Relevan", 4
    else:
        return "Sangat Relevan", 5

@login_required(login_url=reverse_lazy('login'))
def home(request):
    getKategori = KategoriSoal.objects.all()
    return render(request, 'index.html', {
        'numbers': range(1, 6),
        'getKategori': getKategori
        })


def extract_pdf_with_ocr(file):
    images = convert_from_bytes(file.read())
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img, lang='ind') + "\n"
    return normalize_text(text)


def extract_pdf_text(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
        temp_file_path = temp_file.name

    with pdfplumber.open(temp_file_path) as pdf:
        texts = []
        for page in pdf.pages:
            txt = page.extract_text()
            if txt and len(txt.strip()) > 30:  # Hanya ambil halaman dengan isi signifikan
                texts.append(txt)
    
    os.remove(temp_file_path)
    clean_text = "\n".join(texts)
    return normalize_text(clean_text)



def clean_noise(text):
    text = re.sub(r'halaman\s+\d+', '', text, flags=re.IGNORECASE)  # hapus 'halaman x'
    text = re.sub(r'sumber:\s+.*', '', text)  # hapus 'sumber:...'
    text = re.sub(r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b', '', text)  # hapus tanggal
    return text


def extract_csv_context():
    """Ekstrak konteks dari dataset CSV untuk pengayaan embedding"""
    csv_path = os.path.join("media", "dataset", "dts_hasil_prediksi_jawaban.csv")
    if os.path.isfile(csv_path):
        try:
            df = pd.read_csv(csv_path)
            df.columns = df.columns.str.lower()  # ubah semua kolom ke lowercase

            # Cek apakah kolom yang diperlukan tersedia
            required_cols = ['soal', 'jawaban_kunci', 'jawaban_siswa']
            if all(col in df.columns for col in required_cols):
                combined_text = " ".join(
                    df['soal'].astype(str) + " " +
                    df['jawaban_kunci'].astype(str) + " " +
                    df['jawaban_siswa'].astype(str)
                )
                return normalize_text(combined_text)
            else:
                print("[WARNING] CSV tidak memiliki kolom lengkap: 'soal', 'jawaban_kunci', 'jawaban_siswa'")
                return ""
        except Exception as e:
            print(f"[ERROR] Gagal membaca CSV referensi: {e}")
            return ""
    else:
        print("[INFO] File CSV tidak ditemukan, abaikan sebagai referensi.")
        return ""


def pembandinganJawaban(request):
    if request.method == 'POST':
        jumlah_soal = int(request.POST.get('jumlah-soal', 0))
        kategori = request.POST.get('kategori', '').strip()
        pdf_file = request.FILES.get('file_pdf')

        soal_list = [request.POST.get(f'soal_{i}', '').strip() for i in range(1, jumlah_soal + 1)]
        kunci_list = [request.POST.get(f'kunci_{i}', '').strip() for i in range(1, jumlah_soal + 1)]
        siswa_list = [request.POST.get(f'jawaban_{i}', '').strip() for i in range(1, jumlah_soal + 1)]

        # Referensi tambahan
        referensi_pdf = extract_pdf_text(pdf_file) if pdf_file else ""
        referensi_csv = extract_csv_context()

        # Gabungan referensi semantik: kategori + PDF + dataset CSV
        referensi_semantik = normalize_text(f"{kategori} {referensi_pdf} {referensi_csv}")
        
        # Simpan embedding PDF ke cache global (opsional tapi efisien)
        if 'pdf_ref' not in embedding_cache:
            embedding_cache['pdf_ref'] = model.encode(referensi_pdf, convert_to_tensor=True)

        if 'semantik_ref' not in embedding_cache:
            embedding_cache['semantik_ref'] = model.encode(referensi_semantik, convert_to_tensor=True)


        hasil_list = []
        total_score = 0

        for i, (soal, kunci, siswa) in enumerate(zip(soal_list, kunci_list, siswa_list), start=1):
            norm_kunci = normalize_text(kunci)
            norm_siswa = normalize_text(siswa)

            # Embedding enriched with context
            emb_kunci = get_embedding(norm_kunci + " " + referensi_semantik)
            emb_siswa = get_embedding(norm_siswa + " " + referensi_semantik)

            similarity = util.pytorch_cos_sim(emb_kunci, emb_siswa).item()
            tingkat, skor = classify_similarity(similarity)

            total_score += skor
            hasil_list.append({
                "no": i,
                "soal": soal,
                "jawaban_kunci": kunci,
                "jawaban_siswa": siswa,
                "skor_similaritas": round(similarity, 4),
                "klasifikasi": tingkat,
                "skor": skor,
            })

        nilai_akhir = round((total_score / (len(soal_list) * 5)) * 100, 2)

        # Simpan ke CSV
        df = pd.DataFrame(hasil_list)
        output_dir = os.path.join("media", "dataset")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "dts_hasil_prediksi_jawaban.csv")
        file_exists = os.path.isfile(output_path)
        df.to_csv(output_path, mode='a', index=False, encoding='utf-8-sig', header=not file_exists)

        request.session['hasilNilai'] = hasil_list
        request.session['nilai_akhir'] = nilai_akhir

        return redirect('kesimpulanViews')

    return render(request, 'index.html', {'numbers': range(1, 6)})




def kesimpulanViews(request):
    hasil = request.session.get('hasilNilai', [])
    nilai_akhir = request.session.get('nilai_akhir', 0)
    return render(request, 'result.html', {'hasil': hasil, 'nilai_akhir': nilai_akhir})
    