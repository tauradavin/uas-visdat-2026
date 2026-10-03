"""
UAS Visualisasi Data dan Informasi
Topik: (1) Geospasial, (2) Berhierarki, (3) Aliran/Flow
Sumber data utama: BPS (Badan Pusat Statistik)

Jalankan:
    streamlit run app.py
"""

import json
import math
import re
import textwrap
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image, ImageDraw, ImageFont

# =========================================================
# KONFIGURASI HALAMAN
# =========================================================
BASE_DIR = Path(__file__).resolve().parent

LOGO_STIS = str(BASE_DIR / "gambar" / "stis.PNG")
DATA_DIR = BASE_DIR / "Data"
CSV_MIGRASI = DATA_DIR / "migrasi_risen_wide.csv"

try:
    ikon_halaman = Image.open(LOGO_STIS).convert("RGBA")
    ikon_halaman.thumbnail((128, 128))
except Exception:
    ikon_halaman = "📊"

st.set_page_config(
    page_title="Dashboard Indikator Makro Indonesia: Potret Kemiskinan, Ekonomi, dan Migrasi",
    page_icon=ikon_halaman,
    layout="wide",
)

# =========================================================
# TEMA VISUAL
# =========================================================
CSS_PATH = Path(__file__).resolve().parent / "style.css"


def inject_bps_theme():
    with open(CSS_PATH, encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _cari_font(ukuran):
    for nama in ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]:
        try:
            return ImageFont.truetype(nama, ukuran)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=ukuran)
    except TypeError:
        return ImageFont.load_default()


@st.cache_data
def buat_logo_dengan_teks(path_logo, baris1, baris2):
    """Gabungkan logo + garis aksen oranye + dua baris teks menjadi satu gambar transparan."""
    logo = Image.open(path_logo).convert("RGBA")
    tinggi = 160
    lebar_logo = int(logo.width * tinggi / logo.height)
    logo = logo.resize((lebar_logo, tinggi), Image.LANCZOS)

    font = _cari_font(50)
    ukur = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lebar_teks = int(max(ukur.textlength(baris1, font=font), ukur.textlength(baris2, font=font)))

    jarak, tebal_bar = 26, 10
    x_bar = lebar_logo + jarak
    x_teks = x_bar + tebal_bar + 16
    kanvas = Image.new("RGBA", (x_teks + lebar_teks + 8, tinggi), (0, 0, 0, 0))
    kanvas.paste(logo, (0, 0), logo)

    d = ImageDraw.Draw(kanvas)
    d.rectangle([x_bar, 22, x_bar + tebal_bar, tinggi - 22], fill=(247, 148, 29, 255))
    for teks, y in ((baris1, 12), (baris2, 84)):
        kotak = d.textbbox((0, 0), teks, font=font)
        d.text(
            (x_teks - kotak[0], y - kotak[1] + (62 - (kotak[3] - kotak[1])) // 2),
            teks, font=font, fill=(255, 255, 255, 255),
        )
    return kanvas


inject_bps_theme()
st.markdown('<div id="paling-atas"></div>', unsafe_allow_html=True)

try:
    st.logo(
        buat_logo_dengan_teks(LOGO_STIS, "Dashboard", "Visualisasi Data"),
        icon_image=LOGO_STIS,      # saat sidebar dilipat, hanya logo yang tampil
        size="large",
    )
except Exception:
    with st.sidebar:
        st.caption("Logo STIS tidak ditemukan, cek path file.")

st.title("Dashboard Indikator Makro Indonesia: Potret Kemiskinan, Ekonomi, dan Migrasi")
st.caption(
    "UAS Visualisasi Data dan Informasi — Tiga topik: "
    "Geospasial, Berhierarki, dan Aliran/Flow"
)

# =========================================================
# PALET WARNA RAMAH BUTA WARNA
# =========================================================
CB_PALETTE = [
    "#0072B2", "#E69F00", "#009E73", "#CC79A7",
    "#D55E00", "#56B4E9", "#F0E442", "#000000",
]

PLOT_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": "hover",
    "displaylogo": False,
}

# =========================================================
# PENYESUAIAN TAMPILAN PONSEL
# Semua penyesuaian di bagian ini HANYA aktif bila ES_PONSEL = True.
# Di laptop/desktop nilainya False, sehingga tampilan tidak berubah sama sekali.
#   - Deteksi otomatis lewat User-Agent peramban.
#   - Untuk menguji di laptop, tambahkan ?mobile=1 pada URL
#     (atau ?mobile=0 untuk memaksa tampilan laptop).
# =========================================================
def deteksi_ponsel():
    """True bila halaman dibuka dari ponsel (atau dipaksa lewat ?mobile=1)."""
    try:
        paksa = str(st.query_params.get("mobile", "")).lower()
        if paksa in ("1", "true", "ya"):
            return True
        if paksa in ("0", "false", "tidak"):
            return False
    except Exception:
        pass
    try:
        ua = st.context.headers.get("User-Agent", "") or ""
    except Exception:
        return False
    return any(k in ua for k in ("Mobi", "iPhone", "iPod"))


ES_PONSEL = deteksi_ponsel()

# Di ponsel: toolbar Plotly disembunyikan (menutupi judul dan sulit diketuk)
CONFIG_PONSEL = {"displayModeBar": False, "displaylogo": False}


def _bungkus_judul(teks, lebar=38):
    """Judul grafik dipotong ke beberapa baris agar tidak terpotong di layar sempit."""
    teks = (teks or "").replace("<br>", " ").strip()
    return "<br>".join(textwrap.wrap(teks, width=lebar)) if teks else ""


def _colorbar_horizontal(**tambahan):
    """Colorbar mendatar agar tidak memakan lebar layar ponsel."""
    cb = dict(
        orientation="h", x=0.5, xanchor="center", ypad=6,
        len=0.9, thickness=10,
        title=dict(side="top", font=dict(size=10)),
        tickfont=dict(size=10),
    )
    cb.update(tambahan)
    return cb


def _sesuaikan_ponsel(fig):
    """Ukuran, margin, judul, dan colorbar yang cocok untuk layar ponsel (sekitar 360-430 px)."""
    jenis = fig.data[0].type if len(fig.data) else ""
    judul = fig.layout.title.text if (fig.layout.title and fig.layout.title.text) else ""
    judul_b = _bungkus_judul(judul)
    n_baris = judul_b.count("<br>") + 1 if judul_b else 0
    t_judul = 12 + 17 * n_baris if n_baris else 8     # ruang atas untuk judul

    fig.update_layout(
        font=dict(size=11),
        title=dict(
            text=judul_b, x=0.01, xanchor="left", y=0.99, yanchor="top",
            font=dict(size=13), pad=dict(t=4, l=4),
        ),
    )

    if jenis in ("choroplethmapbox", "scattermapbox"):
        # Peta: lebih pendek (agar halaman tetap bisa digulir), zoom awal diturunkan
        # karena layar lebih sempit, colorbar mendatar di bawah peta.
        zoom = fig.layout.mapbox.zoom
        zoom = DEFAULT_ZOOM if zoom is None else zoom
        fig.update_layout(
            height=460,
            margin=dict(l=0, r=0, t=t_judul, b=70),
            mapbox_zoom=max(1.5, zoom - 1.1),
            coloraxis_colorbar=_colorbar_horizontal(y=0, yanchor="top"),
        )

    elif jenis in ("treemap", "sunburst"):
        fig.update_layout(height=560, margin=dict(l=0, r=0, t=t_judul, b=90))
        fig.update_traces(
            textfont=dict(size=10),
            marker_colorbar=_colorbar_horizontal(y=0, yanchor="top"),
        )

    elif jenis == "sankey":
        tinggi = fig.layout.height or 600
        fig.update_layout(
            height=int(max(480, min(900, tinggi * 0.8))),
            margin=dict(l=6, r=6, t=t_judul + 38, b=14),
            font=dict(size=10),
        )
        fig.update_traces(node_pad=10, node_thickness=12)

        def _ringkas(a):
            t = (a.text or "").lower()
            if "tujuan" in t:
                a.update(text="<b>Tujuan (sekarang)</b>", font=dict(size=11))
            elif "asal" in t:
                a.update(text="<b>Asal (5 th lalu)</b>", font=dict(size=11))

        fig.for_each_annotation(_ringkas)

    elif jenis == "heatmap":
        n_baris_h = len(fig.data[0].y) if fig.data[0].y is not None else 20
        ukuran_tick = 9 if n_baris_h <= 20 else 8
        fig.update_layout(
            height=int(max(380, min(820, 19 * n_baris_h + 210))),
            margin=dict(l=4, r=6, t=t_judul + 52, b=6),
        )
        fig.update_xaxes(
            tickfont=dict(size=ukuran_tick),
            title=dict(font=dict(size=10), standoff=4),
        )
        fig.update_yaxes(
            tickfont=dict(size=ukuran_tick),
            title=dict(font=dict(size=10), standoff=4),
        )
        fig.update_traces(colorbar=_colorbar_horizontal(y=1.0, yanchor="bottom"))

    elif jenis == "scatter":
        fig.update_layout(
            height=340,
            margin=dict(l=0, r=0, t=t_judul + 4, b=0),
            legend=dict(font=dict(size=10)),
        )
        fig.update_yaxes(title_font=dict(size=10))


def tampilkan_plot(fig, **kwargs):
    """Tampilkan figure Plotly dengan latar transparan agar menyatu dengan background halaman."""
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    if ES_PONSEL:
        _sesuaikan_ponsel(fig)
        kwargs["config"] = {**(kwargs.get("config") or {}), **CONFIG_PONSEL}
    kwargs.setdefault("use_container_width", True)
    st.plotly_chart(fig, **kwargs)


# =========================================================
# KONFIGURASI & FUNGSI TOPIK 1: GEOSPASIAL
# =========================================================
GEO_PATH = Path(__file__).resolve().parent / "geo_ipm_miskin.geojson"
TAHUN = [2020, 2021, 2022, 2023, 2024]
MAP_STYLE = "open-street-map"   # alternatif polos: "white-bg"

DEFAULT_CENTER = {"lat": -2.5, "lon": 118}
DEFAULT_ZOOM = 3.4

WARNA_IPM = "#0072B2"
WARNA_MISKIN = "#D55E00"


@st.cache_data
def load_geo_data():
    gdf = gpd.read_file(GEO_PATH)
    for t in TAHUN:
        gdf[f"ipm_{t}"] = pd.to_numeric(gdf[f"ipm_{t}"], errors="coerce")
        gdf[f"miskin_{t}"] = pd.to_numeric(gdf[f"miskin_{t}"], errors="coerce")
    gdf["provinsi_label"] = gdf["provinsi_bps"].fillna("-").str.title()
    gdf["centroid_lon"] = gdf.geometry.centroid.x
    gdf["centroid_lat"] = gdf.geometry.centroid.y
    gdf = gdf.reset_index(drop=True)
    geojson_dict = json.loads(gdf[["geometry"]].to_json())
    return gdf, geojson_dict


def fmt_val(x):
    return "n/a" if pd.isna(x) else f"{x:.2f}"


def fmt_delta(now, prev):
    """Selisih terhadap tahun sebelumnya, mis. ' (▲ +0.35)'."""
    if pd.isna(now) or pd.isna(prev):
        return ""
    d = now - prev
    simbol = "▲" if d > 0 else ("▼" if d < 0 else "▬")
    return f" ({simbol} {d:+.2f})"


def hitung_tampilan_peta(gdf_sub):
    """Hitung pusat & zoom peta agar pas dengan batas wilayah yang difilter."""
    if gdf_sub.empty:
        return DEFAULT_CENTER, DEFAULT_ZOOM
    minx, miny, maxx, maxy = gdf_sub.total_bounds
    center = {"lat": (miny + maxy) / 2, "lon": (minx + maxx) / 2}
    lon_span = max(maxx - minx, 0.05) * 1.25
    lat_span = max(maxy - miny, 0.05) * 1.25
    zoom_lon = math.log2(774 / lon_span)
    zoom_lat = math.log2(422 / lat_span)
    zoom = max(3.0, min(zoom_lon, zoom_lat, 10.0))
    return center, zoom


# =========================================================
# KONFIGURASI & FUNGSI TOPIK 2: BERHIERARKI
# =========================================================
DATA_DIR = Path(__file__).resolve().parent / "Data"
# Untuk deploy, ganti menjadi: DATA_DIR = Path(__file__).resolve().parent / "Data"
TAHUN_PDB = [2020, 2021, 2022, 2023, 2024]
FILE_GROWTH = DATA_DIR / "pertumbuhan_pdb_adhk2010_2020_2024.csv"


def file_pdb(t):
    """Cari file PDB ADHB tahun t di DATA_DIR (tahan terhadap beda spasi pada nama file)."""
    kandidat = sorted(
        p for p in DATA_DIR.glob("*.csv")
        if "produk domestik bruto" in p.name.lower()
        and "harga berlaku" in p.name.lower()
        and str(t) in p.name
    )
    if not kandidat:
        raise FileNotFoundError(
            f"File PDB ADHB tahun {t} tidak ditemukan di {DATA_DIR}. "
            "Pastikan nama file memuat 'Produk Domestik Bruto', 'Harga Berlaku', dan tahunnya."
        )
    return kandidat[0]


# Baris utama = diawali kode huruf (A-Q, "M,N", "R,S,T,U"); sub-baris diawali angka / a. b. c.
KODE_UTAMA = r"^(R,S,T,U|M,N|[A-Q])"

# Pengelompokan sektor (asumsi umum tiga sektor; ubah di sini bila dosen meminta lain)
LAPUS_SEKTOR = {
    "A": "Primer", "B": "Primer",
    "C": "Sekunder", "D": "Sekunder", "E": "Sekunder", "F": "Sekunder",
    "G": "Tersier", "H": "Tersier", "I": "Tersier", "J": "Tersier",
    "K": "Tersier", "L": "Tersier", "M,N": "Tersier", "O": "Tersier",
    "P": "Tersier", "Q": "Tersier", "R,S,T,U": "Tersier",
}
LAPUS_PENDEK = {
    "A": "Pertanian, Kehutanan & Perikanan", "B": "Pertambangan & Penggalian",
    "C": "Industri Pengolahan", "D": "Listrik & Gas", "E": "Air, Sampah & Daur Ulang",
    "F": "Konstruksi", "G": "Perdagangan & Reparasi", "H": "Transportasi & Pergudangan",
    "I": "Akomodasi & Makan Minum", "J": "Informasi & Komunikasi",
    "K": "Jasa Keuangan & Asuransi", "L": "Real Estat", "M,N": "Jasa Perusahaan",
    "O": "Adm. Pemerintahan & Pertahanan", "P": "Jasa Pendidikan",
    "Q": "Jasa Kesehatan & Sosial", "R,S,T,U": "Jasa Lainnya",
}


def ke_angka(x):
    """Ubah teks angka ke float. Tahan terhadap tanda catatan kaki (mis. ' (*)')
    dan berbagai format: 2115494.5 / 2115494,5 / 2.115.494,5 / 2,115,494.5"""
    s = re.sub(r"[^0-9,.\-]", "", str(x))   # buang spasi & tanda seperti " (*)"
    if s in ("", "-", ".", ","):
        return np.nan
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):      # 2.115.494,5
            s = s.replace(".", "").replace(",", ".")
        else:                                # 2,115,494.5
            s = s.replace(",", "")
    elif s.count(",") > 1:
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    return pd.to_numeric(s, errors="coerce")


def parse_pdb_adhb(path, tahun):
    """Ambil 17 lapus utama dari satu file PDB ADHB (sub-lapus & baris total dibuang)."""
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = ["lapus_raw", "nilai"]
    df["baris1"] = df["lapus_raw"].fillna("").astype(str).str.split("\n").str[0].str.strip()
    # Baris "Nilai Tambah Bruto" dst. (total, pajak, PDB, catatan kaki) dibuang
    idx_ntb = df.index[df["baris1"].str.contains("Nilai Tambah Bruto", case=False, na=False)][0]
    df = df.loc[: idx_ntb - 1]
    df = df[df["baris1"].str.match(KODE_UTAMA, na=False)].copy()
    df["kode"] = df["baris1"].str.extract(KODE_UTAMA)[0]
    df["nilai_miliar"] = df["nilai"].map(ke_angka)
    df["tahun"] = tahun
    return df[["kode", "tahun", "nilai_miliar"]]


@st.cache_data
def load_hier_data():
    g = pd.read_csv(FILE_GROWTH, encoding="utf-8-sig")
    g = g.dropna(subset=["Kode"]).rename(columns={"Kode": "kode", "Lapangan Usaha": "lapus"})
    g = g.melt(id_vars=["kode", "lapus"], var_name="tahun", value_name="pertumbuhan")
    g["tahun"] = g["tahun"].str.extract(r"(\d{4})")[0].astype(int)

    pdb = pd.concat([parse_pdb_adhb(file_pdb(t), t) for t in TAHUN_PDB], ignore_index=True)

    df = pdb.merge(g, on=["kode", "tahun"], how="inner")
    df["nilai_triliun"] = df["nilai_miliar"] / 1000
    df["sektor"] = df["kode"].map(LAPUS_SEKTOR)
    df["label"] = df["kode"] + ". " + df["kode"].map(LAPUS_PENDEK)
    return df


def bangun_node(d):
    """Susun node hierarki: sektor (induk) dan lapus (anak)."""
    total = d["nilai_triliun"].sum()
    simpul = []
    for sektor, sub in d.groupby("sektor", sort=False):
        nilai_s = sub["nilai_triliun"].sum()
        # Pertumbuhan sektor = rata-rata tertimbang (bobot: nilai PDB ADHB)
        tumbuh_s = (sub["nilai_triliun"] * sub["pertumbuhan"]).sum() / nilai_s
        simpul.append(dict(
            id=sektor, label=f"Sektor {sektor}", parent="", nilai=nilai_s,
            tumbuh=tumbuh_s, nama=f"Sektor {sektor}", share=nilai_s / total * 100,
        ))
        for r in sub.itertuples():
            simpul.append(dict(
                id=f"{sektor}|{r.kode}", label=r.label, parent=sektor, nilai=r.nilai_triliun,
                tumbuh=r.pertumbuhan, nama=r.lapus, share=r.nilai_triliun / total * 100,
            ))
    return pd.DataFrame(simpul)


def buat_figure_hier(d, representasi, tahun, batas):
    n = bangun_node(d)
    customdata = list(zip(
        n["nama"],
        n["nilai"].map(lambda x: f"{x:,.1f}"),
        n["share"].map(lambda x: f"{x:.1f}%"),
        n["tumbuh"].map(lambda x: f"{x:+.2f}%"),
    ))
    marker = dict(
        colors=n["tumbuh"], colorscale="RdBu", cmid=0, cmin=-batas, cmax=batas,
        showscale=True,
        colorbar=dict(title="Pertumbuhan<br>(% y-o-y)"),
        line=dict(width=1, color="white"),
    )
    hover = (
        "<b>%{customdata[0]}</b><br>"
        "──────────────<br>"
        "PDB (ADHB): <b>Rp %{customdata[1]} T</b><br>"
        "Porsi: <b>%{customdata[2]}</b><br>"
        "Pertumbuhan: <b>%{customdata[3]}</b>"
        "<extra></extra>"
    )
    kwargs = dict(
        ids=n["id"], labels=n["label"], parents=n["parent"], values=n["nilai"],
        branchvalues="total", customdata=customdata, marker=marker,
        hovertemplate=hover, texttemplate="<b>%{label}</b><br>%{customdata[2]}",
    )

    if representasi == "Treemap":
        trace = go.Treemap(**kwargs, tiling=dict(pad=3))
        judul = f"Treemap PDB Menurut Lapangan Usaha, {tahun} (ukuran = PDB ADHB, warna = pertumbuhan)"
    else:
        trace = go.Sunburst(**kwargs, insidetextorientation="radial")
        judul = f"Sunburst PDB Menurut Lapangan Usaha, {tahun} (ukuran = PDB ADHB, warna = pertumbuhan)"

    fig = go.Figure(trace)
    fig.update_layout(
        title=judul,
        height=700,
        margin={"t": 50, "l": 0, "r": 0, "b": 100},
    )
    return fig


# =========================================================
# KONFIGURASI & FUNGSI TOPIK 3: ALIRAN / FLOW
# =========================================================
CSV_MIGRASI = Path(__file__).resolve().parent / "Data" / "migrasi_risen_wide.csv"


@st.cache_data
def load_migrasi(path):
    wide = pd.read_csv(path, encoding="utf-8-sig")
    wide = wide.rename(columns={wide.columns[0]: "tujuan"})
    wide = wide[wide["tujuan"] != "Jumlah"]                      # buang baris total
    long = (wide.drop(columns=["Jumlah"])                        # buang kolom total
                .melt(id_vars="tujuan", var_name="asal", value_name="jumlah"))
    long["jumlah"] = pd.to_numeric(long["jumlah"], errors="coerce").fillna(0).astype(int)
    # buang yang tidak pindah (diagonal) dan sel kosong
    return long[(long["asal"] != long["tujuan"]) & (long["jumlah"] > 0)]


def hex_to_rgba(warna, alpha=0.45):
    if isinstance(warna, str) and warna.startswith("#") and len(warna) == 7:
        r, g, b = (int(warna[i:i+2], 16) for i in (1, 3, 5))
        return f"rgba({r},{g},{b},{alpha})"
    return "rgba(150,150,150,0.4)"


LUAR_NEGERI = "Lainnya/Luar Negeri"
WILAYAH = {
    "Sumatera": ["Aceh", "Sumatera Utara", "Sumatera Barat", "Riau", "Jambi",
                 "Sumatera Selatan", "Bengkulu", "Lampung",
                 "Kep. Bangka Belitung", "Kepulauan Riau"],
    "Jawa": ["DKI Jakarta", "Jawa Barat", "Jawa Tengah", "DI Yogyakarta",
             "Jawa Timur", "Banten"],
    "Bali & Nusa Tenggara": ["Bali", "Nusa Tenggara Barat", "Nusa Tenggara Timur"],
    "Kalimantan": ["Kalimantan Barat", "Kalimantan Tengah", "Kalimantan Selatan",
                   "Kalimantan Timur", "Kalimantan Utara"],
    "Sulawesi": ["Sulawesi Utara", "Sulawesi Tengah", "Sulawesi Selatan",
                 "Sulawesi Tenggara", "Gorontalo", "Sulawesi Barat"],
    "Maluku & Papua": ["Maluku", "Maluku Utara", "Papua Barat", "Papua"],
}
URUTAN_PROV = [p for ps in WILAYAH.values() for p in ps]

# =========================================================
# MUAT SEMUA DATA
# =========================================================
gdf_geo, geojson_geo = load_geo_data()
df_hier_all = load_hier_data()
df_migrasi = load_migrasi(CSV_MIGRASI) if CSV_MIGRASI.exists() else None

# Jumlah kab/kota yang benar-benar terpetakan (punya data IPM tahun terakhir), untuk footer
n_peta = int(gdf_geo[f"ipm_{TAHUN[-1]}"].notna().sum())

# =========================================================
# SIDEBAR INFO
# =========================================================
with st.sidebar:
    st.markdown("### Tentang Dashboard")
    st.markdown(
        "Dashboard ini dibuat untuk UAS **Visualisasi Data dan Informasi**, "
        "Politeknik Statistika STIS, menampilkan tiga topik: sebaran spasial "
        "kesejahteraan, struktur ekonomi, dan pola migrasi penduduk Indonesia."
    )
    st.markdown("---")
    st.markdown("**Sumber data:** BPS (Badan Pusat Statistik)")
    st.markdown("**Dibuat dengan:** Streamlit + Plotly")

# =========================================================
# PEMILIH TAHUN GLOBAL + KPI RINGKAS (berubah mengikuti tahun)
# =========================================================
tahun_kpi = st.select_slider(
    "📅 Tahun data (berlaku untuk KPI, peta, dan struktur PDB):",
    options=TAHUN, value=TAHUN[-1], key="tahun_global",
)
tahun_prev = tahun_kpi - 1 if tahun_kpi > TAHUN[0] else None

kpi_ipm = gdf_geo[f"ipm_{tahun_kpi}"].mean()
kpi_miskin = gdf_geo[f"miskin_{tahun_kpi}"].mean()
pdb_per_tahun = df_hier_all.groupby("tahun")["nilai_triliun"].sum()
kpi_pdb = pdb_per_tahun.get(tahun_kpi, np.nan)

if tahun_prev:
    d_kpi_ipm = f"{kpi_ipm - gdf_geo[f'ipm_{tahun_prev}'].mean():+.2f}"
    d_kpi_mis = f"{kpi_miskin - gdf_geo[f'miskin_{tahun_prev}'].mean():+.2f}"
    d_kpi_pdb = f"{(kpi_pdb / pdb_per_tahun.get(tahun_prev, np.nan) - 1) * 100:+.1f}%"
else:
    d_kpi_ipm = d_kpi_mis = d_kpi_pdb = None

k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Rata-rata IPM kab/kota {tahun_kpi}", f"{kpi_ipm:.2f}", d_kpi_ipm)
k2.metric(
    f"Rata-rata % Miskin kab/kota {tahun_kpi}", f"{kpi_miskin:.2f}%", d_kpi_mis,
    delta_color="inverse",  # turun = membaik (hijau)
)
k3.metric(f"Nilai Tambah Bruto {tahun_kpi} (ADHB)", f"Rp{kpi_pdb:,.0f} T", d_kpi_pdb)
if df_migrasi is not None:
    k4.metric(
        "Total Migran Antarprovinsi", f"{df_migrasi['jumlah'].sum() / 1e6:.2f} juta jiwa",
        help="Data migrasi risen hanya untuk satu periode survei/sensus, jadi tidak berubah per tahun.",
    )
else:
    k4.metric("Total Migran Antarprovinsi", "n/a")
st.markdown("---")

# =========================================================
# TABS
# =========================================================
tab_home, tab_geo, tab_hier, tab_flow = st.tabs(
    ["🏠 Home", "🗺️ Geospasial", "🌳 Berhierarki", "🔀 Aliran/Flow"]
)

# =========================================================
# HOME: pengantar, ringkasan topik, dan sekilas temuan
# =========================================================
def angka_id(x, desimal=0):
    """Format angka gaya Indonesia: 1.234.567 atau 1.234,5"""
    s = f"{x:,.{desimal}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


with tab_home:
    st.markdown(
        """
        <style>
        .rata-kk { text-align: justify; text-justify: inter-word; }
        .rata-kk ul { text-align: left; margin-top: 0.3rem; }
        .rata-kk li { text-align: justify; text-justify: inter-word; margin-bottom: 0.4rem; }
        .hero-home {
            border-left: 5px solid #F7941D; border-radius: 10px;
            background: rgba(255,255,255,0.05); padding: 16px 20px; margin-bottom: 1rem;
        }
        </style>
        <div class="hero-home rata-kk">
        <b>Selamat datang.</b> Dashboard ini memotret Indonesia dari tiga sisi:
        <b>di mana</b> kesejahteraan tersebar (IPM dan kemiskinan kabupaten/kota),
        <b>apa</b> yang menopang perekonomian (struktur PDB menurut lapangan usaha), dan
        <b>ke mana</b> penduduk berpindah (migrasi risen antarprovinsi). Seluruh data
        utama bersumber dari <b>BPS</b>. Gunakan pemilih tahun di atas untuk mengubah
        KPI, peta, dan struktur PDB; lalu jelajahi tiap topik pada tab di bawah.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- Tiga kartu topik ----------
    st.markdown("#### Tiga Topik Visualisasi")
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("##### 🗺️ Geospasial")
            st.markdown(
                "**Pertanyaan:** daerah mana yang IPM-nya tinggi dan kemiskinannya rendah?\n\n"
                f"**Teknik:** peta choropleth dan proportional symbol, ±{n_peta} kab/kota.\n\n"
                "**Data:** IPM dan persentase penduduk miskin (BPS), 2020–2024.\n\n"
                "**Interaksi:** zoom/pan, filter provinsi, tooltip, panel detail dan tren."
            )
    with c2:
        with st.container(border=True):
            st.markdown("##### 🌳 Berhierarki")
            st.markdown(
                "**Pertanyaan:** sektor dan lapangan usaha apa yang menopang PDB, dan mana yang tumbuh?\n\n"
                "**Teknik:** treemap dan sunburst, 4 level (PDB › sektor › lapangan usaha › sub).\n\n"
                "**Data:** PDB ADHB dan laju pertumbuhan ADHK (BPS), 2020–2024.\n\n"
                "**Interaksi:** drill-down dengan posisi/breadcrumb, tooltip."
            )
    with c3:
        with st.container(border=True):
            st.markdown("##### 🔀 Aliran/Flow")
            st.markdown(
                "**Pertanyaan:** dari mana ke mana penduduk berpindah antarprovinsi?\n\n"
                "**Teknik:** Sankey dan matriks origin-destination (skala log).\n\n"
                "**Data:** Migrasi risen, Long Form Sensus Penduduk 2020 (BPS).\n\n"
                "**Interaksi:** filter provinsi asal dan tujuan, tooltip."
            )

    # ---------- Sekilas temuan (dihitung dari data, mengikuti tahun) ----------
    st.markdown(f"#### Sekilas Temuan ({tahun_kpi})")
    temuan = []

    kol_ipm, kol_mis = f"ipm_{tahun_kpi}", f"miskin_{tahun_kpi}"
    if gdf_geo[kol_ipm].notna().any() and gdf_geo[kol_mis].notna().any():
        hi, lo = gdf_geo[kol_ipm].idxmax(), gdf_geo[kol_ipm].idxmin()
        mis = gdf_geo[kol_mis].idxmax()
        temuan.append(
            f"**🗺️ Kesenjangan antardaerah:** IPM tertinggi ada di "
            f"**{gdf_geo.loc[hi, 'kabkota_bps']}** ({gdf_geo.loc[hi, 'provinsi_label']}, "
            f"{gdf_geo.loc[hi, kol_ipm]:.2f}), terendah di **{gdf_geo.loc[lo, 'kabkota_bps']}** "
            f"({gdf_geo.loc[lo, 'provinsi_label']}, {gdf_geo.loc[lo, kol_ipm]:.2f}). "
            f"Persentase penduduk miskin tertinggi: **{gdf_geo.loc[mis, 'kabkota_bps']}** "
            f"({gdf_geo.loc[mis, kol_mis]:.2f}%)."
        )

    d_h = df_hier_all[df_hier_all["tahun"] == tahun_kpi]
    if not d_h.empty:
        per_sektor = d_h.groupby("sektor")["nilai_triliun"].sum()
        sektor_top = per_sektor.idxmax()
        porsi = per_sektor.max() / per_sektor.sum() * 100
        lap_top = d_h.loc[d_h["nilai_triliun"].idxmax()]
        lap_tumbuh = d_h.loc[d_h["pertumbuhan"].idxmax()]
        temuan.append(
            f"**🌳 Struktur ekonomi:** sektor **{sektor_top}** menyumbang {porsi:.1f}% nilai tambah. "
            f"Lapangan usaha terbesar: **{lap_top['label']}**; pertumbuhan tertinggi: "
            f"**{lap_tumbuh['label']}** ({lap_tumbuh['pertumbuhan']:+.2f}%)."
        )

    if df_migrasi is not None:
        dm = df_migrasi[df_migrasi["asal"] != LUAR_NEGERI]
        top = dm.nlargest(1, "jumlah").iloc[0]
        neto = dm.groupby("tujuan")["jumlah"].sum().sub(dm.groupby("asal")["jumlah"].sum(), fill_value=0)
        temuan.append(
            f"**🔀 Koridor migrasi:** aliran terbesar adalah **{top['asal']} → {top['tujuan']}** "
            f"({angka_id(top['jumlah'])} jiwa). Penerima migran neto terbesar: **{neto.idxmax()}** "
            f"(+{angka_id(neto.max())}); pengirim neto terbesar: **{neto.idxmin()}** "
            f"({angka_id(neto.min())}). *(Data migrasi satu periode, tidak berubah per tahun.)*"
        )

    for t in temuan:
        st.markdown(f"- {t}")

    # ---------- Cara menggunakan ----------
    st.markdown("#### Cara Menggunakan")
    st.markdown(
        "1. **Pilih tahun** pada slider di atas (berlaku untuk KPI, peta, dan struktur PDB).\n"
        "2. **Buka tab topik** dan atur representasi serta filter yang tersedia.\n"
        "3. **Arahkan kursor** ke peta, blok, pita, atau sel untuk melihat rincian pada tooltip.\n"
        "4. **Unduh data** yang sedang ditampilkan lewat tombol ⬇️ di tiap topik."
    )

    # ---------- Sumber data ----------
    st.markdown("#### Sumber Data")
    st.markdown(
        "| Topik | Data | Sumber | Periode |\n"
        "|---|---|---|---|\n"
        "| Geospasial | IPM; Persentase Penduduk Miskin (P0) per kab/kota | BPS | 2020–2024 |\n"
        "| Geospasial | Batas administrasi kab/kota (non-BPS) | GADM v4.1 | – |\n"
        "| Berhierarki | PDB ADHB dan laju pertumbuhan ADHK 2010 menurut lapangan usaha | BPS | 2020–2024 |\n"
        "| Aliran | Migrasi risen menurut provinsi tempat tinggal sekarang dan 5 tahun lalu | BPS (Long Form SP2020) | 2020 |\n\n"
        "Tautan lengkap tiap tabel ada di bagian **Akses data** pada masing-masing tab."
    )

    # ---------- Catatan & keterbatasan ----------
    with st.expander("Catatan metodologi dan keterbatasan"):
        st.markdown(
            "- **Geospasial:** poligon tanpa data berasal dari objek non-administratif, daerah otonom "
            "baru yang belum ada di GADM, atau perbedaan penulisan nama wilayah BPS dan GADM.\n"
            "- **Berhierarki:** pertumbuhan tingkat sektor dan PDB adalah rata-rata tertimbang (bukan "
            "angka resmi BPS), dan warna sub-lapangan usaha mengikuti lapangan usaha induknya.\n"
            "- **Aliran:** data hanya satu periode dan tingkat provinsi (pemekaran Papua digabung ke "
            "provinsi induk). Label kolom Papua dan Papua Barat pada tabel sumber telah dikoreksi "
            "karena nilai diagonalnya menunjukkan urutan yang terbalik. Tanda “-” dianggap 0.\n"
            "- **Pemakaian AI:** alat bantu berbasis AI digunakan sebatas alat bantu dalam "
            "pengembangan."
        )

# =========================================================
# TOPIK 1: GEOSPASIAL
# Tema: IPM & persentase kemiskinan per kabupaten/kota, 2020-2024
# Jenis peta: (1) choropleth, (2) proportional symbol
# =========================================================
with tab_geo:
    st.subheader("IPM & Kemiskinan Menurut Kabupaten/Kota, 2020–2024")

    col_a, col_b, col_d = st.columns([1.1, 1.1, 2.0])
    with col_a:
        indikator = st.radio(
            "Pilih indikator:",
            ["IPM", "Persentase Penduduk Miskin"],
            key="geo_indikator",
        )
    with col_b:
        jenis_peta = st.radio(
            "Jenis peta:",
            ["Choropleth", "Proportional Symbol"],
            key="geo_jenis_peta",
        )
    with col_d:
        daftar_provinsi = sorted(gdf_geo["provinsi_bps"].dropna().unique())
        provinsi_filter = st.multiselect(
            "Filter provinsi (peta otomatis zoom):", daftar_provinsi, default=[],
        )

    tahun = tahun_kpi   # mengikuti pemilih tahun global

    prefix = "ipm" if indikator == "IPM" else "miskin"
    kolom = f"{prefix}_{tahun}"
    label_kolom = "IPM" if indikator == "IPM" else "% Penduduk Miskin"
    skala_warna = "Viridis" if indikator == "IPM" else "Viridis_r"  # colorblind-friendly

    # Skala warna dikunci lintas tahun supaya antar tahun bisa dibandingkan
    semua_nilai = gdf_geo[[f"{prefix}_{t}" for t in TAHUN]].stack()
    rentang = (semua_nilai.min(), semua_nilai.max())

    gdf_plot = gdf_geo.copy()
    if provinsi_filter:
        gdf_plot = gdf_plot[gdf_plot["provinsi_bps"].isin(provinsi_filter)]
    gdf_plot = gdf_plot.dropna(subset=[kolom])

    # Pusat & zoom mengikuti provinsi yang difilter
    if provinsi_filter:
        view_center, view_zoom = hitung_tampilan_peta(gdf_plot)
    else:
        view_center, view_zoom = DEFAULT_CENTER, DEFAULT_ZOOM

    if jenis_peta == "Choropleth":
        fig_geo = px.choropleth_mapbox(
            gdf_plot,
            geojson=geojson_geo,
            locations=gdf_plot.index,
            color=kolom,
            color_continuous_scale=skala_warna,
            range_color=rentang,
            mapbox_style=MAP_STYLE,
            zoom=view_zoom,
            center=view_center,
            opacity=0.85,
            title=f"Peta Choropleth: {label_kolom} Menurut Kabupaten/Kota, {tahun}",
        )
    else:
        fig_geo = px.scatter_mapbox(
            gdf_plot,
            lat="centroid_lat", lon="centroid_lon",
            size=kolom,
            color=kolom,
            color_continuous_scale=skala_warna,
            range_color=rentang,
            size_max=22,
            zoom=view_zoom,
            center=view_center,
            mapbox_style=MAP_STYLE,
            title=f"Peta Proportional Symbol: {label_kolom} Menurut Kabupaten/Kota, {tahun}",
        )

    # ---------- Tooltip kustom ----------
    t_prev = tahun - 1 if tahun > TAHUN[0] else None
    ipm_now = gdf_plot[f"ipm_{tahun}"]
    miskin_now = gdf_plot[f"miskin_{tahun}"]
    if t_prev:
        d_ipm = [fmt_delta(a, b) for a, b in zip(ipm_now, gdf_plot[f"ipm_{t_prev}"])]
        d_miskin = [fmt_delta(a, b) for a, b in zip(miskin_now, gdf_plot[f"miskin_{t_prev}"])]
    else:
        d_ipm = [""] * len(gdf_plot)
        d_miskin = [""] * len(gdf_plot)

    customdata = np.column_stack([
        gdf_plot["kabkota_bps"].astype(str),
        gdf_plot["provinsi_label"].astype(str),
        [fmt_val(x) for x in ipm_now],
        d_ipm,
        [fmt_val(x) for x in miskin_now],
        d_miskin,
    ])

    fig_geo.update_traces(
        customdata=customdata,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "<i>%{customdata[1]}</i><br>"
            "──────────────<br>"
            f"IPM {tahun}: <b>%{{customdata[2]}}</b>%{{customdata[3]}}<br>"
            f"% Miskin {tahun}: <b>%{{customdata[4]}}</b>%{{customdata[5]}}"
            "<extra></extra>"
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#555555",
            font=dict(size=13, color="#222222"),
            align="left",
        ),
    )

    fig_geo.update_layout(
        height=600,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        coloraxis_colorbar_title=label_kolom,
    )
    tampilkan_plot(fig_geo, use_container_width=True, config=PLOT_CONFIG)

    if ES_PONSEL:
        st.caption(
            "📱 Di ponsel: geser peta dengan satu jari dan cubit untuk zoom. "
            "Untuk menggulir halaman, sentuh area di luar peta (judul atau skala warna)."
        )

    if t_prev:
        st.caption(
            f"Tanda ▲/▼ pada tooltip = perubahan dibanding {t_prev}. "
            "Untuk IPM, ▲ berarti membaik; untuk % miskin, ▼ berarti membaik."
        )

    # =====================================================
    # PANEL DETAIL INTERAKTIF
    # =====================================================
    st.markdown("---")
    st.markdown("#### 🔍 Detail Kabupaten/Kota")

    opsi = {
        f"{r.kabkota_bps} — {r.provinsi_label}": i
        for i, r in gdf_plot.sort_values(["provinsi_label", "kabkota_bps"]).iterrows()
    }

    if not opsi:
        st.warning("Tidak ada kabupaten/kota dengan data untuk filter dan tahun yang dipilih.")
    else:
        pilihan = st.selectbox(
            "Pilih kabupaten/kota (ketik untuk mencari):",
            list(opsi.keys()),
            key="geo_detail",
        )
        baris = gdf_geo.loc[opsi[pilihan]]

        def peringkat(kol, ascending):
            valid = gdf_geo[kol].dropna()
            nilai = baris[kol]
            urut = (valid < nilai).sum() if ascending else (valid > nilai).sum()
            return int(urut) + 1, len(valid)

        # Peringkat 1 = IPM tertinggi / kemiskinan terendah
        rank_ipm, n_ipm = peringkat(f"ipm_{tahun}", ascending=False)
        rank_mis, n_mis = peringkat(f"miskin_{tahun}", ascending=True)

        m1, m2, m3, m4 = st.columns(4)
        delta_ipm = (
            None if not t_prev or pd.isna(baris[f"ipm_{t_prev}"])
            else f"{baris[f'ipm_{tahun}'] - baris[f'ipm_{t_prev}']:+.2f}"
        )
        delta_mis = (
            None if not t_prev or pd.isna(baris[f"miskin_{t_prev}"])
            else f"{baris[f'miskin_{tahun}'] - baris[f'miskin_{t_prev}']:+.2f}"
        )
        m1.metric(f"IPM {tahun}", fmt_val(baris[f"ipm_{tahun}"]), delta_ipm)
        m2.metric(
            f"% Miskin {tahun}", fmt_val(baris[f"miskin_{tahun}"]), delta_mis,
            delta_color="inverse",  # turun = bagus (hijau)
        )
        m3.metric("Peringkat IPM", f"{rank_ipm} / {n_ipm}")
        m4.metric("Peringkat Kemiskinan (terendah = 1)", f"{rank_mis} / {n_mis}")

        # Grafik tren dua sumbu
        ipm_series = [baris[f"ipm_{t}"] for t in TAHUN]
        mis_series = [baris[f"miskin_{t}"] for t in TAHUN]

        fig_tren = make_subplots(specs=[[{"secondary_y": True}]])
        fig_tren.add_trace(
            go.Scatter(
                x=TAHUN, y=ipm_series, name="IPM", mode="lines+markers",
                line=dict(color=WARNA_IPM, width=3),
                hovertemplate="IPM %{x}: <b>%{y:.2f}</b><extra></extra>",
            ),
            secondary_y=False,
        )
        fig_tren.add_trace(
            go.Scatter(
                x=TAHUN, y=mis_series, name="% Penduduk Miskin", mode="lines+markers",
                line=dict(color=WARNA_MISKIN, width=3, dash="dash"),
                hovertemplate="% Miskin %{x}: <b>%{y:.2f}</b><extra></extra>",
            ),
            secondary_y=True,
        )
        fig_tren.update_xaxes(tickmode="array", tickvals=TAHUN)
        fig_tren.update_yaxes(title_text="IPM", secondary_y=False, color=WARNA_IPM)
        fig_tren.update_yaxes(title_text="% Penduduk Miskin", secondary_y=True, color=WARNA_MISKIN)
        fig_tren.update_layout(
            title=f"Tren {baris['kabkota_bps']} ({baris['provinsi_label']}), 2020–2024",
            height=380,
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.2),
            margin={"t": 50, "l": 0, "r": 0, "b": 0},
        )
        tampilkan_plot(fig_tren, use_container_width=True)

    # =====================================================
    # SUMBER & CATATAN
    # =====================================================
    st.download_button(
        "⬇️ Unduh data kab/kota yang ditampilkan (CSV)",
        gdf_plot.drop(columns="geometry").to_csv(index=False).encode("utf-8"),
        file_name=f"ipm_miskin_{tahun}.csv", mime="text/csv",
        key="dl_geo",
    )

    st.markdown(
        """
        <style>
        .rata-kk { text-align: justify; text-justify: inter-word; }
        .rata-kk ul { text-align: left; margin-top: 0.3rem; }
        .rata-kk li { text-align: justify; text-justify: inter-word; margin-bottom: 0.4rem; }
        </style>

        <div class="rata-kk">

        <b>Data yang digunakan pada topik ini:</b>

        <ul>
        <li><b>Indeks Pembangunan Manusia (IPM)</b> — indikator komposit BPS yang mengukur
        capaian pembangunan manusia dari tiga dimensi dasar: umur panjang dan hidup sehat
        (angka harapan hidup), pengetahuan (harapan dan rata-rata lama sekolah), serta
        standar hidup layak (pengeluaran per kapita yang disesuaikan). Skala 0–100, semakin
        tinggi semakin baik.</li>
        <li><b>Persentase Penduduk Miskin (P0)</b> — proporsi penduduk yang pengeluaran per
        kapita per bulannya berada di bawah Garis Kemiskinan BPS, terhadap jumlah penduduk
        di wilayah tersebut.</li>
        <li><b>Batas administrasi kabupaten/kota</b> — data pendukung non-BPS yang dipakai
        untuk menggambar poligon wilayah pada peta choropleth.</li>
        </ul>

        <p>Kedua indikator BPS di atas disajikan pada level kabupaten/kota (±500 unit) untuk
        tahun 2020–2024, lalu digabungkan dengan data batas wilayah berdasarkan kecocokan
        nama provinsi dan kabupaten/kota.</p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="rata-kk">

        <b>Akses data:</b>

        <ul>
        <li>IPM Menurut Kabupaten/Kota (BPS):
        <a href="https://www.bps.go.id/id/statistics-table/2/NDEzIzI=/-metode-baru-indeks-pembangunan-manusia.html" target="_blank" rel="noopener noreferrer">Link Akses</a></li>
        <li>Persentase Penduduk Miskin (P0) Menurut Kabupaten/Kota (BPS):
        <a href="https://www.bps.go.id/id/statistics-table/2/NjIxIzI=/persentase-penduduk-miskin-menurut-kabupaten-kota.html" target="_blank" rel="noopener noreferrer">Link Akses</a></li>
        <li>Batas Wilayah Administrasi Kabupaten/Kota, GADM v4.1:
        <a href="https://gadm.org/download_country.html" target="_blank" rel="noopener noreferrer">Link Akses</a></li>
        </ul>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if ES_PONSEL:
        st.info(
            "Interaksi: **geser** peta dengan satu jari dan **cubit** untuk zoom, **ketuk** wilayah "
            "untuk melihat tooltip berisi nilai dan perubahan tahunan, **pemilih tahun** di "
            "bagian atas halaman, **filter provinsi** (peta otomatis zoom ke provinsi terpilih), serta "
            "**panel detail** (pilih kabupaten/kota) untuk melihat peringkat dan tren 2020–2024."
        )
    else:
        st.info(
            "Interaksi: **scroll mouse** untuk zoom, **drag** untuk geser peta, toolbar kanan atas "
            "untuk zoom/reset, **tooltip** berisi nilai dan perubahan tahunan, **pemilih tahun** di "
            "bagian atas halaman, **filter provinsi** (peta otomatis zoom ke provinsi terpilih), serta "
            "**panel detail** (pilih kabupaten/kota) untuk melihat peringkat dan tren 2020–2024."
        )
    n_total = len(gdf_geo)
    n_terisi = gdf_geo[kolom].notna().sum()
    st.caption(
        f"Cakupan data {tahun}: {n_terisi} dari {n_total} poligon kabupaten/kota pada batas "
        f"wilayah GADM v4.1 memiliki data. Poligon tanpa data berasal dari objek non-administratif "
        f"(danau/waduk), daerah otonom baru yang belum ada di GADM, atau perbedaan penulisan nama "
        f"wilayah antara BPS dan GADM."
    )

# =========================================================
# TOPIK 2: BERHIERARKI
# Tema: struktur PDB menurut sektor, lapangan usaha, dan sub-lapangan usaha
# Representasi: treemap + sunburst (2 representasi berbeda)
# Drill-down: pilihan sektor/lapangan usaha + breadcrumb (jejak posisi)
# =========================================================

# Baris sub-lapangan usaha diawali angka yang menempel pada nama (mis. "1Pertanian, ...");
# baris "a. b. c." (sub-sub) sengaja diabaikan.
POLA_SUB = re.compile(r"^(\d{1,2})\s*[\.\)]?\s*(\D.*)$")


def nama_sub(baris):
    """Ambil nama Indonesia dari sel bertingkat baris (Indonesia dulu, lalu Inggris)."""
    teks = " ".join(baris)
    if "/" in teks:                                   # format "Nama Indonesia/English name"
        nama = teks.split("/")[0]
    else:                                             # format baris: paruh awal Indonesia, paruh akhir Inggris
        n_indo = max(1, len(baris) // 2)
        nama = " ".join(baris[:n_indo])
    return nama.strip().rstrip(";,").strip()


def parse_sub_lapus(path, tahun):
    """Ambil sub-lapangan usaha (baris bernomor) dari satu file PDB ADHB."""
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = ["lapus_raw", "nilai"]
    df["baris"] = df["lapus_raw"].fillna("").astype(str).map(
        lambda s: [b.strip() for b in s.split("\n") if b.strip()]
    )
    df["teks"] = df["baris"].map(" ".join)
    idx_ntb = df.index[df["teks"].str.contains("Nilai Tambah Bruto", case=False, na=False)][0]
    df = df.loc[: idx_ntb - 1]

    hasil, kode_induk = [], None
    for baris, teks, nilai in zip(df["baris"], df["teks"], df["nilai"]):
        if not baris:
            continue
        m_utama = re.match(KODE_UTAMA, teks)
        if m_utama:                                   # baris lapangan usaha utama (A, B, ...)
            kode_induk = m_utama.group(1)
            continue
        m_sub = POLA_SUB.match(baris[0])
        if m_sub and kode_induk is not None:          # baris sub-lapangan usaha (1, 2, 3, ...)
            baris_nama = [m_sub.group(2)] + baris[1:]
            hasil.append((kode_induk, int(m_sub.group(1)), nama_sub(baris_nama),
                          ke_angka(nilai), tahun))

    out = pd.DataFrame(hasil, columns=["kode", "no", "nama", "nilai_miliar", "tahun"])
    return out.dropna(subset=["nilai_miliar"])


@st.cache_data
def load_sub_data():
    sub = pd.concat([parse_sub_lapus(file_pdb(t), t) for t in TAHUN_PDB], ignore_index=True)
    sub["nilai_triliun"] = sub["nilai_miliar"] / 1000
    sub["sektor"] = sub["kode"].map(LAPUS_SEKTOR)
    return sub.dropna(subset=["sektor"]).sort_values(["tahun", "kode", "no"]).reset_index(drop=True)


KOLOM_SUB = ["kode", "no", "nama", "nilai_miliar", "tahun", "nilai_triliun", "sektor"]
try:
    df_sub_all = load_sub_data()
    galat_sub = None
except Exception as e:           # jangan sampai seluruh dashboard ikut gagal
    df_sub_all = pd.DataFrame(columns=KOLOM_SUB)
    galat_sub = str(e)


def potong(teks, maks=38):
    return teks if len(teks) <= maks else teks[: maks - 1].rstrip() + "…"


def bangun_node_3level(d_main, d_sub):
    """Susun node hierarki: PDB (akar) > sektor > lapangan usaha > sub-lapangan usaha.
    Nilai lapangan usaha yang punya sub = jumlah sub-lapangannya (syarat branchvalues='total').
    Warna sub-lapangan usaha mengikuti pertumbuhan lapangan usaha induknya."""
    sub_per_kode = {k: g for k, g in d_sub.groupby("kode")} if not d_sub.empty else {}

    lapus = d_main.copy().reset_index(drop=True)
    lapus["nilai"] = lapus["nilai_triliun"]
    selisih_maks = 0.0   # selisih terbesar jumlah sub vs angka resmi lapus (miliar Rp), akibat pembulatan
    for i, r in lapus.iterrows():
        g = sub_per_kode.get(r["kode"])
        if g is not None and not g.empty:
            jumlah = g["nilai_triliun"].sum()
            selisih_maks = max(selisih_maks, abs(jumlah - r["nilai_triliun"]) * 1000)
            lapus.at[i, "nilai"] = jumlah

    total = lapus["nilai"].sum()
    tumbuh_total = (lapus["nilai"] * lapus["pertumbuhan"]).sum() / total

    simpul = [dict(
        id="PDB", label="PDB", parent="", nilai=total, tumbuh=tumbuh_total,
        nama="PDB (jumlah 17 lapangan usaha)", share=100.0, ket="rata-rata tertimbang",
    )]
    for sektor, sub in lapus.groupby("sektor", sort=False):
        nilai_s = sub["nilai"].sum()
        tumbuh_s = (sub["nilai"] * sub["pertumbuhan"]).sum() / nilai_s
        simpul.append(dict(
            id=sektor, label=f"Sektor {sektor}", parent="PDB", nilai=nilai_s, tumbuh=tumbuh_s,
            nama=f"Sektor {sektor}", share=nilai_s / total * 100, ket="rata-rata tertimbang",
        ))
        for r in sub.itertuples():
            id_lapus = f"{sektor}|{r.kode}"
            simpul.append(dict(
                id=id_lapus, label=r.label, parent=sektor, nilai=r.nilai, tumbuh=r.pertumbuhan,
                nama=r.lapus, share=r.nilai / total * 100, ket="angka BPS",
            ))
            g = sub_per_kode.get(r.kode)
            if g is None:
                continue
            for s in g.itertuples():
                simpul.append(dict(
                    id=f"{id_lapus}|{s.no}", label=f"{r.kode}.{s.no} {potong(s.nama)}",
                    parent=id_lapus, nilai=s.nilai_triliun, tumbuh=r.pertumbuhan,
                    nama=s.nama, share=s.nilai_triliun / total * 100,
                    ket="mengikuti lapangan usaha induk",
                ))
    return pd.DataFrame(simpul), selisih_maks


def buat_figure_hier_3level(d_main, d_sub, representasi, tahun, batas, level_id=""):
    n, selisih_maks = bangun_node_3level(d_main, d_sub)
    customdata = list(zip(
        n["nama"],
        n["nilai"].map(lambda x: f"{x:,.1f}"),
        n["share"].map(lambda x: f"{x:.1f}%"),
        n["tumbuh"].map(lambda x: f"{x:+.2f}%"),
        n["ket"],
    ))
    marker = dict(
        colors=n["tumbuh"], colorscale="RdBu", cmid=0, cmin=-batas, cmax=batas,
        showscale=True,
        colorbar=dict(title="Pertumbuhan<br>(% y-o-y)"),
        line=dict(width=1, color="white"),
    )
    hover = (
        "<b>%{customdata[0]}</b><br>"
        "──────────────<br>"
        "PDB (ADHB): <b>Rp %{customdata[1]} T</b><br>"
        "Porsi: <b>%{customdata[2]}</b><br>"
        "Pertumbuhan: <b>%{customdata[3]}</b> <i>(%{customdata[4]})</i>"
        "<extra></extra>"
    )
    kwargs = dict(
        ids=n["id"], labels=n["label"], parents=n["parent"], values=n["nilai"],
        branchvalues="total", customdata=customdata, marker=marker,
        hovertemplate=hover, texttemplate="<b>%{label}</b><br>%{customdata[2]}",
        level=level_id,     # simpul yang menjadi pusat tampilan (drill-down)
    )

    if representasi == "Treemap":
        trace = go.Treemap(**kwargs, tiling=dict(pad=3))
        judul = f"Treemap PDB Menurut Lapangan Usaha, {tahun} (ukuran = PDB ADHB, warna = pertumbuhan)"
    else:
        # maxdepth=3: tiga cincin sekaligus agar tidak padat; level berikutnya muncul saat drill-down
        trace = go.Sunburst(**kwargs, insidetextorientation="radial", maxdepth=3)
        judul = f"Sunburst PDB Menurut Lapangan Usaha, {tahun} (ukuran = PDB ADHB, warna = pertumbuhan)"

    fig = go.Figure(trace)
    fig.update_layout(
        title=judul,
        height=700,
        margin={"t": 50, "l": 0, "r": 0, "b": 100},
    )
    return fig, n, selisih_maks


with tab_hier:
    st.subheader("Struktur PDB Menurut Sektor, Lapangan Usaha, dan Sub-Lapangan Usaha, 2020–2024")

    if galat_sub:
        st.warning(
            "Sub-lapangan usaha gagal dibaca dari file PDB ADHB, jadi hierarki sementara hanya "
            f"2 level. Detail galat: {galat_sub}"
        )
    elif df_sub_all.empty:
        st.warning(
            "Tidak ada baris sub-lapangan usaha yang terbaca dari file PDB ADHB. Pastikan kolom "
            "pertama memuat baris bernomor (1, 2, 3, ...) di bawah tiap lapangan usaha."
        )

    view = st.radio(
        "Pilih representasi:", ["Treemap", "Sunburst"], horizontal=True, key="hier_view",
    )
    tahun_h = tahun_kpi   # mengikuti pemilih tahun global

    # Skala warna dikunci lintas tahun & simetris di sekitar 0 supaya antar tahun bisa dibandingkan
    batas_warna = float(df_hier_all["pertumbuhan"].abs().max())

    df_h = df_hier_all[df_hier_all["tahun"] == tahun_h]
    df_s = df_sub_all[df_sub_all["tahun"] == tahun_h]

    # ---------- Kontrol drill-down + breadcrumb ----------
    daftar_sektor = list(dict.fromkeys(df_h["sektor"]))      # urutan: Primer, Sekunder, Tersier
    col_s, col_l = st.columns(2)
    with col_s:
        sektor_pilih = st.selectbox(
            "Drill-down: sektor", ["Semua sektor"] + daftar_sektor, key="hier_sektor",
        )

    lapus_sektor = (df_h[df_h["sektor"] == sektor_pilih]
                    if sektor_pilih != "Semua sektor" else df_h.iloc[0:0])
    opsi_lapus = {"Semua lapangan usaha": None}
    opsi_lapus.update({r.label: r.kode for r in lapus_sektor.itertuples()})
    with col_l:
        lapus_pilih = st.selectbox(
            "Drill-down: lapangan usaha", list(opsi_lapus.keys()),
            disabled=(sektor_pilih == "Semua sektor"),
            key=f"hier_lapus_{sektor_pilih}",       # key per sektor agar pilihan tidak bentrok
        )

    jejak, level_id = ["PDB"], ""
    if sektor_pilih != "Semua sektor":
        jejak.append(f"Sektor {sektor_pilih}")
        level_id = sektor_pilih
        kode_pilih = opsi_lapus.get(lapus_pilih)
        if kode_pilih:
            jejak.append(lapus_pilih)
            level_id = f"{sektor_pilih}|{kode_pilih}"
    st.markdown("📍 **Posisi:** " + " › ".join(jejak))

    fig_hier, n_hier, selisih_maks = buat_figure_hier_3level(
        df_h, df_s, view, tahun_h, batas_warna, level_id,
    )
    tampilkan_plot(fig_hier, use_container_width=True, config=PLOT_CONFIG)

    st.download_button(
        "⬇️ Unduh data hierarki PDB tahun ini (CSV)",
        n_hier.rename(columns={
            "nilai": "nilai_adhb_triliun_rp", "tumbuh": "pertumbuhan_persen",
            "share": "porsi_persen", "ket": "keterangan_pertumbuhan",
        }).to_csv(index=False).encode("utf-8"),
        file_name=f"pdb_hierarki_{tahun_h}.csv", mime="text/csv",
        key="dl_hier",
    )

    st.markdown(
        """
        <style>
        .rata-kk { text-align: justify; text-justify: inter-word; }
        .rata-kk ul { text-align: left; margin-top: 0.3rem; }
        .rata-kk li { text-align: justify; text-justify: inter-word; margin-bottom: 0.4rem; }
        </style>

        <div class="rata-kk">

        <b>Data yang digunakan pada topik ini:</b>

        <ul>
        <li><b>Produk Domestik Bruto (PDB) Atas Dasar Harga Berlaku (ADHB) Menurut Lapangan
        Usaha</b> — nilai nominal seluruh barang dan jasa akhir yang dihasilkan perekonomian
        Indonesia dalam satu tahun, dipecah menjadi 17 kategori lapangan usaha (klasifikasi
        baku BPS). Dipakai sebagai <b>ukuran blok</b> pada treemap/sunburst karena
        mencerminkan besar-kecilnya kontribusi nominal tiap lapangan usaha terhadap
        perekonomian.</li>
        <li><b>Laju Pertumbuhan PDB Atas Dasar Harga Konstan (ADHK) 2010 Menurut Lapangan
        Usaha</b> — persentase perubahan volume produksi riil tiap lapangan usaha dari tahun
        ke tahun, sudah dibersihkan dari efek inflasi (berbeda dari ADHB yang masih
        mengandung efek harga). Dipakai sebagai <b>warna blok</b> karena mencerminkan murni
        pertumbuhan aktivitas ekonomi, bukan sekadar kenaikan harga.</li>
        <li><b>Sub-lapangan usaha</b> — rincian lebih detail di bawah tiap lapangan usaha
        utama (baris bernomor pada tabel PDB ADHB BPS), dipakai sebagai level ke-3 hierarki.
        Karena BPS tidak merilis angka pertumbuhan khusus di level sub-lapangan usaha, warna
        sub-lapangan usaha mengikuti angka pertumbuhan lapangan usaha induknya.</li>
        </ul>

        <p>Kedua tabel BPS di atas disajikan pada level nasional untuk tahun 2020–2024,
        kemudian digabungkan berdasarkan kode lapangan usaha (A sampai R,S,T,U) dan
        dikelompokkan ke tiga sektor besar (Primer, Sekunder, Tersier) mengikuti klasifikasi
        ekonomi standar.</p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="rata-kk">

        <b>Akses data:</b>

        <ul>
        <li>Produk Domestik Bruto Atas Dasar Harga Berlaku Menurut Lapangan Usaha (BPS):
        <a href="https://www.bps.go.id/id/statistics-table/3/UzFSTVVXUlliME5XYzBZNUwwNVFRa3h6Y1d3M1p6MDkjMw==/produk-domestik-bruto-atas-dasar-harga-berlaku-menurut-lapangan-usaha-miliar-rupiah-.html" target="_blank">Link Akses</a></li>
        <li>Laju Pertumbuhan PDB Atas Dasar Harga Konstan 2010 Menurut Lapangan Usaha (BPS),
        Berita Resmi Statistik Pertumbuhan Ekonomi Indonesia:
        <a href="https://www.bps.go.id/assets/pressrelease/2023/02/06/1997/ekonomi-indonesia-tahun-2022-tumbuh-5-31-persen.html" target="_blank">Link Akses 2022</a> dan
        <a href="https://www.bps.go.id/assets/pressrelease/2025/02/05/2408/ekonomi-indonesia-tahun-2024-tumbuh-5-03-persen--c-to-c---ekonomi-indonesia-triwulan-iv-2024-tumbuh-5-02-persen--y-on-y---ekonomi-indonesia-triwulan-iv-2024-tumbuh-0-53-persen--q-to-q--.html" target="_blank">Link Akses 2024</a></li>
        </ul>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "Interaksi: pilih **sektor** dan **lapangan usaha** di atas grafik untuk drill-down; jejak "
        "posisinya tampil pada baris **Posisi**. Klik blok/irisan di dalam grafik juga bisa untuk "
        "masuk ke level di bawahnya, dan klik bagian tengah sunburst untuk naik satu level. "
        "Pada treemap, bilah di atas grafik adalah breadcrumb bawaan yang ikut berubah saat "
        "klik; baris **Posisi** hanya mengikuti pilihan di atas grafik, bukan klik di dalam grafik. "
        "**Pemilih tahun** ada di bagian atas halaman, dan **tooltip** berisi nilai PDB, porsi, "
        "serta pertumbuhan."
    )
    st.caption(
        "Catatan metodologi: hierarki terdiri dari PDB > sektor (Primer A-B, Sekunder C-F, "
        "Tersier G-R,S,T,U) > 17 lapangan usaha > sub-lapangan usaha (baris bernomor pada tabel "
        "BPS; lapangan usaha tanpa sub tampil sebagai blok akhir). Ukuran blok memakai PDB atas "
        "dasar harga berlaku (ADHB), sedangkan warna memakai laju pertumbuhan atas dasar harga "
        "konstan 2010 (ADHK). Tabel pertumbuhan BPS hanya memuat 17 lapangan usaha, sehingga warna "
        "sub-lapangan usaha mengikuti lapangan usaha induknya dan bukan angka resmi sub-lapangan. "
        "Pertumbuhan tingkat sektor dan PDB adalah rata-rata tertimbang dengan bobot nilai ADHB, "
        "bukan angka resmi BPS. Porsi dihitung terhadap jumlah 17 lapangan usaha (Nilai Tambah "
        "Bruto, tanpa pajak dikurang subsidi). Nilai lapangan usaha yang punya sub dihitung dari "
        f"jumlah sub-lapangannya; selisih terbesar terhadap angka resmi {selisih_maks:,.1f} miliar "
        "rupiah (akibat pembulatan)."
    )

# =========================================================
# TOPIK 3: ALIRAN / FLOW
# Tema: migrasi risen antarprovinsi (BPS)
# Teknik: Sankey diagram & Matriks Origin-Destination
# =========================================================
with tab_flow:
    st.subheader("Migrasi Risen Antarprovinsi")

    if df_migrasi is None:
        st.error(f"File data tidak ditemukan di: `{CSV_MIGRASI}`")
    else:
        representasi_flow = st.radio(
            "Pilih representasi:",
            ["Sankey Diagram", "Matriks Origin-Destination"],
            horizontal=True,
            key="flow_view"
        )
        st.markdown("---")

        if representasi_flow == "Sankey Diagram":
            # ---------------------------------------------------------
            # 1. SANKEY DIAGRAM
            # ---------------------------------------------------------
            urut_asal = (df_migrasi.groupby("asal")["jumlah"].sum()
                         .sort_values(ascending=False).index.tolist())
            urut_tujuan = (df_migrasi.groupby("tujuan")["jumlah"].sum()
                           .sort_values(ascending=False).index.tolist())

            col_a, col_b = st.columns(2)
            with col_a:
                prov_filter = st.multiselect(
                    "Filter provinsi asal (5 tahun lalu):",
                    urut_asal,
                    default=[p for p in urut_asal if p != LUAR_NEGERI][:3],
                    key="sankey_asal",
                )
            with col_b:
                tujuan_filter = st.multiselect(
                    "Filter provinsi tujuan (tempat tinggal sekarang):",
                    urut_tujuan,
                    default=[],
                    placeholder="Semua tujuan",
                    help="Kosongkan untuk menampilkan semua provinsi tujuan.",
                    key="sankey_tujuan",
                )

            df_flow = df_migrasi[df_migrasi["asal"].isin(prov_filter)]
            if tujuan_filter:
                df_flow = df_flow[df_flow["tujuan"].isin(tujuan_filter)]

            if df_flow.empty:
                st.warning(
                    "Tidak ada aliran untuk kombinasi filter ini. Pilih minimal satu provinsi asal; "
                    "perpindahan di dalam provinsi yang sama tidak ditampilkan."
                )
            else:
                asal_nodes = df_flow["asal"].unique().tolist()
                tujuan_nodes = df_flow["tujuan"].unique().tolist()
                labels = asal_nodes + tujuan_nodes
                idx_asal = {n: i for i, n in enumerate(asal_nodes)}
                idx_tuju = {n: i + len(asal_nodes) for i, n in enumerate(tujuan_nodes)}

                # warna konsisten per provinsi menggunakan CB_PALETTE awal
                semua = sorted(df_migrasi["asal"].unique())
                warna_prov = {p: CB_PALETTE[i % len(CB_PALETTE)] for i, p in enumerate(semua)}

                fig_flow = go.Figure(go.Sankey(
                    valueformat=",d",
                    valuesuffix=" jiwa",
                    node=dict(
                        label=labels,
                        pad=20,
                        thickness=18,
                        color=[warna_prov.get(n, "#999999") for n in labels],
                    ),
                    link=dict(
                        source=[idx_asal[a] for a in df_flow["asal"]],
                        target=[idx_tuju[t] for t in df_flow["tujuan"]],
                        value=df_flow["jumlah"],
                        color=[hex_to_rgba(warna_prov.get(a)) for a in df_flow["asal"]],
                    ),
                ))

                # tinggi menyesuaikan jumlah node agar label tidak bertumpuk
                n_node_maks = max(len(asal_nodes), len(tujuan_nodes))
                tinggi_sankey = max(600, min(1100, 28 * n_node_maks + 160))

                fig_flow.update_layout(
                    title=dict(
                        text=f"Sankey Diagram: {len(df_flow)} Aliran Migrasi Risen Antarprovinsi (jiwa)",
                        x=0, xanchor="left", y=1, yanchor="top",
                        pad=dict(t=12, l=10),
                    ),
                    height=tinggi_sankey,
                    font_size=13,
                    margin=dict(t=125, b=20, l=10, r=10),
                    annotations=[
                        dict(x=0, y=1, xref="paper", yref="paper", showarrow=False, yshift=14,
                             text="<b>Provinsi asal (5 tahun lalu)</b>",
                             xanchor="left", yanchor="bottom"),
                        dict(x=1, y=1, xref="paper", yref="paper", showarrow=False, yshift=14,
                             text="<b>Provinsi tujuan (tempat tinggal sekarang)</b>",
                             xanchor="right", yanchor="bottom"),
                    ],
                )
                tampilkan_plot(fig_flow, use_container_width=True)

        else:
            # ---------------------------------------------------------
            # 2. MATRIKS ORIGIN-DESTINATION
            # ---------------------------------------------------------
            df_prov = df_migrasi[(df_migrasi["asal"] != LUAR_NEGERI)
                                 & df_migrasi["tujuan"].isin(URUTAN_PROV)]

            ada = set(df_prov["asal"]) | set(df_prov["tujuan"])
            opsi_od = [p for p in URUTAN_PROV if p in ada]               # urut per wilayah

            col_o1, col_o2 = st.columns(2)
            with col_o1:
                asal_od = st.multiselect(
                    "Filter provinsi asal (baris):", opsi_od, default=[],
                    placeholder="Semua asal", key="od_asal",
                )
            with col_o2:
                tujuan_od = st.multiselect(
                    "Filter provinsi tujuan (kolom):", opsi_od, default=[],
                    placeholder="Semua tujuan", key="od_tujuan",
                )

            urut_baris = [p for p in opsi_od if p in asal_od] if asal_od else opsi_od
            urut_kolom = [p for p in opsi_od if p in tujuan_od] if tujuan_od else opsi_od

            mat = (df_prov[df_prov["asal"].isin(urut_baris) & df_prov["tujuan"].isin(urut_kolom)]
                   .pivot_table(index="asal", columns="tujuan", values="jumlah", fill_value=0)
                   .reindex(index=urut_baris, columns=urut_kolom, fill_value=0))

            if mat.values.sum() == 0:
                st.warning(
                    "Tidak ada aliran untuk kombinasi filter ini. "
                    "Perpindahan di dalam provinsi yang sama tidak ditampilkan."
                )
            else:
                z = np.log10(mat.where(mat > 0))                        # log: aliran kecil tetap terlihat
                fig_od = go.Figure(go.Heatmap(
                    z=z.values, x=urut_kolom, y=urut_baris, customdata=mat.values,
                    colorscale="Viridis",                               # ramah buta warna
                    hovertemplate="Asal: %{y}<br>Tujuan: %{x}<br>"
                                  "Migran: %{customdata:,.0f} jiwa<extra></extra>",
                    colorbar=dict(
                        title="Jiwa (skala log)",
                        tickvals=[0, 1, 2, 3, 4, 5],
                        ticktext=["1", "10", "100", "1 rb", "10 rb", "100 rb"],
                    ),
                    hoverongaps=False,
                ))
                fig_od.update_layout(
                    title=(f"Matriks OD migrasi risen — {len(urut_baris)} asal × "
                           f"{len(urut_kolom)} tujuan (baris = asal, kolom = tujuan)"),
                    xaxis=dict(title="Provinsi tujuan (sekarang)", tickangle=-60, side="bottom"),
                    yaxis=dict(title="Provinsi asal (5 tahun lalu)", autorange="reversed"),
                    height=max(420, min(900, 26 * len(urut_baris) + 220)),
                    margin=dict(l=10, r=10, t=70, b=10),
                )
                tampilkan_plot(fig_od, use_container_width=True)

        # ---------------------------------------------------------
        # UNDUH, PENJELASAN DATA & AKSES DATA (berlaku untuk kedua mode)
        # ---------------------------------------------------------
        data_unduh = df_flow if representasi_flow == "Sankey Diagram" else mat.reset_index()
        st.download_button(
            "⬇️ Unduh data migrasi yang ditampilkan (CSV)",
            data_unduh.to_csv(index=False).encode("utf-8"),
            file_name="migrasi_antarprovinsi.csv", mime="text/csv",
            key="dl_flow",
        )

        st.markdown(
            """
            <style>
            .rata-kk { text-align: justify; text-justify: inter-word; }
            .rata-kk ul { text-align: left; margin-top: 0.3rem; }
            .rata-kk li { text-align: justify; text-justify: inter-word; margin-bottom: 0.4rem; }
            </style>

            <div class="rata-kk">

            <b>Data yang digunakan pada topik ini:</b>

            <ul>
            <li><b>Migrasi Risen Menurut Provinsi Tempat Tinggal Sekarang dan Provinsi Tempat
            Tinggal 5 Tahun yang Lalu</b> — tabel Long Form Sensus Penduduk 2020 (pencacahan
            2022) berbentuk matriks asal–tujuan: baris menunjukkan provinsi tempat tinggal
            sekarang (tujuan), kolom menunjukkan provinsi tempat tinggal lima tahun sebelumnya
            (asal), dan isi sel adalah jumlah penduduk. Migrasi risen adalah perpindahan
            penduduk antarprovinsi, yaitu penduduk yang provinsi tempat tinggalnya saat
            pencacahan berbeda dengan provinsi tempat tinggal lima tahun sebelumnya. Dipakai
            sebagai <b>lebar pita aliran</b> pada Sankey dan sebagai <b>warna sel</b> pada
            matriks origin-destination.</li>
            <li><b>Pengolahan data</b> — baris dan kolom total ("Jumlah") dibuang, matriks
            diubah menjadi pasangan asal–tujuan, lalu sel diagonal (penduduk yang tidak
            berpindah provinsi) dan sel bernilai nol tidak ditampilkan. Kolom asal
            "Lainnya/Luar Negeri" hanya muncul pada Sankey, tidak pada matriks.</li>
            </ul>

            <p>Berbeda dengan Topik 1 dan 2, data migrasi hanya tersedia untuk satu periode
            (bukan runtun 2020–2024), sehingga tidak mengikuti pemilih tahun di bagian atas
            halaman. Cakupannya tingkat provinsi (34 provinsi).</p>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="rata-kk">

            <b>Akses data:</b>

            <ul>
            <li>Migrasi Risen Menurut Provinsi Tempat Tinggal Sekarang dan Provinsi Tempat
            Tinggal 5 Tahun yang Lalu, Long Form Sensus Penduduk 2020 (BPS):
            <a href="https://www.bps.go.id/en/publication/2023/07/20/97c956dd7ff3ece924911115/statistics-of-migration-indonesia-results-of-the-2020-population-census.html" target="_blank" rel="noopener noreferrer">Link Akses</a></li>
            </ul>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info(
            "Interaksi: **filter** provinsi asal dan tujuan untuk mengatur data yang ditampilkan, "
            "serta **tooltip** (arahkan kursor ke pita aliran atau sel matriks untuk melihat jumlah migran). "
            "Pada matriks, warna menggunakan skala logaritmik agar aliran kecil tetap terlihat."
        )

# =========================================================
# FOOTER
# =========================================================
st.divider()

f1, f2, f3 = st.columns(3)

with f1:
    st.markdown("#### 📊 Tentang Proyek")
    st.markdown(
        '<div style="text-align: justify; text-justify: inter-word;">'
        "Dashboard ini mencakup 3 topik visualisasi <b>geospasial</b>, "
        "<b>berhierarki</b>, dan <b>aliran/flow</b> dengan data <b>BPS 2020–2024</b>: "
        f"<b>{n_peta} kabupaten/kota</b> terpetakan (batas wilayah GADM), "
        "<b>17 lapangan usaha</b>, dan <b>34 provinsi</b> (pemekaran Papua digabung "
        "ke provinsi induk)."
        "</div>",
        unsafe_allow_html=True,
    )

with f2:
    st.markdown("#### 🔗 Tautan")
    st.markdown(
        "- [Repositori GitHub](https://github.com/tauradavin/uas-visdat-2026)\n"
        "- [Portal Data BPS](https://www.bps.go.id)\n"
        "- [Batas Wilayah GADM](https://gadm.org)"
    )

with f3:
    st.markdown("#### 👤 Dibuat oleh")
    st.markdown(
        "**Taura Davin Santosa**  \n"
        "NIM 222313401 (Kelas 3SD1)  \n"
        "Politeknik Statistika STIS"
    )

st.markdown(
    """
    <div style="text-align:left; margin-top:1rem;">
        <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
        <img src="https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white">
        <img src="https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white">
        <img src="https://img.shields.io/badge/Data-BPS%202020--2024-0A3161">
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "UAS Visualisasi Data dan Informasi, Semester Genap TA. 2025/2026, "
    "Politeknik Statistika STIS."
)

# =========================================================
# TOMBOL KEMBALI KE ATAS (CSS murni, tanpa iframe)
# =========================================================
st.markdown(
    '<a class="to-top" href="#paling-atas" title="Kembali ke atas">↑</a>',
    unsafe_allow_html=True,
)
