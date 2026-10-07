# Optimasi Layout Kabin Crew Kapal (versi web)

Algoritma NSGA-II (Python) dengan tampilan web Streamlit.

## Jalankan di komputer sendiri
```
pip install -r requirements.txt
streamlit run app.py
```
Buka http://localhost:8501

## Publikasi gratis (Streamlit Community Cloud)
1. Buat repo di GitHub, upload SEMUA isi folder ini (app.py di root repo).
2. Buka https://share.streamlit.io, login dengan GitHub.
3. Klik **Create app** -> pilih repo & branch -> Main file path: `app.py` -> Deploy.
4. Tunggu beberapa menit, link publik siap dibagikan.

## Struktur
- `app.py`          : tampilan web (Streamlit)
- `web_helper.py`   : penghubung web ke `pipeline.optimasi_layout()`
- `pipeline.py` dkk : logika optimasi (tidak diubah)
- `main.py`         : versi CLI (tetap bisa dipakai: `python main.py`)

## Catatan
- Mode **Cepat** ~10 detik, **Normal** ~40 detik, **Teliti** lebih lama (di laptop).
  Hosting gratis biasanya 2-3x lebih lambat.
- Hasil tiap sesi pengguna terpisah; gambar memakai file sementara unik.
