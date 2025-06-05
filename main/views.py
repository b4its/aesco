from django.shortcuts import redirect, render, HttpResponse
from django.contrib.auth.decorators import login_required
import os
import tempfile
from django.urls import reverse_lazy
import pdfplumber
import re
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage

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
    return render(request, 'index.html', {'numbers': range(1, 6)})

def evaluate_answers(soal_list, kunci_list, siswa_list, threshold=0.7):
    results = []
    total_score = 0
    for i, (soal, kunci, siswa) in enumerate(zip(soal_list, kunci_list, siswa_list), start=1):
        norm_kunci = normalize_text(kunci)
        norm_siswa = normalize_text(siswa)

        # Cek exact match sebagai shortcut (case insensitive dan normalisasi)
        if norm_kunci == norm_siswa and norm_kunci != '':
            skor = 5
            tingkat = "Sangat Relevan (Exact Match)"
            similarity = 1.0
        else:
            e_kunci = get_embedding(norm_kunci)
            e_siswa = get_embedding(norm_siswa)
            similarity = util.pytorch_cos_sim(e_kunci, e_siswa).item()
            tingkat, skor = classify_similarity(similarity)

        total_score += skor
        results.append({
            "no": i,
            "soal": soal,
            "jawaban_kunci": kunci,
            "jawaban_siswa": siswa,
            "similaritas": round(similarity, 4),
            "klasifikasi": tingkat,
            "skor": skor,
        })

    nilai_akhir = round((total_score / (len(soal_list) * 5)) * 100, 2)
    return results, nilai_akhir

def pembandinganJawaban(request):
    if request.method == 'POST':
        jumlah_soal = int(request.POST.get('jumlah-soal', 0))

        soal_list = [request.POST.get(f'soal_{i}', '').strip() for i in range(1, jumlah_soal + 1)]
        kunci_list = [request.POST.get(f'kunci_{i}', '').strip() for i in range(1, jumlah_soal + 1)]
        siswa_list = [request.POST.get(f'jawaban_{i}', '').strip() for i in range(1, jumlah_soal + 1)]

        hasil_list, nilai_akhir = evaluate_answers(soal_list, kunci_list, siswa_list)

        request.session['hasilNilai'] = hasil_list
        request.session['nilai_akhir'] = nilai_akhir

        return redirect('kesimpulanViews')

    return render(request, 'index.html', {'numbers': range(1, 6)})

def kesimpulanViews(request):
    hasil = request.session.get('hasilNilai', [])
    nilai_akhir = request.session.get('nilai_akhir', 0)
    return render(request, 'result.html', {'hasil': hasil, 'nilai_akhir': nilai_akhir})
    