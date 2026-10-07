"""
main.py (REVISI)
Antarmuka CLI sederhana - client cuma isi:
- ukuran ruang (panjang, lebar, tinggi opsional)
- pintu & jendela: DI DINDING MANA saja (depan/belakang/kiri/kanan)
- furniture: JENIS & JUMLAH saja (ukuran otomatis dari standar)
- opsi tumpuk kalau bed >= 2
- jenis crew (rating/officer)

CATATAN: ini contoh antarmuka PALING SEDERHANA. Kalau nanti mau diganti web
form atau GUI desktop, cukup panggil optimasi_layout() dari pipeline.py
dengan dict berformat sama seperti di sini - tidak perlu ubah pipeline.py
maupun file-file inti lainnya sama sekali.

Jalankan dengan: python3 main.py
"""

from pipeline import optimasi_layout
from constants import FURNITURE_STANDAR_M
from models import DINDING_VALID


def input_angka(prompt, tipe=float):
    while True:
        try:
            return tipe(input(prompt))
        except ValueError:
            print("  input tidak valid, coba lagi.")


def input_pilihan(prompt, pilihan_valid):
    while True:
        nilai = input(prompt).strip().lower()
        if nilai in pilihan_valid:
            return nilai
        print(f"  pilih salah satu dari: {', '.join(pilihan_valid)}")


def input_ya_tidak(prompt) -> bool:
    return input_pilihan(prompt, ["y", "n"]) == "y"


def jalankan_cli():
    print("=== Software Optimasi Layout Kabin Crew Kapal ===\n")

    print("-- Data Ruangan --")
    panjang = input_angka("Panjang ruangan (m): ")
    lebar = input_angka("Lebar ruangan (m): ")
    isi_tinggi = input("Tinggi ruangan (m) [kosongkan = pakai standar minimum 2.03 m]: ").strip()
    tinggi = float(isi_tinggi) if isi_tinggi else 2.03

    print(f"\nDinding yang bisa dipilih: {', '.join(DINDING_VALID)}")
    print("(ukuran & posisi pintu/jendela otomatis mengikuti standar - cuma pilih dindingnya)")

    print("\n-- Data Pintu (wajib) --")
    dinding_pintu = input_pilihan("Pintu di dinding: ", DINDING_VALID)

    print("\n-- Data Jendela (opsional) --")
    ada_jendela = input_ya_tidak("Apakah ada jendela? (y/n): ")
    dinding_jendela = input_pilihan("Jendela di dinding: ", DINDING_VALID) if ada_jendela else None

    print("\n-- Data Furniture --")
    print(f"Jenis yang tersedia (ukuran standar sudah ditentukan): {', '.join(j for j in FURNITURE_STANDAR_M if j != 'kursi')}")
    print("(kursi otomatis ditambahkan: 1 kursi untuk setiap meja)")
    furnitures = []
    for jenis in FURNITURE_STANDAR_M:
        if jenis == "kursi":
            continue  # kursi OTOMATIS = jumlah meja (tiap meja wajib punya kursi)
        jumlah = input_angka(f"Jumlah '{jenis}' (0 kalau tidak ada): ", tipe=int)
        if jumlah <= 0:
            continue
        item = {"jenis": jenis, "jumlah": jumlah}
        if jenis == "bed" and jumlah >= 2:
            item["tumpuk"] = input_ya_tidak(f"  Apakah {jumlah} bed ini ditumpuk (bunk bed)? (y/n): ")
        furnitures.append(item)

    if not any(f["jenis"] == "bed" for f in furnitures):
        print("\nMinimal harus ada 1 bed (jumlah_crew dihitung dari bed). Program dihentikan.")
        return

    print("\n-- Data Crew --")
    jenis_crew = input_pilihan("Jenis crew (rating/officer): ", ["rating", "officer"])

    data_input = {
        "room": {"panjang": panjang, "lebar": lebar, "tinggi": tinggi},
        "pintu": {"dinding": dinding_pintu},
        "jendela": {"dinding": dinding_jendela} if dinding_jendela else None,
        "furnitures": furnitures,
        "jenis_crew": jenis_crew,
    }

    print("\nMenjalankan optimasi (NSGA-II + pemindaian semua pola penempatan)...")
    print("Mohon tunggu beberapa saat.\n")
    hasil = optimasi_layout(
        data_input,
        jumlah_alternatif=3,
        simpan_gambar_ke="hasil_layout.png",
    )

    if not hasil["berhasil"]:
        print(hasil["pesan"])
        return

    print(f"Jumlah crew (otomatis dari kapasitas bed): {hasil['jumlah_crew']}")
    print(f"Ditemukan {hasil['jumlah_alternatif']} alternatif layout yang BERAGAM:\n")
    for i, alt in enumerate(hasil["alternatif"]):
        print(f"Alternatif {i + 1}:  [{alt['pola']}]")
        print(f"  Efisiensi ruang      : {alt['efisiensi_ruang'] * 100:.1f}% (porsi lantai kosong yang terpakai/terjangkau)")
        print(f"  Skor ergonomi        : {alt['skor_ergonomi_penalti']} (0 = ideal, makin besar makin kurang nyaman)")
        print(f"  Sirkulasi            : rata-rata {alt['sirkulasi_rata2_m']} m per titik, total {alt['total_sirkulasi_m']} m (jalan dari pintu ke bed/lemari/kursi; makin pendek makin baik)")
        print(f"  Memenuhi standar     : {'ya' if alt['memenuhi_standar'] else 'TIDAK'}")
        for p in alt["peringatan"]:
            print(f"     ! {p}")
        for o in alt["bukaan"]:
            print(f"     - {o['tipe']} (dinding {o['dinding']}): mulai {o['posisi']} m dari ujung dinding, lebar {o['lebar']} m")
        for f in alt["furniture"]:
            tanda_tumpuk = " [TUMPUK, 2 crew]" if f["tumpuk"] else ""
            print(f"     - {f['id']}: posisi=({f['x']}, {f['y']}) m{tanda_tumpuk}")
        print()

    if hasil.get("catatan_keragaman"):
        print("CATATAN KERAGAMAN:", hasil["catatan_keragaman"], "\n")

    print(f"Gambar perbandingan tersimpan di: {hasil['gambar']}")


if __name__ == "__main__":
    jalankan_cli()
