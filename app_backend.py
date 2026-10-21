# -*- coding: utf-8 -*-
"""
Dashboard Customer Satisfaction (CSI) — Sales / Service / Spare Part
+ Page Profil Wilayah (Cluster BPS & Kelompok Budaya)
Streamlit + Plotly, data dari Google Sheets + Shapefile GeoPandas.

Jalankan dengan:
    python -m streamlit run app.py
"""

import os
import re
import io
import json
import math
import html
import textwrap
from datetime import datetime, timezone, timedelta
import time
from typing import Any

WIB = timezone(timedelta(hours=7))

import requests
import numpy as np
import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

import folium
from branca.element import Template, MacroElement
from streamlit_folium import st_folium

st.set_page_config(page_title="Dashboard Kepuasan Dealer", layout="wide")

# ============================================================
# KONSTANTA & METADATA PROFILE
# ============================================================

RED_OUTLINE = "#E60012"
ORANGE_OUTLINE = "#FF6B00"
BLUE_OUTLINE = "#1665D8"

GREEN = "#35A853"
RED = "#E60012"
YELLOW = "#FFB000"
ORANGE = "#FF6B00"

pio.templates["csl_performance"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color="#262626", size=12),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        colorway=[RED, ORANGE, YELLOW, GREEN, BLUE_OUTLINE, "#C8102E"],
        # Seluruh hover Plotly diratakan ke kiri secara global, sehingga
        # berlaku konsisten pada chart H1, H2, H3, profil, dan profil wilayah.
        hoverlabel=dict(
            bgcolor="#262626",
            font=dict(color="#FFFFFF"),
            bordercolor="#262626",
            align="left",
        ),
        xaxis=dict(gridcolor="#F0F1F3", zerolinecolor="#C7C9CD", linecolor="#E7E9EC"),
        yaxis=dict(gridcolor="#F0F1F3", zerolinecolor="#C7C9CD", linecolor="#E7E9EC"),
        legend=dict(bgcolor="rgba(255,255,255,0)", font=dict(size=11)),
    )
)
pio.templates.default = "csl_performance"

SEMESTER_ORDER = {1: 0, 2: 1}

TARGET_PROVINCES = {
    "dki jakarta", "jakarta", "jawa barat", "jawa tengah",
    "daerah istimewa yogyakarta", "di yogyakarta", "yogyakarta",
    "jawa timur", "banten", "bali", "nusa tenggara barat", "ntb",
    "nusa tenggara timur", "ntt"
}

SHP_KAB_CANDIDATES = [
    "WADMKK", "ADM2_EN", "NAME_2", "KABKOT", "kabupaten", "name",
    "ADM2_REF", "ADM2ALT1EN", "ADM2ALT2EN"
]

SHP_PROV_CANDIDATES = [
    "WADMPR", "ADM1_EN", "NAME_1", "PROVINSI", "PROVINCE", "adm1_en"
]

PROFILE_NAMES = {
    "P1": "Detractor", "P2": "Below Average", "P3": "Middle",
    "P4": "Above Average", "P5": "Promoter",
}
PROFILE_COLORS = {
    "P1": RED, "P2": ORANGE, "P3": YELLOW, "P4": "#9CCC65", "P5": GREEN,
}

# Mapping nama wilayah baku dashboard -> Keresidenan.
# Nama dan kelompok mengikuti mapping operasional yang diberikan pengguna.
KARESIDENAN_MAP = {
    "Surabaya": "Karesidenan Surabaya",
    "Gresik": "Karesidenan Eks Surabaya",
    "Sidoarjo": "Karesidenan Eks Surabaya",
    "Mojokerto": "Karesidenan Eks Surabaya",
    "Jombang": "Karesidenan Eks Surabaya",
    "Malang": "Karesidenan Malang",
    "Kota Malang": "Karesidenan Malang",
    "Pasuruan": "Karesidenan Eks Malang",
    "Probolinggo": "Karesidenan Eks Malang",
    "Lumajang": "Karesidenan Eks Malang",
    "Banyuwangi": "Karesidenan Besuki",
    "Jember": "Karesidenan Besuki",
    "Bondowoso": "Karesidenan Besuki",
    "Situbondo": "Karesidenan Besuki",
    "Kediri": "Karesidenan Kediri",
    "Kab-Kodya Blitar": "Karesidenan Kediri",
    "Tulungagung": "Karesidenan Kediri",
    "Trenggalek": "Karesidenan Kediri",
    "Nganjuk": "Karesidenan Kediri",
    "Madiun": "Karesidenan Madiun",
    "Ngawi": "Karesidenan Madiun",
    "Magetan": "Karesidenan Madiun",
    "Ponorogo": "Karesidenan Madiun",
    "Pacitan": "Karesidenan Madiun",
    "Bojonegoro": "Karesidenan Bojonegoro",
    "Tuban": "Karesidenan Bojonegoro",
    "Lamongan": "Karesidenan Bojonegoro",
    "Bangkalan": "Karesidenan Madura",
    "Sampang": "Karesidenan Madura",
    "Pamekasan": "Karesidenan Madura",
    "Sumenep": "Karesidenan Madura",
    "Kupang": "Karesidenan Kupang",
}

KAB_TO_PROVINSI = {
    "surabaya": "Jawa Timur", "sidoarjo": "Jawa Timur", "gresik": "Jawa Timur",
    "malang": "Jawa Timur", "batu": "Jawa Timur", "pasuruan": "Jawa Timur",
    "probolinggo": "Jawa Timur", "lumajang": "Jawa Timur", "kediri": "Jawa Timur",
    "nganjuk": "Jawa Timur", "tulungagung": "Jawa Timur", "trenggalek": "Jawa Timur",
    "blitar": "Jawa Timur", "madiun": "Jawa Timur", "ngawi": "Jawa Timur",
    "magetan": "Jawa Timur", "ponorogo": "Jawa Timur", "pacitan": "Jawa Timur",
    "bojonegoro": "Jawa Timur", "tuban": "Jawa Timur", "lamongan": "Jawa Timur",
    "jombang": "Jawa Timur", "mojokerto": "Jawa Timur", "jember": "Jawa Timur",
    "banyuwangi": "Jawa Timur", "bondowoso": "Jawa Timur", "situbondo": "Jawa Timur",
    "pamekasan": "Jawa Timur", "sampang": "Jawa Timur", "sumenep": "Jawa Timur",
    "bangkalan": "Jawa Timur",
    "jakarta": "DKI Jakarta",
    "bandung": "Jawa Barat", "bogor": "Jawa Barat", "bekasi": "Jawa Barat",
    "depok": "Jawa Barat", "cirebon": "Jawa Barat", "tasikmalaya": "Jawa Barat",
    "sukabumi": "Jawa Barat", "karawang": "Jawa Barat",
    "semarang": "Jawa Tengah", "solo": "Jawa Tengah", "surakarta": "Jawa Tengah",
    "tegal": "Jawa Tengah", "pekalongan": "Jawa Tengah", "magelang": "Jawa Tengah",
    "yogyakarta": "DI Yogyakarta", "sleman": "DI Yogyakarta", "bantul": "DI Yogyakarta",
    "denpasar": "Bali", "badung": "Bali", "gianyar": "Bali",
    "mataram": "Nusa Tenggara Barat", "lombok": "Nusa Tenggara Barat",
    "kupang": "Nusa Tenggara Timur",
}


# ============================================================
# DATA LOADING (GOOGLE SHEETS & SHAPEFILE)
# ============================================================

def _extract_spreadsheet_id(url: str) -> str:
    m = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if not m:
        raise ValueError("URL Google Sheets tidak valid.")
    return m.group(1)


def _gviz_csv_url(spreadsheet_url: str, sheet_name: str) -> str:
    sid = _extract_spreadsheet_id(spreadsheet_url)
    return (
        f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq"
        f"?tqx=out:csv&sheet={sheet_name}"
    )


@st.cache_data(ttl=600, show_spinner=False)
def read_sheet(sheet_name: str) -> pd.DataFrame:

    spreadsheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    url = _gviz_csv_url(spreadsheet_url, sheet_name)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
    }

    last_error = None

    # coba maksimal 5 kali
    for attempt in range(5):

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()

            df = pd.read_csv(
                io.StringIO(response.text)
            )

            df.columns = [
                str(c).strip()
                for c in df.columns
            ]

            return df

        except Exception as e:

            last_error = e

            # tunggu sebelum mencoba lagi
            time.sleep(2 * (attempt + 1))

    # kalau 5 kali tetap gagal
    raise RuntimeError(
        f"Gagal mengambil sheet '{sheet_name}' "
        f"setelah 5 percobaan. Error terakhir: {last_error}"
    )


def try_read_sheet(sheet_name: str) -> pd.DataFrame:
    try:
        return read_sheet(sheet_name)


    except Exception as e:
        st.error(
            f"Gagal membaca sheet '{sheet_name}': "
            f"{type(e).__name__}: {e}"
        )
        return pd.DataFrame()


def try_read_sheet_silent(sheet_name: str) -> pd.DataFrame:
    """Sama seperti try_read_sheet, tetapi tidak menampilkan st.error.
    Dipakai saat mencoba beberapa alternatif nama worksheet secara berurutan."""
    try:
        return read_sheet(sheet_name)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_shapefile():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "assets", "maps", "batas_kabkota_indonesia", "idn_admbnda_adm2_bps_20200401.shp"),
        os.path.join("assets", "maps", "batas_kabkota_indonesia", "idn_admbnda_adm2_bps_20200401.shp"),
        "idn_admbnda_adm2_bps_20200401.shp",
    ]
    shp_path = None
    for p in possible_paths:
        if os.path.exists(p):
            shp_path = p
            break

    if not shp_path:
        return None

    try:
        gdf = gpd.read_file(shp_path)
        if gdf.crs is None or str(gdf.crs).lower() != "epsg:4326":
            gdf = gdf.to_crs(epsg=4326)

        # 1. Filter provinsi target (Jawa, Bali, NTB, NTT) saat loading
        prov_col = _find_shp_col(gdf, SHP_PROV_CANDIDATES)
        if prov_col:
            gdf["__norm_prov"] = gdf[prov_col].apply(
                lambda x: str(x).strip().lower() if pd.notna(x) else ""
            )
            gdf = gdf[
                gdf["__norm_prov"].apply(lambda p: any(tp in p for tp in TARGET_PROVINCES))
            ].copy()
            if "__norm_prov" in gdf.columns:
                gdf = gdf.drop(columns=["__norm_prov"])

        # 2. Simplify geometry dengan tolerance=0.01 agar ukuran JSON sangat kecil (mencegah MessageSizeError)
        gdf["geometry"] = gdf.geometry.simplify(tolerance=0.01, preserve_topology=True)
        return gdf
    except Exception:
        return None


# ============================================================
# COLUMN AUTO-DETECTION & HELPERS
# ============================================================

ALIASES = {
    "year": ["year", "tahun"],
    "semester": ["semester", "periode"],
    "main_dealer": ["main dealer", "md code", "maindealer", "kode main dealer"],
    "layer": ["layer"],
    "karesidenan": ["karesidenan", "keresidenan", "residency"],
    "kab_kota": [
        "kab/kota", "kabupaten/kota", "kab kota", "city of dealer",
        "city of ahass", "city of parts shop", "city", "kota", "kabupaten",
    ],
    "dealer_code": [
        "dealer code", "kode dealer", "ahass code", "kode ahass",
        "parts shop code", "kode part shop", "dealer", "ahass", "part shop",
    ],
    "profile": ["profile", "profil"],
    "gender": ["gender", "jenis kelamin"],
    "age": ["age group", "age", "usia", "kelompok usia"],
    "motor_type": [
        "type of motorcycle", "variant of motorcycle", "type of parts",
        "type motor", "tipe motor", "jenis motor", "merk", "segment"
    ],
    "ses": ["ses"],
    "payment": [
        "d15", "d12", "d6", "d7", "payment", "tipe pembayaran", "metode pembayaran",
        "method of payment", "method of purchasing", "cara pembayaran"
    ],
    "retention": [
        "retention unit", "retention service", "retention part", "retention level",
        "retention", "retensi pelanggan", "retensi"
    ],
    "nps": ["nps"],
    "nps_unit": ["nps_unit", "nps unit"],
    "nps_dealer": ["nps_dealer", "nps dealer", "nps ahass", "nps part shop", "nps part"],
    "importance": ["importance"],
}


def find_col(df: pd.DataFrame, candidates):
    if df is None or df.empty:
        return None
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        cand_l = cand.strip().lower()
        if cand_l in cols_lower:
            return cols_lower[cand_l]
    for cand in candidates:
        cand_l = cand.strip().lower()
        for lower, orig in cols_lower.items():
            if cand_l in lower:
                return orig
    return None


def build_indicator_name_map(meta_df: pd.DataFrame) -> dict:
    """Membentuk mapping KODE -> nama indikator dari metadata H1/H2/H3."""
    if meta_df is None or meta_df.empty:
        return {}
    code_col = find_col(meta_df, [
        "Kode_Indikator", "kode indikator", "Kode Indicator",
        "kode_indicator", "indicator code", "kode", "code",
    ])
    name_col = find_col(meta_df, [
        "Nama_Indikator", "nama indikator", "Indicator Name",
        "nama_indicator", "indicator", "atribut", "attribute",
        "description", "keterangan",
    ])
    if not code_col or not name_col:
        return {}
    result = {}
    for _, row in meta_df[[code_col, name_col]].dropna(subset=[code_col]).iterrows():
        code = str(row[code_col]).strip().upper()
        name = str(row[name_col]).strip()
        if code and name and name.lower() != "nan":
            result[code] = name
    return result


def detect_columns(df: pd.DataFrame, unit_key: str) -> dict:
    cols = {}
    for logical, candidates in ALIASES.items():
        cand = list(candidates)
        if logical == "dealer_code":
            if unit_key == "sales":
                cand = ["dealer code", "kode dealer", "dealer"] + cand
            elif unit_key == "service":
                cand = ["ahass code", "kode ahass", "ahass"] + cand
            elif unit_key == "parts":
                cand = ["parts shop code", "kode part shop", "part shop"] + cand
        if logical == "nps_dealer":
            if unit_key == "sales":
                cand = ["nps dealer"] + cand
            elif unit_key == "service":
                cand = ["nps ahass"] + cand
            elif unit_key == "parts":
                cand = ["nps part shop"] + cand
        if logical == "nps":
            # NPS umum dipakai sebagai gauge tambahan khusus H3. Pencarian
            # dibuat exact agar tidak tertukar dengan NPS Unit/Part Shop.
            exact_nps = {str(c).strip().lower(): c for c in df.columns}
            cols[logical] = exact_nps.get("nps")
            continue
        cols[logical] = find_col(df, cand)
    return cols


def _norm(s):
    if pd.isna(s):
        return ""
    return re.sub(r"^(kota|kabupaten|kab\.?)\s+", "", str(s).strip().lower()).strip()


def _normalize_location_name(s):
    if pd.isna(s) or not s:
        return ""
    name = str(s).strip().lower()
    name = re.sub(r"\bkab-kodya\b", "", name)
    name = re.sub(r"\b(kabupaten|kab|kodya|kota)\b\.?", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _normalize_exact_location(s):
    if pd.isna(s) or not s:
        return ""
    name = str(s).strip().lower()
    name = re.sub(r"\bkab-kodya\b", "", name)
    name = re.sub(r"\b(kabupaten|kab)\b\.?", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _dashboard_region_name(value):
    """Nama wilayah baku yang dipakai bersama oleh data, peta, dan filter."""
    if pd.isna(value) or not str(value).strip():
        return ""
    raw = re.sub(r"[_/]+", " ", str(value).strip().lower())
    raw = re.sub(r"\s+", " ", raw).strip()
    simple = _normalize_location_name(raw)
    # Inset tetap ditampilkan sebagai NTT, tetapi filter Kab/Kota mengikuti
    # nama wilayah pada data responden, yaitu Kupang.
    if simple in {"ntt", "nusa tenggara timur"} or "kupang" in simple:
        return "Kupang"
    if "kota malang" in raw or "kodya malang" in raw:
        return "Kota Malang"
    if simple in {"malang", "batu"}:
        return "Malang"
    merged_names = {
        "mojokerto": "Mojokerto", "kediri": "Kediri",
        "probolinggo": "Probolinggo", "pasuruan": "Pasuruan",
        "madiun": "Madiun", "blitar": "Kab-Kodya Blitar",
    }
    if simple in merged_names:
        return merged_names[simple]
    return simple.title()


def _set_map_region_filter(df, cols, key_prefix, region):
    """Memindahkan hasil klik peta ke state filter sebelum widget dibuat."""
    kab_col = cols.get("kab_kota") if cols else None
    md_col = cols.get("main_dealer") if cols else None
    kar_col = cols.get("karesidenan") if cols else None
    canonical_region = _dashboard_region_name(region)
    if not canonical_region or not kab_col or kab_col not in df.columns:
        return False
    region_rows = df.loc[df[kab_col].apply(_dashboard_region_name) == canonical_region]
    if region_rows.empty:
        return False
    st.session_state[f"{key_prefix}_kab"] = canonical_region

    # Pilih Main Dealer dari scope Tahun dan Semester yang sedang aktif agar
    # wilayah hasil klik tetap tersedia pada rangkaian filter bertingkat.
    scoped_region_rows = region_rows
    year_col = cols.get("year")
    sem_col = cols.get("semester")
    selected_year = st.session_state.get(f"{key_prefix}_year")
    selected_sem = st.session_state.get(f"{key_prefix}_sem")
    if selected_year not in (None, "Semua") and year_col and year_col in scoped_region_rows.columns:
        scoped_region_rows = scoped_region_rows[
            scoped_region_rows[year_col].astype(str) == str(selected_year)
        ]
    if selected_sem in ("Semester 1", "Semester 2") and sem_col and sem_col in scoped_region_rows.columns:
        sem_number = 1 if "1" in selected_sem else 2
        scoped_region_rows = scoped_region_rows[
            scoped_region_rows[sem_col].apply(_parse_semester) == sem_number
        ]
    if scoped_region_rows.empty:
        scoped_region_rows = region_rows

    if md_col and md_col in region_rows.columns:
        region_mds = sorted(scoped_region_rows[md_col].dropna().astype(str).unique().tolist())
        if region_mds:
            st.session_state[f"{key_prefix}_md"] = region_mds[0]

    # Karesidenan mengikuti kabupaten/kota yang dipilih lewat peta.
    if kar_col and kar_col in scoped_region_rows.columns:
        region_kars = sorted(
            scoped_region_rows[kar_col].dropna().astype(str).unique().tolist()
        )
        if region_kars:
            st.session_state[f"{key_prefix}_kar"] = region_kars[0]
        else:
            st.session_state[f"{key_prefix}_kar"] = "Semua"
    else:
        st.session_state[f"{key_prefix}_kar"] = "Semua"

    for suffix in ("layer", "dealer"):
        st.session_state[f"{key_prefix}_{suffix}"] = "Semua"
    return True


def _find_shp_col(gdf, candidates):
    if gdf is None or gdf.empty:
        return None
    cols_lower = {str(c).strip().lower(): c for c in gdf.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    for cand in candidates:
        for cl, orig in cols_lower.items():
            if cand.lower() in cl:
                return orig
    return None


def add_karesidenan(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    if df.empty:
        return df
    if cols.get("karesidenan") and cols["karesidenan"] in df.columns:
        return df
    kab_col = cols.get("kab_kota")
    if not kab_col or kab_col not in df.columns:
        return df
    df = df.copy()
    df["Karesidenan"] = df[kab_col].apply(
        lambda x: KARESIDENAN_MAP.get(_dashboard_region_name(x), "Lainnya")
    )
    cols["karesidenan"] = "Karesidenan"
    return df


def kab_to_provinsi(kab_value):
    return KAB_TO_PROVINSI.get(_norm(kab_value), None)


# ============================================================
# INDICATOR METADATA
# ============================================================

# Indikator berikut hanya ditambahkan ke metadata agar nama/keterangan dapat
# ditampilkan pada matriks. Indikator tidak boleh masuk ke perhitungan CSL,
# target gap, improvement, peta, maupun visual profiling/heatmap.
EXCLUDED_CALCULATION_INDICATORS = {
    "sales": {"E16", "E17", "F19", "F20", "B8", "C13"},
    "service": {"D14", "C11", "A4"},
    "parts": {"G21", "D10", "D12", "D14", "D13"},
}


def _canonical_unit_key(unit_key: str) -> str:
    unit = str(unit_key or "").strip().lower()
    return {
        "h1": "sales",
        "h2": "service",
        "h3": "parts",
    }.get(unit, unit)


def excluded_calculation_indicators(unit_key: str) -> set:
    """Kode yang hanya boleh digunakan sebagai metadata matriks per unit."""
    return EXCLUDED_CALCULATION_INDICATORS.get(_canonical_unit_key(unit_key), set())


def indicator_columns(df: pd.DataFrame, meta_df: pd.DataFrame, unit_key: str = None):
    if df is None or df.empty:
        return []
    excluded = excluded_calculation_indicators(unit_key)
    if meta_df is not None and not meta_df.empty:
        code_col = find_col(meta_df, ["kode_indicator", "code", "kode", "atribut", "attribute"])
        if code_col:
            codes = [str(c).strip() for c in meta_df[code_col].dropna().unique()]
            return [c for c in codes if c in df.columns and c.upper() not in excluded]
    pattern = re.compile(r"^[A-Za-z]\d{1,2}$")
    return [
        c for c in df.columns
        if pattern.match(str(c).strip()) and str(c).strip().upper() not in excluded
    ]


def _canonical_main_dealer(value) -> str:
    """Nilai baku Main Dealer untuk filter data dan nama kolom target."""
    normalized = re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
    if normalized in {"M2Z", "M3Z"}:
        return normalized
    # Nilai kosong dan pilihan gabungan sama-sama memakai target Semua.
    return "Semua"


def _canonical_target_layer(value) -> str:
    """Menyamakan variasi penulisan Layer dengan suffix kolom metadata."""
    normalized = re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
    aliases = {
        "BIGWING": "BigWing",
        "WING": "Wing",
        "REGULERH123": "RegulerH123",
        "REGULARH123": "RegulerH123",
        "REGULER123": "RegulerH123",
        "REGULERH23": "RegulerH23",
        "REGULARH23": "RegulerH23",
        "REGULER23": "RegulerH23",
    }
    return aliases.get(normalized, "")


def _find_target_col(meta_df: pd.DataFrame, candidates) -> str:
    """Pencarian exact yang toleran terhadap spasi/underscore pada header."""
    if meta_df is None or meta_df.empty:
        return None
    normalized_columns = {
        re.sub(r"[^a-z0-9]", "", str(column).lower()): column
        for column in meta_df.columns
    }
    for candidate in candidates:
        normalized_candidate = re.sub(r"[^a-z0-9]", "", candidate.lower())
        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]
    return None


def get_target_col(meta_df: pd.DataFrame, main_dealer: str, layer: str):
    """Pilih target sesuai MD dan Layer tanpa jatuh ke target MD lain."""
    md = _canonical_main_dealer(main_dealer)
    layer_suffix = _canonical_target_layer(layer)

    candidates = []
    if layer_suffix:
        candidates.append(f"Target_{md}_{layer_suffix}")
    candidates.append(f"Target_{md}")

    # Kolom generik hanya menjadi fallback terakhir untuk kompatibilitas data lama.
    candidates.append("Target")
    return _find_target_col(meta_df, candidates)


# ============================================================
# PERIOD HELPERS
# ============================================================

def get_available_periods(df: pd.DataFrame, cols: dict):
    year_col, sem_col = cols.get("year"), cols.get("semester")
    if not year_col or not sem_col or df.empty:
        return []
    tmp = df[[year_col, sem_col]].dropna().copy()
    tmp[year_col] = pd.to_numeric(tmp[year_col], errors="coerce")
    tmp[sem_col] = tmp[sem_col].apply(_parse_semester)
    tmp = tmp.dropna()
    periods = sorted(set(zip(tmp[year_col].astype(int), tmp[sem_col].astype(int))))
    return periods


def _parse_semester(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip().lower()
    if "2" in s:
        return 2
    if "1" in s:
        return 1
    try:
        return int(float(s))
    except Exception:
        return np.nan


def get_previous_period(selected_year, selected_semester, available_periods):
    if selected_year is None or selected_semester is None:
        return None
    try:
        selected_year = int(selected_year)
        selected_semester = int(selected_semester)
    except Exception:
        return None
    if not available_periods:
        return None
    ordered = sorted(set(available_periods), key=lambda p: (p[0], p[1]))
    try:
        idx = ordered.index((selected_year, selected_semester))
    except ValueError:
        return None
    if idx == 0:
        return None
    return ordered[idx - 1]


def period_label(year, sem):
    return f"Semester {sem} {year}"


# ============================================================
# FILTERS
# ============================================================

def _options(df, col):
    if not col or col not in df.columns:
        return []
    vals = sorted([str(v) for v in df[col].dropna().unique()])
    return vals

def _fmt_pct(value):
    """
    Format persentase:
    42.0  -> 42%
    42    -> 42%
    42.3  -> 42.3%
    """
    if value is None or pd.isna(value):
        return ""

    value = round(float(value), 1)

    if math.isclose(value, round(value), abs_tol=1e-9):
        return f"{int(round(value))}%"

    return f"{value:.1f}%"


def _entity_name_column(df: pd.DataFrame, key_prefix: str, dealer_label: str):
    """Cari kolom nama Dealer/AHASS/Part Shop tanpa mengubah identifier kode."""
    if df is None or df.empty:
        return None

    unit = str(key_prefix or "").strip().lower()
    label = str(dealer_label or "").strip().lower()

    if unit == "sales" or "dealer" in label:
        candidates = [
            "Dealer Name", "Name of Dealer", "Nama Dealer",
            "Dealer_Name", "dealer name",
        ]
    elif unit == "service" or "ahass" in label:
        candidates = [
            "AHASS Name", "Name of AHASS", "Nama AHASS",
            "AHASS_Name", "ahass name",
        ]
    else:
        candidates = [
            "Parts Shop Name", "Part Shop Name", "Name of Parts Shop",
            "Nama Parts Shop", "Nama Part Shop", "Parts_Shop_Name",
            "parts shop name", "part shop name",
        ]

    # Prioritaskan exact match agar kolom kode seperti "Dealer Code"
    # tidak salah terdeteksi sebagai kolom nama.
    exact = {
        re.sub(r"\s+", " ", str(col).strip().lower()): col
        for col in df.columns
    }
    for candidate in candidates:
        key = re.sub(r"\s+", " ", candidate.strip().lower())
        if key in exact:
            return exact[key]

    return find_col(df, candidates)



def apply_filters(df: pd.DataFrame, cols: dict, filters: dict,
                   override_year=None, override_semester=None,
                   ignore_period=False) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()

    year_col, sem_col = cols.get("year"), cols.get("semester")
    if not ignore_period:
        yr = override_year if override_year is not None else filters.get("year")
        sm = override_semester if override_semester is not None else filters.get("semester")
        if yr is not None and year_col:
            out = out[out[year_col].astype(str) == str(yr)]
        if sm is not None and sem_col:
            out = out[out[sem_col].apply(_parse_semester) == sm]
    else:
        if override_year is not None and year_col:
            out = out[out[year_col].astype(str) == str(override_year)]
        if override_semester is not None and sem_col:
            out = out[out[sem_col].apply(_parse_semester) == override_semester]

    mapping = [
        ("main_dealer", cols.get("main_dealer")),
        ("layer", cols.get("layer")),
        ("karesidenan", cols.get("karesidenan")),
        ("dealer", cols.get("dealer_code")),
    ]
    for key, col in mapping:
        val = filters.get(key)
        if val not in (None, "Semua") and col and col in out.columns:
            out = out[out[col].astype(str) == str(val)]

    kab_val = filters.get("kab_kota")
    kab_col = cols.get("kab_kota")
    if kab_val is not None and kab_col and kab_col in out.columns:
        out = out[
            out[kab_col].apply(_dashboard_region_name)
            == _dashboard_region_name(kab_val)
        ]
    return out


# ============================================================
# CALCULATIONS
# ============================================================

def calculate_satisfaction(df: pd.DataFrame, indicator_cols: list):
    if df is None or df.empty or not indicator_cols:
        return None
    vals = df[indicator_cols].apply(pd.to_numeric, errors="coerce")
    mean_score = vals.mean(axis=1).mean()
    if pd.isna(mean_score):
        return None
    return round(mean_score / 5 * 100, 1)


def calculate_attribute_satisfaction(df: pd.DataFrame, indicator_cols: list):
    result = {}
    if df is None or df.empty or not indicator_cols:
        return result
    for c in indicator_cols:
        series = pd.to_numeric(df[c], errors="coerce")
        m = series.mean()
        if pd.isna(m):
            continue
        result[c] = round(m / 5 * 100, 1)
    return result


def calculate_target_gap(attr_sat: dict, meta_df: pd.DataFrame, main_dealer: str, layer: str):
    gaps = {}
    if not attr_sat or meta_df is None or meta_df.empty:
        return gaps

    code_col = find_col(meta_df, ["kode_indicator", "code", "kode", "atribut", "attribute"])
    target_col = get_target_col(meta_df, main_dealer, layer)

    if not code_col or not target_col:
        return gaps

    meta_indexed = meta_df.set_index(meta_df[code_col].astype(str).str.strip())
    for code, sat in attr_sat.items():
        c_code = str(code).strip()
        if c_code in meta_indexed.index:
            raw_t = meta_indexed.loc[c_code, target_col]
            if isinstance(raw_t, pd.Series):
                raw_t = raw_t.iloc[0]
            t_str = str(raw_t).replace("%", "").replace(",", ".").strip()
            try:
                t_val = float(t_str)
                gaps[c_code] = round(sat - t_val, 1)
            except Exception:
                pass
    return gaps


def calculate_semester_difference(df_cur: pd.DataFrame, df_prev: pd.DataFrame, indicator_cols: list):
    if df_prev is None or df_prev.empty:
        return None
    cur = calculate_attribute_satisfaction(df_cur, indicator_cols)
    prev = calculate_attribute_satisfaction(df_prev, indicator_cols)
    if not prev:
        return None
    diffs = {}
    for code in cur:
        if code in prev:
            diffs[code] = round(cur[code] - prev[code], 1)
    return diffs


def compute_nps(series: pd.Series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    promoters = (s >= 9).sum()
    detractors = (s <= 6).sum()
    total = len(s)
    if total == 0:
        return None
    return round((promoters - detractors) / total * 100, 1)

# ============================================================
# MOTOR MAPPING & CANONICALIZATION HELPERS
# ============================================================

MOTOR_MASTER = [
    "Beat", "Beat Street", "Genio", "Scoopy", "Vario 125",
    "Vario 125 Street", "Vario Evo 160", "Stylo 160", "PCX 160",
    "ADV 160", "Forza", "CB150 Verza", "Sonic 150R",
    "CB150R StreetFire", "SB150X", "CRF150L", "CBR150R",
    "CBR250RR", "CRF250L", "ST125 Dax", "Monkey",
    "CRF250 Rally", "Revo", "Supra X 125 FI", "GTR 150",
    "Super Cub C125", "CT125", "ICON e:", "EM1 e:", "CUV e:",
]
MOTOR_RANK = {name: i for i, name in enumerate(MOTOR_MASTER)}

MOTOR_ALIAS = {
    # Beat
    "beat": "Beat",
    "beatfi": "Beat",
    "beatesp": "Beat",
    "beatespcbsiss": "Beat",
    "beatespcbsseries": "Beat",
    "beatpopesp": "Beat",
    "beatdeluxe": "Beat",
    "beatdeluxesmartkey": "Beat",
    "beatcbs": "Beat",
    "beatfi": "Beat",
    "beatfics": "Beat",
    "beatficw": "Beat",
    "beatsw": "Beat",

    # Beat Street
    "beatstreet": "Beat Street",
    "beatstreetfi": "Beat Street",
    "newbeatstreetesp": "Beat Street",
    "allnewbeatstreet": "Beat Street",

    # Genio
    "genio": "Genio",
    "geniocbs": "Genio",
    "geniocbsiss": "Genio",

    # Scoopy
    "scoopy": "Scoopy",
    "scoopyfisporty": "Scoopy",
    "scoopyfistylish": "Scoopy",
    "allnewscoopy": "Scoopy",
    "allnewscoopy2025": "Scoopy",
    "allnewscoopy2025smartkeytype": "Scoopy",
    "allnewscoopy2025cbstype": "Scoopy",
    "allnewscoopynewgenerationengine": "Scoopy",
    "allnewscoopynewgenerationenginesmartkeytype": "Scoopy",
    "allnewhondascoopyespsporty": "Scoopy",
    "allnewhondascoopyespstylish": "Scoopy",

    # Vario 125
    "vario125": "Vario 125",
    "vario125cbs": "Vario 125",
    "variotechno125pgmfi": "Vario 125",
    "variotechno125pgmficbs": "Vario 125",
    "vario125cbsidlingstopsystem": "Vario 125",

    # Vario 125 Street
    "vario125street": "Vario 125 Street",

    # Vario 160
    "vario160": "Vario Evo 160",
    "varioevo160": "Vario Evo 160",
    "vario160cbs": "Vario Evo 160",
    "vario160abs": "Vario Evo 160",

    # Stylo
    "stylo160": "Stylo 160",
    "stylo160abs": "Stylo 160",
    "stylo160cbs": "Stylo 160",

    # PCX
    "pcx": "PCX 160",
    "pcx160": "PCX 160",
    "allnewpcx160": "PCX 160",
    "allnewpcx160cbs": "PCX 160",
    "allnewpcx160abs": "PCX 160",
    "allnewpcx1602025cbstype": "PCX 160",
    "allnewpcx1602025roadsynctype": "PCX 160",
    "pcxhybrid": "PCX 160",
    "pcx150": "PCX 160",
    "allnewpcx150": "PCX 160",

    # ADV
    "adv": "ADV 160",
    "adv160": "ADV 160",
    "adv160abs": "ADV 160",
    "adv160cbs": "ADV 160",
    "adv160roadsync": "ADV 160",

    # Forza
    "forza": "Forza",

    # Verza
    "verza": "CB150 Verza",
    "verza150cw": "CB150 Verza",
    "cb150verza": "CB150 Verza",
    "cb150verzasw": "CB150 Verza",

    # Sonic
    "sonic": "Sonic 150R",
    "sonic150r": "Sonic 150R",

    # CB150R StreetFire
    "streetfire": "CB150R StreetFire",
    "cb150rstreetfire": "CB150R StreetFire",

    # CB150X
    "cb150x": "SB150X",
    "sb150x": "SB150X",

    # CRF150L
    "crf150": "CRF150L",
    "crf150l": "CRF150L",

    # CBR150R
    "cbr150": "CBR150R",
    "cbr150r": "CBR150R",

    # CBR250RR
    "cbr250rr": "CBR250RR",

    # CRF250L
    "crf250": "CRF250L",
    "crf250l": "CRF250L",

    # ST125 Dax
    "st125dax": "ST125 Dax",
    "dax": "ST125 Dax",

    # Monkey
    "monkey": "Monkey",

    # CRF250 Rally
    "crf250rally": "CRF250 Rally",

    # Revo
    "revo": "Revo",
    "revofit": "Revo",
    "revofi": "Revo",
    "revofi sw": "Revo",
    "revox": "Revo",

    # Supra X 125
    "suprax125": "Supra X 125 FI",
    "suprax125fi": "Supra X 125 FI",
    "newsuprax125fi": "Supra X 125 FI",
    "newsuprax125fisw": "Supra X 125 FI",
    "newsuprax125rcw": "Supra X 125 FI",
    "newsuprax125ficw": "Supra X 125 FI",

    # GTR
    "gtr150": "GTR 150",

    # Super Cub
    "supercub": "Super Cub C125",
    "supercubc125": "Super Cub C125",

    # CT125
    "ct125": "CT125",

    # Electric
    "icone": "ICON e:",
    "em1e": "EM1 e:",
    "cuve": "CUV e:",
}

MOTOR_KEYWORD_RULES = [
    # Harus yang lebih spesifik diletakkan lebih dahulu
    ("beatstreet", "Beat Street"),
    ("beat", "Beat"),

    ("vario125street", "Vario 125 Street"),
    ("vario125", "Vario 125"),

    ("vario160", "Vario Evo 160"),
    ("varioevo160", "Vario Evo 160"),

    ("stylo160", "Stylo 160"),
    ("stylo", "Stylo 160"),

    ("scoopy", "Scoopy"),
    ("genio", "Genio"),
    ("forza", "Forza"),

    ("pcx", "PCX 160"),

    ("adv160", "ADV 160"),
    ("adv", "ADV 160"),

    ("cb150verza", "CB150 Verza"),
    ("verza", "CB150 Verza"),

    ("sonic150r", "Sonic 150R"),
    ("sonic", "Sonic 150R"),

    ("cb150rstreetfire", "CB150R StreetFire"),
    ("streetfire", "CB150R StreetFire"),

    ("cb150x", "SB150X"),
    ("sb150x", "SB150X"),

    ("crf150l", "CRF150L"),
    ("crf150", "CRF150L"),

    ("cbr150r", "CBR150R"),
    ("cbr150", "CBR150R"),

    ("cbr250rr", "CBR250RR"),

    # CRF250 Rally harus sebelum CRF250L
    ("crf250rally", "CRF250 Rally"),
    ("crf250l", "CRF250L"),
    ("crf250", "CRF250L"),

    ("st125dax", "ST125 Dax"),
    ("dax", "ST125 Dax"),

    ("monkey", "Monkey"),

    ("revo", "Revo"),

    ("suprax125", "Supra X 125 FI"),

    ("gtr150", "GTR 150"),

    ("supercubc125", "Super Cub C125"),
    ("supercub", "Super Cub C125"),

    ("ct125", "CT125"),

    ("icone", "ICON e:"),
    ("em1e", "EM1 e:"),
    ("cuve", "CUV e:"),
]


def compact_motor_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def canonical_motor(value):
    raw = re.sub(r"\s+", " ", str(value)).strip()
    if not raw or raw.lower() in {"nan", "none", "-"}:
        return None
    key_norm = compact_motor_key(raw)
    if key_norm in MOTOR_ALIAS:
        return MOTOR_ALIAS[key_norm]

    for needle, canonical in MOTOR_KEYWORD_RULES:
        if needle in key_norm:
            return canonical

    return raw


def _find_exact_data_col(df: pd.DataFrame, column_name: str):
    """Cari nama kolom secara exact tanpa tertukar dengan suffix seperti .1."""
    if df is None or not column_name:
        return None
    exact_columns = {
        re.sub(r"\s+", " ", str(column).strip().lower()): column
        for column in df.columns
    }
    normalized_name = re.sub(r"\s+", " ", str(column_name).strip().lower())
    return exact_columns.get(normalized_name)
# ============================================================
# REGION / PROFIL WILAYAH (CLUSTER BPS & KELOMPOK BUDAYA)
# Gaya visual (warna, kartu KPI, chart-card) disamakan dengan
# tema utama dashboard (RED/ORANGE/YELLOW/GREEN/BLUE_OUTLINE).
# ============================================================

RW_CLUSTER_SHEET = "Hasil_Cluster"
RW_CULTURE_SHEET_CANDIDATES = ["Pengelompokkan_budaya", "pengelompokkan_budaya", "pengelompokan_budaya"]
RW_CLUSTER_COLUMN = "Cluster_k3"
RW_CLUSTER_PROFILE_COLUMN = "Profil_k3"
RW_CLUSTER_REGION_COLUMN = "Kabupaten/Kota"

RW_H_CONFIG = {
    "H1": {"sheet": "sales_respondent", "region_column": "City of Dealer", "profile_column": "Profile",
           "metadata_sheet": "profile_metadata_H1", "title": "Sales"},
    "H2": {"sheet": "service_respondent", "region_column": "City of AHASS", "profile_column": "Profile",
           "metadata_sheet": "profile_metadata_H2", "title": "Service"},
    "H3": {"sheet": "parts_respondent", "region_column": "City of Parts Shop", "profile_column": "Profile",
           "metadata_sheet": "profile_metadata_H3", "title": "Spare Part"},
}

RW_PROFILE_ORDER = [1, 2, 3, 4, 5]
# Palet warna Profile 1-5 disamakan persis dengan PROFILE_COLORS (P1..P5)
# yang sudah dipakai pada page H1/H2/H3 agar konsisten satu dashboard.
RW_PROFILE_COLORS = {1: RED, 2: ORANGE, 3: YELLOW, 4: "#9CCC65", 5: GREEN}
RW_CLUSTER_PROFILE_COLORS = {f"Profile {p}": RW_PROFILE_COLORS[p] for p in RW_PROFILE_ORDER}


# Dasar pembentukan profil wilayah mengikuti notebook Clustering_wilayah_BPS:
# K-Means pada 10 variabel yang sudah distandardisasi dengan Z-Score.
RW_CLUSTERING_VARIABLES = [
    ("Kepadatan penduduk", "Jumlah penduduk dibagi luas wilayah."),
    ("Proporsi usia produktif", "Penduduk usia produktif dibanding total penduduk."),
    ("Motor per 1.000 penduduk", "Populasi sepeda motor per 1.000 penduduk."),
    ("Mobil per 1.000 penduduk", "Populasi mobil per 1.000 penduduk."),
    ("PDRB per kapita", "Total PDRB sembilan sektor dibanding jumlah penduduk."),
    ("Proporsi sektor primer", "PDRB pertanian + pertambangan dibanding total PDRB."),
    ("Proporsi sektor sekunder", "PDRB manufaktur + listrik + konstruksi dibanding total PDRB."),
    ("UMK", "Upah Minimum Kabupaten/Kota."),
    ("Persentase penduduk miskin", "Persentase penduduk miskin BPS."),
    ("TPT", "Tingkat Pengangguran Terbuka."),
]

RW_CLUSTER_EXPLANATIONS = {
    "Metropolitan Ekonomi Tinggi": {
        "description": (
            "Wilayah pada cluster ini memiliki karakteristik perkotaan yang kuat, "
            "ditandai dengan kepadatan penduduk, PDRB per kapita, tingkat upah, "
            "serta jumlah kendaraan yang relatif tinggi. Di sisi lain, persentase "
            "penduduk miskinnya relatif lebih rendah dibandingkan wilayah lain."
        ),
        "character": (
            "Kepadatan penduduk tinggi · PDRB per kapita tinggi · "
            "Upah tinggi · Jumlah kendaraan tinggi · Kemiskinan relatif rendah"
        ),
    },

    "Industri Berupah Tinggi": {
        "description": (
            "Wilayah pada cluster ini memiliki aktivitas ekonomi yang banyak didukung "
            "oleh sektor sekunder seperti industri, manufaktur, listrik, dan konstruksi. "
            "Tingkat upahnya relatif tinggi, sedangkan peran sektor primer seperti "
            "pertanian dan pertambangan relatif lebih rendah."
        ),
        "character": (
            "Sektor industri kuat · Upah relatif tinggi · "
            "Sektor primer relatif lebih rendah"
        ),
    },

    "Nonmetropolitan Berbasis Primer": {
        "description": (
            "Wilayah pada cluster ini memiliki karakteristik yang relatif lebih "
            "nonmetropolitan dibandingkan dua cluster lainnya dan kegiatan ekonominya "
            "cenderung lebih bertumpu pada sektor primer."
        ),
        "character": (
            "Karakter nonmetropolitan · Peran sektor primer relatif lebih kuat"
        ),
    },
}

RW_CULTURE_INFO = {
    "arek": {
        "description": "Budaya urban-pesisir, egaliter, dan lugas.",
        "character": "Terbuka, berani, spontan, egaliter, dan guyub.",
    },
    "mataraman": {
        "description": "Dipengaruhi budaya Jawa pedalaman/Mataram.",
        "character": "Halus, santun, menghormati tata krama, dan menjaga harmoni.",
    },
    "pendalungan": {
        "description": "Percampuran budaya Jawa dan Madura.",
        "character": "Adaptif, terbuka, pekerja keras, dan multikultural.",
    },
    "madura": {
        "description": "Budaya Madura dengan bahasa, tradisi, dan ikatan kekerabatan yang kuat.",
        "character": "Tegas, berani, pekerja keras, menjunjung harga diri dan solidaritas.",
    },
    "using": {
        "description": "Budaya asli Banyuwangi dengan bahasa dan kesenian khas.",
        "character": "Memegang tradisi, ekspresif, kuat dalam seni dan identitas lokal.",
    },
    "tengger": {
        "description": "Masyarakat Tengger dengan tradisi dan adat khas pegunungan.",
        "character": "Komunal, menjaga adat, gotong royong, dan kuat pada tradisi.",
    },
    "ntt": {
        "description": "Sangat beragam, termasuk Timor, Flores, Sumba, Rote, Alor, Sabu, dan lainnya.",
        "character": "Komunal, kekeluargaan, kuat pada adat, solidaritas, dan penghormatan terhadap leluhur.",
    },
}


def rw_culture_info(culture_name: str) -> dict:
    key = re.sub(r"[^a-z]", "", str(culture_name or "").lower())
    if "arek" in key:
        return RW_CULTURE_INFO["arek"]
    if "mataram" in key:
        return RW_CULTURE_INFO["mataraman"]
    if "pendalungan" in key or "pendhalungan" in key or "pendaulungan" in key:
        return RW_CULTURE_INFO["pendalungan"]
    if "madura" in key:
        return RW_CULTURE_INFO["madura"]
    if "using" in key or "osing" in key:
        return RW_CULTURE_INFO["using"]
    if "tengger" in key:
        return RW_CULTURE_INFO["tengger"]
    if key == "ntt" or "nusatenggaratimur" in key:
        return RW_CULTURE_INFO["ntt"]
    return {
        "description": "Penjelasan budaya belum tersedia.",
        "character": "Karakter umum belum tersedia.",
    }


# Alias disesuaikan dengan bentuk nama wilayah pada file cluster BPS.
# Tambahkan alias baru di sini apabila nama pada data CSL berbeda.
RW_REGION_ALIASES = {
    "surabaya": "Kota Surabaya",
    "kota surabaya": "Kota Surabaya",
    "kota malang": "Kota Malang",
    "kabupaten malang": "Kabupaten Malang",
    "kab malang": "Kabupaten Malang",
    "blitar": "Kab-Kodya Blitar",
    "kab kodya blitar": "Kab-Kodya Blitar",
    "kab-kodya blitar": "Kab-Kodya Blitar",
    "kabupaten blitar": "Kab-Kodya Blitar",
    "kota blitar": "Kab-Kodya Blitar",
    "kediri": "Kediri",
    "kabupaten kediri": "Kediri",
    "kota kediri": "Kediri",
    "kab kodya kediri": "Kediri",
    "probolinggo": "Probolinggo",
    "kabupaten probolinggo": "Probolinggo",
    "kota probolinggo": "Probolinggo",
    "kab kodya probolinggo": "Probolinggo",
    "mojokerto": "Mojokerto",
    "kabupaten mojokerto": "Mojokerto",
    "kota mojokerto": "Mojokerto",
    "kab kodya mojokerto": "Mojokerto",
    "pasuruan": "Pasuruan",
    "kabupaten pasuruan": "Pasuruan",
    "kota pasuruan": "Pasuruan",
    "kab kodya pasuruan": "Pasuruan",
    "madiun": "Madiun",
    "kabupaten madiun": "Madiun",
    "kota madiun": "Madiun",
    "kab kodya madiun": "Madiun",
    "sidoarjo": "Sidoarjo",
    "kabupaten sidoarjo": "Sidoarjo",
    "pamekasan": "Pamekasan",
    "kabupaten pamekasan": "Pamekasan",
    "trenggalek": "Trenggalek",
    "kabupaten trenggalek": "Trenggalek",
    "nganjuk": "Nganjuk",
    "kabupaten nganjuk": "Nganjuk",
    "lamongan": "Lamongan",
    "kabupaten lamongan": "Lamongan",
    "jember": "Jember",
    "kabupaten jember": "Jember",
    "lumajang": "Lumajang",
    "kabupaten lumajang": "Lumajang",
    "bojonegoro": "Bojonegoro",
    "kabupaten bojonegoro": "Bojonegoro",
    "bangkalan": "Bangkalan",
    "kabupaten bangkalan": "Bangkalan",
    "jombang": "Jombang",
    "kabupaten jombang": "Jombang",
    "banyuwangi": "Banyuwangi",
    "kabupaten banyuwangi": "Banyuwangi",
    "gresik": "Gresik",
    "kabupaten gresik": "Gresik",
    "situbondo": "Situbondo",
    "kabupaten situbondo": "Situbondo",
    "tulungagung": "Tulungagung",
    "kabupaten tulungagung": "Tulungagung",
    "sumenep": "Sumenep",
    "kabupaten sumenep": "Sumenep",
    "magetan": "Magetan",
    "kabupaten magetan": "Magetan",
    "pacitan": "Pacitan",
    "kabupaten pacitan": "Pacitan",
    "ngawi": "Ngawi",
    "kabupaten ngawi": "Ngawi",
    "ponorogo": "Ponorogo",
    "kabupaten ponorogo": "Ponorogo",
    "tuban": "Tuban",
    "kabupaten tuban": "Tuban",
    "bondowoso": "Bondowoso",
    "kabupaten bondowoso": "Bondowoso",
    "sampang": "Sampang",
    "kabupaten sampang": "Sampang",
    "kupang": "Kupang",
    "kabupaten kupang": "Kupang",
    "kota kupang": "Kupang",
}


def rw_normalize_text(value: Any):
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if not text or text in {"nan", "none", "-", ""}:
        return None
    text = re.sub(r"[/_.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def rw_normalize_region(value: Any):
    """Menyamakan nama Kabupaten/Kota CSL dengan nama pada data cluster BPS."""
    text = rw_normalize_text(value)
    if text is None:
        return None
    text = text.replace("kab.", "kabupaten ")
    text = text.replace("kab ", "kabupaten ")
    text = text.replace("kodya", "kota")
    text = re.sub(r"\s+", " ", text).strip()

    if text in RW_REGION_ALIASES:
        return RW_REGION_ALIASES[text]
    without_kab = re.sub(r"^kabupaten\s+", "", text).strip()
    if without_kab in RW_REGION_ALIASES:
        return RW_REGION_ALIASES[without_kab]
    return " ".join(word.capitalize() for word in text.split())


def rw_normalize_profile(value: Any):
    """Mengubah nilai seperti 1, 1.0, 'Profile 1' menjadi integer 1."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, np.integer)):
        p = int(value)
        return p if p in RW_PROFILE_ORDER else None
    if isinstance(value, (float, np.floating)):
        if math.isnan(float(value)):
            return None
        p = int(value)
        return p if p in RW_PROFILE_ORDER else None
    match = re.search(r"([1-5])", str(value))
    if not match:
        return None
    p = int(match.group(1))
    return p if p in RW_PROFILE_ORDER else None


def rw_validate_columns(df: pd.DataFrame, required_columns: list, source_name: str):
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise KeyError(f"Kolom berikut tidak ditemukan pada {source_name}: " + ", ".join(missing))


def rw_load_cluster_data() -> pd.DataFrame:
    cluster_df = try_read_sheet_silent(RW_CLUSTER_SHEET)
    if cluster_df.empty:
        raise KeyError(f"Worksheet '{RW_CLUSTER_SHEET}' tidak ditemukan atau kosong.")

    rw_validate_columns(
        cluster_df,
        [RW_CLUSTER_REGION_COLUMN, RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN],
        f"worksheet {RW_CLUSTER_SHEET}",
    )

    cluster_df = cluster_df[[RW_CLUSTER_REGION_COLUMN, RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN]].copy()
    cluster_df["Region_Key"] = cluster_df[RW_CLUSTER_REGION_COLUMN].apply(rw_normalize_region)
    cluster_df[RW_CLUSTER_COLUMN] = pd.to_numeric(cluster_df[RW_CLUSTER_COLUMN], errors="coerce").astype("Int64")
    cluster_df = (
        cluster_df.dropna(subset=["Region_Key", RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN])
        .drop_duplicates(subset=["Region_Key"], keep="first")
        .reset_index(drop=True)
    )
    return cluster_df


def rw_load_culture_data() -> pd.DataFrame:
    culture_df = pd.DataFrame()
    for sheet_name in RW_CULTURE_SHEET_CANDIDATES:
        culture_df = try_read_sheet_silent(sheet_name)
        if not culture_df.empty:
            break

    if culture_df.empty:
        raise KeyError("Worksheet 'Pengelompokkan_budaya' tidak ditemukan atau kosong.")

    kab_col = find_col(culture_df, ["kabupaten/kota", "kab/kota", "kabupaten", "kota", "wilayah"])
    zona_col = find_col(culture_df, ["budaya_utama", "zona budaya", "budaya", "cluster budaya", "kelompok budaya"])
    cluster_col = find_col(culture_df, ["cluster_budaya", "cluster budaya"])

    if not kab_col or not zona_col:
        raise KeyError("Kolom Kabupaten/Kota atau Budaya_Utama tidak ditemukan pada worksheet budaya.")

    culture_df = culture_df.rename(columns={kab_col: "Kabupaten/Kota_Budaya", zona_col: "Kelompok_Budaya"})
    if cluster_col and cluster_col in culture_df.columns:
        culture_df = culture_df.rename(columns={cluster_col: "Cluster_Budaya"})
    else:
        culture_df["Cluster_Budaya"] = np.nan

    culture_df = culture_df[["Kabupaten/Kota_Budaya", "Kelompok_Budaya", "Cluster_Budaya"]].copy()
    culture_df["Region_Key"] = culture_df["Kabupaten/Kota_Budaya"].apply(rw_normalize_region)
    culture_df["Kelompok_Budaya"] = culture_df["Kelompok_Budaya"].astype(str).str.strip()
    culture_df["Cluster_Budaya"] = pd.to_numeric(culture_df["Cluster_Budaya"], errors="coerce").astype("Int64")
    culture_df = (
        culture_df.dropna(subset=["Region_Key", "Kelompok_Budaya"])
        .drop_duplicates(subset=["Region_Key"], keep="first")
        .reset_index(drop=True)
    )
    return culture_df


def rw_load_profile_metadata(h_code: str) -> pd.DataFrame:
    config = RW_H_CONFIG[h_code]
    metadata_df = try_read_sheet_silent(config["metadata_sheet"])
    if metadata_df.empty:
        raise KeyError(f"Worksheet '{config['metadata_sheet']}' tidak ditemukan atau kosong.")

    profile_col = find_col(metadata_df, ["profile", "profil", "no", "code"])
    name_col = find_col(metadata_df, ["profile name", "nama profil", "nama", "name"])
    if not profile_col or not name_col:
        raise KeyError(f"Kolom Profile / Profile Name tidak ditemukan pada '{config['metadata_sheet']}'.")

    metadata_df = metadata_df.rename(columns={profile_col: "Profile", name_col: "Profile Name"})
    metadata_df["Profile"] = metadata_df["Profile"].apply(rw_normalize_profile)
    metadata_df = metadata_df.dropna(subset=["Profile"]).copy()
    metadata_df["Profile"] = metadata_df["Profile"].astype(int)
    return metadata_df


def rw_load_csl_profile_data(h_code: str):
    config = RW_H_CONFIG[h_code]
    respondent_df = try_read_sheet_silent(config["sheet"])
    if respondent_df.empty:
        raise KeyError(f"Worksheet '{config['sheet']}' tidak ditemukan atau kosong.")

    region_col = find_col(respondent_df, [config["region_column"].lower()]) or (
        config["region_column"] if config["region_column"] in respondent_df.columns else None
    )
    profile_col = find_col(respondent_df, [config["profile_column"].lower()]) or (
        config["profile_column"] if config["profile_column"] in respondent_df.columns else None
    )
    if not region_col or not profile_col:
        raise KeyError(f"Kolom wilayah/profile tidak ditemukan pada '{config['sheet']}'.")

    diagnostic = {
        "total_rows": len(respondent_df),
        "region_non_null": int(respondent_df[region_col].notna().sum()),
        "profile_non_null": int(respondent_df[profile_col].notna().sum()),
    }

    result = respondent_df.copy()
    result["Region_Key"] = result[region_col].apply(rw_normalize_region)
    result["Profile_Clean"] = result[profile_col].apply(rw_normalize_profile)
    result = result[["Region_Key", "Profile_Clean"]].dropna(subset=["Region_Key", "Profile_Clean"]).copy()
    result["Profile_Clean"] = result["Profile_Clean"].astype(int)

    diagnostic["valid_rows"] = len(result)
    diagnostic["valid_regions"] = int(result["Region_Key"].nunique())
    return result, diagnostic


def rw_calculate_region_profile_distribution(respondent_df, metadata_df, cluster_df, minimum_respondents):
    merged_respondents = respondent_df.merge(cluster_df, on="Region_Key", how="left", validate="many_to_one")
    valid_cluster_respondents = merged_respondents.dropna(subset=[RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN]).copy()

    counts = (
        valid_cluster_respondents.groupby(
            ["Region_Key", RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN, "Profile_Clean"], observed=True
        ).size().rename("Jumlah").reset_index()
    )

    if counts.empty:
        return pd.DataFrame(), merged_respondents

    pivot_count = counts.pivot_table(
        index=["Region_Key", RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN],
        columns="Profile_Clean", values="Jumlah", aggfunc="sum", fill_value=0,
    ).reset_index()

    for profile in RW_PROFILE_ORDER:
        if profile not in pivot_count.columns:
            pivot_count[profile] = 0

    profile_count_columns = []
    for profile in RW_PROFILE_ORDER:
        new_column = f"Jumlah_Profile_{profile}"
        pivot_count[new_column] = pivot_count[profile].astype(int)
        profile_count_columns.append(new_column)

    pivot_count["Jumlah_Responden"] = pivot_count[profile_count_columns].sum(axis=1)

    for profile in RW_PROFILE_ORDER:
        pivot_count[f"Persen_Profile_{profile}"] = np.where(
            pivot_count["Jumlah_Responden"] > 0,
            pivot_count[f"Jumlah_Profile_{profile}"] / pivot_count["Jumlah_Responden"] * 100,
            np.nan,
        )

    percent_columns = [f"Persen_Profile_{profile}" for profile in RW_PROFILE_ORDER]
    percent_matrix = pivot_count[percent_columns].to_numpy(dtype=float)
    sorted_indices = np.argsort(-percent_matrix, axis=1)

    pivot_count["Profile_Dominan"] = sorted_indices[:, 0] + 1
    pivot_count["Profile_Kedua"] = sorted_indices[:, 1] + 1
    pivot_count["Persen_Dominan"] = np.take_along_axis(percent_matrix, sorted_indices[:, [0]], axis=1).ravel()
    pivot_count["Persen_Kedua"] = np.take_along_axis(percent_matrix, sorted_indices[:, [1]], axis=1).ravel()
    pivot_count["Margin_Dominasi"] = pivot_count["Persen_Dominan"] - pivot_count["Persen_Kedua"]

    pivot_count["Status_Sampel"] = np.where(
        pivot_count["Jumlah_Responden"] >= minimum_respondents, "Memadai", "Di Bawah Minimum"
    )

    profile_name_map = metadata_df.set_index("Profile")["Profile Name"].to_dict()
    pivot_count["Nama_Profile_Dominan"] = pivot_count["Profile_Dominan"].map(profile_name_map)
    pivot_count["Nama_Profile_Kedua"] = pivot_count["Profile_Kedua"].map(profile_name_map)

    region_display_map = cluster_df.set_index("Region_Key")[RW_CLUSTER_REGION_COLUMN].to_dict()
    pivot_count["Kabupaten/Kota"] = pivot_count["Region_Key"].map(region_display_map)

    ordered_columns = [
        "Kabupaten/Kota", "Region_Key", RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN,
        "Jumlah_Responden", *profile_count_columns, *percent_columns,
        "Profile_Dominan", "Nama_Profile_Dominan", "Persen_Dominan",
        "Profile_Kedua", "Nama_Profile_Kedua", "Persen_Kedua",
        "Margin_Dominasi", "Status_Sampel",
    ]

    region_summary = pivot_count[ordered_columns].sort_values([RW_CLUSTER_COLUMN, "Kabupaten/Kota"]).reset_index(drop=True)
    return region_summary, merged_respondents


def rw_jensen_shannon_similarity(first_distribution, second_distribution):
    first = np.asarray(first_distribution, dtype=float)
    second = np.asarray(second_distribution, dtype=float)
    if first.sum() <= 0 or second.sum() <= 0:
        return np.nan
    first = first / first.sum()
    second = second / second.sum()
    midpoint = 0.5 * (first + second)

    def kl_divergence(distribution, reference):
        mask = distribution > 0
        return float(np.sum(distribution[mask] * np.log2(distribution[mask] / reference[mask])))

    js_divergence = 0.5 * kl_divergence(first, midpoint) + 0.5 * kl_divergence(second, midpoint)
    js_distance = math.sqrt(max(js_divergence, 0.0))
    return float(1.0 - js_distance)


def rw_classify_similarity(value):
    if value is None or pd.isna(value):
        return "Belum Dapat Dinilai"
    if value >= 0.85:
        return "Sangat Mirip"
    if value >= 0.70:
        return "Cukup Mirip"
    return "Beragam"


def rw_calculate_cluster_similarity(region_summary, minimum_respondents):
    if region_summary.empty:
        return pd.DataFrame()

    eligible = region_summary[region_summary["Jumlah_Responden"] >= minimum_respondents].copy()
    percent_columns = [f"Persen_Profile_{p}" for p in RW_PROFILE_ORDER]
    results = []

    for (cluster_number, cluster_name), group in eligible.groupby(
        [RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN], observed=True
    ):
        group = group.copy()
        region_count = len(group)
        dominant_counts = group["Profile_Dominan"].value_counts()

        if dominant_counts.empty:
            majority_profile, majority_regions, consistency = np.nan, 0, np.nan
        else:
            majority_profile = int(dominant_counts.index[0])
            majority_regions = int(dominant_counts.iloc[0])
            consistency = majority_regions / region_count * 100

        distribution_matrix = group[percent_columns].to_numpy(dtype=float) / 100
        pairwise_similarities = []
        for i in range(region_count):
            for j in range(i + 1, region_count):
                sim = rw_jensen_shannon_similarity(distribution_matrix[i], distribution_matrix[j])
                if not pd.isna(sim):
                    pairwise_similarities.append(sim)

        average_similarity = float(np.mean(pairwise_similarities)) if pairwise_similarities else np.nan

        results.append({
            "Cluster": int(cluster_number),
            "Profil_Wilayah": cluster_name,
            "Jumlah_Wilayah_Valid": region_count,
            "Profile_Mayoritas": majority_profile,
            "Jumlah_Wilayah_Sesuai": majority_regions,
            "Konsistensi_Profile_Dominan": consistency,
            "Kemiripan_Distribusi": average_similarity,
            "Kategori_Kemiripan": rw_classify_similarity(average_similarity),
        })

    return pd.DataFrame(results).sort_values("Cluster").reset_index(drop=True)


def rw_calculate_culture_similarity(region_summary, minimum_respondents):
    if region_summary.empty:
        return pd.DataFrame()

    eligible = region_summary[region_summary["Jumlah_Responden"] >= minimum_respondents].copy()
    percent_columns = [f"Persen_Profile_{p}" for p in RW_PROFILE_ORDER]
    results = []

    for culture, group in eligible.groupby("Kelompok_Budaya", observed=True):
        group = group.copy()
        region_count = len(group)
        dominant_counts = group["Profile_Dominan"].value_counts()

        if dominant_counts.empty:
            majority_profile, majority_regions, consistency = np.nan, 0, np.nan
        else:
            majority_profile = int(dominant_counts.index[0])
            majority_regions = int(dominant_counts.iloc[0])
            consistency = majority_regions / region_count * 100

        distribution_matrix = group[percent_columns].to_numpy(dtype=float) / 100
        pairwise_similarities = []
        for i in range(region_count):
            for j in range(i + 1, region_count):
                sim = rw_jensen_shannon_similarity(distribution_matrix[i], distribution_matrix[j])
                if not pd.isna(sim):
                    pairwise_similarities.append(sim)

        average_similarity = float(np.mean(pairwise_similarities)) if pairwise_similarities else np.nan

        results.append({
            "Kelompok_Budaya": culture,
            "Jumlah_Wilayah_Valid": region_count,
            "Profile_Mayoritas": majority_profile,
            "Jumlah_Wilayah_Sesuai": majority_regions,
            "Konsistensi_Profile_Dominan": consistency,
            "Kemiripan_Distribusi": average_similarity,
            "Kategori_Kemiripan": rw_classify_similarity(average_similarity),
        })

    return pd.DataFrame(results).sort_values("Kelompok_Budaya").reset_index(drop=True)
