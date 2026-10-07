"""
web_helper.py
Lapisan penghubung antara tampilan web (app.py) dan optimasi (pipeline.py).
Sengaja dipisah dari app.py supaya bisa dites tanpa Streamlit, dan supaya
file inti (pipeline.py dkk.) TIDAK perlu diubah sama sekali.
"""

import os
import tempfile

import matplotlib
matplotlib.use("Agg")  # backend tanpa layar, wajib untuk server
import matplotlib.pyplot as plt

from pipeline import optimasi_layout

# Preset kecepatan. "Normal" = nilai bawaan pipeline.optimasi_layout().
PRESET = {
    "Cepat":  dict(ukuran_populasi=40, jumlah_generasi=40, jumlah_restart=1, jumlah_sampel_acak=1000),
    "Normal": dict(ukuran_populasi=80, jumlah_generasi=80, jumlah_restart=2, jumlah_sampel_acak=3000),
    "Teliti": dict(ukuran_populasi=100, jumlah_generasi=120, jumlah_restart=3, jumlah_sampel_acak=5000),
}


def bangun_input(panjang, lebar, tinggi, dinding_pintu, dinding_jendela, furnitures, jenis_crew) -> dict:
    """Susun dict dengan format yang sama persis seperti main.py / contoh_penggunaan.py."""
    return {
        "room": {"panjang": float(panjang), "lebar": float(lebar), "tinggi": float(tinggi)},
        "pintu": {"dinding": dinding_pintu},
        "jendela": {"dinding": dinding_jendela} if dinding_jendela else None,
        "furnitures": furnitures,
        "jenis_crew": jenis_crew,
    }


def validasi(data: dict) -> list:
    """Kembalikan daftar pesan error (kosong = input aman dijalankan)."""
    error = []
    room = data["room"]
    if room["panjang"] <= 0 or room["lebar"] <= 0:
        error.append("Panjang dan lebar ruangan harus lebih dari 0.")
    if not any(f["jenis"] == "bed" for f in data["furnitures"]):
        error.append("Minimal harus ada 1 bed (jumlah crew dihitung dari kapasitas bed).")
    return error


def jalankan(data: dict, preset: str = "Normal", jumlah_alternatif: int = 3):
    """
    Jalankan optimasi. Return (hasil_dict, png_bytes).
    Gambar ditulis ke file sementara yang UNIK per pemanggilan, jadi aman
    kalau beberapa pengguna menjalankan optimasi bersamaan.
    """
    parameter = PRESET[preset]
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        hasil = optimasi_layout(
            data,
            jumlah_alternatif=jumlah_alternatif,
            simpan_gambar_ke=path,
            **parameter,
        )
        png_bytes = None
        if hasil.get("gambar") and os.path.exists(path):
            with open(path, "rb") as f:
                png_bytes = f.read()
    finally:
        plt.close("all")  # lepaskan memori figure matplotlib
        if os.path.exists(path):
            os.remove(path)
    return hasil, png_bytes
