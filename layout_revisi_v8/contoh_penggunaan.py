"""
contoh_penggunaan.py (REVISI)
Contoh lengkap cara memakai software ini - sudah disesuaikan dengan
arsitektur input baru (jumlah furniture, bukan ukuran; posisi dinding,
bukan koordinat presisi; opsi tumpuk).

Ada 2 cara pakai:
  CARA 1 (DIREKOMENDASIKAN) - lewat pipeline.py, data berupa dict simpel.
    Ini format yang sama dipakai main.py (CLI).
  CARA 2 (untuk belajar struktur internal / debug) - bangun Layout manual
    dari models.py, cek constraint SATU susunan spesifik tanpa optimasi.

Jalankan dengan: python3 contoh_penggunaan.py
"""

import random
from pipeline import optimasi_layout
from models import Room, Furniture, JenisFurniture, CrewRequirement, Opening, Layout
from constraints import check_all_constraints, is_valid


def contoh_cara_1():
    print("=== CARA 1: lewat pipeline.optimasi_layout() ===\n")

    # --- BAGIAN A: DIISI CLIENT ---
    data_input = {
        "room": {
            "panjang": 3.8,   # <-- ISI: panjang ruangan (m)
            "lebar": 2.5,     # <-- ISI: lebar ruangan (m)
            "tinggi": 2.4,    # <-- ISI (opsional, boleh dihapus -> pakai standar 2.03 m)
        },
        "pintu": {"dinding": "depan"},     # <-- ISI: depan/belakang/kiri/kanan
        "jendela": {"dinding": "kanan"},   # <-- ISI (opsional, boleh None/dihapus kalau tidak ada)
        "furnitures": [
            # cuma JENIS & JUMLAH - ukuran otomatis dari katalog standar
            {"jenis": "bed", "jumlah": 2, "tumpuk": True},   # <-- ISI (tumpuk opsional, khusus bed)
            {"jenis": "lemari", "jumlah": 2},                # <-- ISI
            {"jenis": "meja", "jumlah": 1},                  # <-- ISI (kursi otomatis 1 per meja)
        ],
        "jenis_crew": "rating",  # <-- ISI: "rating" atau "officer"
        # jumlah_crew TIDAK perlu diisi - otomatis dihitung dari kapasitas bed
    }

    # --- BAGIAN B: OTOMATIS, TIDAK PERLU DIUBAH ---
    random.seed(42)
    print("(Menjalankan NSGA-II + pemindaian semua pola penempatan - beberapa saat)\n")
    hasil = optimasi_layout(
        data_input,
        jumlah_alternatif=3,
        simpan_gambar_ke="contoh_hasil.png",
    )

    if not hasil["berhasil"]:
        print(hasil["pesan"])
        return

    print(f"Jumlah crew (otomatis dari kapasitas bed): {hasil['jumlah_crew']}")
    print(f"Ditemukan {hasil['jumlah_alternatif']} alternatif layout:\n")
    for i, alt in enumerate(hasil["alternatif"]):
        print(
            f"Alternatif {i + 1}: efisiensi={alt['efisiensi_ruang']}  "
            f"ergonomi={alt['skor_ergonomi_penalti']}  sirkulasi={alt['total_sirkulasi_m']} m  [{alt['pola']}]"
        )
    print(f"\nGambar perbandingan tersimpan di: {hasil['gambar']}")


def contoh_cara_2():
    print("\n=== CARA 2: bangun Layout manual, cek constraint tanpa optimasi ===\n")

    room = Room(
        panjang=3.0, lebar=2.5, tinggi=2.4,
        openings=[Opening(tipe="pintu", dinding="depan", posisi=1.1, lebar=0.81)],
    )
    furnitures = [
        # di CARA 2 ini x, y, orientasi BOLEH diisi manual - karena kita mau
        # mengecek satu susunan spesifik, bukan menjalankan optimasi
        Furniture(id="bed1", jenis=JenisFurniture.BED, panjang=1.9, lebar=0.7, x=0.1, y=1.7, orientasi=0),
        Furniture(id="lemari1", jenis=JenisFurniture.LEMARI, panjang=0.6, lebar=0.6, x=0.1, y=0.1, orientasi=0),
    ]
    crew = CrewRequirement(jumlah_crew=1, jenis_crew="rating")
    layout = Layout(room=room, furnitures=furnitures, crew=crew)

    pelanggaran = check_all_constraints(layout)
    print(f"Jumlah pelanggaran: {len(pelanggaran)}")
    for v in pelanggaran:
        print(f" - [{v.jenis}] {v.deskripsi}")
    print("Layout valid?", is_valid(layout))


if __name__ == "__main__":
    contoh_cara_1()
    contoh_cara_2()
