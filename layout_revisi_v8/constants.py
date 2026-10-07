"""
constants.py
Kumpulan standar ruang & ergonomi kabin crew kapal (MLC 2006, SOLAS, ergonomi interior).

PENTING: Nilai-nilai ini adalah CONSTRAINT TETAP yang dipakai algoritma untuk
memvalidasi dan menilai layout. Client TIDAK menginput ulang nilai-nilai ini -
mereka hanya menginput ukuran ruang, furniture, dan jumlah crew (lihat models.py).
"""

STANDARDS = {
    # Luas minimum kabin (m^2) berdasarkan kapasitas orang - MLC 2006 Std A3.1
    # (kapal selain penumpang/special purpose)
    "luas_min_per_kapasitas_m2": {
        1: 4.5,   # 1 orang, kapal >=3000 GT (rating)
        2: 7.5,   # 2 orang
        3: 11.5,  # 3 orang
        4: 14.5,  # 4 orang
    },

    # Tinggi headroom minimum (m) - MLC 2006 Std A3.1 para 6(c)
    "tinggi_headroom_min_m": 2.03,

    # Dimensi minimum berth / tempat tidur (m) - panjang x lebar
    "berth_dim_min_m": (1.90, 0.70),

    # Lebar minimum berth yang meruncing (tapered) (m)
    "berth_tapered_min_lebar_m": 0.50,

    # Clearance (jarak bebas) di sekitar tempat tidur (m)
    "clearance_bed_min_m": 0.50,    # mutlak minimum (hard constraint)
    "clearance_bed_ideal_m": 0.70,  # ideal/nyaman (dipakai di objective ergonomi)

    # Kedalaman area akses di DEPAN lemari (m) - area ini harus kosong
    # (REVISI 5: diperkecil - kapal butuh ruang ringkas, yang penting masih ada jarak
    #  untuk membuka pintu lemari & berdiri di depannya)
    "clearance_lemari_min_m": 0.55,
    "clearance_lemari_ideal_m": 0.65,

    # Kedalaman area ayun/akses di DEPAN pintu (m) yang harus bebas furniture.
    # (REVISI 5: sebelumnya memakai lebar_sirkulasi_min 0.80 m -> terlalu lebar)
    "area_pintu_m": 0.55,

    # Jarak (m) antar bed yang disusun BERSEBELAHAN (sejajar, berdampingan) - cukup
    # sedikit saja supaya footprint tidak menempel (REVISI 6).
    "jarak_bed_bersebelahan_m": 0.10,

    # Lebar jalur sirkulasi minimum (m) - SOLAS (ruang di bawah bulkhead deck)
    "lebar_sirkulasi_min_m": 0.80,

    # Lebar pintu minimum (m)
    "lebar_pintu_umum_min_m": 0.81,
    "lebar_pintu_crew_only_min_m": 0.71,

    # Volume minimum lemari & laci per orang (liter) - MLC 2006
    "volume_lemari_min_liter": 475,
    "volume_laci_min_liter": 56,

    # Panjang maksimum lorong buntu / dead-end corridor (m) - SOLAS
    "panjang_dead_end_max_m": 7.0,

    # Dimensi standar pintu & jendela (m) - client TIDAK input ukuran ini lagi,
    # cuma pilih DI DINDING MANA (depan/belakang/kiri/kanan). Lebar pintu
    # dipakai dari batas atas rentang MLC (0.81 m, "lebar_pintu_umum_min_m")
    # supaya aman dipakai sebagai lebar aktual, bukan cuma syarat minimum.
    "lebar_pintu_standar_m": 0.81,
    "lebar_jendela_standar_m": 0.60,

    # --- AKSES FURNITURE (asumsi desain umum interior; boleh diubah di sini) ---
    # Ruang kosong di BELAKANG kursi (sisi yang menjauhi meja) supaya kursi bisa
    # ditarik mundur dan orang bisa duduk/berdiri. min = wajib, ideal = target.
    "tarik_kursi_min_m": 0.60,
    "tarik_kursi_ideal_m": 0.90,

    # --- KERAPIAN (estetika) ---
    # Pintu/jendela tidak boleh terlalu mepet sudut ruangan (m)
    "margin_pintu_dari_sudut_m": 0.15,
    "margin_jendela_dari_sudut_m": 0.30,
    # Jarak minimum antara pintu & jendela jika berada di dinding yang sama (m)
    "jarak_min_pintu_jendela_m": 0.20,
    # Celah antar furniture yang lebih sempit dari ini (tapi > 0) dianggap
    # "celah nanggung" - tidak muat dipakai & tidak enak dilihat -> dipenalti
    "celah_nanggung_m": 0.30,
    # Posisi pintu/jendela dibulatkan ke kelipatan ini (m) supaya angkanya rapi
    "kuantisasi_posisi_m": 0.05,

    # --- JENDELA (REVISI 7) ---
    # Lemari itu tinggi -> TIDAK BOLEH berdiri di depan jendela. Zona "depan jendela" =
    # lebar jendela diperpanjang sedalam ini ke dalam ruangan (sedikit > kedalaman lemari
    # 0.60 m, jadi lemari yang menempel dinding di bawah jendela pasti terdeteksi).
    # Meja, kursi & bed BOLEH berada di depan jendela.
    "kedalaman_depan_jendela_m": 0.65,
    # Jendela sebaiknya berada di SISI bed, tepat di tengah panjang bed (bukan di
    # sisi kepala/kaki). Selisih titik tengah jendela-bed sampai batas ini masih
    # dianggap "di tengah" (tidak dilaporkan sebagai peringatan).
    "toleransi_tengah_bed_jendela_m": 0.25,
}

# ---------------------------------------------------------------------------
# Katalog dimensi standar furniture (m) - panjang x lebar.
# Client TIDAK input ukuran furniture lagi, cuma pilih JENIS dan JUMLAH-nya
# (lihat pipeline.py). Angka di sini dipilih dari riset standar sebelumnya
# (bed = berth MLC 2006; lemari/meja/kursi = ukuran umum interior kabin
# kapal) - kalau mau diubah, edit di sini saja, seluruh sistem ikut berubah.
# ---------------------------------------------------------------------------
FURNITURE_STANDAR_M = {
    "bed": (1.90, 0.70),       # sama dengan berth_dim_min_m - standar MLC 2006
    "lemari": (0.60, 0.60),
    "meja": (1.00, 0.50),
    "kursi": (0.45, 0.45),     # jumlah kursi OTOMATIS = jumlah meja (lihat pipeline.py)
}
