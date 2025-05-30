from django.shortcuts import redirect, render, HttpResponse
from django.contrib.auth.decorators import login_required
import os
import tempfile
import pdfplumber
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage

from .models import KategoriSoal


# Load model sekali
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')


def kesimpulanViews(request):
    hasil = request.session.get('hasilNilai', [])
    nilai_akhir = request.session.get('nilai_akhir', 0)
    context = {
        'hasil': hasil,
        'nilai_akhir': nilai_akhir
    }
    return render(request, 'result.html', context)


def extract_pdf_sentences(pdf_path):
    words = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts = [s.strip() for s in text.replace('\n', ' ').split('.') if len(s.strip().split()) >= 1]
                words.extend(parts)
    return words

@login_required
def home(request):
    kategori = KategoriSoal.objects.all()
    context = {
        'getKategori' : kategori
    }
    return render(request, 'index.html', context)

def classify_similarity(score):
    if score <= 0.20:
        return "Sangat Tidak Relevan", 1
    elif score <= 0.40:
        return "Tidak Relevan", 2
    elif score <= 0.60:
        return "Sedang", 3
    elif score <= 0.80:
        return "Relevan", 4
    else:
        return "Sangat Relevan", 5

def evaluate_with_pdf_context(soal_list, kunci_list, siswa_list, pdf_sentences, threshold=0.80):
    results = []
    total_score = 0

    for i in range(len(soal_list)):
        soal = soal_list[i]
        kunci = kunci_list[i]
        siswa = siswa_list[i]

        e_kunci = model.encode(kunci, convert_to_tensor=True)
        e_siswa = model.encode(siswa, convert_to_tensor=True)
        sim_kunci_siswa = util.pytorch_cos_sim(e_kunci, e_siswa).item()

        # Ambil klasifikasi dan skor
        tingkat, skor = classify_similarity(sim_kunci_siswa)
        total_score += skor

        status = "Cocok" if sim_kunci_siswa >= threshold else "Tidak cocok"

        sim_from_pdf = 0.0
        for kal_pdf in pdf_sentences:
            e_pdf = model.encode(kal_pdf, convert_to_tensor=True)
            sim_pdf = util.pytorch_cos_sim(e_kunci, e_pdf).item()
            sim_siswa_pdf = util.pytorch_cos_sim(e_pdf, e_siswa).item()
            if sim_pdf >= threshold and sim_siswa_pdf >= threshold:
                sim_from_pdf = max(sim_from_pdf, (sim_pdf + sim_siswa_pdf) / 2)

        if sim_kunci_siswa < threshold and sim_from_pdf >= threshold:
            status = "Cocok (berdasarkan konteks PDF)"

        results.append({
            "no": i + 1,
            "soal": soal,
            "jawaban_kunci": kunci,
            "jawaban_siswa": siswa,
            "similaritas_kunci_siswa": round(sim_kunci_siswa, 4),
            "similaritas_pdf": round(sim_from_pdf, 4),
            "tingkat_relevansi": tingkat,
            "skor": skor,
            "status": status
        })

    nilai_akhir = round((total_score / (len(soal_list) * 5)) * 100, 2)  # Skor maksimal = 5 * jumlah soal
    return results, nilai_akhir



def pembandinganJawaban(request):
    if request.method == 'POST':
        jumlahSoal = int(request.POST.get('jumlah-soal', 0))
        kategori = request.POST.get('kategori')
        file_pdf = request.FILES.get('file-pdf')
        

        # Simpan file sementara
        temp_path = None
        if file_pdf:
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, file_pdf.name)
            with open(temp_path, 'wb+') as destination:
                for chunk in file_pdf.chunks():
                    destination.write(chunk)

        # Ambil soal dan jawaban
        soal_list = []
        jawaban_kunci = []
        jawaban_siswa = []

        for i in range(1, jumlahSoal + 1):
            soal = request.POST.get(f'soal_{i}', '').strip()
            kunci = request.POST.get(f'kunci_{i}', '').strip()
            siswa = request.POST.get(f'jawaban_{i}', '').strip()

            soal_list.append(soal)
            jawaban_kunci.append(kunci)
            jawaban_siswa.append(siswa)

        # Ekstrak teks dari PDF
        pdf_sentences = extract_pdf_sentences(temp_path) if temp_path else []

        # Evaluasi
        hasil = evaluate_with_pdf_context(soal_list, jawaban_kunci, jawaban_siswa, pdf_sentences)
        print("=== DEBUG hasil ===")
        print(type(hasil))
        print(hasil)

        # Pisahkan hasil dari fungsi evaluasi
        data_hasil, nilai_akhir = hasil  # hasil = (list of dict, nilai akhir float)

        # Hitung total skor dan nilai akhir
        total_skor = sum(item['skor'] for item in data_hasil)
        maks_skor = len(data_hasil) * 5
        nilai_akhir = round((total_skor / maks_skor) * 100, 2)
        request.session['hasilNilai'] = hasil[0]  # list of dicts
        request.session['nilai_akhir'] = nilai_akhir

        context = {
            'soalData': soal_list,
            'jawabanKunci': jawaban_kunci,
            'jawabanSiswa': jawaban_siswa,
            'skor': hasil,
            'nilaiAkhir': nilai_akhir
        }

        print("\n=== Data Hasil Kesimpulan ===")
        for key, value in context.items():
            print(f"{key}:")
            if isinstance(value, list):
                for i, item in enumerate(value, 1):
                    print(f"  {i}.")
                    if isinstance(item, dict):
                        for k, v in item.items():
                            print(f"     {k}: {v}")
                    else:
                        print(f"     {item}")  # jika bukan dict
            else:
                print(f"  {value}")
        return redirect('kesimpulanViews')
        
    # return HttpResponse("Ok");

    