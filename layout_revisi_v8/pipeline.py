"""
pipeline.py (REVISI)
Fungsi pipeline utama: dari data mentah (dict sederhana) sampai ke hasil
akhir berupa beberapa alternatif layout yang BERAGAM + visualisasinya.

PERUBAHAN BESAR dari versi sebelumnya (+ revisi penempatan terstruktur: bed di pojok,
lemari/meja berjajar rapat di dinding, kursi otomatis di depan meja - lihat ga_encoding.py):
1. Client TIDAK input ukuran furniture lagi - cuma JENIS & JUMLAH. Ukuran
   diambil dari katalog standar (constants.FURNITURE_STANDAR_M).
2. Client TIDAK input ukuran/posisi presisi pintu & jendela - cuma pilih
   ADA DI DINDING MANA ("depan"/"belakang"/"kiri"/"kanan"). Ukuran dari
   standar, posisi otomatis di tengah dinding itu.
3. Ada opsi BED TUMPUK (bunk bed) - 2 bed jadi 1 footprint, muat 2 crew.
4. jumlah_crew TIDAK diinput terpisah - dihitung otomatis dari total
   kapasitas bed yang diinput (termasuk bed tumpuk = 2 crew/footprint).
5. Alternatif hasil akhir dipilih supaya BERAGAM secara SPASIAL (bukan
   cuma beda di angka objective) - lihat pilih_alternatif_beragam().

REVISI 7 (jendela):
 - WAJIB : lemari tidak boleh berdiri di depan jendela (lemari tinggi). Meja/kursi/bed boleh.
 - USAHAKAN: bila ada bed, jendela di SISI bed, tepat di tengah panjangnya - saat tidur
   jendela tidak berada di kepala/kaki. Dinding jendela tetap pilihan client; yang diatur
   adalah arah bed & posisi jendela sepanjang dinding itu.
"""

import copy
import itertools
from models import Room, Furniture, JenisFurniture, CrewRequirement, Opening, Layout, DINDING_VALID, dimensi_efektif
from constants import STANDARDS, FURNITURE_STANDAR_M
from nsga2_main import run_nsga2
from visualize import plot_beberapa_layout
from ga_encoding import decode, random_chromosome, enumerasi_struktur, variasi_bukaan
from nsga2_sorting import Individual, evaluate_individual
from objectives import kepadatan_furniture, evaluate, evaluate_dengan_jangkauan, pelanggaran_jangkauan
from constraints import check_all_constraints, memenuhi_standar, TOL_NEMPEL, check_jendela_bed


CONTOH_INPUT = {
    "room": {"panjang": 3.8, "lebar": 2.5, "tinggi": 2.4},
    "pintu": {"dinding": "depan"},
    "jendela": {"dinding": "kanan"},  # opsional - boleh dihapus/None kalau tidak ada jendela
    "furnitures": [
        {"jenis": "bed", "jumlah": 2, "tumpuk": True},   # 2 bed tumpuk -> 1 footprint, 2 crew
        {"jenis": "lemari", "jumlah": 2},
        {"jenis": "meja", "jumlah": 1},   # kursi OTOMATIS = jumlah meja, tidak perlu diisi
    ],
    "jenis_crew": "rating",  # "rating" atau "officer" - dipakai utk standar luas minimum
}


def _bangun_opening(tipe: str, info_dinding: dict, room_panjang: float, room_lebar: float) -> Opening:
    """
    Bangun 1 Opening (pintu/jendela) dari info client (cuma dinding), dengan
    ukuran dari STANDARDS dan posisi otomatis DI TENGAH dinding itu.
    """
    dinding = info_dinding["dinding"]
    if dinding not in DINDING_VALID:
        raise ValueError(f"Dinding '{dinding}' tidak dikenal - pilih salah satu dari {DINDING_VALID}")

    lebar_opening = STANDARDS["lebar_pintu_standar_m"] if tipe == "pintu" else STANDARDS["lebar_jendela_standar_m"]
    panjang_dinding = room_panjang if dinding in ("depan", "belakang") else room_lebar
    posisi = max((panjang_dinding - lebar_opening) / 2, 0.0)

    return Opening(tipe=tipe, dinding=dinding, posisi=posisi, lebar=lebar_opening)


def _bangun_furnitures(daftar_furniture_input: list) -> list:
    """
    Ubah daftar {jenis, jumlah, tumpuk?} jadi list objek Furniture lengkap,
    dengan dimensi dari katalog standar (FURNITURE_STANDAR_M).

    Khusus bed dengan tumpuk=True: setiap 2 bed digabung jadi 1 Furniture
    (footprint 1 bed, kapasitas=2). Kalau jumlahnya ganjil, sisa 1 bed jadi
    bed biasa (tumpuk=False, kapasitas=1).
    """
    # ATURAN: tiap meja wajib punya kursi -> jumlah kursi OTOMATIS = jumlah meja,
    # apa pun yang diisi client untuk "kursi".
    jumlah_meja = sum(i["jumlah"] for i in daftar_furniture_input if i["jenis"] == "meja")
    daftar_furniture_input = [i for i in daftar_furniture_input if i["jenis"] != "kursi"]
    if jumlah_meja > 0:
        daftar_furniture_input.append({"jenis": "kursi", "jumlah": jumlah_meja})

    furnitures = []
    penghitung_id = {}

    def id_berikutnya(jenis):
        penghitung_id[jenis] = penghitung_id.get(jenis, 0) + 1
        return f"{jenis}{penghitung_id[jenis]}"

    for item in daftar_furniture_input:
        jenis_str = item["jenis"]
        jumlah = item["jumlah"]
        if jumlah <= 0:
            continue
        if jenis_str not in FURNITURE_STANDAR_M:
            raise ValueError(f"Jenis furniture '{jenis_str}' tidak dikenal. Pilihan: {list(FURNITURE_STANDAR_M)}")

        panjang, lebar = FURNITURE_STANDAR_M[jenis_str]
        jenis_enum = JenisFurniture(jenis_str)
        tumpuk = item.get("tumpuk", False) and jenis_str == "bed"

        if tumpuk:
            jumlah_bunk = jumlah // 2
            sisa = jumlah % 2
            for _ in range(jumlah_bunk):
                furnitures.append(Furniture(
                    id=id_berikutnya(jenis_str), jenis=jenis_enum,
                    panjang=panjang, lebar=lebar, tumpuk=True, kapasitas=2,
                ))
            for _ in range(sisa):
                furnitures.append(Furniture(
                    id=id_berikutnya(jenis_str), jenis=jenis_enum,
                    panjang=panjang, lebar=lebar, tumpuk=False, kapasitas=1,
                ))
        else:
            for _ in range(jumlah):
                furnitures.append(Furniture(
                    id=id_berikutnya(jenis_str), jenis=jenis_enum,
                    panjang=panjang, lebar=lebar, tumpuk=False, kapasitas=1,
                ))

    return furnitures


def bangun_layout_template(data_input: dict) -> Layout:
    """Ubah data mentah (dict sederhana) jadi objek Layout awal (template)."""
    room_data = data_input["room"]
    panjang, lebar = room_data["panjang"], room_data["lebar"]
    tinggi = room_data.get("tinggi", STANDARDS["tinggi_headroom_min_m"])

    openings = [_bangun_opening("pintu", data_input["pintu"], panjang, lebar)]
    if data_input.get("jendela"):
        openings.append(_bangun_opening("jendela", data_input["jendela"], panjang, lebar))

    room = Room(panjang=panjang, lebar=lebar, tinggi=tinggi, openings=openings)
    furnitures = _bangun_furnitures(data_input["furnitures"])

    jumlah_crew = sum(f.kapasitas for f in furnitures if f.jenis == JenisFurniture.BED)
    if jumlah_crew == 0:
        raise ValueError("Tidak ada bed di daftar furniture - tidak bisa menentukan jumlah crew.")
    crew = CrewRequirement(jumlah_crew=jumlah_crew, jenis_crew=data_input.get("jenis_crew", "rating"))

    return Layout(room=room, furnitures=furnitures, crew=crew)


def _jarak_spasial(layout_a: Layout, layout_b: Layout) -> float:
    """
    Seberapa 'beda' 2 layout secara SPASIAL (posisi furniture), bukan cuma
    beda angka objective. Dihitung dari total jarak Euclidean posisi tiap
    furniture yang BERPASANGAN id-nya (urutan furniture sama persis di
    semua layout, karena semua didekode dari layout_template yang sama).
    """
    total = 0.0
    for fa, fb in zip(layout_a.furnitures, layout_b.furnitures):
        total += ((fa.x - fb.x) ** 2 + (fa.y - fb.y) ** 2) ** 0.5
    for oa, ob in zip(layout_a.room.openings, layout_b.room.openings):
        total += 0.5 * abs(oa.posisi - ob.posisi)    # posisi pintu/jendela ikut membedakan layout
    return total


def _cerminkan(layout: Layout, sumbu: str) -> Layout:
    """
    Cerminkan posisi SEMUA furniture terhadap sumbu 'x' (kiri<->kanan) atau
    'y' (depan<->belakang). Room & openings TIDAK ikut dicerminkan (tetap di
    posisi aslinya) - makanya fungsi ini HANYA aman dipakai kalau tidak ada
    opening yang akan "pindah dinding" akibatnya (lihat _sumbu_cermin_aman).

    Pencerminan adalah ISOMETRI (menjaga semua jarak), jadi efisiensi_ruang,
    ergonomi, dan sirkulasi (karena titik tengah pintu juga simetris di
    tengah dindingnya) objectives-nya IDENTIK dengan layout asli - cuma
    tampilannya yang jadi berbeda (kiri<->kanan atau depan<->belakang).
    """
    baru = copy.deepcopy(layout)
    room = baru.room
    for f in baru.furnitures:
        p_eff, l_eff = dimensi_efektif(f.panjang, f.lebar, f.orientasi)
        o = int(f.orientasi)
        if sumbu == "x":
            f.x = room.panjang - (f.x + p_eff)
            f.orientasi = {90: 270, 270: 90}.get(o, o)   # arah hadap kiri<->kanan ikut terbalik
        else:
            f.y = room.lebar - (f.y + l_eff)
            f.orientasi = {0: 180, 180: 0}.get(o, o)     # arah hadap depan<->belakang ikut terbalik
    # pintu/jendela: dinding TETAP (sumbu cermin dipilih yang aman), tapi posisinya
    # sepanjang dinding ikut dicerminkan.
    for op in room.openings:
        if sumbu == "x" and op.dinding in ("depan", "belakang"):
            op.posisi = room.panjang - (op.posisi + op.lebar)
        elif sumbu == "y" and op.dinding in ("kiri", "kanan"):
            op.posisi = room.lebar - (op.posisi + op.lebar)
    return baru


def _sumbu_cermin_aman(room: Room) -> list[str]:
    """
    Tentukan sumbu cermin mana yang AMAN dipakai - yaitu yang TIDAK akan
    membuat pintu/jendela "pindah dinding" secara tidak realistis.
    - sumbu 'x' (kiri<->kanan) aman HANYA kalau tidak ada opening di
      dinding kiri/kanan (karena opening di situ akan ikut tertukar posisi
      dinding kalau x dicerminkan).
    - sumbu 'y' (depan<->belakang) aman HANYA kalau tidak ada opening di
      dinding depan/belakang.
    """
    dinding_dipakai = {o.dinding for o in room.openings}
    aman = []
    if not (dinding_dipakai & {"kiri", "kanan"}):
        aman.append("x")
    if not (dinding_dipakai & {"depan", "belakang"}):
        aman.append("y")
    return aman


# ---------------------------------------------------------------------------
# REVISI 3 - Keberagaman berbasis POLA DINDING (bed/lemari/meja ada di sisi mana)
# ---------------------------------------------------------------------------

_DINDING_DARI_ORIENTASI = {0: "depan", 90: "kanan", 180: "belakang", 270: "kiri"}
_SUMBU_DINDING = {"depan": "H", "belakang": "H", "kiri": "V", "kanan": "V"}

# Bobot beda pola: perpindahan bed paling terasa bagi client, jadi paling berat.
BOBOT_POLA = {"bed": 1.5, "lemari": 1.0, "meja": 1.0}
# Seberapa kuat kualitas (ergonomi+efisiensi) mengurangi nilai sebuah kandidat saat
# memilih alternatif. Makin kecil = makin mengutamakan keberagaman.
BOBOT_KUALITAS = 1.0


def _dinding_bed(room: Room, f) -> str:
    """Dinding tempat SISI PANJANG bed menempel (bed selalu di pojok)."""
    xmin, ymin, xmax, ymax = f.bounding_box()
    if int(f.orientasi) in (0, 180):          # sisi panjang sejajar sumbu X -> dinding depan/belakang
        if ymin <= TOL_NEMPEL:
            return "depan"
        if room.lebar - ymax <= TOL_NEMPEL:
            return "belakang"
        return "sebelah-kiri" if xmin <= TOL_NEMPEL else "sebelah-kanan"   # bersebelahan dgn bed lain
    if xmin <= TOL_NEMPEL:
        return "kiri"
    if room.panjang - xmax <= TOL_NEMPEL:
        return "kanan"
    return "sebelah-depan" if ymin <= TOL_NEMPEL else "sebelah-belakang"


def pola_dinding(layout: Layout) -> dict:
    """
    'Sidik jari' susunan: bed / lemari / meja ada di dinding mana.
    Dua layout dengan pola sama = secara struktur SAMA (hanya beda geser kecil).
    """
    room = layout.room
    pola = {"bed": tuple(_dinding_bed(room, f) for f in layout.furnitures
                         if f.jenis == JenisFurniture.BED),
            "lemari": None, "meja": None}
    for jenis in (JenisFurniture.LEMARI, JenisFurniture.MEJA):
        for f in layout.furnitures:
            if f.jenis == jenis:
                pola[jenis.value] = _DINDING_DARI_ORIENTASI[int(f.orientasi)]
                break
    return pola


def _kunci_pola(pola: dict) -> tuple:
    return (tuple(sorted(pola["bed"])), pola["lemari"], pola["meja"])


def _jarak_dinding(a, b) -> float:
    """0 = dinding sama, 0.5 = dinding seberang (sumbu sama), 1 = beda sumbu (mis. depan vs kiri)."""
    if a == b:
        return 0.0
    if a is None or b is None:
        return 1.0
    sa, sb = _SUMBU_DINDING[a.replace("sebelah-", "")], _SUMBU_DINDING[b.replace("sebelah-", "")]
    return 0.5 if sa == sb else 1.0


def jarak_pola(p1: dict, p2: dict) -> float:
    """Seberapa BEDA dua pola dinding (0 = identik). Bed dicocokkan dengan urutan terbaik."""
    b1, b2 = p1["bed"], p2["bed"]
    if len(b1) == len(b2) and b1:
        d_bed = min(sum(_jarak_dinding(x, y) for x, y in zip(b1, perm))
                    for perm in set(itertools.permutations(b2)))
    else:
        d_bed = float(max(len(b1), len(b2)))
    return (BOBOT_POLA["bed"] * d_bed
            + BOBOT_POLA["lemari"] * _jarak_dinding(p1["lemari"], p2["lemari"])
            + BOBOT_POLA["meja"] * _jarak_dinding(p1["meja"], p2["meja"]))


def label_pola(pola: dict) -> str:
    bagian = ["bed: " + "+".join(pola["bed"])]
    if pola["lemari"]:
        bagian.append(f"lemari: {pola['lemari']}")
    if pola["meja"]:
        bagian.append(f"meja: {pola['meja']}")
    return " | ".join(bagian)


def _skor_kualitas(objectives) -> float:
    return objectives[0] + objectives[1]          # ergonomi + efisiensi (makin kecil makin baik)


def _perhalus_bukaan(layout: Layout) -> tuple:
    """
    Setelah susunan furniture dipilih, geser pintu/jendela (di dinding yang TETAP)
    ke posisi terbaik: ergonomi+efisiensi terkecil, lalu sirkulasi terpendek.
    Furniture tidak disentuh. Kembalikan (objectives, layout) baru.
    """
    L = copy.deepcopy(layout)
    room = L.room
    q = STANDARDS["kuantisasi_posisi_m"]

    def nilai(lay):
        o, n_tak = evaluate_dengan_jangkauan(lay)
        # pintu WAJIB bebas & bisa dibuka, ABK WAJIB bisa menjangkau: posisi yang melanggar dibuang
        tak_layak = n_tak > 0 or any(v.hard for v in check_all_constraints(lay))
        return (int(tak_layak), round(_skor_kualitas(o), 6), o[2]), o

    terbaik = nilai(L)
    for _ in range(2):                            # 2 putaran coordinate-descent
        for op in room.openings:
            panjang = room.panjang if op.dinding in ("depan", "belakang") else room.lebar
            margin = (STANDARDS["margin_pintu_dari_sudut_m"] if op.tipe == "pintu"
                      else STANDARDS["margin_jendela_dari_sudut_m"])
            lo, hi = margin, max(panjang - op.lebar - margin, margin)
            terbaik_pos = op.posisi
            n = int(round((hi - lo) / q))
            for k in range(n + 1):
                op.posisi = lo + k * q
                hasil = nilai(L)
                if hasil[0] < terbaik[0]:
                    terbaik, terbaik_pos = hasil, op.posisi
            op.posisi = terbaik_pos
    return terbaik[1], L


def _pilih_dengan_info(individuals, layout_template, n):
    """
    Inti pemilihan alternatif. Kembalikan (terpilih, jumlah_pola_valid) dengan
    terpilih = list of (objectives, layout).

    Langkah:
    1. Decode semua kandidat valid (+ versi cerminan yang aman), buang duplikat.
    2. Kelompokkan per POLA DINDING (bed/lemari/meja di sisi mana). Dari tiap
       kelompok cukup ambil yang TERBAIK (ergonomi+efisiensi, lalu sirkulasi).
    3. Pilih n pola dengan greedy farthest-point pada jarak_pola(): pertama yang
       kualitasnya terbaik, berikutnya yang paling BEDA polanya dari yang sudah
       terpilih (dikurangi sedikit penalti kalau kualitasnya jauh di bawah terbaik).
    4. Kalau pola berbeda tidak cukup n (ruang terlalu sempit), sisanya diisi
       variasi terjauh secara spasial dari pola yang sama.
    """
    sumbu_aman = _sumbu_cermin_aman(layout_template.room)

    kandidat = []
    for ind in individuals:
        layout_asli = decode(ind.chromosome, layout_template)
        kandidat.append((ind.objectives, layout_asli))
        for sumbu in sumbu_aman:
            kandidat.append((ind.objectives, _cerminkan(layout_asli, sumbu)))

    unik = {}
    for k in kandidat:
        sig = (tuple((f.jenis.value, round(f.x, 2), round(f.y, 2), int(f.orientasi)) for f in k[1].furnitures),
               tuple(round(o.posisi, 2) for o in k[1].room.openings))
        unik.setdefault(sig, k)
    kandidat = list(unik.values())

    def kunci_urut(k):
        return (_skor_kualitas(k[0]), k[0][2])

    # wakil terbaik tiap pola dinding
    wakil = {}
    for k in kandidat:
        kp = _kunci_pola(pola_dinding(k[1]))
        if kp not in wakil or kunci_urut(k) < kunci_urut(wakil[kp]):
            wakil[kp] = k
    # hitung ulang objective EKSAK hanya untuk wakil tiap pola (kandidat cerminan
    # memakai nilai asli, yang bisa selisih sedikit akibat pembulatan grid)
    daftar_wakil = [(evaluate(k[1]), k[1]) for k in wakil.values()]
    jumlah_pola = len(daftar_wakil)

    terbaik_skor = min(_skor_kualitas(k[0]) for k in daftar_wakil)
    pola_cache = {id(k): pola_dinding(k[1]) for k in daftar_wakil}

    # REVISI 7: pola yang menaruh jendela di sisi KEPALA/KAKI bed hanya dipakai bila pola
    # yang sesuai (jendela di sisi bed) tidak cukup untuk mengisi n alternatif.
    def jendela_ok(k):
        return not any(v.jenis == "jendela_di_kepala_kaki" for v in check_jendela_bed(k[1]))
    daftar_ok = [k for k in daftar_wakil if jendela_ok(k)]
    daftar_buruk = [k for k in daftar_wakil if not jendela_ok(k)]

    def nilai_pilih(k, terpilih):
        jarak = min(jarak_pola(pola_cache[id(k)], pola_cache[id(t)]) for t in terpilih)
        return jarak - BOBOT_KUALITAS * (_skor_kualitas(k[0]) - terbaik_skor)

    terpilih = [min(daftar_ok or daftar_wakil, key=kunci_urut)]
    for sumber in (daftar_ok, daftar_buruk):
        sisa = [k for k in sumber if k is not terpilih[0]]
        while len(terpilih) < n and sisa:
            pilih = max(sisa, key=lambda k: nilai_pilih(k, terpilih))
            terpilih.append(pilih)
            sisa.remove(pilih)

    # tidak cukup pola berbeda -> isi dengan variasi spasial dari kandidat lain
    if len(terpilih) < n:
        sudah = {id(k) for k in terpilih}
        cadangan = [k for k in kandidat if id(k) not in sudah]
        cadangan.sort(key=kunci_urut)
        cadangan = [k for k in cadangan if _skor_kualitas(k[0]) <= terbaik_skor + 1.0] or cadangan
        while len(terpilih) < n and cadangan:
            pilih = max(cadangan, key=lambda k: min(_jarak_spasial(k[1], t[1]) for t in terpilih))
            terpilih.append(pilih)
            cadangan.remove(pilih)

    return terpilih, jumlah_pola


def pilih_alternatif_beragam(individuals, layout_template, n):
    """
    Pilih n layout yang BERAGAM secara STRUKTUR - bukan cuma beda koordinat.
    (Versi lama memakai jarak koordinat + saringan kualitas ketat, sehingga
    ketiga alternatif sering sama-sama "bed vertikal di sisi samping".)
    Lihat _pilih_dengan_info() untuk langkah lengkapnya.
    """
    return _pilih_dengan_info(individuals, layout_template, n)[0]


def _sampel_acak(layout_template: Layout, jumlah: int) -> list:
    """Sampling acak kromosom terstruktur (semua dievaluasi; feasible/tidaknya dicek belakangan)."""
    hasil = []
    for _ in range(jumlah):
        ind = Individual(chromosome=random_chromosome(layout_template))
        evaluate_individual(ind, layout_template)
        hasil.append(ind)
    return hasil


def _pindai_struktur(layout_template: Layout, batas: int = 30000, top_k: int = 120) -> list:
    """
    Pindai SEMUA susunan furniture (fase 1, pintu/jendela di tengah), lalu untuk susunan
    terbaik tiap pola + top_k terbaik secara keseluruhan, variasikan POSISI PINTU & JENDELA
    (fase 2) supaya furniture 'mengikuti' letak pintu.
    """
    fase1 = []
    for kromosom in enumerasi_struktur(layout_template, batas, fase_bukaan=False):
        ind = Individual(chromosome=kromosom)
        evaluate_individual(ind, layout_template)
        fase1.append(ind)

    layak = [i for i in fase1 if i.feasible] or sorted(fase1, key=lambda i: i.constraint_violation)[:top_k]
    layak.sort(key=lambda i: (i.objectives[0] + i.objectives[1], i.objectives[2]))
    terpilih, pola_terlihat = [], {}
    for ind in layak:                       # wakil terbaik (maks 3) tiap pola dinding
        kp = _kunci_pola(pola_dinding(decode(ind.chromosome, layout_template)))
        if pola_terlihat.get(kp, 0) < 3:
            pola_terlihat[kp] = pola_terlihat.get(kp, 0) + 1
            terpilih.append(ind)
    ids = {id(i) for i in terpilih}
    terpilih += [i for i in layak[:top_k] if id(i) not in ids]

    hasil = list(fase1)
    for ind in terpilih:
        for kromosom in variasi_bukaan(ind.chromosome, layout_template):
            baru = Individual(chromosome=kromosom)
            evaluate_individual(baru, layout_template)
            hasil.append(baru)
    return hasil


def optimasi_layout(
    data_input: dict,
    jumlah_alternatif: int = 3,
    ukuran_populasi: int = 80,
    jumlah_generasi: int = 80,
    jumlah_restart: int = 2,
    jumlah_sampel_acak: int = 3000,
    simpan_gambar_ke: str = None,
    pindai_semua_pola: bool = True,
) -> dict:
    """
    Fungsi utama yang dipanggil front-end (CLI/web/GUI).

    Return dict:
    {
      "berhasil": bool (SELALU True: layout tetap dibuat walau ruangan sempit),
      "layout_valid_fisik": bool (False = ada furniture yang menimpa / keluar ruangan),
      "jumlah_crew": int (otomatis dihitung dari kapasitas bed),
      "jumlah_alternatif": int,
      "alternatif": [ {pola, skor_ergonomi_penalti, efisiensi_ruang, total_sirkulasi_m,
                       memenuhi_standar, peringatan: [...], furniture: [...], bukaan: [...]}, ... ],
      "catatan_keragaman": str | None,
      "gambar": path file gambar (kalau simpan_gambar_ke diisi),

    Semua jarak bebas/akses (bed, lemari, kursi, pintu) adalah SOFT: kekurangannya
    jadi penalti pada skor, bukan alasan layout ditolak.
    }

    jumlah_restart: NSGA-II dijalankan independen sebanyak ini (populasi
    awal acak yang BEDA tiap kali, bukan direset ke seed yang sama), lalu
    hasilnya digabung. PENTING untuk keberagaman: satu kali jalan NSGA-II
    cenderung konvergen ke SATU pola susunan furniture saja (sekali
    "kepincut" satu susunan di generasi awal, sisanya cuma dieksplorasi di
    sekitar situ) - restart independen membuka peluang menemukan pola
    struktural yang benar-benar berbeda, bukan cuma variasi kecil dari pola
    yang sama. Konsekuensinya waktu komputasi naik ~jumlah_restart kali.
    """
    layout_template = bangun_layout_template(data_input)

    semua_individu = []
    for _ in range(jumlah_restart):
        _, populasi_akhir = run_nsga2(
            layout_template, ukuran_populasi=ukuran_populasi, jumlah_generasi=jumlah_generasi,
            kembalikan_populasi_penuh=True,
        )
        semua_individu.extend(populasi_akhir)
    semua_individu.extend(_sampel_acak(layout_template, jumlah_sampel_acak))
    # periksa SEMUA pola penempatan (bed di depan/belakang/kiri/kanan, lemari & meja
    # di dinding mana pun) supaya tidak ada pola yang terlewat.
    if pindai_semua_pola:
        semua_individu.extend(_pindai_struktur(layout_template))

    kandidat = [ind for ind in semua_individu if ind.feasible]
    fisik_valid = bool(kandidat)
    if not fisik_valid:
        # Ruangan SANGAT sempit: furniture pasti tumpang tindih / keluar ruangan.
        # Tetap tampilkan layout dengan pelanggaran fisik paling kecil (dengan peringatan).
        semua_individu.sort(key=lambda ind: ind.constraint_violation)
        kandidat = semua_individu[:300]

    pilihan, jumlah_pola = _pilih_dengan_info(kandidat, layout_template, jumlah_alternatif)
    # geser pintu/jendela ke posisi terbaik untuk susunan yang sudah dipilih
    pilihan = [_perhalus_bukaan(layout) for _, layout in pilihan]
    layouts = [layout for _, layout in pilihan]
    daftar_pola = [pola_dinding(layout) for layout in layouts]
    pola_berbeda = len({_kunci_pola(p) for p in daftar_pola})

    hasil_ringkas = []
    for (objectives, layout), pola in zip(pilihan, daftar_pola):
        erg, efi, sirk = objectives
        pelanggaran = check_all_constraints(layout)
        for v in pelanggaran_jangkauan(layout, evaluate_dengan_jangkauan(layout)[1]):
            v.hard = True
            pelanggaran.append(v)
        hasil_ringkas.append({
            "pola": label_pola(pola),
            "skor_ergonomi_penalti": round(erg, 3),
            "efisiensi_ruang": round(1 - efi, 3),
            "total_sirkulasi_m": round(sirk, 3),
            "sirkulasi_rata2_m": round(sirk / max(sum(1 for f in layout.furnitures if f.jenis in (JenisFurniture.BED, JenisFurniture.LEMARI, JenisFurniture.KURSI)), 1), 2),
            "kepadatan_furniture": round(kepadatan_furniture(layout), 3),
            "jendela_di_sisi_bed": not any(v.jenis == "jendela_di_kepala_kaki" for v in pelanggaran),
            "valid_fisik": not any(v.hard for v in pelanggaran),   # False = menimpa / keluar ruangan / pintu atau lemari tak bisa dibuka / ABK tak bisa menjangkau
            "memenuhi_standar": not pelanggaran,
            "peringatan": sorted({v.deskripsi for v in pelanggaran}),
            "furniture": [
                {"id": f.id, "jenis": f.jenis.value, "x": round(f.x, 3), "y": round(f.y, 3),
                 "orientasi": f.orientasi, "tumpuk": f.tumpuk, "kapasitas": f.kapasitas}
                for f in layout.furnitures
            ],
            "bukaan": [
                {"tipe": o.tipe, "dinding": o.dinding, "posisi": round(o.posisi, 3), "lebar": o.lebar}
                for o in layout.room.openings
            ],
        })

    fisik_valid = all(h["valid_fisik"] for h in hasil_ringkas)
    catatan = []
    if not fisik_valid:
        catatan.append(
            "Ruangan terlalu sempit untuk memuat semua furniture tanpa saling menimpa / keluar ruangan "
            "(lihat 'valid_fisik' & 'peringatan'). Layout tetap ditampilkan dengan pelanggaran paling sedikit - "
            "perbesar ruangan, kurangi furniture, atau aktifkan bed tumpuk.")
    elif pola_berbeda < min(jumlah_alternatif, 3):
        catatan.append(
            f"Hanya {jumlah_pola} pola penempatan (bed/lemari/meja di sisi mana) yang bisa disusun tanpa "
            f"furniture saling menimpa di ruang ini; alternatif tambahan hanya variasi posisi dari pola yang sama.")
    if any(not h["memenuhi_standar"] for h in hasil_ringkas):
        catatan.append(
            "Sebagian alternatif belum memenuhi standar jarak bebas/akses/luas minimum - kekurangannya "
            "tercermin pada skor ergonomi, efisiensi & sirkulasi (lihat 'peringatan' tiap alternatif).")

    hasil = {
        "berhasil": True,
        "layout_valid_fisik": fisik_valid,
        "jumlah_crew": layout_template.crew.jumlah_crew,
        "jumlah_alternatif": len(hasil_ringkas),
        "alternatif": hasil_ringkas,
        "jumlah_pola_valid": jumlah_pola,
        "catatan_keragaman": " ".join(catatan) if catatan else None,
        "gambar": None,
    }

    if simpan_gambar_ke:
        judul = [
            f"Alt {i + 1}: {h['pola']}\nergonomi={h['skor_ergonomi_penalti']}  efisiensi={h['efisiensi_ruang'] * 100:.0f}%  sirkulasi={h['sirkulasi_rata2_m']}m/titik (total {h['total_sirkulasi_m']}m)"
            for i, h in enumerate(hasil_ringkas)
        ]
        plot_beberapa_layout(layouts, judul, simpan_ke=simpan_gambar_ke)
        hasil["gambar"] = simpan_gambar_ke

    return hasil
