"""
app.py - CABINFLOW: tampilan web (Streamlit) untuk Software Optimasi Layout Kabin Crew Kapal.

Jalankan lokal :  streamlit run app.py
Tema dasar ada di .streamlit/config.toml (taruh di folder yang sama dengan app.py).
"""

import streamlit as st

from constants import FURNITURE_STANDAR_M
from models import DINDING_VALID
from web_helper import PRESET, bangun_input, jalankan, validasi

st.set_page_config(page_title="CABINFLOW | Optimasi Layout Kabin", page_icon="🚢", layout="wide")

# ---------------------------------------------------------------- BRAND
BLUE, BUTTER, CHOCO, CREAM, GRAY = "#C4D8E8", "#F7E6A1", "#4A2F2E", "#FAF7ED", "#A7A09A"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Poppins:wght@300;400;500;600&display=swap');

:root { --blue:#C4D8E8; --butter:#F7E6A1; --choco:#4A2F2E; --cream:#FAF7ED; --gray:#A7A09A; --line:#E6DFC9; }

html, body, [class*="css"], .stApp, .stMarkdown, label, p, li, input, textarea, button {
    font-family: 'Poppins', sans-serif !important;
}
.stApp { background: var(--cream); color: var(--choco); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1200px; }

h1, h2, h3, h4, .serif { font-family: 'Playfair Display', serif !important; color: var(--choco) !important; letter-spacing: 0; }
h2 { font-size: 1.7rem !important; }
h3 { font-size: 1.25rem !important; }

/* ---------- sidebar */
section[data-testid="stSidebar"] { background: var(--blue); border-right: none; }
section[data-testid="stSidebar"] * { color: var(--choco); }
.nav-item { display:flex; align-items:center; gap:.7rem; padding:.55rem .8rem; border-radius:10px;
            font-size:.88rem; margin-bottom:.25rem; }
.nav-item .no { width:1.5rem; height:1.5rem; border-radius:50%; background:rgba(250,247,237,.7);
                display:flex; align-items:center; justify-content:center; font-size:.72rem; font-weight:600; }
.nav-item.on { background: var(--butter); font-weight:500; }
.nav-item.on .no { background: var(--choco); color: var(--cream); }
.side-note { font-size:.75rem; opacity:.75; margin-top:1.5rem; line-height:1.5; }

/* ---------- hero */
.hero { display:flex; justify-content:space-between; align-items:center; gap:1.5rem; flex-wrap:wrap;
        background: linear-gradient(120deg, #C4D8E8 0%, #A9C6DC 100%); border-radius:18px;
        padding:1.8rem 2rem; margin-bottom:1.6rem; position:relative; overflow:hidden; }
.hero h1 { font-size:2rem !important; margin:0 0 .4rem 0; padding:0; color: var(--choco) !important; }
.hero p { margin:0; max-width:34rem; font-size:.9rem; color: var(--choco); opacity:.85; }
.hero .tagline { font-family:'Playfair Display',serif; font-style:italic; font-size:1.15rem; text-align:right;
                 color: var(--cream); text-shadow: 0 1px 8px rgba(74,47,46,.35); line-height:1.4; }

/* ---------- kartu & section */
div[data-testid="stVerticalBlockBorderWrapper"] { background:#FFFDF6; border:1px solid var(--line) !important;
        border-radius:16px !important; padding:.4rem .6rem; box-shadow: 0 2px 10px rgba(74,47,46,.04); }
.sec-title { display:flex; align-items:baseline; gap:.7rem; margin:1.6rem 0 .6rem 0; }
.sec-title .no { font-size:.8rem; letter-spacing:.14em; color: var(--gray); font-weight:500; }
.sec-title .tt { font-family:'Playfair Display',serif; font-size:1.35rem; font-weight:600; color: var(--choco); }

/* ---------- input */
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
    background:#FFFDF6 !important; border-radius:10px !important; border-color: var(--line) !important; }
div[data-baseweb="input"] input { color: var(--choco) !important; }
label, .stNumberInput label p, .stSelectbox label p, .stCheckbox p, .stRadio label p { color: var(--choco) !important; font-size:.85rem !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: var(--gray) !important; }
.stCheckbox [data-baseweb="checkbox"] > div:first-child { border-radius:5px; }
div[role="radiogroup"] label { background:#FFFDF6; border:1px solid var(--line); border-radius:12px; padding:.45rem 1rem; }

/* ---------- tombol */
.stButton > button, .stDownloadButton > button {
    border-radius:12px; border:1px solid var(--line); background:#FFFDF6; color: var(--choco);
    font-weight:500; padding:.55rem 1.4rem; transition: background .15s, transform .15s; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--butter); background: #FFF6CF; color: var(--choco); }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: var(--butter); border:1px solid #EBD67A; color: var(--choco); font-weight:600; }
.stButton > button[kind="primary"]:hover { background:#F2DC84; border-color:#E3CB63; color: var(--choco); }
.stButton > button:focus-visible { outline:2px solid var(--choco); outline-offset:2px; }

/* ---------- metrik */
div[data-testid="stMetric"] { background:#FFFDF6; border:1px solid var(--line); border-radius:14px; padding:.9rem 1.1rem; }
div[data-testid="stMetricLabel"] p { color: var(--gray) !important; font-size:.78rem !important; }
div[data-testid="stMetricValue"] { font-family:'Playfair Display',serif; color: var(--choco); }

/* ---------- tab */
button[data-baseweb="tab"] { font-weight:500; color: var(--gray); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--choco); }
div[data-baseweb="tab-highlight"] { background: var(--butter) !important; height:3px !important; }

/* ---------- tag / pill */
.pill { display:inline-block; padding:.2rem .8rem; border-radius:999px; font-size:.75rem; font-weight:500; }
.pill.ok { background:#DCEBDD; color:#2F6B3F; }
.pill.warn { background:#FBE9C8; color:#8A5A12; }
.pill.info { background: var(--blue); color: var(--choco); }

/* ---------- alert, tabel, expander */
div[data-testid="stAlert"] { border-radius:12px; }
div[data-testid="stExpander"] { background:#FFFDF6; border:1px solid var(--line); border-radius:14px; }
div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
hr { border-color: var(--line); }
.preview-box { background: var(--blue); border-radius:14px; padding:1rem; display:flex; justify-content:center; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def logo_svg(lebar=120, gelap=False):
    """Logo CABINFLOW (kapal + ombak) sebagai SVG inline."""
    ombak2 = CREAM if gelap else CHOCO
    return f"""
<svg width="{lebar}" viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" aria-label="CABINFLOW">
  <path d="M54 8h12v6H54z" fill="{ombak2}"/><path d="M58 4h5v4h-5z" fill="{ombak2}"/>
  <path d="M40 16h42l-5 8H45z" fill="{ombak2}"/>
  <path d="M16 40C38 24 72 28 104 40C76 36 44 40 20 54Z" fill="{BUTTER}"/>
  <path d="M20 54C46 38 82 44 110 36C102 58 70 68 40 66C30 65 22 62 20 54Z" fill="{ombak2}"/>
</svg>"""


def denah_svg(p, l, d_pintu, d_jendela):
    """Pratinjau denah ruangan sederhana (tampak atas) dengan pintu & jendela."""
    maks = 260
    skala = maks / max(p, l)
    w, h = p * skala, l * skala
    ox, oy = 34, 26
    tebal = 6
    pintu = 0.8 * skala
    svg = [
        f'<svg width="{w + ox + 20:.0f}" height="{h + oy + 24:.0f}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect x="{ox}" y="{oy}" width="{w:.1f}" height="{h:.1f}" fill="{CREAM}" stroke="{CHOCO}" stroke-width="{tebal}"/>',
        f'<text x="{ox + w / 2:.0f}" y="{oy - 9}" text-anchor="middle" font-size="11" fill="{CHOCO}" font-family="Poppins,sans-serif">{p:.2f} m</text>',
        f'<text x="{ox - 12}" y="{oy + h / 2:.0f}" text-anchor="middle" font-size="11" fill="{CHOCO}" font-family="Poppins,sans-serif" '
        f'transform="rotate(-90 {ox - 12} {oy + h / 2:.0f})">{l:.2f} m</text>',
    ]

    def tanda(dinding, warna, panjang):
        cx, cy = ox + w / 2, oy + h / 2
        if dinding in ("depan", "belakang"):
            y = oy + h if dinding == "depan" else oy
            return f'<rect x="{cx - panjang / 2:.1f}" y="{y - tebal / 2 - 1:.1f}" width="{panjang:.1f}" height="{tebal + 2}" fill="{warna}" stroke="{CHOCO}" stroke-width="1"/>'
        x = ox if dinding == "kiri" else ox + w
        return f'<rect x="{x - tebal / 2 - 1:.1f}" y="{cy - panjang / 2:.1f}" width="{tebal + 2}" height="{panjang:.1f}" fill="{warna}" stroke="{CHOCO}" stroke-width="1"/>'

    svg.append(tanda(d_pintu, BUTTER, pintu))
    if d_jendela:
        svg.append(tanda(d_jendela, "#7FA6C9", pintu * 0.9))
    svg.append("</svg>")
    return "".join(svg)


def judul_seksi(no, teks):
    st.markdown(f'<div class="sec-title"><span class="no">{no}</span><span class="tt">{teks}</span></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- SIDEBAR
LANGKAH = ["Data ruangan", "Pintu & jendela", "Furniture", "Crew", "Hasil & alternatif"]
with st.sidebar:
    st.markdown(logo_svg(110) + '<div class="serif" style="font-size:1.4rem;font-weight:700;margin-top:.2rem">CABINFLOW</div>'
                '<div style="font-size:.78rem;opacity:.8;margin-bottom:1.4rem">Crew Cabin Interior Optimization</div>', unsafe_allow_html=True)
    nav = "".join(
        f'<div class="nav-item {"on" if i == 0 else ""}"><span class="no">{i + 1}</span>{t}</div>' for i, t in enumerate(LANGKAH)
    )
    st.markdown(nav, unsafe_allow_html=True)
    st.markdown('<div class="side-note">Algoritma NSGA-II multi-objektif: efisiensi ruang, ergonomi, dan sirkulasi.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- HERO
st.markdown(
    f"""
<div class="hero">
  <div>
    <h1>Optimasi Layout Kabin Crew Kapal</h1>
    <p>Isi data ruangan di bawah, lalu klik <b>Jalankan optimasi</b>. Sistem akan menyusun beberapa alternatif layout
    yang efisien, ergonomis, dan aman untuk bergerak.</p>
  </div>
  <div class="tagline">Better Layout.<br>Safer Movement.<br>More Comfortable Crew.</div>
</div>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- INPUT
judul_seksi("01", "Data ruangan")
kiri, kanan = st.columns([3, 2], gap="large")
with kiri:
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        panjang = c1.number_input("Panjang ruangan (m)", min_value=1.0, max_value=20.0, value=3.8, step=0.1)
        lebar = c2.number_input("Lebar ruangan (m)", min_value=1.0, max_value=20.0, value=2.5, step=0.1)
        tinggi = c3.number_input(
            "Tinggi ruangan (m)", min_value=2.03, max_value=6.0, value=2.40, step=0.05,
            help="Standar minimum 2.03 m (MLC 2006).",
        )
        st.caption(
            "Arah dinding pada denah (tampak atas): **depan** = sisi bawah, **belakang** = sisi atas, "
            "**kiri** = sisi kiri, **kanan** = sisi kanan. Panjang ruangan searah kiri-kanan."
        )

    judul_seksi("02", "Pintu & jendela")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        dinding_pintu = c1.selectbox("Pintu di dinding", DINDING_VALID, index=0)
        ada_jendela = c2.checkbox("Ada jendela?", value=True)
        dinding_jendela = None
        if ada_jendela:
            dinding_jendela = c2.selectbox("Jendela di dinding", DINDING_VALID, index=3)
        c1.caption("Ukuran dan posisi pintu/jendela otomatis mengikuti standar.")

with kanan:
    st.markdown(
        f'<div class="preview-box">{denah_svg(panjang, lebar, dinding_pintu, dinding_jendela)}</div>'
        '<div style="font-size:.75rem;color:#A7A09A;margin-top:.5rem;text-align:center">'
        "Pratinjau denah. Kuning = pintu, biru = jendela.</div>",
        unsafe_allow_html=True,
    )

judul_seksi("03", "Furniture")
with st.container(border=True):
    st.caption("Cukup isi jumlah. Ukuran otomatis dari standar, dan kursi otomatis 1 per meja.")
    default_jumlah = {"bed": 2, "lemari": 2, "meja": 1}
    jenis_input = [j for j in FURNITURE_STANDAR_M if j != "kursi"]
    kolom = st.columns(len(jenis_input))
    furnitures = []
    for kol, jenis in zip(kolom, jenis_input):
        jumlah = kol.number_input(
            f"Jumlah {jenis}", min_value=0, max_value=10, value=default_jumlah.get(jenis, 0), step=1, key=f"jml_{jenis}"
        )
        if jumlah > 0:
            item = {"jenis": jenis, "jumlah": int(jumlah)}
            if jenis == "bed" and jumlah >= 2:
                item["tumpuk"] = kol.checkbox("Bed ditumpuk (bunk bed)?", value=True, key="tumpuk_bed")
            furnitures.append(item)

judul_seksi("04", "Crew")
jenis_crew = st.radio("Jenis crew", ["rating", "officer"], horizontal=True, label_visibility="collapsed")

with st.expander("⚙️ Pengaturan lanjutan"):
    preset = st.select_slider(
        "Kecepatan vs ketelitian", options=list(PRESET), value="Normal",
        help="Cepat = hasil kilat tapi kurang beragam. Teliti = lebih lama, kandidat lebih banyak.",
    )
    jumlah_alternatif = st.slider("Jumlah alternatif layout", 1, 5, 3)

# ---------------------------------------------------------------- JALANKAN
st.write("")
if st.button("🚀 Jalankan optimasi", type="primary"):
    data = bangun_input(panjang, lebar, tinggi, dinding_pintu, dinding_jendela, furnitures, jenis_crew)
    error = validasi(data)
    if error:
        for e in error:
            st.error(e)
    else:
        with st.spinner(f"Menjalankan NSGA-II (mode {preset}). Bisa memakan waktu setengah sampai beberapa menit..."):
            hasil, png = jalankan(data, preset=preset, jumlah_alternatif=jumlah_alternatif)
        st.session_state["hasil"] = hasil
        st.session_state["png"] = png
        st.session_state["data"] = data

# ---------------------------------------------------------------- HASIL
hasil = st.session_state.get("hasil")
if hasil:
    st.divider()
    judul_seksi("05", "Hasil & alternatif")

    if not hasil.get("berhasil", True):
        st.error(hasil.get("pesan", "Optimasi gagal."))
    else:
        m1, m2 = st.columns(2)
        m1.metric("Jumlah crew (dari kapasitas bed)", hasil["jumlah_crew"])
        m2.metric("Alternatif ditemukan", hasil["jumlah_alternatif"])

        if not hasil.get("layout_valid_fisik", True):
            st.error("Ruangan terlalu sempit, ada furniture yang tumpang tindih atau keluar ruangan.")
        if hasil.get("catatan_keragaman"):
            st.info(hasil["catatan_keragaman"])

        if st.session_state.get("png"):
            with st.container(border=True):
                st.image(st.session_state["png"], caption="Perbandingan alternatif layout (tampak atas)", use_container_width=True)

        tabs = st.tabs([f"Alternatif {i + 1}" for i in range(len(hasil["alternatif"]))])
        for tab, alt in zip(tabs, hasil["alternatif"]):
            with tab:
                ok = alt["memenuhi_standar"]
                st.markdown(
                    f'<span class="pill info">Pola: {alt["pola"]}</span> &nbsp;'
                    f'<span class="pill {"ok" if ok else "warn"}">{"Memenuhi standar" if ok else "Perlu ditinjau"}</span>',
                    unsafe_allow_html=True,
                )
                st.write("")
                a, b, c, d = st.columns(4)
                a.metric("Efisiensi ruang", f"{alt['efisiensi_ruang'] * 100:.1f}%")
                b.metric("Skor ergonomi", alt["skor_ergonomi_penalti"], help="0 = ideal, makin besar makin kurang nyaman")
                c.metric("Sirkulasi rata-rata", f"{alt['sirkulasi_rata2_m']} m", help="Makin pendek makin baik")
                d.metric("Memenuhi standar", "Ya ✅" if ok else "Tidak ⚠️")

                for p in alt["peringatan"]:
                    st.warning(p)

                st.markdown("**Posisi furniture** (meter, dari sudut kiri-bawah ruangan)")
                st.dataframe(
                    [
                        {
                            "ID": f["id"], "Jenis": f["jenis"], "x (m)": f["x"], "y (m)": f["y"],
                            "Ditumpuk": "ya" if f["tumpuk"] else "-",
                        }
                        for f in alt["furniture"]
                    ],
                    use_container_width=True, hide_index=True,
                )
                st.markdown("**Pintu & jendela**")
                st.dataframe(
                    [
                        {
                            "Tipe": o["tipe"], "Dinding": o["dinding"],
                            "Mulai dari ujung dinding (m)": o["posisi"], "Lebar (m)": o["lebar"],
                        }
                        for o in alt["bukaan"]
                    ],
                    use_container_width=True, hide_index=True,
                )

        if st.session_state.get("png"):
            st.write("")
            st.download_button("⬇️ Unduh gambar layout (PNG)", st.session_state["png"], "hasil_layout.png", "image/png", type="primary")
