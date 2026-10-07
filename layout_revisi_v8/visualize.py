"""
visualize.py (REVISI)
Visualisasi 2D (top-view) layout kabin, gaya seperti contoh client:
ruangan abu-abu, bed biru, lemari oranye, meja hijau, kursi ungu,
pintu merah & jendela biru muda lengkap dengan labelnya.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from models import Layout, JenisFurniture
from constants import STANDARDS
from constraints import zona_depan

WARNA_FURNITURE = {
    JenisFurniture.BED: "#33b5ff",
    JenisFurniture.LEMARI: "#ffb85c",
    JenisFurniture.MEJA: "#b8f562",
    JenisFurniture.KURSI: "#c86be6",
}
WARNA_RUANG = "#8f8f8f"
WARNA_PINTU = "#ff3b3b"
WARNA_JENDELA = "#4fd8e8"


def _gambar_bukaan(ax, room, opening):
    """Pintu/jendela = garis tebal di dinding + label di luar ruangan."""
    warna = WARNA_PINTU if opening.tipe == "pintu" else WARNA_JENDELA
    a, b = opening.posisi, opening.posisi + opening.lebar
    off = 0.14
    kw = dict(color=warna, linewidth=5, solid_capstyle="butt", zorder=5)
    tk = dict(ha="center", va="center", fontsize=8)
    if opening.dinding == "depan":
        ax.plot([a, b], [0, 0], **kw);                      ax.text((a + b) / 2, -off, opening.tipe, **tk)
    elif opening.dinding == "belakang":
        ax.plot([a, b], [room.lebar, room.lebar], **kw);    ax.text((a + b) / 2, room.lebar + off, opening.tipe, **tk)
    elif opening.dinding == "kiri":
        ax.plot([0, 0], [a, b], **kw);                      ax.text(-off, (a + b) / 2, opening.tipe, rotation=90, **tk)
    elif opening.dinding == "kanan":
        ax.plot([room.panjang, room.panjang], [a, b], **kw); ax.text(room.panjang + off, (a + b) / 2, opening.tipe, rotation=90, **tk)


def plot_layout(layout: Layout, ax=None, title: str = None, tampilkan_akses: bool = True):
    """Gambar satu Layout (ruangan + furniture) ke sebuah matplotlib Axes.
    tampilkan_akses=True: gambar area akses ideal (buka lemari = oranye putus-putus,
    tarik kursi = ungu putus-putus) supaya terlihat apakah muat."""
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 4.5))
    room = layout.room

    ruang = patches.Rectangle((0, 0), room.panjang, room.lebar,
                              facecolor=WARNA_RUANG, edgecolor="#555555", linewidth=2, zorder=1)
    ax.add_patch(ruang)

    if tampilkan_akses:
        for f in layout.furnitures:
            if f.jenis == JenisFurniture.LEMARI:
                z, warna = zona_depan(f, STANDARDS["clearance_lemari_ideal_m"]), "#ffb85c"
            elif f.jenis == JenisFurniture.KURSI:
                z, warna = zona_depan(f, STANDARDS["tarik_kursi_ideal_m"]), "#d18bff"
            else:
                continue
            zp = patches.Rectangle((z[0], z[1]), z[2] - z[0], z[3] - z[1], facecolor=warna, alpha=0.22,
                                   edgecolor="white", linestyle="--", linewidth=1.2, zorder=2)
            ax.add_patch(zp)
            zp.set_clip_path(ruang)
    for opening in room.openings:
        _gambar_bukaan(ax, room, opening)

    for f in layout.furnitures:
        xmin, ymin, xmax, ymax = f.bounding_box()
        ax.add_patch(patches.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                                       facecolor=WARNA_FURNITURE.get(f.jenis, "#adb5bd"),
                                       edgecolor="#333333" if f.tumpuk else "none",
                                       linewidth=1.5, linestyle="--" if f.tumpuk else "-", zorder=3))
        label = f.jenis.value if not f.tumpuk else f"{f.jenis.value}\n(tumpuk)"
        ax.text((xmin + xmax) / 2, (ymin + ymax) / 2, label, ha="center", va="center",
                fontsize=8, zorder=4,
                rotation=90 if (f.jenis == JenisFurniture.BED and (xmax - xmin) < (ymax - ymin)) else 0)

    ax.set_xlim(-0.35, room.panjang + 0.35)
    ax.set_ylim(-0.35, room.lebar + 0.35)
    ax.set_aspect("equal")
    ax.set_xlabel("panjang (m)", fontsize=8)
    ax.set_ylabel("lebar (m)", fontsize=8)
    ax.tick_params(labelsize=7)
    if title:
        ax.set_title(title, fontsize=10, weight="bold")
    return ax


def plot_beberapa_layout(layouts: list[Layout], judul_list: list[str], simpan_ke: str = None):
    """Gambar beberapa Layout berdampingan (untuk bandingkan alternatif)."""
    n = len(layouts)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4.8))
    if n == 1:
        axes = [axes]
    for ax, layout, judul in zip(axes, layouts, judul_list):
        plot_layout(layout, ax=ax, title=judul)
    fig.tight_layout()
    fig.text(0.5, -0.045, "area transparan = ruang akses ideal: buka lemari (oranye, %.2f m) & tarik kursi (ungu, %.2f m)" % (STANDARDS["clearance_lemari_ideal_m"], STANDARDS["tarik_kursi_ideal_m"]),
             ha="center", fontsize=8, color="#444444")
    if simpan_ke:
        fig.savefig(simpan_ke, dpi=150, bbox_inches="tight")
    return fig
