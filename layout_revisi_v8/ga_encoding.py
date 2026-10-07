"""
ga_encoding.py (REVISI 2 - penempatan terstruktur + pintu/jendela fleksibel)

Kromosom menyimpan KEPUTUSAN TATA LETAK (bukan koordinat mentah); koordinat
dihitung di decode(). Karena itu aturan susunan terpenuhi secara konstruksi:

  1. BED          -> selalu di POJOK ruangan.
  2. LEMARI       -> semua lemari berjajar rapat di SATU dinding.
  3. MEJA + KURSI -> semua meja berjajar rapat di SATU dinding, kursi tepat
                     di depan tiap meja.
  4. PINTU/JENDELA-> tetap di dinding yang dipilih client, tetapi POSISI
                     sepanjang dinding itu ikut dioptimasi (agar pas dengan
                     furniture di dalamnya).

Satuan keputusan ("unit") dan gen (a, b, c)-nya:
  - tiap bed        : (pojok 0..3, orientasi 0/90, -)
  - grup lemari     : (dinding 0..3, anchor 0..2, -)
  - grup meja+kursi : (dinding 0..3, anchor 0..4, -)
  - pintu           : (mode 0..3, t 0..1, -)
  - jendela         : (mode 0..2, t 0..1, -)

pojok   : 0=kiri-depan  1=kanan-depan  2=kanan-belakang  3=kiri-belakang
dinding : 0=depan(y=0)  1=kanan(x=P)   2=belakang(y=L)    3=kiri(x=0)
anchor  : 0 = mulai dari ujung awal dinding (pojok)
          1 = mulai dari ujung akhir dinding (pojok seberang)
          2 = di TENGAH dinding
          3 = (khusus meja) menyambung RAPAT tepat setelah barisan lemari
          4 = (khusus meja) menyambung RAPAT tepat sebelum barisan lemari
          (anchor 3/4 hanya berlaku bila lemari di dinding yang sama)
Pilihan anchor yang DISKRIT ini yang membuat susunan selalu rapi: furniture
hanya mungkin berada di pojok, di tengah dinding, atau menyambung dengan
furniture lain - tidak pernah di posisi "nanggung" sembarang.

pintu  mode: 0=posisi bebas (t), 1=tengah dinding, 2=dekat ujung awal, 3=dekat ujung akhir
jendela mode: 0=posisi bebas (t), 1=tengah dinding, 2=tepat di atas meja (jika
              meja di dinding yang sama, kalau tidak -> tengah dinding),
              3=(REVISI 7) sejajar TENGAH bed - titik tengah jendela lurus dengan titik
              tengah sisi panjang bed (jika dinding jendela sejajar bed, kalau tidak -> tengah dinding)
"""

import copy
import random
from models import Layout, JenisFurniture, dimensi_efektif
from constants import STANDARDS
from constraints import bed_sejajar_dinding, tengah_sepanjang_dinding

ORIENTASI_VALID = [0, 90, 180, 270]
ORIENTASI_DINDING = {0: 0, 1: 90, 2: 180, 3: 270}
NAMA_DINDING = ["depan", "kanan", "belakang", "kiri"]

Gene = tuple[float, float, float]
Chromosome = list[Gene]


def daftar_unit(layout: Layout) -> list[tuple]:
    """
    Daftar unit keputusan (urutan = urutan gen di kromosom):
      ("bed", [idx])  |  ("lemari", [idx..])  |  ("meja", [idx_meja..], [idx_kursi..])
      ("pintu", idx_opening)  |  ("jendela", idx_opening)
    """
    fs = layout.furnitures
    unit = [("bed", [i]) for i, f in enumerate(fs) if f.jenis == JenisFurniture.BED]
    if len(unit) > 4:
        raise ValueError("Maksimal 4 bed/bed tumpuk (satu per pojok ruangan). "
                         "Aktifkan opsi tumpuk supaya jumlah footprint bed berkurang.")
    lemari = [i for i, f in enumerate(fs) if f.jenis == JenisFurniture.LEMARI]
    if lemari:
        unit.append(("lemari", lemari))
    meja = [i for i, f in enumerate(fs) if f.jenis == JenisFurniture.MEJA]
    kursi = [i for i, f in enumerate(fs) if f.jenis == JenisFurniture.KURSI]
    if meja:
        if len(kursi) != len(meja):
            raise ValueError("Jumlah kursi harus sama dengan jumlah meja (tiap meja wajib punya kursi).")
        unit.append(("meja", meja, kursi))
    elif kursi:
        raise ValueError("Ada kursi tapi tidak ada meja - kursi harus berpasangan dengan meja.")
    for i, o in enumerate(layout.room.openings):
        unit.append((o.tipe, i))
    return unit


def gen_acak(tipe: str) -> Gene:
    if tipe == "bed":
        return (float(random.randint(0, 5)), float(random.choice([0, 90])), 0.0)
    if tipe == "lemari":
        return (float(random.randint(0, 3)), float(random.randint(0, 2)), 0.0)
    if tipe == "meja":
        return (float(random.randint(0, 3)), float(random.randint(0, 4)), 0.0)
    if tipe == "pintu":
        return (float(random.randint(0, 3)), random.random(), 0.0)
    return (float(random.randint(0, 3)), random.random(), 0.0)   # jendela


# ---------------------------------------------------------------------------
# Decode: kromosom -> koordinat nyata
# ---------------------------------------------------------------------------

def _taruh_bed(room, f, pojok: int, orient: int, prev=None) -> None:
    """pojok 0..3 = di pojok ruangan; 4/5 (hanya bila ada bed sebelumnya) = BERSEBELAHAN
    dengan bed sebelumnya (orientasi sama, celah jarak_bed_bersebelahan_m): 4 = ke arah +, 5 = ke arah -."""
    if pojok >= 4 and prev is not None:
        gap = STANDARDS["jarak_bed_bersebelahan_m"]
        f.orientasi = prev.orientasi
        p, l = dimensi_efektif(f.panjang, f.lebar, f.orientasi)
        px0, py0, px1, py1 = prev.bounding_box()
        if int(prev.orientasi) % 180 == 0:      # panjang sejajar X -> geser di sumbu Y
            f.x = px0
            f.y = py1 + gap if pojok == 4 else py0 - gap - l
        else:                                   # panjang sejajar Y -> geser di sumbu X
            f.y = py0
            f.x = px1 + gap if pojok == 4 else px0 - gap - p
        return
    pojok = pojok % 4
    p, l = dimensi_efektif(f.panjang, f.lebar, orient)
    f.x = room.panjang - p if pojok in (1, 2) else 0.0
    f.y = room.lebar - l if pojok in (2, 3) else 0.0
    f.orientasi = orient


def _rentang_bebas(room, dinding: int, beds) -> tuple[float, float]:
    """
    Rentang (awal, akhir) sepanjang dinding yang TIDAK ditempati bed di pojok.
    Baris lemari/meja dirapatkan ke bed (tanpa celah nanggung) alih-alih menimpanya.
    """
    panjang_dinding = room.panjang if dinding in (0, 2) else room.lebar
    awal, akhir = 0.0, panjang_dinding
    tol = 1e-6
    for f in beds:
        x0, y0, x1, y1 = f.bounding_box()
        if dinding == 0 and y0 <= tol:
            a, b = x0, x1
        elif dinding == 2 and y1 >= room.lebar - tol:
            a, b = x0, x1
        elif dinding == 3 and x0 <= tol:
            a, b = y0, y1
        elif dinding == 1 and x1 >= room.panjang - tol:
            a, b = y0, y1
        else:
            continue
        if a <= tol:
            awal = max(awal, b)
        elif b >= panjang_dinding - tol:
            akhir = min(akhir, a)
    return awal, akhir


def _awal_barisan(panjang_dinding, total, anchor, info_lemari, dinding, rentang=None):
    lo, hi = rentang if rentang else (0.0, panjang_dinding)
    if hi - lo < total - 1e-9:          # tidak muat di sela bed -> biarkan (nanti terdeteksi overlap)
        lo, hi = 0.0, panjang_dinding
    maks = hi - total
    if anchor == 1:
        return maks
    if anchor == 2:
        return (lo + maks) / 2
    if anchor in (3, 4) and info_lemari is not None and info_lemari[0] == dinding:
        _, mulai_l, total_l = info_lemari
        awal = mulai_l + total_l if anchor == 3 else mulai_l - total
        return min(max(awal, lo), maks)
    return lo


def _taruh_baris(room, items, dinding: int, anchor: int, kursi_items=None, info_lemari=None, beds=()):
    """Taruh `items` berjajar RAPAT menempel dinding. Kembalikan (dinding, awal, total)."""
    panjang_dinding = room.panjang if dinding in (0, 2) else room.lebar
    total = sum(f.panjang for f in items)
    awal = _awal_barisan(panjang_dinding, total, anchor, info_lemari, dinding,
                         _rentang_bebas(room, dinding, beds))
    pos = awal
    orient = ORIENTASI_DINDING[dinding]

    for k, f in enumerate(items):
        sepanjang, kedalaman = f.panjang, f.lebar
        if dinding == 0:
            f.x, f.y = pos, 0.0
        elif dinding == 1:
            f.x, f.y = room.panjang - kedalaman, pos
        elif dinding == 2:
            f.x, f.y = pos, room.lebar - kedalaman
        else:
            f.x, f.y = 0.0, pos
        f.orientasi = orient

        if kursi_items is not None:
            c = kursi_items[k]
            tengah = pos + sepanjang / 2
            if dinding == 0:
                c.x, c.y = tengah - c.panjang / 2, kedalaman
            elif dinding == 1:
                c.x, c.y = room.panjang - kedalaman - c.lebar, tengah - c.panjang / 2
            elif dinding == 2:
                c.x, c.y = tengah - c.panjang / 2, room.lebar - kedalaman - c.lebar
            else:
                c.x, c.y = kedalaman, tengah - c.panjang / 2
            c.orientasi = orient
        pos += sepanjang
    return (dinding, awal, total)


def _taruh_bukaan(room, op, mode: int, t: float, info_meja, beds=()) -> None:
    """Tentukan op.posisi (sepanjang dinding op.dinding yang TETAP) dari gen."""
    panjang = room.panjang if op.dinding in ("depan", "belakang") else room.lebar
    margin = STANDARDS["margin_pintu_dari_sudut_m"] if op.tipe == "pintu" else STANDARDS["margin_jendela_dari_sudut_m"]
    lo = margin
    hi = max(panjang - op.lebar - margin, lo)
    tengah = (panjang - op.lebar) / 2

    if mode == 1:
        pos = tengah
    elif mode == 2:
        if op.tipe == "pintu":
            pos = lo
        elif info_meja is not None and NAMA_DINDING[info_meja[0]] == op.dinding:
            pos = info_meja[1] + info_meja[2] / 2 - op.lebar / 2
        else:
            pos = tengah
    elif mode == 3 and op.tipe == "pintu":
        pos = hi
    elif mode == 3:                       # jendela: sejajar tengah bed (REVISI 7)
        sejajar = [f for f in beds if bed_sejajar_dinding(f, op.dinding)]
        if sejajar:
            pusat = sum(tengah_sepanjang_dinding(f.bounding_box(), op.dinding) for f in sejajar) / len(sejajar)
            pos = pusat - op.lebar / 2
        else:
            pos = tengah
    else:
        pos = lo + min(max(t, 0.0), 1.0) * (hi - lo)

    q = STANDARDS["kuantisasi_posisi_m"]
    pos = round(pos / q) * q
    op.posisi = min(max(pos, lo), hi)


def decode(chromosome: Chromosome, layout_template: Layout) -> Layout:
    """Bangun Layout baru dari kromosom (jenis/dimensi furniture tetap)."""
    L = copy.deepcopy(layout_template)
    fs, room = L.furnitures, L.room
    info_lemari = info_meja = None
    prev_bed = None
    bukaan = []

    for unit, (a, b, _c) in zip(daftar_unit(L), chromosome):
        tipe = unit[0]
        if tipe == "bed":
            _taruh_bed(room, fs[unit[1][0]], int(a), int(b), prev_bed)
            prev_bed = fs[unit[1][0]]
        elif tipe == "lemari":
            info_lemari = _taruh_baris(room, [fs[i] for i in unit[1]], int(a) % 4, int(b),
                                       beds=[f for f in fs if f.jenis == JenisFurniture.BED])
        elif tipe == "meja":
            info_meja = _taruh_baris(room, [fs[i] for i in unit[1]], int(a) % 4, int(b),
                                     kursi_items=[fs[i] for i in unit[2]], info_lemari=info_lemari,
                                     beds=[f for f in fs if f.jenis == JenisFurniture.BED])
        else:
            bukaan.append((room.openings[unit[1]], int(a), b))

    for op, mode, t in bukaan:     # bukaan terakhir: jendela bisa menyesuaikan posisi meja
        _taruh_bukaan(room, op, mode, t, info_meja, beds=[f for f in fs if f.jenis == JenisFurniture.BED])
    return L


def random_chromosome(layout_template: Layout) -> Chromosome:
    return [gen_acak(u[0]) for u in daftar_unit(layout_template)]


def init_population(layout_template: Layout, ukuran_populasi: int) -> list[Chromosome]:
    return [random_chromosome(layout_template) for _ in range(ukuran_populasi)]


# ---------------------------------------------------------------------------
# Pemindaian struktur (REVISI 3) - supaya SEMUA pola penempatan ikut diperiksa
# ---------------------------------------------------------------------------

def _opsi_diskrit(tipe: str) -> list[Gene]:
    """Pilihan gen DISKRIT per jenis unit, dipakai untuk memindai semua pola struktur."""
    if tipe == "bed":
        return [(float(p), float(o), 0.0) for p in range(4) for o in (0, 90)]
    if tipe == "lemari":
        return [(float(d), float(a), 0.0) for d in range(4) for a in range(3)]
    if tipe == "meja":
        return [(float(d), float(a), 0.0) for d in range(4) for a in range(5)]
    if tipe == "pintu":
        # REVISI 5: posisi pintu dipindai di beberapa titik sepanjang dinding (tetap di
        # dinding yang sama) -> furniture ikut menyesuaikan letak pintu.
        return [(0.0, t, 0.0) for t in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0)]
    return [(float(m), 0.5, 0.0) for m in (1, 2, 3)]       # jendela: tengah / di atas meja / sejajar tengah bed


def enumerasi_struktur(layout_template: Layout, batas: int = 30000, fase_bukaan: bool = True) -> list[Chromosome]:
    """
    Daftar kromosom yang mencakup SEMUA kombinasi keputusan diskret: bed di pojok
    mana & orientasi apa, lemari di dinding mana (+anchor), meja di dinding mana
    (+anchor), dan (opsional) mode pintu/jendela.

    REVISI 5: bed identik tidak dihitung ganda (kombinasi, bukan permutasi) dan
    pintu/jendela TIDAK ikut dikalikan di fase ini (fase_bukaan=False -> pintu &
    jendela di tengah dinding). Posisi pintu/jendela divariasikan terpisah lewat
    variasi_bukaan() hanya untuk susunan yang menjanjikan. Dengan begitu pindaian
    tetap LENGKAP walau furniture banyak, tidak lagi diambil acak.
    """
    import itertools
    unit = daftar_unit(layout_template)
    bagian_bed = [u for u in unit if u[0] == "bed"]
    lainnya = [u for u in unit if u[0] != "bed"]
    opsi_bed = _opsi_diskrit("bed")
    opsi_sebelah = [(4.0, 0.0, 0.0), (5.0, 0.0, 0.0)]     # bersebelahan dgn bed sebelumnya
    n_bed = len(bagian_bed)
    kombinasi_bed = []
    if n_bed:
        for seq in itertools.product(opsi_bed, *([opsi_bed + opsi_sebelah] * (n_bed - 1))):
            semua_pojok = all(g[0] < 4 for g in seq)
            if semua_pojok and list(seq) != sorted(seq):
                continue                     # bed identik: hindari duplikat permutasi
            kombinasi_bed.append(seq)
    else:
        kombinasi_bed = [()]
    opsi_lain = []
    for u in lainnya:
        if u[0] in ("pintu", "jendela") and not fase_bukaan:
            opsi_lain.append([(1.0, 0.5, 0.0)])
        else:
            opsi_lain.append(_opsi_diskrit(u[0]))
    total = len(kombinasi_bed)
    for o in opsi_lain:
        total *= len(o)
    semua = (list(kb) + list(rest) for kb in kombinasi_bed for rest in itertools.product(*opsi_lain))
    if total <= batas:
        return list(semua)
    return [list(random.choice(kombinasi_bed)) + [random.choice(o) for o in opsi_lain] for _ in range(batas)]


def variasi_bukaan(kromosom: Chromosome, layout_template: Layout) -> list[Chromosome]:
    """Semua variasi posisi pintu (7 titik) x jendela (tengah / di atas meja / tengah bed) untuk 1 susunan furniture."""
    unit = daftar_unit(layout_template)
    idx_pintu = [i for i, u in enumerate(unit) if u[0] == "pintu"]
    idx_jendela = [i for i, u in enumerate(unit) if u[0] == "jendela"]
    import itertools
    opsi = [_opsi_diskrit("pintu") for _ in idx_pintu] + [_opsi_diskrit("jendela") for _ in idx_jendela]
    idx = idx_pintu + idx_jendela
    hasil = []
    for kombinasi in itertools.product(*opsi):
        k = list(kromosom)
        for i, g in zip(idx, kombinasi):
            k[i] = g
        hasil.append(k)
    return hasil
