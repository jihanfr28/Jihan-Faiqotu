"""
models.py
Struktur data dasar untuk software optimasi layout kabin crew.

Alur data:
- Room, opening (pintu/jendela), CrewRequirement -> INPUT dari client
- Furniture -> INPUT dari client (jenis & dimensi), tapi (x, y, orientasi)
  adalah VARIABEL KEPUTUSAN yang akan diisi/diubah oleh algoritma optimasi
- Layout -> satu kandidat solusi lengkap (dipakai NSGA-II sebagai "individu")
"""

from dataclasses import dataclass, field
from enum import Enum


def dimensi_efektif(panjang: float, lebar: float, orientasi: float) -> tuple[float, float]:
    """
    Dimensi footprint (lebar_x, lebar_y) SETELAH rotasi. Dipakai bersama oleh
    Furniture.bounding_box() DAN oleh ga_encoding.py/ga_operators.py supaya
    logika klip posisi ke batas ruangan konsisten dengan bounding box asli
    (kalau tidak, furniture bisa "lolos" ke luar ruangan setelah dirotasi -
    ini bug nyata yang pernah kejadian, bukan cuma floating point).
    """
    if orientasi in (90, 270):
        return lebar, panjang
    return panjang, lebar


class JenisFurniture(str, Enum):
    BED = "bed"
    LEMARI = "lemari"
    MEJA = "meja"
    KURSI = "kursi"


# Istilah dinding dipakai relatif terhadap orientasi ruangan/kapal (bukan arah
# mata angin) - supaya client bisa jawab "pintu di depan, jendela di
# belakang" tanpa perlu tahu orientasi kompas kapal. Pemetaan ke sumbu x/y
# ada di constraints.py (opening_zone) dan objectives.py (titik_tengah_bukaan)
# - KEDUANYA HARUS pakai pemetaan yang SAMA, lihat DINDING_VALID di sana.
DINDING_VALID = ["depan", "belakang", "kiri", "kanan"]


@dataclass
class Opening:
    """Elemen tetap di ruangan: pintu atau jendela. Tidak boleh diblokir furniture."""
    tipe: str      # "pintu" atau "jendela"
    dinding: str   # dinding tempat bukaan: "depan" / "belakang" / "kiri" / "kanan"
    posisi: float  # jarak (m) dari sudut awal dinding tsb ke tepi bukaan (biasanya dihitung otomatis, lihat pipeline.py)
    lebar: float   # lebar bukaan (m) - diisi dari STANDARDS, bukan input client langsung


@dataclass
class Room:
    """Ruang kabin yang akan dioptimasi tata letaknya. Input dari client."""
    panjang: float  # meter, sumbu X
    lebar: float    # meter, sumbu Y
    tinggi: float   # meter
    openings: list[Opening] = field(default_factory=list)

    @property
    def luas(self) -> float:
        return self.panjang * self.lebar


@dataclass
class Furniture:
    """
    Satu unit furniture.
    jenis, panjang, lebar, tinggi -> diisi dari katalog standar (constants.py),
                                      BUKAN input manual client (lihat pipeline.py)
    x, y, orientasi                -> variabel keputusan (diisi algoritma optimasi)
    tumpuk, kapasitas               -> KHUSUS bed: tempat tidur tumpuk (bunk bed).
                                      Kalau tumpuk=True, furniture ini merepresentasikan
                                      2 tempat tidur bertingkat yang footprint lantainya
                                      SAMA dengan 1 bed biasa (hemat ruang lantai), tapi
                                      kapasitas=2 (muat 2 crew). Bed biasa: tumpuk=False,
                                      kapasitas=1.
    """
    id: str
    jenis: JenisFurniture
    panjang: float           # meter, dimensi asli sebelum rotasi
    lebar: float             # meter
    tinggi: float = 0.0      # meter (opsional, untuk cek headroom/tabrakan vertikal nanti)
    x: float = 0.0           # posisi x pojok kiri-bawah (m)
    y: float = 0.0           # posisi y pojok kiri-bawah (m)
    orientasi: float = 0.0   # derajat: 0, 90, 180, atau 270.
                             # BED   : 0/180 = sisi panjang sejajar sumbu X, 90/270 = sejajar sumbu Y
                             # LEMARI/MEJA: arah MENGHADAP (sisi depan), sekaligus dinding tempatnya menempel:
                             #   0   = menempel dinding depan   (y=0),       menghadap +Y
                             #   90  = menempel dinding kanan   (x=panjang), menghadap -X
                             #   180 = menempel dinding belakang(y=lebar),   menghadap -Y
                             #   270 = menempel dinding kiri    (x=0),       menghadap +X
    tumpuk: bool = False     # True = bed tumpuk/bunk bed (lihat docstring di atas)
    kapasitas: int = 1       # jumlah crew yang ditampung furniture ini (bed tumpuk = 2)

    @property
    def luas(self) -> float:
        return self.panjang * self.lebar

    def bounding_box(self) -> tuple[float, float, float, float]:
        """
        Footprint axis-aligned (xmin, ymin, xmax, ymax) setelah rotasi.
        Untuk rotasi 90/270 derajat, panjang & lebar tertukar posisinya.
        """
        p, l = dimensi_efektif(self.panjang, self.lebar, self.orientasi)
        return (self.x, self.y, self.x + p, self.y + l)


@dataclass
class CrewRequirement:
    """Kebutuhan crew untuk cabin ini. Input dari client."""
    jumlah_crew: int
    jenis_crew: str = "rating"  # "rating" atau "officer" -> menentukan luas_min yang berlaku


@dataclass
class Layout:
    """
    Satu kandidat solusi lengkap: ruang + susunan seluruh furniture di dalamnya.
    Ini yang nanti jadi representasi "individu" (chromosome) di NSGA-II.
    """
    room: Room
    furnitures: list[Furniture]
    crew: CrewRequirement
