import re
from pathlib import Path
import pandas as pd
import geopandas as gpd

DATA_DIR = Path(r"C:\Users\taura\Downloads\UAS VISDAT\Data")
GADM_PATH = Path(r"C:\Users\taura\Downloads\UAS VISDAT\gadm41_IDN_2.json\gadm41_IDN_2.json")
OUT_PATH = Path(r"C:\Users\taura\Downloads\UAS VISDAT\geo_ipm_miskin.geojson")
TAHUN = [2020, 2021, 2022, 2023, 2024]

# Semua file memakai pola nama yang sama: "IPM {tahun}.csv" dan "Miskin {tahun}.csv"
FILE_IPM = {t: DATA_DIR / f"IPM {t}.csv" for t in TAHUN}
FILE_MISKIN = {t: DATA_DIR / f"Miskin {t}.csv" for t in TAHUN}


# ---------- 1. Parsing CSV BPS ----------
def parse_bps_wide_csv(path, value_col_name):
    df_raw = pd.read_csv(path, skiprows=3, header=None,
                         names=["wilayah", "nilai"], encoding="utf-8-sig")
    df_raw = df_raw.dropna(subset=["wilayah"]).reset_index(drop=True)
    df_raw["wilayah"] = df_raw["wilayah"].astype(str).str.strip()

    records, current_prov = [], None
    for _, row in df_raw.iterrows():
        w = row["wilayah"]
        if w.upper() == "INDONESIA":
            continue
        if w == w.upper() and any(c.isalpha() for c in w):
            current_prov = w
            continue
        nilai = pd.to_numeric(str(row["nilai"]).replace(",", "."), errors="coerce")
        records.append({"provinsi_bps": current_prov, "kabkota_bps": w,
                        value_col_name: nilai})
    return pd.DataFrame(records)


frames = []
for t in TAHUN:
    frames.append(parse_bps_wide_csv(FILE_IPM[t], f"ipm_{t}"))
    frames.append(parse_bps_wide_csv(FILE_MISKIN[t], f"miskin_{t}"))
    print(f"{t}: IPM {len(frames[-2])} baris, Miskin {len(frames[-1])} baris")

df_bps = frames[0]
for f in frames[1:]:
    df_bps = pd.merge(df_bps, f, on=["provinsi_bps", "kabkota_bps"], how="outer")
print(f"Gabungan semua tahun: {len(df_bps)} baris")


# ---------- 2. Normalisasi nama ----------
KECUALI_PREFIX_KOTA = {"kotabaru", "kotawaringinbarat", "kotawaringintimur", "kotamobagu"}
MANUAL_FIX = {
    "tanjungjabungbarat": "tanjungjabungb",
    "tanjungjabungtimur": "tanjungjabungt",
    "makasar": "makassar",
    "pakpakbharat": "pakpakbarat",
}


def normalize_name(name):
    if pd.isna(name):
        return ""
    name = str(name).split("/")[0].strip()
    stripped = re.sub(r"^(Kota|Kabupaten|Kab\.)\s*", "", name, flags=re.IGNORECASE)
    stripped_key = re.sub(r"\s+", "", re.sub(r"[.,\-]", " ", stripped)).lower()
    full_key = re.sub(r"\s+", "", re.sub(r"[.,\-]", " ", name)).lower()
    key = stripped_key if full_key not in KECUALI_PREFIX_KOTA else full_key
    return MANUAL_FIX.get(key, key)


df_bps["match_key"] = df_bps["kabkota_bps"].apply(normalize_name)

PROV_BPS_TO_GADM = {
    "ACEH": "Aceh", "SUMATERA UTARA": "SumateraUtara", "SUMATERA BARAT": "SumateraBarat",
    "RIAU": "Riau", "JAMBI": "Jambi", "SUMATERA SELATAN": "SumateraSelatan",
    "BENGKULU": "Bengkulu", "LAMPUNG": "Lampung", "KEP. BANGKA BELITUNG": "BangkaBelitung",
    "KEPULAUAN RIAU": "KepulauanRiau", "DKI JAKARTA": "JakartaRaya", "JAWA BARAT": "JawaBarat",
    "JAWA TENGAH": "JawaTengah", "D I YOGYAKARTA": "Yogyakarta", "JAWA TIMUR": "JawaTimur",
    "BANTEN": "Banten", "BALI": "Bali", "NUSA TENGGARA BARAT": "NusaTenggaraBarat",
    "NUSA TENGGARA TIMUR": "NusaTenggaraTimur", "KALIMANTAN BARAT": "KalimantanBarat",
    "KALIMANTAN TENGAH": "KalimantanTengah", "KALIMANTAN SELATAN": "KalimantanSelatan",
    "KALIMANTAN TIMUR": "KalimantanTimur", "KALIMANTAN UTARA": "KalimantanUtara",
    "SULAWESI UTARA": "SulawesiUtara", "SULAWESI TENGAH": "SulawesiTengah",
    "SULAWESI SELATAN": "SulawesiSelatan", "SULAWESI TENGGARA": "SulawesiTenggara",
    "GORONTALO": "Gorontalo", "SULAWESI BARAT": "SulawesiBarat", "MALUKU": "Maluku",
    "MALUKU UTARA": "MalukuUtara",
    "PAPUA": "Papua", "PAPUA BARAT": "PapuaBarat",
    "PAPUA BARAT DAYA": "PapuaBarat", "PAPUA SELATAN": "Papua",
    "PAPUA TENGAH": "Papua", "PAPUA PEGUNUNGAN": "Papua",
}
df_bps["provinsi_gadm_key"] = df_bps["provinsi_bps"].map(PROV_BPS_TO_GADM)


# ---------- 3. Join dengan GADM ----------
gdf = gpd.read_file(GADM_PATH)
print(f"GADM: {len(gdf)} kab/kota")
gdf["match_key"] = gdf["NAME_2"].apply(normalize_name)

merged = gdf.merge(
    df_bps, left_on=["match_key", "NAME_1"], right_on=["match_key", "provinsi_gadm_key"],
    how="left", indicator=True,
)
merged = merged.drop_duplicates(subset=["GID_2"], keep="first").reset_index(drop=True)

print(f"\nCocok: {(merged['_merge'] == 'both').sum()} dari {len(gdf)} wilayah GADM")
print(merged.loc[merged["_merge"] == "left_only", ["NAME_1", "NAME_2"]].head(20).to_string())

used = set(merged.loc[merged["_merge"] == "both", "match_key"])
unused = df_bps[~df_bps["match_key"].isin(used)]
print(f"\nBaris BPS tidak match ke GADM: {len(unused)}")
print(unused[["provinsi_bps", "kabkota_bps"]].head(20).to_string())


# ---------- 4. Simpan ----------
kolom_nilai = [f"ipm_{t}" for t in TAHUN] + [f"miskin_{t}" for t in TAHUN]
out = merged[["NAME_1", "NAME_2", "provinsi_bps", "kabkota_bps"] + kolom_nilai + ["geometry"]].copy()
out = out.rename(columns={"NAME_1": "provinsi_gadm", "NAME_2": "kabkota_gadm"})
out["geometry"] = out["geometry"].simplify(0.01, preserve_topology=True)

out.to_file(OUT_PATH, driver="GeoJSON")
print(f"\nTersimpan: {OUT_PATH}")