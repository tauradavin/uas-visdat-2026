# Dashboard Indikator Makro Indonesia: Potret Kemiskinan, Ekonomi, dan Migrasi

Dashboard interaktif untuk UAS **Visualisasi Data dan Informasi** (K203407), Politeknik Statistika STIS, Semester Genap TA. 2025/2026. Dashboard memotret Indonesia dari tiga sisi: **di mana** kesejahteraan tersebar (IPM dan kemiskinan kabupaten/kota), **apa** yang menopang perekonomian (struktur PDB menurut lapangan usaha), dan **ke mana** penduduk berpindah (migrasi risen antarprovinsi).

| | |
|---|---|
| **Aplikasi (publik)** | uas-visdat-2026-to2vo4vj4yqopzjpmcdu8x.streamlit.app |
| **Repositori** | https://github.com/tauradavin/uas-visdat-2026 |
| **Penulis** | Taura Davin Santosa, NIM 222313401, Kelas 3SD1 |
| **Sumber data utama** | BPS (Badan Pusat Statistik) |

## Tiga Topik Visualisasi

| Topik | Pertanyaan | Teknik | Data BPS |
|---|---|---|---|
| **Geospasial** | Daerah mana yang IPM-nya tinggi dan kemiskinannya rendah? | Peta choropleth dan proportional symbol (±500 kab/kota) | IPM dan persentase penduduk miskin (P0) per kab/kota, 2020–2024 |
| **Berhierarki** | Sektor dan lapangan usaha apa yang menopang PDB, dan mana yang tumbuh? | Treemap dan sunburst (4 level: PDB › sektor › lapangan usaha › sub-lapangan usaha) | PDB ADHB dan laju pertumbuhan ADHK 2010 menurut lapangan usaha, 2020–2024 |
| **Aliran/Flow** | Dari mana ke mana penduduk berpindah antarprovinsi? | Sankey dan matriks origin-destination (skala log) | Migrasi risen, Long Form Sensus Penduduk 2020 |

Tab **Home** berisi pengantar, ringkasan topik, temuan utama yang dihitung otomatis dari data, dan daftar sumber data.

### Ketentuan minimal yang dipenuhi (Lampiran A)

**Geospasial**
- Tingkat kabupaten/kota; dua jenis peta (choropleth dan proportional symbol)
- Indikator berupa nilai indeks dan persentase (bukan angka absolut)
- Skala warna Viridis dengan rentang dikunci lintas tahun agar antar tahun dapat dibandingkan
- Tooltip (nilai dan perubahan tahunan), legenda, zoom/pan, filter provinsi dengan zoom otomatis, panel detail dengan peringkat dan grafik tren

**Berhierarki**
- 4 level hierarki (PDB, sektor, 17 lapangan usaha, sub-lapangan usaha)
- 2 representasi berbeda: treemap dan sunburst
- Dua variabel berbeda: **ukuran** = PDB ADHB, **warna** = laju pertumbuhan ADHK (skala divergen simetris di sekitar 0)
- Drill-down melalui pilihan sektor dan lapangan usaha, dengan penunjuk posisi (breadcrumb) dan klik langsung pada grafik

**Aliran/Flow**
- 34 provinsi asal/tujuan (ditambah kategori Lainnya/Luar Negeri)
- 2 teknik: Sankey dan matriks OD
- Volume dikodekan oleh lebar pita (Sankey) dan warna sel (matriks); arah asal → tujuan kiri ke kanan (Sankey), baris = asal dan kolom = tujuan (matriks)
- Filter provinsi asal dan tujuan, serta tooltip

### Ketentuan umum
- **Interaksi:** filter, tooltip, zoom/pan, dan drill-down pada setiap topik
- **Ramah buta warna:** palet Okabe-Ito (`CB_PALETTE`), Viridis, dan skala divergen biru–merah
- **Responsif:** tampilan diuji di laptop dan ponsel
- **Sumber:** "Sumber: BPS" dan tautan tabel tercantum pada setiap topik

## Sumber Data

Tanggal akses: **3 Oktober 2026**

| Data | Judul tabel/publikasi | Tahun | URL |
|---|---|---|---|
| IPM kab/kota | [Metode Baru] Indeks Pembangunan Manusia (IPM) Menurut Kabupaten/Kota | 2020–2024 | https://www.bps.go.id/id/statistics-table/2/NDEzIzI=/-metode-baru-indeks-pembangunan-manusia.html |
| Kemiskinan kab/kota | Persentase Penduduk Miskin (P0) Menurut Kabupaten/Kota | 2020–2024 | https://www.bps.go.id/id/statistics-table/2/NjIxIzI=/persentase-penduduk-miskin-menurut-kabupaten-kota.html |
| PDB ADHB | Produk Domestik Bruto Atas Dasar Harga Berlaku Menurut Lapangan Usaha (miliar rupiah) | 2020–2024 | https://www.bps.go.id/id/statistics-table/3/UzFSTVVXUlliME5XYzBZNUwwNVFRa3h6Y1d3M1p6MDkjMw==/produk-domestik-bruto-atas-dasar-harga-berlaku-menurut-lapangan-usaha-miliar-rupiah-.html |
| Pertumbuhan PDB ADHK | Laju Pertumbuhan PDB Atas Dasar Harga Konstan 2010 Menurut Lapangan Usaha, bersumber dari Berita Resmi Statistik Pertumbuhan Ekonomi Indonesia | 2020–2024 | [BRS 2022](https://www.bps.go.id/assets/pressrelease/2023/02/06/1997/ekonomi-indonesia-tahun-2022-tumbuh-5-31-persen.html), [BRS 2024](https://www.bps.go.id/assets/pressrelease/2025/02/05/2408/ekonomi-indonesia-tahun-2024-tumbuh-5-03-persen--c-to-c---ekonomi-indonesia-triwulan-iv-2024-tumbuh-5-02-persen--y-on-y---ekonomi-indonesia-triwulan-iv-2024-tumbuh-0-53-persen--q-to-q--.html) |
| Migrasi risen | Migrasi Risen Menurut Provinsi Tempat Tinggal Sekarang dan Provinsi Tempat Tinggal 5 Tahun yang Lalu, Long Form Sensus Penduduk 2020 | 2020 | https://sensus.bps.go.id/topik/tabular/sp2022/170/1/2 dan [publikasi BPS](https://www.bps.go.id/en/publication/2023/07/20/97c956dd7ff3ece924911115/statistics-of-migration-indonesia-results-of-the-2020-population-census.html) |
| Batas wilayah (non-BPS) | GADM v4.1, level 2 (kab/kota) | – | https://gadm.org/download_country.html |

## Pengolahan Data

Semua langkah pengolahan ada di kode agar dapat direproduksi.

- **Geospasial** (`prepare_geo_data.py`): menggabungkan IPM dan persentase penduduk miskin BPS dengan batas wilayah GADM, menghasilkan `geo_ipm_miskin.geojson`. Penggabungan dilakukan berdasarkan kecocokan nama provinsi dan kab/kota.
- **Berhierarki** (`app.py`): file PDB ADHB per tahun dibaca dan dibersihkan (format angka dan catatan kaki), diambil 17 lapangan usaha utama serta sub-lapangan usaha (baris bernomor), lalu digabung dengan tabel laju pertumbuhan menurut kode lapangan usaha. Pengelompokan sektor (Primer: A–B, Sekunder: C–F, Tersier: G–R,S,T,U) mengikuti klasifikasi umum.
- **Aliran** (`app.py`): matriks asal–tujuan diubah ke format panjang. Baris dan kolom total dibuang, sel diagonal (tidak berpindah provinsi) dan sel nol tidak ditampilkan, tanda "-" dianggap 0.

## Cara Menjalankan Secara Lokal

Prasyarat: Python 3.11 atau lebih baru.

```bash
git clone https://github.com/tauradavin/uas-visdat-2026.git
cd uas-visdat-2026
pip install -r requirements.txt
streamlit run app.py
```

Aplikasi terbuka di `http://localhost:8501`.

## Struktur Repositori

```
.
├── app.py                      # aplikasi Streamlit (Home, Geospasial, Berhierarki, Aliran)
├── style.css                   # tema tampilan (navy dan oranye BPS)
├── prepare_geo_data.py         # pengolahan data geospasial -> geo_ipm_miskin.geojson
├── geo_ipm_miskin.geojson      # data terolah: IPM, % miskin, dan batas wilayah
├── requirements.txt            # dependensi Python
├── Data/                       # data BPS: PDB ADHB, pertumbuhan PDB, migrasi risen
│   ├── Produk Domestik Bruto ... Harga Berlaku ... (per tahun).csv
│   ├── pertumbuhan_pdb_adhk2010_2020_2024.csv
│   └── migrasi_risen_wide.csv
└── gambar/                     # logo
```

## Deployment

Dideploy di **Streamlit Community Cloud** dari branch `main`, dengan file utama `app.py` dan Python 3.11. Tautan aplikasi dapat diakses publik tanpa login dan dijaga tetap aktif sampai nilai akhir diumumkan.

## Keterbatasan

- Data migrasi hanya satu periode dan tingkat provinsi, sehingga tidak mengikuti pemilih tahun. Pemekaran Papua digabung ke provinsi induk (34 provinsi).
- Data migrasi (`migrasi_risen_wide.csv`) ditranskripsi dari tabel BPS. Label kolom Papua dan Papua Barat pada tabel sumber dikoreksi karena nilai diagonalnya menunjukkan urutan yang terbalik. Jumlah baris dan kolom dapat berbeda 1–5 jiwa dari angka "Jumlah" pada tabel (pembulatan sumber).
- Geospasial: batas wilayah GADM tidak sepenuhnya identik dengan wilayah administrasi BPS (daerah otonom baru, objek non-administratif, perbedaan penulisan nama), sehingga sebagian poligon tidak memiliki data.
- Berhierarki: tabel pertumbuhan BPS hanya memuat 17 lapangan usaha, sehingga warna sub-lapangan usaha mengikuti lapangan usaha induknya. Pertumbuhan tingkat sektor dan PDB adalah rata-rata tertimbang (bobot nilai ADHB), bukan angka resmi BPS.

## Deklarasi Penggunaan AI

Alat bantu berbasis AI (Claude, Anthropic) digunakan sebatas alat bantu, antara lain untuk membantu menyusun kode, memformat data migrasi dari tabel BPS menjadi CSV, dan menyusun draf dokumentasi. Seluruh isi proyek, termasuk pemilihan data, rancangan visualisasi, dan interpretasi, menjadi tanggung jawab penuh penulis.

## Lisensi dan Atribusi

Data statistik bersumber dari Badan Pusat Statistik (BPS). Batas wilayah administrasi bersumber dari GADM v4.1 dan tunduk pada lisensi GADM. Proyek ini dibuat untuk keperluan akademik.
