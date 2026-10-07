"""
app.py - Tampilan web (Streamlit) untuk Software Optimasi Layout Kabin Crew Kapal.

Jalankan lokal :  streamlit run app.py
"""

import streamlit as st

from constants import FURNITURE_STANDAR_M
from models import DINDING_VALID
from web_helper import PRESET, bangun_input, jalankan, validasi

st.set_page_config(page_title="Optimasi Layout Kabin Kapal", page_icon="🚢", layout="wide")

st.title("🚢 Optimasi Layout Kabin Crew Kapal")
st.caption(
    "Algoritma NSGA-II multi-objektif: efisiensi ruang, ergonomi, dan sirkulasi. "
    "Isi data ruangan di bawah, lalu klik **Jalankan optimasi**."
)

# ---------------------------------------------------------------- INPUT
st.subheader("1. Data ruangan")
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

st.subheader("2. Pintu & jendela")
c1, c2 = st.columns(2)
dinding_pintu = c1.selectbox("Pintu di dinding", DINDING_VALID, index=0)
ada_jendela = c2.checkbox("Ada jendela?", value=True)
dinding_jendela = None
if ada_jendela:
    dinding_jendela = c2.selectbox("Jendela di dinding", DINDING_VALID, index=3)
c1.caption("Ukuran dan posisi pintu/jendela otomatis mengikuti standar.")

st.subheader("3. Furniture")
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

st.subheader("4. Crew")
jenis_crew = st.radio("Jenis crew", ["rating", "officer"], horizontal=True)

with st.expander("⚙️ Pengaturan lanjutan"):
    preset = st.select_slider(
        "Kecepatan vs ketelitian", options=list(PRESET), value="Normal",
        help="Cepat = hasil kilat tapi kurang beragam. Teliti = lebih lama, kandidat lebih banyak.",
    )
    jumlah_alternatif = st.slider("Jumlah alternatif layout", 1, 5, 3)

# ---------------------------------------------------------------- JALANKAN
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
    st.header("Hasil optimasi")

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
            st.image(st.session_state["png"], caption="Perbandingan alternatif layout (tampak atas)", use_container_width=True)

        tabs = st.tabs([f"Alternatif {i + 1}" for i in range(len(hasil["alternatif"]))])
        for tab, alt in zip(tabs, hasil["alternatif"]):
            with tab:
                st.markdown(f"**Pola:** {alt['pola']}")
                a, b, c, d = st.columns(4)
                a.metric("Efisiensi ruang", f"{alt['efisiensi_ruang'] * 100:.1f}%")
                b.metric("Skor ergonomi", alt["skor_ergonomi_penalti"], help="0 = ideal, makin besar makin kurang nyaman")
                c.metric("Sirkulasi rata-rata", f"{alt['sirkulasi_rata2_m']} m", help="Makin pendek makin baik")
                d.metric("Memenuhi standar", "Ya ✅" if alt["memenuhi_standar"] else "Tidak ⚠️")

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
            st.subheader("Unduh hasil")
            st.download_button("⬇️ Gambar layout (PNG)", st.session_state["png"], "hasil_layout.png", "image/png")
