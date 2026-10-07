"""
sensitivity_test.py
Uji sensitivitas: untuk satu set furniture kabin 2 crew yang tetap, coba
beberapa ukuran ruang (panjang bervariasi, lebar tetap) dan catat mana yang
benar-benar berhasil ditemukan layout valid-nya oleh NSGA-II.

Tujuan: membuktikan bahwa standar MLC 2006 (yang cuma mensyaratkan LUAS
minimum, mis. 7.5 m2 utk 2 crew) belum tentu menjamin furniture-nya bisa
benar-benar disusun dengan clearance yang benar - ada "luas minimum praktis"
yang bisa lebih besar dari luas minimum standar.

CATATAN PENTING (kejujuran ilmiah): NSGA-II itu stokastik dan generasi/
populasinya terbatas di sini demi kecepatan uji. Hasil "GAGAL" di sini
berarti "algoritma tidak menemukan solusi valid dalam anggaran generasi
yang diberikan", BUKAN bukti matematis bahwa ruangan itu pasti mustahil -
bisa saja berhasil kalau generasi/populasinya ditambah lagi.

TEMUAN DARI PENGUJIAN SEBELUMNYA: kasus 6-furniture (18 variabel keputusan,
beberapa jenis clearance sekaligus) butuh anggaran JAUH lebih besar (>=200
populasi, >=350-500 generasi) dibanding kasus 2-furniture sederhana
(cukup 60 populasi, 100 generasi). Ini bukan bug - ini "curse of
dimensionality" yang lazim di optimasi kombinatorial: makin banyak
variabel keputusan & constraint yang harus dipenuhi BERSAMAAN, makin
besar ruang pencarian yang harus dijelajahi algoritma.
"""

import time
import random
import matplotlib.pyplot as plt

from pipeline import optimasi_layout

FURNITURES = [
    {"jenis": "bed", "jumlah": 2},
    {"jenis": "lemari", "jumlah": 2},
    {"jenis": "meja", "jumlah": 1},   # kursi otomatis
]
LEBAR_TETAP = 2.5
LUAS_MIN_MLC = 7.5  # standar MLC utk 2 crew (m2) - lihat constants.py


def buat_data_input(panjang: float) -> dict:
    return {
        "room": {"panjang": panjang, "lebar": LEBAR_TETAP, "tinggi": 2.4},
        "pintu": {"dinding": "depan"},
        "jendela": {"dinding": "kanan"},
        "furnitures": FURNITURES,
        "jenis_crew": "rating",
    }


def jalankan_uji_sensitivitas(daftar_panjang, ukuran_populasi=200, jumlah_generasi=400):
    hasil = []
    for panjang in daftar_panjang:
        random.seed(2024)  # seed sama tiap ukuran -> perbandingan lebih adil
        data_input = buat_data_input(panjang)
        luas = panjang * LEBAR_TETAP

        mulai = time.time()
        r = optimasi_layout(data_input, ukuran_populasi=ukuran_populasi, jumlah_generasi=jumlah_generasi)
        durasi = time.time() - mulai

        hasil.append({
            "panjang": panjang,
            "luas": round(luas, 2),
            "berhasil": r["berhasil"],
            "waktu_detik": round(durasi, 1),
            "penuhi_standar_mlc": luas >= LUAS_MIN_MLC,
        })
        status = "BERHASIL" if r["berhasil"] else "gagal"
        print(f"panjang={panjang:.1f} m  luas={luas:.2f} m2  ->  {status}  ({durasi:.1f}s)")

    return hasil


def plot_hasil_sensitivitas(hasil, simpan_ke=None):
    fig, ax = plt.subplots(figsize=(8, 4))
    for h in hasil:
        warna = "#2a9d8f" if h["berhasil"] else "#e63946"
        marker = "o" if h["berhasil"] else "x"
        ax.scatter(h["luas"], 1, color=warna, marker=marker, s=120, zorder=3)
        ax.annotate(f'{h["luas"]}m2', (h["luas"], 1), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=8)

    ax.axvline(LUAS_MIN_MLC, color="gray", linestyle="--", linewidth=1)
    ax.text(LUAS_MIN_MLC, 1.15, f"standar MLC\n({LUAS_MIN_MLC} m2)", ha="center", fontsize=8, color="gray")

    ax.set_yticks([])
    ax.set_xlabel("luas ruangan (m2)")
    ax.set_title("Uji Sensitivitas: Luas Ruangan vs Keberhasilan Optimasi\n(kabin 2 crew, 6 furniture)")
    ax.set_ylim(0.5, 1.5)

    from matplotlib.lines import Line2D
    legenda = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2a9d8f", markersize=10, label="Berhasil (valid)"),
        Line2D([0], [0], marker="x", color="#e63946", markersize=10, label="Gagal"),
    ]
    ax.legend(handles=legenda, loc="upper left")

    fig.tight_layout()
    if simpan_ke:
        fig.savefig(simpan_ke, dpi=150, bbox_inches="tight")
    return fig


if __name__ == "__main__":
    daftar_panjang = [3.0, 3.4, 3.8, 4.0, 4.2, 4.5, 5.0]
    hasil = jalankan_uji_sensitivitas(daftar_panjang)
    plot_hasil_sensitivitas(hasil, simpan_ke="sensitivitas_ukuran_ruang.png")
