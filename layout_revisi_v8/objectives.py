"""
objectives.py (REVISI 4)
Tiga objective NSGA-II - SEMUANYA MINIMIZE (makin kecil makin baik):

  1. ergonomi   : kekurangan ruang akses (bed, buka lemari, tarik kursi, area pintu)
                  terhadap nilai IDEAL, ditambah pelanggaran di bawah batas MINIMUM,
                  ditambah (REVISI 7) penalti jika jendela di kepala/kaki bed atau
                  bergeser dari tengah sisi bed.
  2. efisiensi  : porsi lantai kosong yang TIDAK terpakai (celah sempit / kantong buntu
                  yang tidak muat dilewati orang atau tidak tersambung ke pintu).
  3. sirkulasi  : total panjang jalur jalan dari pintu ke bed, lemari & kursi
                  (+ penalti besar kalau suatu furniture tidak bisa dijangkau).

KERAPIAN DIHAPUS (tidak lagi dinilai). Semua jarak bebas bukan lagi syarat
wajib: layout tetap dibuat walau ruangan sempit, dan kekurangannya tercermin
di skor-skor di atas (lihat constraints.JENIS_HARD).

Efisiensi & sirkulasi dihitung pada grid 10 cm (hitungan perkiraan; cukup untuk
membandingkan susunan, bukan ukuran presisi).
"""

import math
import numpy as np
from models import Layout, JenisFurniture
from constraints import (overlap_area, zona_depan, lebar_depan, zona_pintu,
                         luas_di_luar_ruang, check_all_constraints, pelanggaran_lunak,
                         opening_zone, gap_distance, bed_bersebelahan,
                         CLEARANCE_BED_IDEAL, LEMARI_AKSES_IDEAL, TARIK_KURSI_IDEAL,
                         JENIS_STANDAR_RUANG, JENIS_JENDELA_BED, selisih_jendela_bed)

SEL = 0.1                 # ukuran sel grid (m)
LEBAR_ORANG = 0.6         # orang berdiri/berjalan butuh kotak bebas segini (m)
W = int(round(LEBAR_ORANG / SEL))
PENALTI_TAK_TERJANGKAU_M = 1.5   # tambahan (m) di atas jarak lurus bila furniture benar-benar tak terjangkau
BOBOT_PELANGGARAN_MIN = 1.0      # bobot pelanggaran di bawah batas minimum pada skor ergonomi
BOBOT_JALAN_SEMPIT = 0.3         # penalti per furniture yang hanya terjangkau lewat jalan sempit
BOBOT_PINTU_TERHALANG = 6.0      # pintu tertutup furniture jauh lebih parah dari sekadar kurang jarak
PENALTI_JENDELA_KEPALA_KAKI = 3.0   # REVISI 7: jendela di sisi kepala/kaki bed (per bed) - sangat dihindari
BOBOT_JENDELA_TENGAH_BED = 1.0      # REVISI 7: per meter jendela bergeser dari tengah sisi bed


def penalti_jendela_bed(layout: Layout) -> float:
    """
    REVISI 7 - jendela diusahakan di SISI bed, tepat di tengah panjangnya, supaya saat tidur
    jendela tidak berada di kepala/kaki. Per bed:
      - dinding jendela tegak lurus panjang bed (kepala/kaki) -> PENALTI_JENDELA_KEPALA_KAKI
      - dinding sejajar panjang bed -> BOBOT_JENDELA_TENGAH_BED x selisih titik tengah (m)
    0 = jendela pas di tengah sisi semua bed (atau tidak ada jendela).
    """
    total = 0.0
    for _bed, _op, kepala_kaki, selisih in selisih_jendela_bed(layout):
        total += PENALTI_JENDELA_KEPALA_KAKI if kepala_kaki else BOBOT_JENDELA_TENGAH_BED * selisih
    return total


# ---------------------------------------------------------------------------
# Objective 1: ergonomi
# ---------------------------------------------------------------------------

def objective_ergonomi(layout: Layout, pelanggaran=None, n_sempit: int = 0) -> float:
    """
    Rata-rata kekurangan ruang akses terhadap nilai IDEAL:
    - BED    : jarak ke furniture lain terhadap 0.70 m.
    - LEMARI : area buka ideal (0.91 m) yang terpakai furniture lain / keluar ruangan / area pintu.
    - KURSI  : ruang tarik ideal (0.90 m) yang terpakai / keluar ruangan / area pintu / area buka lemari.
    PLUS besaran pelanggaran jarak/akses di bawah MINIMUM (soft constraint),
    mis. furniture menutup pintu, pintu-jendela bertabrakan.
    0 = semua akses ideal. Dibagi jumlah furniture yang butuh akses.
    """
    room = layout.room
    fs = layout.furnitures
    pintu = zona_pintu(layout)
    lemari = [f for f in fs if f.jenis == JenisFurniture.LEMARI]
    kursi = [f for f in fs if f.jenis == JenisFurniture.KURSI]
    total = 0.0

    for i in range(len(fs)):
        for j in range(i + 1, len(fs)):
            if JenisFurniture.BED in (fs[i].jenis, fs[j].jenis) and not bed_bersebelahan(fs[i], fs[j]):
                gap = gap_distance(fs[i].bounding_box(), fs[j].bounding_box())
                total += max(0.0, CLEARANCE_BED_IDEAL - gap)

    zona_l = []
    for l in lemari:
        z = zona_depan(l, LEMARI_AKSES_IDEAL)
        w = max(lebar_depan(l), 1e-9)
        zona_l.append(z)
        total += luas_di_luar_ruang(room, z) / w
        total += sum(overlap_area(zp, z) for zp in pintu) / w
        total += sum(overlap_area(o.bounding_box(), z) for o in fs
                     if o is not l and o.jenis != JenisFurniture.LEMARI) / w

    for k in kursi:
        z = zona_depan(k, TARIK_KURSI_IDEAL)
        w = max(lebar_depan(k), 1e-9)
        total += luas_di_luar_ruang(room, z) / w
        total += sum(overlap_area(zp, z) for zp in pintu) / w
        total += sum(overlap_area(o.bounding_box(), z) for o in fs if o is not k) / w
        total += sum(overlap_area(zl, z) for zl in zona_l) / w

    if pelanggaran is None:
        pelanggaran = check_all_constraints(layout)
    for v in pelanggaran_lunak(pelanggaran):
        if v.jenis in JENIS_STANDAR_RUANG or v.jenis in JENIS_JENDELA_BED:
            continue          # jendela-bed dihitung terpisah di bawah (penalti_jendela_bed)
        bobot = BOBOT_PINTU_TERHALANG if v.jenis == "blokir_bukaan" else BOBOT_PELANGGARAN_MIN
        total += bobot * v.besaran

    total += penalti_jendela_bed(layout)        # REVISI 7: jendela di sisi tengah bed
    total += BOBOT_JALAN_SEMPIT * n_sempit      # jalan ABK < 0.6 m (masih lolos min 0.4 m)
    n = sum(1 for f in fs if f.jenis in (JenisFurniture.BED, JenisFurniture.LEMARI, JenisFurniture.KURSI))
    return total / n if n else 0.0


# ---------------------------------------------------------------------------
# Grid: ruang yang bisa dilalui orang
# ---------------------------------------------------------------------------

def _idx(v: float) -> int:
    return int(math.floor(v / SEL + 0.5))


def _jarak_ke_kotak(cx, cy, box) -> np.ndarray:
    """Jarak (m) dari tiap titik pusat sel (grid cx x cy) ke sebuah kotak (xmin,ymin,xmax,ymax)."""
    dx = np.maximum(np.maximum(box[0] - cx, 0.0), cx - box[2])
    dy = np.maximum(np.maximum(box[1] - cy, 0.0), cy - box[3])
    return np.hypot(dx[:, None], dy[None, :])


W_MIN_ABK = 4    # lebar jalan minimum ABK (sel) = 0.4 m; di bawah ini dianggap tak terjangkau


def _analisis_ruang(layout: Layout) -> tuple[float, float, int, int]:
    """
    Kembalikan (penalti_efisiensi 0..1, total_sirkulasi_m, n_tak_terjangkau, n_jalan_sempit).
    n_tak_terjangkau = jumlah bed/lemari/kursi yang TIDAK bisa dicapai dari pintu dengan
    lebar jalan >= 0.4 m; n_jalan_sempit = yang hanya bisa dicapai lewat jalan < 0.6 m.

    - Sel "bisa dilalui" = posisi kotak 0.6x0.6 m yang sepenuhnya kosong dan di dalam ruangan.
    - Penjelajahan dimulai dari sekitar pintu dan menyebar lewat sel yang bisa dilalui.
    - Efisiensi : bagian lantai kosong yang tercakup oleh area yang bisa dijangkau dari pintu.
    - Sirkulasi : jarak jalan terpendek ke bed / depan lemari / belakang kursi.
    """
    room = layout.room
    nx, ny = max(int(math.ceil(room.panjang / SEL - 1e-9)), 1), max(int(math.ceil(room.lebar / SEL - 1e-9)), 1)

    occ = np.zeros((nx, ny), dtype=bool)
    for f in layout.furnitures:
        x0, y0, x1, y1 = f.bounding_box()
        i0, i1 = max(_idx(x0), 0), min(max(_idx(x1), _idx(x0) + 1), nx)
        j0, j1 = max(_idx(y0), 0), min(max(_idx(y1), _idx(y0) + 1), ny)
        occ[i0:i1, j0:j1] = True

    jumlah_bebas = int((~occ).sum())
    pintu_list = [o for o in room.openings if o.tipe == "pintu"]
    target = []
    for f in layout.furnitures:
        if f.jenis == JenisFurniture.BED:
            target.append((f.bounding_box(), 0.5))
        elif f.jenis == JenisFurniture.LEMARI:
            target.append((zona_depan(f, 0.5), 0.2))
        elif f.jenis == JenisFurniture.KURSI:
            target.append((f.bounding_box(), 0.5))      # kursi fix: cukup bisa didekati ABK
    n_target = len(target)

    if not pintu_list or jumlah_bebas == 0:
        return 1.0, 0.0, 0, 0
    pz = opening_zone(room, pintu_list[0], 0.01)

    def jelajah(w):
        """BFS dari pintu untuk orang selebar w sel. Kembalikan (ok,cx,cy,reach,dist) atau None."""
        nxw, nyw = nx - w + 1, ny - w + 1
        if nxw <= 0 or nyw <= 0:
            return None
        S = np.zeros((nx + 1, ny + 1), dtype=np.int32)
        S[1:, 1:] = occ.cumsum(0).cumsum(1)
        jml = S[w:, w:] - S[:-w, w:] - S[w:, :-w] + S[:-w, :-w]
        ok = (jml == 0)
        cx = (np.arange(nxw) + w / 2.0) * SEL
        cy = (np.arange(nyw) + w / 2.0) * SEL
        start = ok & (_jarak_ke_kotak(cx, cy, pz) <= 0.4)
        if not start.any():
            return None
        reach = start.copy()
        frontier = start.copy()
        dist = np.full(ok.shape, -1, dtype=np.int32)
        dist[start] = 0
        langkah = 0
        while frontier.any():
            langkah += 1
            nb = np.zeros_like(frontier)
            nb[1:] |= frontier[:-1]
            nb[:-1] |= frontier[1:]
            nb[:, 1:] |= frontier[:, :-1]
            nb[:, :-1] |= frontier[:, 1:]
            baru = nb & ok & ~reach
            dist[baru] = langkah
            reach |= baru
            frontier = baru
        return ok, cx, cy, reach, dist

    # Lebar orang berjenjang: 0.6 m (nyaman) -> 0.4 m -> 0.3 m (miring/menyelip).
    # Ruang sempit di kapal tetap punya jarak jalan yang WAJAR (bukan penalti flat).
    hasil_w = {}

    def ambil(w):          # BFS dihitung malas (lebar sempit hanya bila perlu)
        if w not in hasil_w:
            hasil_w[w] = jelajah(w)
        return hasil_w[w]

    w_utama = next((w for w in (W, 4, 3) if ambil(w) is not None), None)
    if w_utama is None:
        return 1.0, sum(_jarak_manhattan_ke_pintu(pz, box) + PENALTI_TAK_TERJANGKAU_M for box, _ in target), n_target, 0
    utama = hasil_w[w_utama]
    ok, cx, cy, reach, dist = utama
    nxw, nyw = reach.shape

    # efisiensi: lantai kosong yang tercakup jendela dari area yang terjangkau
    w = w_utama
    pad = np.zeros((nxw + 2 * (w - 1), nyw + 2 * (w - 1)), dtype=np.int32)
    pad[w - 1:w - 1 + nxw, w - 1:w - 1 + nyw] = reach
    T = np.zeros((pad.shape[0] + 1, pad.shape[1] + 1), dtype=np.int32)
    T[1:, 1:] = pad.cumsum(0).cumsum(1)
    tutup = (T[w:, w:] - T[:-w, w:] - T[w:, :-w] + T[:-w, :-w]) > 0
    terpakai = int((tutup & ~occ).sum())
    penalti_efisiensi = 1.0 - terpakai / jumlah_bebas

    # sirkulasi: jarak jalan terpendek dari pintu ke tiap target, orang paling lebar yang masih muat
    total = 0.0
    n_tak = n_sempit = 0
    for box, r in target:
        d_ = None
        w_pakai = None
        for w2 in (W, 4, 3):
            h = ambil(w2)
            if h is None:
                continue
            _, cx2, cy2, reach2, dist2 = h
            kena = dist2[(_jarak_ke_kotak(cx2, cy2, box) <= r) & reach2]
            if kena.size:
                d_, w_pakai = float(kena.min() * SEL), w2
                break
        if d_ is None or w_pakai < W_MIN_ABK:
            n_tak += 1
        elif w_pakai < W:
            n_sempit += 1
        total += d_ if d_ is not None else _jarak_manhattan_ke_pintu(pz, box) + PENALTI_TAK_TERJANGKAU_M
    return float(max(penalti_efisiensi, 0.0)), float(total), n_tak, n_sempit


def _jarak_manhattan_ke_pintu(pz, box) -> float:
    dx = max(box[0] - pz[2], pz[0] - box[2], 0.0)
    dy = max(box[1] - pz[3], pz[1] - box[3], 0.0)
    return dx + dy


def objective_efisiensi(layout: Layout) -> float:
    return _analisis_ruang(layout)[0]


def objective_sirkulasi(layout: Layout) -> float:
    return _analisis_ruang(layout)[1]


def pelanggaran_jangkauan(layout: Layout, n_tak: int = None) -> list:
    """Pelanggaran WAJIB 'tak_terjangkau': ada bed/lemari/kursi yang tidak bisa dicapai ABK dari pintu."""
    from constraints import ConstraintViolation
    if n_tak is None:
        n_tak = _analisis_ruang(layout)[2]
    if n_tak <= 0:
        return []
    return [ConstraintViolation(jenis="tak_terjangkau",
                                deskripsi=f"{n_tak} furniture tidak punya jalur (min 0.4 m) dari pintu untuk ABK",
                                furniture_ids=[], besaran=float(n_tak), hard=True)]


def kepadatan_furniture(layout: Layout) -> float:
    """Luas furniture / luas ruang (0..1). Hanya informasi laporan; nilainya sama untuk semua susunan."""
    if layout.room.luas <= 0:
        return 1.0
    return min(sum(f.luas for f in layout.furnitures) / layout.room.luas, 1.0)


def evaluate_dengan_jangkauan(layout: Layout, pelanggaran=None):
    """Kembalikan ((ergonomi, efisiensi_penalti, sirkulasi), n_tak_terjangkau)."""
    efi, sirk, n_tak, n_sempit = _analisis_ruang(layout)
    erg = objective_ergonomi(layout, pelanggaran, n_sempit)
    return (erg, efi, sirk), n_tak


def evaluate(layout: Layout, pelanggaran=None) -> tuple[float, float, float]:
    """(ergonomi, efisiensi_penalti, sirkulasi) - ketiganya MINIMIZE."""
    return evaluate_dengan_jangkauan(layout, pelanggaran)[0]
