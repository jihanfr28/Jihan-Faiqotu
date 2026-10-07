"""
constraints.py
Fungsi-fungsi validasi layout terhadap standar (MLC 2006, SOLAS, ergonomi).

Semua fungsi cek mengembalikan list[ConstraintViolation] (kosong = tidak ada
pelanggaran). Nanti dipakai dua cara:
1. Sebagai HARD CONSTRAINT -> layout dengan pelanggaran tertentu langsung
   dibuang / diberi fitness sangat buruk oleh NSGA-II.
2. Sebagai bahan OBJECTIVE FUNCTION ergonomi -> besar_pelanggaran dipakai
   untuk menghitung skor seberapa jauh dari ideal.
"""

from dataclasses import dataclass
from models import Room, Furniture, Opening, Layout, JenisFurniture
from constants import STANDARDS

Box = tuple[float, float, float, float]  # (xmin, ymin, xmax, ymax)

# Toleransi floating-point. PENTING: NSGA-II sering mendorong solusi optimal
# PERSIS ke batas constraint (mis. clearance pas-pasan di batas minimum,
# furniture pas menempel di dinding) - itu WAJAR dan VALID secara matematis,
# tapi perbandingan "<" yang terlalu ketat bisa salah mendeteksinya sebagai
# pelanggaran gara-gara pembulatan floating point (mis. 0.4999999999999998
# hasil operasi blend crossover, padahal seharusnya persis 0.5).
EPS = 1e-6

# Standar jarak bebas:
# - BED   : jarak bebas ke furniture lain (min = hard, ideal = objective ergonomi)
# - LEMARI: area akses di DEPAN lemari harus kosong (kedalaman min/ideal).
#           Lemari BOLEH berdempetan dengan lemari lain di sampingnya.
CLEARANCE_BED_MIN = STANDARDS["clearance_bed_min_m"]
CLEARANCE_BED_IDEAL = STANDARDS["clearance_bed_ideal_m"]
LEMARI_AKSES_MIN = STANDARDS["clearance_lemari_min_m"]
LEMARI_AKSES_IDEAL = STANDARDS["clearance_lemari_ideal_m"]

TARIK_KURSI_MIN = STANDARDS["tarik_kursi_min_m"]
TARIK_KURSI_IDEAL = STANDARDS["tarik_kursi_ideal_m"]

# Toleransi "menempel" untuk cek aturan susunan (m)
TOL_NEMPEL = 0.01
KURSI_MAKS_JARAK_M = 0.06   # kursi harus tepat di depan meja (jarak maks)


@dataclass
class ConstraintViolation:
    jenis: str                 # kategori pelanggaran, misal "overlap", "blokir_pintu"
    deskripsi: str             # penjelasan singkat untuk debugging/laporan
    furniture_ids: list[str]   # furniture yang terlibat
    besaran: float = 0.0       # besar pelanggaran (m, m^2, dst) - untuk penalti gradual
    hard: bool = True          # True = solusi tidak valid, False = sekadar penalti/soft


# ---------------------------------------------------------------------------
# Util geometri dasar
# ---------------------------------------------------------------------------

def overlap_area(b1: Box, b2: Box) -> float:
    """Luas area tumpang tindih dua bounding box. 0 kalau tidak overlap."""
    xmin1, ymin1, xmax1, ymax1 = b1
    xmin2, ymin2, xmax2, ymax2 = b2
    dx = min(xmax1, xmax2) - max(xmin1, xmin2)
    dy = min(ymax1, ymax2) - max(ymin1, ymin2)
    if dx > 0 and dy > 0:
        return dx * dy
    return 0.0


def gap_distance(b1: Box, b2: Box) -> float:
    """Jarak terdekat antar dua bounding box (0 kalau bersinggungan/overlap)."""
    xmin1, ymin1, xmax1, ymax1 = b1
    xmin2, ymin2, xmax2, ymax2 = b2
    dx = max(xmin1 - xmax2, xmin2 - xmax1, 0.0)
    dy = max(ymin1 - ymax2, ymin2 - ymax1, 0.0)
    return (dx ** 2 + dy ** 2) ** 0.5


def opening_zone(room: Room, opening: Opening, depth: float) -> Box:
    """
    Zona yang harus tetap bebas dari furniture untuk sebuah bukaan (pintu/jendela),
    yaitu bukaan itu sendiri diperpanjang sejauh `depth` ke dalam ruangan
    (misal untuk area ayunan pintu / akses).
    """
    depth = max(depth, 0.01)
    if opening.dinding == "depan":
        return (opening.posisi, 0.0, opening.posisi + opening.lebar, depth)
    if opening.dinding == "belakang":
        return (opening.posisi, room.lebar - depth, opening.posisi + opening.lebar, room.lebar)
    if opening.dinding == "kiri":
        return (0.0, opening.posisi, depth, opening.posisi + opening.lebar)
    if opening.dinding == "kanan":
        return (room.panjang - depth, opening.posisi, room.panjang, opening.posisi + opening.lebar)
    raise ValueError(f"Dinding tidak dikenal: {opening.dinding}")


# ---------------------------------------------------------------------------
# Cek 1: furniture harus berada di dalam batas ruangan
# ---------------------------------------------------------------------------

def check_within_room(layout: Layout) -> list[ConstraintViolation]:
    violations = []
    room = layout.room
    for f in layout.furnitures:
        xmin, ymin, xmax, ymax = f.bounding_box()
        lewat = max(-xmin, -ymin, xmax - room.panjang, ymax - room.lebar, 0.0)
        if lewat > EPS:
            violations.append(ConstraintViolation(
                jenis="keluar_ruangan",
                deskripsi=f"Furniture '{f.id}' keluar dari batas ruangan sejauh {lewat:.3f} m",
                furniture_ids=[f.id],
                besaran=lewat,
                hard=True,
            ))
    return violations


# ---------------------------------------------------------------------------
# Cek 2: furniture tidak boleh saling overlap
# ---------------------------------------------------------------------------

def check_overlap(layout: Layout) -> list[ConstraintViolation]:
    violations = []
    furnitures = layout.furnitures
    for i in range(len(furnitures)):
        for j in range(i + 1, len(furnitures)):
            f1, f2 = furnitures[i], furnitures[j]
            area = overlap_area(f1.bounding_box(), f2.bounding_box())
            if area > 1e-9:   # abaikan sisa pembulatan float pada furniture yang bersentuhan
                violations.append(ConstraintViolation(
                    jenis="overlap",
                    deskripsi=f"'{f1.id}' dan '{f2.id}' saling tumpang tindih seluas {area:.3f} m2",
                    furniture_ids=[f1.id, f2.id],
                    besaran=area,
                    hard=True,
                ))
    return violations


# ---------------------------------------------------------------------------
# Cek 3: furniture tidak boleh menutup akses pintu/jendela
# ---------------------------------------------------------------------------

def check_opening_blocked(layout: Layout) -> list[ConstraintViolation]:
    """
    - PINTU  : tidak boleh ada furniture apa pun di area ayunan/akses pintu (WAJIB,
      pintu harus selalu bisa dibuka).
    - JENDELA: tidak dicek di sini (meja/kursi/bed boleh di depan jendela).
      Khusus LEMARI di depan jendela dilarang -> lihat check_lemari_depan_jendela().
    """
    violations = []
    room = layout.room
    for opening in room.openings:
        if opening.tipe != "pintu":
            continue
        zone = opening_zone(room, opening, STANDARDS["area_pintu_m"])
        for f in layout.furnitures:
            area = overlap_area(f.bounding_box(), zone)
            if area > 1e-9:
                violations.append(ConstraintViolation(
                    jenis="blokir_bukaan",
                    deskripsi=f"Furniture '{f.id}' menghalangi {opening.tipe} di dinding {opening.dinding}",
                    furniture_ids=[f.id],
                    besaran=area,
                    hard=True,
                ))
    return violations


# ---------------------------------------------------------------------------
# Cek 4: clearance (jarak bebas) minimum antar furniture
# ---------------------------------------------------------------------------

def zona_depan(f: Furniture, kedalaman: float) -> Box:
    """Zona persegi panjang di DEPAN furniture (lemari/meja) sedalam `kedalaman`,
    sesuai arah menghadap (lihat docstring orientasi di models.py)."""
    xmin, ymin, xmax, ymax = f.bounding_box()
    o = int(f.orientasi)
    if o == 0:
        return (xmin, ymax, xmax, ymax + kedalaman)
    if o == 90:
        return (xmin - kedalaman, ymin, xmin, ymax)
    if o == 180:
        return (xmin, ymin - kedalaman, xmax, ymin)
    return (xmax, ymin, xmax + kedalaman, ymax)  # 270


def lebar_depan(f: Furniture) -> float:
    """Lebar sisi depan (sisi yang sejajar dinding tempat menempel)."""
    xmin, ymin, xmax, ymax = f.bounding_box()
    return (xmax - xmin) if int(f.orientasi) in (0, 180) else (ymax - ymin)


BED_GAP = STANDARDS["jarak_bed_bersebelahan_m"]


def bed_bersebelahan(f1: Furniture, f2: Furniture) -> bool:
    """True bila dua bed disusun sejajar berdampingan dengan celah kecil (sekitar BED_GAP)."""
    if f1.jenis != JenisFurniture.BED or f2.jenis != JenisFurniture.BED:
        return False
    if (int(f1.orientasi) % 180 == 0) != (int(f2.orientasi) % 180 == 0):
        return False
    b1, b2 = f1.bounding_box(), f2.bounding_box()
    gap = gap_distance(b1, b2)
    if gap < BED_GAP - EPS or gap > BED_GAP + 0.05:
        return False
    # harus sejajar di sumbu panjang (saling berhadapan sisi panjangnya)
    if int(f1.orientasi) % 180 == 0:
        sejajar = min(b1[2], b2[2]) - max(b1[0], b2[0])
    else:
        sejajar = min(b1[3], b2[3]) - max(b1[1], b2[1])
    return sejajar > 0.5 * max(f1.panjang, f1.lebar)


def check_clearance(layout: Layout) -> list[ConstraintViolation]:
    """
    Hard constraint jarak bebas:
    1) BED  : jarak ke furniture lain >= clearance bed minimum (0.5 m).
    2) LEMARI: area akses di depannya (0.76 m) tidak boleh dimasuki furniture
       NON-lemari. Lemari bersebelahan dengan lemari lain itu BOLEH (justru
       diwajibkan berdekatan, lihat check_aturan_susunan).
    Selisih terhadap nilai IDEAL dipakai di objectives.py (ergonomi).
    """
    violations = []
    fs = layout.furnitures
    for i in range(len(fs)):
        for j in range(i + 1, len(fs)):
            f1, f2 = fs[i], fs[j]
            if JenisFurniture.BED in (f1.jenis, f2.jenis) and not bed_bersebelahan(f1, f2):
                gap = gap_distance(f1.bounding_box(), f2.bounding_box())
                if gap < CLEARANCE_BED_MIN - EPS:
                    violations.append(ConstraintViolation(
                        jenis="clearance_kurang",
                        deskripsi=f"Jarak '{f1.id}'-'{f2.id}' hanya {gap:.3f} m (min {CLEARANCE_BED_MIN} m)",
                        furniture_ids=[f1.id, f2.id],
                        besaran=CLEARANCE_BED_MIN - gap,
                        hard=True,
                    ))

    for lem in fs:
        if lem.jenis != JenisFurniture.LEMARI:
            continue
        zona = zona_depan(lem, LEMARI_AKSES_MIN - EPS)
        for other in fs:
            if other is lem or other.jenis == JenisFurniture.LEMARI:
                continue
            area = overlap_area(other.bounding_box(), zona)
            if area > 1e-9:
                violations.append(ConstraintViolation(
                    jenis="akses_lemari_terhalang",
                    deskripsi=f"Akses depan '{lem.id}' terhalang '{other.id}'",
                    furniture_ids=[lem.id, other.id],
                    besaran=area,
                    hard=True,
                ))
    return violations


# ---------------------------------------------------------------------------
# Cek 5: luas ruangan & tinggi headroom sesuai standar untuk jumlah crew
# ---------------------------------------------------------------------------

def check_room_standard(layout: Layout) -> list[ConstraintViolation]:
    violations = []
    room, crew = layout.room, layout.crew

    if room.tinggi < STANDARDS["tinggi_headroom_min_m"] - EPS:
        violations.append(ConstraintViolation(
            jenis="headroom_kurang",
            deskripsi=f"Tinggi ruangan {room.tinggi} m < standar {STANDARDS['tinggi_headroom_min_m']} m",
            furniture_ids=[],
            besaran=STANDARDS["tinggi_headroom_min_m"] - room.tinggi,
            hard=True,
        ))

    tabel_luas = STANDARDS["luas_min_per_kapasitas_m2"]
    n = crew.jumlah_crew
    luas_min = tabel_luas.get(n, tabel_luas[max(tabel_luas)] / max(tabel_luas) * n)
    if room.luas < luas_min - EPS:
        violations.append(ConstraintViolation(
            jenis="luas_kurang",
            deskripsi=f"Luas ruangan {room.luas:.2f} m2 < standar {luas_min:.2f} m2 utk {n} crew",
            furniture_ids=[],
            besaran=luas_min - room.luas,
            hard=True,
        ))
    return violations


# ---------------------------------------------------------------------------
# Cek 5b: akses furniture - tarik kursi, buka lemari, pintu vs jendela
# ---------------------------------------------------------------------------

def zona_pintu(layout: Layout) -> list[Box]:
    """Area ayunan/akses pintu (harus bebas dari furniture & ruang akses lain)."""
    return [opening_zone(layout.room, o, STANDARDS["area_pintu_m"])
            for o in layout.room.openings if o.tipe == "pintu"]


def luas_di_luar_ruang(room: Room, box: Box) -> float:
    """Luas bagian `box` yang berada DI LUAR dinding ruangan (0 = seluruhnya di dalam)."""
    xmin, ymin, xmax, ymax = box
    total = (xmax - xmin) * (ymax - ymin)
    dx = max(0.0, min(xmax, room.panjang) - max(xmin, 0.0))
    dy = max(0.0, min(ymax, room.lebar) - max(ymin, 0.0))
    return max(total - dx * dy, 0.0)


def check_akses_furniture(layout: Layout) -> list[ConstraintViolation]:
    """
    Hard constraint ruang AKSES (ukuran minimum):
    1) KURSI : ruang di belakang kursi (0.60 m) untuk menarik kursi harus
       kosong dari furniture lain, tidak keluar ruangan, tidak masuk area
       pintu, dan tidak bertabrakan dengan area buka lemari.
    2) LEMARI: area buka lemari (0.76 m) tidak boleh keluar ruangan atau
       masuk area ayunan pintu.
    (Area buka lemari vs furniture lain sudah dicek di check_clearance.)
    """
    v = []
    room = layout.room
    fs = layout.furnitures
    pintu = zona_pintu(layout)
    lemari = [f for f in fs if f.jenis == JenisFurniture.LEMARI]
    zona_lemari = [(l, zona_depan(l, LEMARI_AKSES_MIN - EPS)) for l in lemari]

    def lapor(jenis, desk, ids, besaran):
        v.append(ConstraintViolation(jenis=jenis, deskripsi=desk, furniture_ids=ids,
                                     besaran=max(besaran, 0.01), hard=True))

    for k in (f for f in fs if f.jenis == JenisFurniture.KURSI):
        zona = zona_depan(k, TARIK_KURSI_MIN - EPS)
        keluar = luas_di_luar_ruang(room, zona)
        if keluar > 1e-9:
            lapor("tarik_kursi_keluar_ruang", f"Ruang tarik '{k.id}' melewati dinding ruangan", [k.id], keluar)
        for o in fs:
            if o is k:
                continue
            a = overlap_area(o.bounding_box(), zona)
            if a > 1e-9:
                lapor("tarik_kursi_terhalang", f"Ruang tarik '{k.id}' terhalang '{o.id}'", [k.id, o.id], a)
        for zp in pintu:
            a = overlap_area(zp, zona)
            if a > 1e-9:
                lapor("tarik_kursi_di_area_pintu", f"Ruang tarik '{k.id}' masuk area pintu", [k.id], a)
        for l, zl in zona_lemari:
            a = overlap_area(zl, zona)
            if a > 1e-9:
                lapor("tarik_kursi_bentrok_lemari", f"Ruang tarik '{k.id}' bentrok dengan area buka '{l.id}'", [k.id, l.id], a)

    for l, zl in zona_lemari:
        keluar = luas_di_luar_ruang(room, zl)
        if keluar > 1e-9:
            lapor("akses_lemari_keluar_ruang", f"Area buka '{l.id}' melewati dinding ruangan", [l.id], keluar)
        for zp in pintu:
            a = overlap_area(zp, zl)
            if a > 1e-9:
                lapor("akses_lemari_di_area_pintu", f"Area buka '{l.id}' masuk area pintu", [l.id], a)
    return v


def check_bukaan_tumpang_tindih(layout: Layout) -> list[ConstraintViolation]:
    """Pintu & jendela di dinding yang sama tidak boleh saling tumpang tindih / terlalu rapat."""
    v = []
    ops = layout.room.openings
    jarak_min = STANDARDS["jarak_min_pintu_jendela_m"]
    for i in range(len(ops)):
        for j in range(i + 1, len(ops)):
            a, b = ops[i], ops[j]
            if a.dinding != b.dinding:
                continue
            gap = max(a.posisi - (b.posisi + b.lebar), b.posisi - (a.posisi + a.lebar))
            if gap < jarak_min - EPS:
                v.append(ConstraintViolation(
                    jenis="pintu_jendela_bertumpuk",
                    deskripsi=f"{a.tipe} dan {b.tipe} di dinding {a.dinding} terlalu berdekatan ({gap:.2f} m)",
                    furniture_ids=[], besaran=jarak_min - gap, hard=True))
    return v


# ---------------------------------------------------------------------------
# Cek 5c (REVISI 7): jendela vs lemari (WAJIB) dan jendela vs bed (DIUSAHAKAN)
# ---------------------------------------------------------------------------

def zona_depan_jendela(room: Room, opening: Opening) -> Box:
    """Zona di depan jendela: lebar jendela diperpanjang ke dalam ruangan."""
    return opening_zone(room, opening, STANDARDS["kedalaman_depan_jendela_m"])


def check_lemari_depan_jendela(layout: Layout) -> list[ConstraintViolation]:
    """
    WAJIB (hard): lemari itu tinggi, jadi tidak boleh berdiri di depan jendela.
    Meja, kursi & bed boleh di depan jendela.
    """
    v = []
    room = layout.room
    for op in room.openings:
        if op.tipe != "jendela":
            continue
        zona = zona_depan_jendela(room, op)
        for f in layout.furnitures:
            if f.jenis != JenisFurniture.LEMARI:
                continue
            area = overlap_area(f.bounding_box(), zona)
            if area > 1e-9:
                v.append(ConstraintViolation(
                    jenis="lemari_depan_jendela",
                    deskripsi=f"Lemari '{f.id}' berdiri di depan jendela (dinding {op.dinding})",
                    furniture_ids=[f.id], besaran=area, hard=True))
    return v


def bed_sejajar_dinding(bed: Furniture, dinding: str) -> bool:
    """True bila sisi PANJANG bed sejajar dinding tsb (jadi dinding itu berada di SISI bed,
    bukan di sisi kepala/kaki). Dinding depan/belakang membentang searah sumbu X; kiri/kanan searah Y."""
    panjang_di_x = int(bed.orientasi) % 180 == 0
    dinding_searah_x = dinding in ("depan", "belakang")
    return panjang_di_x == dinding_searah_x


def tengah_sepanjang_dinding(box: Box, dinding: str) -> float:
    """Titik tengah sebuah kotak diukur SEPANJANG dinding (x untuk depan/belakang, y untuk kiri/kanan)."""
    if dinding in ("depan", "belakang"):
        return (box[0] + box[2]) / 2
    return (box[1] + box[3]) / 2


def pusat_bed_sejajar(layout: Layout, dinding: str):
    """Rata-rata titik tengah bed yang sisi panjangnya sejajar dinding (None bila tidak ada)."""
    pusat = [tengah_sepanjang_dinding(f.bounding_box(), dinding)
             for f in layout.furnitures
             if f.jenis == JenisFurniture.BED and bed_sejajar_dinding(f, dinding)]
    return sum(pusat) / len(pusat) if pusat else None


def selisih_jendela_bed(layout: Layout) -> list[tuple]:
    """
    Untuk tiap (jendela, bed): (bed, jendela, di_kepala_kaki: bool, selisih_tengah_m).
    - di_kepala_kaki=True  : dinding jendela tegak lurus panjang bed -> jendela ada di sisi
                             kepala/kaki orang yang tidur (selisih_tengah_m = 0, tak relevan).
    - di_kepala_kaki=False : jendela di sisi bed; selisih_tengah_m = jarak titik tengah jendela
                             ke titik tengah bed sepanjang dinding (0 = pas di tengah bed).
    """
    hasil = []
    for op in layout.room.openings:
        if op.tipe != "jendela":
            continue
        pusat_jendela = op.posisi + op.lebar / 2
        for f in layout.furnitures:
            if f.jenis != JenisFurniture.BED:
                continue
            if bed_sejajar_dinding(f, op.dinding):
                selisih = abs(pusat_jendela - tengah_sepanjang_dinding(f.bounding_box(), op.dinding))
                hasil.append((f, op, False, selisih))
            else:
                hasil.append((f, op, True, 0.0))
    return hasil


def check_jendela_bed(layout: Layout) -> list[ConstraintViolation]:
    """
    DIUSAHAKAN (soft): bila ada bed, jendela berada di SISI bed, di titik tengah panjangnya -
    jadi saat tidur jendela tidak berada di kepala atau kaki. Hanya LAPORAN (peringatan);
    nilai penaltinya dihitung di objectives.penalti_jendela_bed (jenis-jenis ini
    dilewati di loop pelanggaran lunak supaya tidak terhitung dua kali).
    """
    v = []
    tol = STANDARDS["toleransi_tengah_bed_jendela_m"]
    for bed, op, kepala_kaki, selisih in selisih_jendela_bed(layout):
        if kepala_kaki:
            v.append(ConstraintViolation(
                jenis="jendela_di_kepala_kaki",
                deskripsi=f"Jendela (dinding {op.dinding}) berada di sisi kepala/kaki '{bed.id}'",
                furniture_ids=[bed.id], besaran=1.0, hard=False))
        elif selisih > tol + EPS:
            v.append(ConstraintViolation(
                jenis="jendela_tidak_di_tengah_bed",
                deskripsi=f"Jendela (dinding {op.dinding}) bergeser {selisih:.2f} m dari tengah sisi '{bed.id}'",
                furniture_ids=[bed.id], besaran=selisih, hard=False))
    return v


# ---------------------------------------------------------------------------
# Cek 6: aturan SUSUNAN (pojok / berdekatan / meja-kursi)
# ---------------------------------------------------------------------------

def _menempel_dinding(room: Room, box: Box) -> bool:
    xmin, ymin, xmax, ymax = box
    return (xmin <= TOL_NEMPEL or ymin <= TOL_NEMPEL or
            room.panjang - xmax <= TOL_NEMPEL or room.lebar - ymax <= TOL_NEMPEL)


def _di_pojok(room: Room, box: Box) -> bool:
    xmin, ymin, xmax, ymax = box
    sisi_x = xmin <= TOL_NEMPEL or room.panjang - xmax <= TOL_NEMPEL
    sisi_y = ymin <= TOL_NEMPEL or room.lebar - ymax <= TOL_NEMPEL
    return sisi_x and sisi_y


def _satu_kelompok_berdekatan(items: list[Furniture]) -> bool:
    """True kalau semua item saling terhubung lewat sentuhan (jarak <= TOL_NEMPEL)."""
    if len(items) <= 1:
        return True
    terhubung = {0}
    antrian = [0]
    while antrian:
        a = antrian.pop()
        for b in range(len(items)):
            if b not in terhubung and gap_distance(items[a].bounding_box(), items[b].bounding_box()) <= TOL_NEMPEL:
                terhubung.add(b)
                antrian.append(b)
    return len(terhubung) == len(items)


def check_aturan_susunan(layout: Layout) -> list[ConstraintViolation]:
    """
    Aturan susunan dari client:
    1) Bed harus di POJOK ruangan (menempel 2 dinding), bukan di tengah.
    2) Lemari harus menempel dinding & semua lemari saling BERDEKATAN (sampingan).
    3) Meja harus menempel dinding & semua meja saling BERDEKATAN.
    4) Setiap meja WAJIB punya kursi tepat di DEPANNYA.
    (Optimasi GA menjamin ini lewat encoding; cek ini penting untuk layout manual.)
    """
    v = []
    room = layout.room
    fs = layout.furnitures

    def lapor(jenis, desk, ids):
        v.append(ConstraintViolation(jenis=jenis, deskripsi=desk, furniture_ids=ids, besaran=1.0, hard=True))

    beds = [f for f in fs if f.jenis == JenisFurniture.BED]
    sah = {f.id for f in beds if _di_pojok(room, f.bounding_box())}
    berubah = True
    while berubah:                      # bed yang berdampingan dgn bed sah (dekat pojok) juga sah
        berubah = False
        for f in beds:
            if f.id not in sah and any(bed_bersebelahan(f, g) for g in beds if g.id in sah) \
                    and _menempel_dinding(room, f.bounding_box()):
                sah.add(f.id)
                berubah = True
    for f in beds:
        if f.id not in sah:
            lapor("bed_bukan_di_pojok", f"Bed '{f.id}' tidak berada di pojok / berdampingan dgn bed di pojok", [f.id])

    for jenis, nama in ((JenisFurniture.LEMARI, "lemari"), (JenisFurniture.MEJA, "meja")):
        grup = [f for f in fs if f.jenis == jenis]
        for f in grup:
            if not _menempel_dinding(room, f.bounding_box()):
                lapor(f"{nama}_tidak_di_dinding", f"'{f.id}' harus menempel dinding", [f.id])
        if not _satu_kelompok_berdekatan(grup):
            lapor(f"{nama}_tidak_berdekatan", f"Semua {nama} harus berdekatan (sampingan)", [f.id for f in grup])

    kursi = [f for f in fs if f.jenis == JenisFurniture.KURSI]
    for m in (f for f in fs if f.jenis == JenisFurniture.MEJA):
        zona = zona_depan(m, KURSI_MAKS_JARAK_M)
        if not any(overlap_area(k.bounding_box(), zona) > 0 for k in kursi):
            lapor("meja_tanpa_kursi", f"Meja '{m.id}' tidak punya kursi tepat di depannya", [m.id])
    return v


# ---------------------------------------------------------------------------
# Master function: jalankan semua pengecekan sekaligus
# ---------------------------------------------------------------------------

# REVISI 4 - Hanya pelanggaran FISIK/STRUKTUR yang tetap WAJIB (hard).
# Furniture tidak boleh keluar ruangan atau saling menimpa, dan aturan susunan
# (bed di pojok, lemari/meja menempel dinding, meja berkursi) dijaga encoding.
# SEMUA jarak bebas & akses (clearance bed, akses lemari, tarik kursi, area pintu,
# pintu-jendela berdekatan, luas/headroom standar) kini SOFT: layout tetap dibuat
# walau ruangan sempit, dan kekurangannya dihitung sebagai penalti ergonomi
# (lihat objectives.py) serta dilaporkan sebagai peringatan.
JENIS_HARD = {
    "keluar_ruangan", "overlap",
    "bed_bukan_di_pojok", "lemari_tidak_di_dinding", "lemari_tidak_berdekatan",
    "meja_tidak_di_dinding", "meja_tidak_berdekatan", "meja_tanpa_kursi",
    # REVISI 6 - WAJIB: pintu harus bisa dibuka & lemari harus bisa dibuka.
    # (Tarik kursi boleh dikorbankan di ruang sangat sempit: kursi dianggap fix.)
    "blokir_bukaan", "akses_lemari_terhalang", "akses_lemari_di_area_pintu", "akses_lemari_keluar_ruang",
    "tak_terjangkau",   # ABK harus bisa berjalan dari pintu ke bed/lemari/meja (lihat objectives.py)
    # REVISI 7 - WAJIB: lemari itu tinggi, tidak boleh berdiri di depan jendela.
    "lemari_depan_jendela",
}
# REVISI 7 - DIUSAHAKAN (soft): jendela di sisi tengah bed, bukan di kepala/kaki. Penaltinya
# dihitung khusus di objectives.penalti_jendela_bed, jadi dilewati di loop pelanggaran lunak.
JENIS_JENDELA_BED = {"jendela_di_kepala_kaki", "jendela_tidak_di_tengah_bed"}
# Pelanggaran standar yang nilainya sama untuk semua susunan (tidak bergantung
# posisi furniture) -> hanya dilaporkan, tidak dimasukkan ke skor ergonomi.
JENIS_STANDAR_RUANG = {"luas_kurang", "headroom_kurang"}


def check_all_constraints(layout: Layout) -> list[ConstraintViolation]:
    """Semua pelanggaran. Atribut .hard=True hanya untuk pelanggaran fisik/struktur (JENIS_HARD)."""
    violations = []
    violations += check_within_room(layout)
    violations += check_overlap(layout)
    violations += check_opening_blocked(layout)
    violations += check_clearance(layout)
    violations += check_room_standard(layout)
    violations += check_akses_furniture(layout)
    violations += check_bukaan_tumpang_tindih(layout)
    violations += check_aturan_susunan(layout)
    violations += check_lemari_depan_jendela(layout)
    violations += check_jendela_bed(layout)
    for v in violations:
        v.hard = v.jenis in JENIS_HARD
    return violations


def pelanggaran_lunak(violations: list[ConstraintViolation]) -> list[ConstraintViolation]:
    """Pelanggaran jarak/akses yang jadi penalti (bukan penolakan layout)."""
    return [v for v in violations if not v.hard]


def is_valid(layout: Layout) -> bool:
    """Valid SECARA FISIK/STRUKTUR (tanpa pelanggaran hard)."""
    return not any(v.hard for v in check_all_constraints(layout))


def memenuhi_standar(layout: Layout) -> bool:
    """True hanya kalau TIDAK ada pelanggaran apa pun (termasuk jarak bebas & luas minimum)."""
    return not check_all_constraints(layout)
