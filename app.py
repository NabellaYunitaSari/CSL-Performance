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
# CSS
# ============================================================

def inject_css():
    st.markdown(
        """
        <style>
        .st-key-csl_performance_section {
            border: 2px solid #E53935 !important;
            border-radius: 12px !important;
            padding: 18px 18px 22px 18px !important;
            margin-bottom: 24px !important;
        }
        .main { background-color: #FFFFFF; }
        .section-box {
            border-radius: 10px;
            padding: 16px 18px 22px 18px;
            margin-bottom: 22px;
        }
        .section-red { border: 2px solid %s; }
        .section-orange { border: 2px solid %s; }
        .section-blue { border: 2px solid %s; }
        .section-title {
            display: flex; align-items: center; gap: 8px;
            font-size: 20px; font-weight: 700; margin-bottom: 10px;
        }
        div[class*="st-key-"][class*="_csl_performance_section"] {
            border: 2px solid #E53935 !important;
            border-radius: 12px !important;
            padding: 18px 18px 22px 18px !important;
            margin-bottom: 24px !important;
            background: #FFFFFF !important;
        }
        div[class*="st-key-"][class*="_matrix_section"] {
            border: 2px solid #FB8C00 !important;
            border-radius: 12px !important;
            padding: 18px 18px 22px 18px !important;
            margin-bottom: 24px !important;
            background: #FFFFFF !important;
        }
        div[class*="st-key-"][class*="_profile_customer_section"] {
            border: 2px solid #1E88E5 !important;
            border-radius: 12px !important;
            padding: 18px 18px 22px 18px !important;
            margin-bottom: 24px !important;
            background: #FFFFFF !important;
        }

        div[class*="st-key-"][class*="_motor_container"] {
            max-height: 280px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
        }

        div[class*="st-key-"][class*="_prof_card_"] {
            position: relative !important;
            background: #FFFFFF !important;
            border: 1px solid #D0D0D0 !important;
            border-radius: 8px !important;
            height: 64px !important;
            min-height: 64px !important;
            max-height: 64px !important;
            padding: 0 !important;
            margin-bottom: 6px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
            transition: all 0.2s ease !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        div[class*="st-key-"][class*="_prof_card_"] .element-container,
        div[class*="st-key-"][class*="_prof_card_"] div[data-testid="stMarkdownContainer"],
        div[class*="st-key-"][class*="_prof_card_"] div[data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
            padding: 0 !important;
        }

        div[class*="st-key-"][class*="_prof_card_"]:hover {
            border-color: #1E88E5 !important;
            background: #F4F8FB !important;
        }

        div[class*="st-key-"][class*="_active"] {
            background: #E3F2FD !important;
            border: 2px solid #1E88E5 !important;
            box-shadow: 0 2px 6px rgba(30,136,229,0.18) !important;
        }

        .profile-card-inner {
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            gap: 5px !important;
            width: 100%% !important;
            height: 100%% !important;
            min-height: 62px !important;
            padding: 8px 12px 8px 12px !important;
            box-sizing: border-box !important;
        }

        .profile-card-header {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            width: 100%% !important;
            font-size: 12.5px !important;
            line-height: 1.2 !important;
        }

        .profile-card-title {
            font-weight: 600 !important;
            color: #212121 !important;
            line-height: 1.2 !important;
        }

        div[class*="st-key-"][class*="_active"] .profile-card-title {
            color: #1565C0 !important;
            font-weight: 700 !important;
        }

        .profile-card-pct {
            font-weight: 700 !important;
            color: #212121 !important;
            margin-left: 8px !important;
            white-space: nowrap !important;
            line-height: 1.2 !important;
        }

        div[class*="st-key-"][class*="_active"] .profile-card-pct {
            color: #1565C0 !important;
        }

        /* Profil 0%% tetap terlihat sebagai informasi, tetapi bukan kontrol. */
        div[class*="st-key-"][class*="_prof_card_"][class*="_disabled"] {
            background: #F7F7F7 !important;
            border-color: #E2E2E2 !important;
            box-shadow: none !important;
            cursor: default !important;
        }
        div[class*="st-key-"][class*="_prof_card_"][class*="_disabled"]:hover {
            background: #F7F7F7 !important;
            border-color: #E2E2E2 !important;
        }
        div[class*="st-key-"][class*="_prof_card_"][class*="_disabled"] .profile-card-inner {
            opacity: 0.55 !important;
        }
        div[class*="st-key-"][class*="_prof_card_"][class*="_disabled"] button {
            cursor: default !important;
        }

        .profile-bar-bg {
            background: #E0E0E0 !important;
            border-radius: 6px !important;
            height: 6px !important;
            width: 100%% !important;
            overflow: hidden !important;
            margin: 0 !important;
            box-sizing: border-box !important;
        }

        .profile-bar-fill {
            border-radius: 6px;
            height: 100%%;
        }

        .insight-box {
            background: linear-gradient(135deg, #FFFFFF 0%%, #F4F8FB 100%%);
            border: 1px solid #BBDEFB !important;
            border-left: 5px solid #1E88E5 !important;
            border-radius: 12px !important;
            padding: 16px 18px 18px 18px !important;
            margin-bottom: 14px !important;
            box-shadow: 0 2px 8px rgba(30,136,229,0.06) !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 10px !important;
            height: auto !important;
            min-height: 100%% !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        .insight-box-header {
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            color: #0D47A1 !important;
            padding-bottom: 8px !important;
            border-bottom: 1px dashed #BBDEFB !important;
        }

        .insight-box-body {
            font-size: 13.5px !important;
            color: #37474F !important;
            line-height: 1.6 !important;
            font-weight: 400 !important;
        }

        .reco-box {
            background: linear-gradient(135deg, #FFFFFF 0%%, #F1F8E9 100%%);
            border: 1px solid #C8E6C9 !important;
            border-left: 5px solid #2E7D32 !important;
            border-radius: 12px !important;
            padding: 16px 18px 18px 18px !important;
            margin-bottom: 14px !important;
            box-shadow: 0 2px 8px rgba(46,125,50,0.06) !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 10px !important;
            height: auto !important;
            min-height: 100%% !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        .reco-box-header {
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            color: #1B5E20 !important;
            padding-bottom: 8px !important;
            border-bottom: 1px dashed #C8E6C9 !important;
        }

        .reco-box-body {
            font-size: 13.5px !important;
            color: #2E3B2C !important;
            line-height: 1.6 !important;
            font-weight: 400 !important;
        }

        .ses-legend-box {
            background: #F8F9FA !important;
            border: 1px solid #E0E0E0 !important;
            border-radius: 8px !important;
            padding: 10px 12px !important;
            margin-top: 10px !important;
        }

        .ses-legend-title {
            font-size: 11.5px !important;
            font-weight: 700 !important;
            color: #37474F !important;
            margin-bottom: 8px !important;
        }

        .ses-badge-grid {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 6px !important;
        }

        .ses-badge {
            background: #FFFFFF !important;
            border: 1px solid #D0D0D0 !important;
            border-radius: 6px !important;
            padding: 4px 9px !important;
            font-size: 11px !important;
            color: #37474F !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
            font-weight: 500 !important;
        }

        div[class*="st-key-"][class*="_btn_select_"] {
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100%% !important;
            height: 100%% !important;
            margin: 0 !important;
            padding: 0 !important;
            z-index: 10 !important;
        }

        div[class*="st-key-"][class*="_btn_select_"] button {
            width: 100%% !important;
            height: 100%% !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            cursor: pointer !important;
            color: transparent !important;
            font-size: 0px !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        div[class*="st-key-"][class*="_btn_select_"] button:hover {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        .custom-section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
        }

        .custom-section-badge {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: #E53935;
            color: white;
            border-radius: 7px;
            font-size: 14px;
            font-weight: 700;
        }

        .custom-section-text {
            font-size: 21px;
            font-weight: 700;
            color: #303440;
        }
        .section-badge {
            display:inline-flex; align-items:center; justify-content:center;
            width:24px; height:24px; border-radius:6px; color:white;
            font-size:14px; font-weight:700;
        }
        .badge-red { background-color: %s; }
        .badge-orange { background-color: %s; }
        .badge-blue { background-color: %s; }
        .kpi-card {
            background: #FFFFFF; border: 1px solid #D0D0D0; border-radius: 12px;
            padding: 14px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            text-align:center;
        }
        .kpi-label { font-size: 13px; color:#555555; font-weight:600; }
        .kpi-value { font-size: 30px; font-weight:800; color:#212121; margin: 4px 0 2px 0; }
        .kpi-sub { font-size: 13px; font-weight:600; }
        .chart-card {
            background:#FFFFFF; border:1px solid #D0D0D0; border-radius:10px;
            padding:10px 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border: 1px solid #D0D0D0 !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
        }
        .chart-title { font-weight:700; font-size:15px; margin-bottom:2px; }
        .chart-subtitle { font-size:12px; color:#888888; margin-bottom:6px; }
        .profile-item {
            border-radius:8px; padding:8px 10px; margin-bottom:8px; cursor:pointer;
            border:1px solid #EEEEEE;
        }
        .profile-item-active { border:1px solid #212121; background:#F5F5F5; }
        .profile-bar-bg { background:#EEEEEE; border-radius:6px; height:8px; width:100%%; }
        .profile-bar-fill { border-radius:6px; height:8px; }

        /* ============ REGION / PROFIL WILAYAH DETAIL BOX ============ */
        .region-detail-box {
            background: #FAFBFC !important;
            border: 1px solid #E7E9EC !important;
            border-left: 4px solid %s !important;
            border-radius: 8px !important;
            padding: 10px 14px !important;
            margin-bottom: 10px !important;
        }
        .region-detail-box.culture { border-left-color: %s !important; }
        .region-detail-title {
            font-weight: 700; font-size: 0.92rem; color: #262626; margin-bottom: 3px;
        }
        .region-detail-count {
            font-weight: 500; color: #666666; font-size: 0.82rem;
        }
        .region-detail-body {
            font-size: 0.85rem; color: #37474F; line-height: 1.5;
        }
        </style>
        """ % (RED_OUTLINE, ORANGE_OUTLINE, BLUE_OUTLINE, RED_OUTLINE, ORANGE_OUTLINE, BLUE_OUTLINE,
               BLUE_OUTLINE, ORANGE_OUTLINE),
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        :root {--csl-red:#E60012;--csl-red-dark:#C8102E;--csl-orange:#FF6B00;--csl-blue:#1665D8;--csl-text:#262626;--csl-muted:#666;--csl-border:#E7E9EC;--csl-shadow:0 1px 2px rgba(20,20,20,.04),0 2px 8px rgba(20,20,20,.05);}
        html,body,[class*="css"]{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;}
        .stApp{background:linear-gradient(180deg,#FF6B00 0%,#FF8A33 420px,#FFF7F2 100%);background-attachment:fixed;color:var(--csl-text);}
        [data-testid="stAppViewContainer"]>.main .block-container{max-width:1600px;padding:.25rem 1.25rem 3rem;}
        [data-testid="stHeader"]{background:transparent;height:0;}
        [data-testid="stToolbar"]{top:.2rem;}
        #MainMenu,footer{visibility:hidden;}
        .csl-header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 20px;margin-bottom:14px;border-radius:10px;background:linear-gradient(120deg,#C8102E 0%,#E60012 45%,#FF6B00 100%);box-shadow:0 4px 16px rgba(200,16,46,.28);color:#fff;}
        .csl-brand{display:flex;align-items:center;justify-content:flex-start;height:40px;gap:12px;}
        .csl-logo{width:40px;height:40px;border-radius:10px;background:#fff;color:#C8102E;display:flex;align-items:center;justify-content:center;font-size:15px;line-height:1;font-weight:800;box-sizing:border-box;}
        .csl-brand h1{display:flex;align-items:center;height:40px;font-size:18px;line-height:1;margin:0;padding:0;color:#fff;font-weight:800;letter-spacing:.2px;white-space:nowrap;}
        .csl-brand p{font-size:12px;margin:2px 0 0;color:rgba(255,255,255,.86);font-weight:500}.csl-header-note{font-size:11.5px;color:rgba(255,255,255,.86);text-align:right;}
        /* Header fungsional: brand, waktu update, refresh, dan reset. */
        div[class*="st-key-top_header"]{margin:0 0 10px!important;padding:14px 20px!important;border:0!important;border-radius:10px!important;background:linear-gradient(110deg,#C8102E 0%,#E60012 43%,#FF6B00 100%)!important;box-shadow:0 4px 16px rgba(200,16,46,.28)!important;color:#fff!important;}
        div[class*="st-key-top_header"]>div[data-testid="stVerticalBlockBorderWrapper"]{background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none!important;}
        div[class*="st-key-top_header"] div[data-testid="stHorizontalBlock"]{align-items:center!important;gap:10px!important;}
        div[class*="st-key-top_header"] .element-container{margin:0!important;display:flex!important;align-items:center!important;}
        div[class*="st-key-top_header"] div[data-testid="stMarkdownContainer"]{width:100%!important;margin:0!important;padding:0!important;display:flex!important;align-items:center!important;}
        div[class*="st-key-top_header"] div[data-testid="stMarkdownContainer"] p{margin:0!important;padding:0!important;}
        .csl-header-brand{display:flex;align-items:center;justify-content:flex-start;gap:12px;height:44px;margin:0;padding:0;}.csl-header-brand .csl-logo{flex:0 0 40px;}
        .csl-update-time{font-size:11px;line-height:1.25;text-align:right;color:rgba(255,255,255,.92);white-space:nowrap;}.csl-update-time b{color:#fff;font-size:11.5px;}
        div[class*="st-key-header_refresh"] button,div[class*="st-key-header_reset"] button{min-height:34px!important;height:34px!important;width:100%!important;padding:0 14px!important;color:#fff!important;background:rgba(255,255,255,.10)!important;border:1px solid rgba(255,255,255,.72)!important;border-radius:9px!important;font-size:12px!important;font-weight:700!important;white-space:nowrap!important;box-shadow:none!important;}
        div[class*="st-key-header_refresh"] button:hover,div[class*="st-key-header_reset"] button:hover{color:#C8102E!important;background:#fff!important;border-color:#fff!important;}
        /* =========================================================
        NAVIGASI PAGE H1, H2, H3
        ========================================================= */

        /* Kotak putih pembungkus seluruh tombol page */
        div[data-testid="stTabs"] > div:first-child {
            display: inline-flex !important;
            width: auto !important;
            max-width: fit-content !important;
            align-items: center !important;
            gap: 6px !important;

            background-color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.95) !important;
            border-radius: 14px !important;

            padding: 6px !important;
            margin-bottom: 14px !important;

            box-shadow:
                0 4px 12px rgba(38, 38, 38, 0.12),
                0 1px 3px rgba(38, 38, 38, 0.08) !important;

            overflow: hidden !important;
        }

        /* Mengatur tab list di dalam kotak */
        div[data-testid="stTabs"] div[role="tablist"] {
            display: flex !important;
            width: auto !important;
            gap: 6px !important;

            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        /* Tombol H1, H2, H3 */
        div[data-testid="stTabs"] button[role="tab"] {
            height: 38px !important;
            min-height: 38px !important;

            padding: 0 17px !important;
            margin: 0 !important;

            background: transparent !important;
            border: none !important;
            border-radius: 9px !important;

            color: #5F6368 !important;
            font-size: 12px !important;
            font-weight: 700 !important;

            transition:
                background-color 0.2s ease,
                color 0.2s ease,
                box-shadow 0.2s ease !important;
        }

        /* Tulisan di dalam tombol */
        div[data-testid="stTabs"] button[role="tab"] p {
            color: inherit !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            margin: 0 !important;
        }

        /* Page yang sedang aktif */
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: linear-gradient(
                135deg,
                #E60012 0%,
                #FF6B00 100%
            ) !important;

            color: #FFFFFF !important;
            border-radius: 9px !important;

            box-shadow: 0 3px 8px rgba(230, 0, 18, 0.22) !important;
        }

        /* Warna tulisan page aktif */
        div[data-testid="stTabs"]
        button[role="tab"][aria-selected="true"] p {
            color: #FFFFFF !important;
        }

        /* Efek hover untuk page yang tidak aktif */
        div[data-testid="stTabs"]
        button[role="tab"][aria-selected="false"]:hover {
            background-color: #FFF1F1 !important;
            color: #C8102E !important;
        }

        /* Hilangkan garis bawah bawaan Streamlit */
        div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
        div[data-testid="stTabs"] div[data-baseweb="tab-border"] {
            display: none !important;
        }

        /* Pemilih page yang stabil: container putih melengkung */
        div[class*="st-key-page_selector_card"] {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin: 0 0 12px 0 !important;
            box-shadow: none !important;
            overflow: visible !important;
        }
        div[class*="st-key-page_selector_card"]
        > div[data-testid="stVerticalBlockBorderWrapper"] {
            width: auto !important;
            background: transparent !important;
            border: 0 !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            padding: 0 !important;
        }
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] {
            width: 100% !important;
            background: transparent !important;
        }
        div[class*="st-key-page_selector_card"] div[role="radiogroup"]{display:flex!important;gap:7px!important;flex-wrap:wrap!important;}
        /* =========================================================
           TOMBOL NAVIGASI PAGE
           Semua tombol tetap putih. Page aktif ditandai outline merah tua.
           Selector anak (*) diperlukan agar warna bawaan Streamlit tidak
           menimpa background dan warna tulisan yang sudah ditentukan.
        ========================================================= */
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button {
            min-height: 40px !important;
            height: 40px !important;
            padding: 0 21px !important;
            box-sizing: border-box !important;
            background-color: #FFFFFF !important;
            background-image: none !important;
            border: 1px solid #E2E2E2 !important;
            border-radius: 9px !important;
            color: #4F4F4F !important;
            font-size: 12.5px !important;
            font-weight: 700 !important;
            opacity: 1 !important;
            box-shadow: 0 2px 5px rgba(38,38,38,.10) !important;
            transition: border-color .18s ease, color .18s ease,
                        box-shadow .18s ease, transform .18s ease !important;
        }

        /* Paksa seluruh lapisan di dalam tombol tetap transparan. */
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button > div,
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button > span {
            background: transparent !important;
            background-color: transparent !important;
        }

        /* PAGE AKTIF: putih solid, outline merah tebal, tulisan merah tua. */
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            background: #FFFFFF !important;
            background-color: #FFFFFF !important;
            background-image: none !important;
            color: #B80F20 !important;
            border: 3px solid #C8102E !important;
            font-weight: 850 !important;
            opacity: 1 !important;
            box-shadow:
                0 4px 11px rgba(112,0,12,.27),
                inset 0 0 0 1px rgba(200,16,46,.08) !important;
            transform: translateY(-1px) !important;
        }

        /* Warna tulisan di semua versi struktur HTML Streamlit. */
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] p,
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] span,
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] div {
            color: #B80F20 !important;
            font-weight: 850 !important;
            opacity: 1 !important;
        }

        /* PAGE TIDAK AKTIF. */
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="false"] {
            background: #FFFFFF !important;
            background-color: #FFFFFF !important;
            background-image: none !important;
            color: #4F4F4F !important;
            border: 1px solid #E2E2E2 !important;
            opacity: 1 !important;
        }
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="false"] p,
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="false"] span,
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="false"] div {
            color: #4F4F4F !important;
            opacity: 1 !important;
        }

        /* Hover page yang tidak aktif. */
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="false"]:hover {
            background: #FFF7F7 !important;
            background-color: #FFF7F7 !important;
            color: #C8102E !important;
            border-color: #E60012 !important;
            box-shadow: 0 3px 8px rgba(200,16,46,.16) !important;
        }
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button[aria-pressed="false"]:hover * {
            color: #C8102E !important;
        }

        /* Fokus keyboard tetap jelas dan rapi. */
        div[class*="st-key-page_selector_card"]
        div[data-testid="stSegmentedControl"] button:focus-visible {
            outline: 3px solid rgba(255,255,255,.95) !important;
            outline-offset: 2px !important;
        }

        /* Kompatibilitas struktur SegmentedControl Streamlit/BaseWeb terbaru.
           Tombol aktif selalu putih; pembeda hanya outline dan teks merah. */
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] label,
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button {
            background:#FFFFFF!important;
            background-color:#FFFFFF!important;
            background-image:none!important;
            border:1px solid #E2E2E2!important;
            color:#4F4F4F!important;
        }
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] label:has(input:checked),
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[aria-checked="true"],
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[aria-selected="true"],
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[aria-pressed="true"],
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[data-active="true"],
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[data-selected="true"] {
            background:#FFFFFF!important;
            background-color:#FFFFFF!important;
            background-image:none!important;
            border:2px solid #E60012!important;
            color:#E60012!important;
            box-shadow:0 2px 7px rgba(230,0,18,.16)!important;
        }
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] label:has(input:checked) *,
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[aria-checked="true"] *,
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[aria-selected="true"] *,
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[aria-pressed="true"] *,
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[data-active="true"] *,
        div[class*="st-key-page_selector_card"] div[role="radiogroup"] button[data-selected="true"] * {
            background:transparent!important;
            background-color:transparent!important;
            background-image:none!important;
            color:#E60012!important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]{background:#fff!important;border:1px solid var(--csl-border)!important;border-radius:10px!important;box-shadow:var(--csl-shadow)!important;}
        div[class*="st-key-"][class*="_csl_performance_section"],div[class*="st-key-"][class*="_matrix_section"],div[class*="st-key-"][class*="_profile_customer_section"]{background:rgba(255,255,255,.98)!important;border:1px solid var(--csl-border)!important;border-radius:10px!important;box-shadow:var(--csl-shadow)!important;padding:16px!important;margin:0 0 18px!important;}
        .custom-section-title{gap:10px;margin-bottom:12px}.custom-section-badge{width:auto;min-width:72px;height:24px;padding:0 10px;border-radius:5px!important;background:#E60012!important;font-size:10.5px;font-weight:800;letter-spacing:.6px}.custom-section-text{font-size:15px;color:#262626;font-weight:800;letter-spacing:.1px}
        div[class*="_matrix_section"] .custom-section-badge{background:#FF6B00!important}div[class*="_profile_customer_section"] .custom-section-badge{background:#1665D8!important}
        .kpi-card{min-height:132px;text-align:left;background:#fff;border:1px solid var(--csl-border);border-radius:10px;padding:16px;box-shadow:var(--csl-shadow);position:relative;overflow:hidden}.kpi-card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#E60012}.kpi-label{font-size:11px;color:#666;font-weight:700;text-transform:uppercase;letter-spacing:.3px}.kpi-value{font-size:34px;color:#262626;font-weight:800;line-height:1.1;margin:8px 0 4px}.kpi-sub{display:inline-block;font-size:10.5px;font-weight:800;background:#F0F1F3;padding:3px 9px;border-radius:20px}
        .chart-title{font-size:12px;font-weight:800;color:#666;letter-spacing:.3px;text-transform:uppercase;margin-bottom:4px}.chart-subtitle{font-size:11.5px;color:#666;margin-bottom:8px}.stSelectbox label,.stMultiSelect label{font-size:10px!important;font-weight:700!important;color:#666!important;text-transform:uppercase;letter-spacing:.4px}div[data-baseweb="select"]>div{border-color:var(--csl-border);border-radius:7px;background:#fff}.stButton>button{border-radius:8px;border:1px solid var(--csl-border);font-size:12.5px;font-weight:700}
        div[class*="st-key-"][class*="_prof_card_"]{border:1px solid var(--csl-border)!important;border-radius:8px!important;box-shadow:none!important}div[class*="st-key-"][class*="_prof_card_"]:hover{border-color:#E60012!important;background:#FFF6F6!important}div[class*="st-key-"][class*="_active"]{background:#FFF1F1!important;border:1.5px solid #E60012!important;box-shadow:none!important}div[class*="st-key-"][class*="_active"] .profile-card-title,div[class*="st-key-"][class*="_active"] .profile-card-pct{color:#C8102E!important}
        div[class*="st-key-"][class*="_prof_card_"][class*="_disabled"],div[class*="st-key-"][class*="_prof_card_"][class*="_disabled"]:hover{background:#F7F7F7!important;border-color:#E2E2E2!important;box-shadow:none!important}div[class*="st-key-"][class*="_prof_card_"][class*="_disabled"] .profile-card-inner{opacity:.55!important}
        .insight-box{background:#FFF6F6!important;border:1px solid #FFDADA!important;border-left:4px solid #E60012!important;border-radius:8px!important;box-shadow:none!important}.insight-box-header{color:#C8102E!important;border-bottom-color:#FFDADA!important}.reco-box{background:#FFF8E8!important;border:1px solid #FCE7B8!important;border-left:4px solid #FF6B00!important;border-radius:8px!important;box-shadow:none!important}.reco-box-header{color:#B45300!important;border-bottom-color:#FCE7B8!important}
        /* Tinggi seluruh outline demographic chart disamakan */
        div[class*="st-key-"][class*="_demographic_chart_card"] {
            height: 390px !important;
            min-height: 390px !important;
            max-height: 390px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            display: flex !important;
            flex-direction: column !important;
        }

        /* Pastikan wrapper border Streamlit benar-benar mengikuti tinggi card. */
        div[class*="st-key-"][class*="_demographic_chart_card"]
        > div[data-testid="stVerticalBlockBorderWrapper"] {
            height: 100% !important;
            min-height: 100% !important;
            max-height: 100% !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
        }

        div[class*="st-key-"][class*="_demographic_chart_card"]
        > div[data-testid="stVerticalBlockBorderWrapper"]
        > div[data-testid="stVerticalBlock"] {
            height: 100% !important;
            min-height: 0 !important;
            overflow: hidden !important;
        }

        /* Hilangkan margin yang dapat menambah tinggi kartu */
        div[class*="st-key-"][class*="_demographic_chart_card"]
        div[data-testid="stMarkdownContainer"] p {
            margin-bottom: 0 !important;
        }

        /* Area khusus chart */
        div[class*="st-key-"][class*="_chart_viewport"] {
            height: 330px !important;
            min-height: 330px !important;
            max-height: 330px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scrollbar-gutter: stable;
        }

        /* Scrollbar chart */
        div[class*="st-key-"][class*="_chart_viewport"]::-webkit-scrollbar {
            width: 6px;
        }

        div[class*="st-key-"][class*="_chart_viewport"]::-webkit-scrollbar-thumb {
            background: #D8DBDF;
            border-radius: 20px;
        }

        div[class*="st-key-"][class*="_chart_viewport"]::-webkit-scrollbar-track {
            background: transparent;
        }

        /* Gauge NPS sejajar dengan kartu tipe pembayaran pada baris yang sama. */
        div[class*="st-key-"][class*="_nps_chart_card"] {
            height: 390px !important;
            min-height: 390px !important;
            max-height: 390px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
        }
        div[class*="st-key-"][class*="_nps_chart_card"]
        > div[data-testid="stVerticalBlockBorderWrapper"] {
            height: 100% !important;
            min-height: 100% !important;
            max-height: 100% !important;
            box-sizing: border-box !important;
        }
        div[class*="st-key-"][class*="_heatmap_scroll"]{max-height:520px;overflow-y:auto;overflow-x:hidden}div[class*="st-key-"][class*="_scroll_chart_card"]::-webkit-scrollbar,div[class*="st-key-"][class*="_heatmap_scroll"]::-webkit-scrollbar{width:7px;height:7px}div[class*="st-key-"][class*="_scroll_chart_card"]::-webkit-scrollbar-thumb,div[class*="st-key-"][class*="_heatmap_scroll"]::-webkit-scrollbar-thumb{background:#D8DBDF;border-radius:20px}

        /* SES dan Retention memakai tinggi outline yang sama. */
        div[class*="st-key-"][class*="_fixed_chart_card"] {
            height: 190px !important;
            min-height: 190px !important;
            max-height: 190px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
        }
        div[class*="st-key-"][class*="_fixed_chart_card"]
        > div[data-testid="stVerticalBlockBorderWrapper"] {
            height: 100% !important;
            min-height: 100% !important;
            max-height: 100% !important;
            box-sizing: border-box !important;
        }
        @media(max-width:700px){.csl-header-note{display:none}.csl-brand h1{font-size:15px}.custom-section-text{font-size:13px}[data-testid="stAppViewContainer"]>.main .block-container{padding:.2rem .65rem 2rem;}div[class*="st-key-top_header"]{padding:12px!important;}.csl-update-time{text-align:left;}div[class*="st-key-page_selector_card"] div[data-testid="stSegmentedControl"] button{padding:0 12px!important;}}
        /* Menyamakan tinggi kotak Heatmap, Daftar Profil, dan Penjelasan Profil */
        div[class*="st-key-"][class*="_profile_equal_height"] {
            height: 520px !important;
            min-height: 520px !important;
            max-height: 520px !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        /* Scroll hanya berada pada konten heatmap bagian dalam. Pembungkus
           kartu luar tidak lagi membuat scrollbar kedua. */
        div[class*="st-key-"][class*="_profile_heatmap_column"] {
            overflow-y: hidden !important;
            overflow-x: hidden !important;
        }

        /* Geser keterangan pembaruan sedikit mendekati tombol Refresh Data. */
        .csl-update-time {
            position: relative;
            left: 8px;
        }

        /* Daftar profil dapat di-scroll jika profilnya terlalu panjang */
        div[class*="st-key-"][class*="_profile_list_column"] {
            overflow-y: auto !important;
            overflow-x: hidden !important;
        }

        /* Penjelasan profil dapat di-scroll jika narasinya terlalu panjang */
        div[class*="st-key-"][class*="_profile_explanation_column"] {
            overflow-y: auto !important;
            overflow-x: hidden !important;
        }

        /* Scrollbar dibuat tipis */
        div[class*="st-key-"][class*="_profile_equal_height"]::-webkit-scrollbar {
            width: 6px;
        }

        div[class*="st-key-"][class*="_profile_equal_height"]::-webkit-scrollbar-thumb {
            background: #D8DBDF;
            border-radius: 20px;
        }

        div[class*="st-key-"][class*="_profile_equal_height"]::-webkit-scrollbar-track {
            background: transparent;
        }

        /* NTT click overlay: invisible Streamlit button above the visual inset */
        div[class*="st-key-"][class*="_map_interaction_wrapper"] {
            position: relative !important;
            overflow: visible !important;
        }
        div[class*="st-key-"][class*="_ntt_overlay_click"] {
            position: absolute !important;
            right: 14px !important;
            bottom: 18px !important;
            width: 29% !important;
            min-width: 255px !important;
            max-width: 330px !important;
            height: 198px !important;
            margin: 0 !important;
            padding: 0 !important;
            z-index: 2147483647 !important;
            pointer-events: auto !important;
        }
        div[class*="st-key-"][class*="_ntt_overlay_click"] .element-container,
        div[class*="st-key-"][class*="_ntt_overlay_click"] div[data-testid="stButton"] {
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[class*="st-key-"][class*="_ntt_overlay_click"] button {
            width: 100% !important;
            height: 100% !important;
            min-height: 198px !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            box-shadow: none !important;
            background: transparent !important;
            color: transparent !important;
            font-size: 0 !important;
            opacity: 0 !important;
            cursor: pointer !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_start(title, color):
    cls = {"red": "section-red", "orange": "section-orange", "blue": "section-blue"}[color]
    badge_cls = {"red": "badge-red", "orange": "badge-orange", "blue": "badge-blue"}[color]
    number = {"red": "1", "orange": "2", "blue": "3"}[color]
    st.markdown(
        f'<div class="section-box {cls}">'
        f'<div class="section-title"><span class="section-badge {badge_cls}">{number}</span>{title}</div>',
        unsafe_allow_html=True,
    )


def section_end():
    st.markdown("</div>", unsafe_allow_html=True)


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


def render_filters(df: pd.DataFrame, cols: dict, dealer_label: str, key_prefix: str):
    filters = {}
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

    year_col = cols.get("year")
    sem_col = cols.get("semester")
    md_col = cols.get("main_dealer")
    layer_col = cols.get("layer")
    kar_col = cols.get("karesidenan")
    kab_col = cols.get("kab_kota")
    dealer_col = cols.get("dealer_code")

    with c1:
        years = _options(df, year_col)
        sel_year = st.selectbox("Tahun", ["Semua"] + years, key=f"{key_prefix}_year")
    with c2:
        sems = ["Semester 1", "Semester 2"]
        sem_key = f"{key_prefix}_sem"
        if st.session_state.get(sem_key) not in sems:
            st.session_state[sem_key] = sems[0]
        sel_sem = st.selectbox("Periode", sems, key=sem_key)

    df_scope = df.copy()
    if sel_year != "Semua" and year_col:
        df_scope = df_scope[df_scope[year_col].astype(str) == str(sel_year)]
    if sem_col:
        target_sem = 1 if "1" in sel_sem else 2
        df_scope = df_scope[df_scope[sem_col].apply(_parse_semester) == target_sem]

    with c3:
        mds = _options(df_scope, md_col)
        mds = [value for value in mds if value.strip().lower() != "semua"]
        md_key = f"{key_prefix}_md"
        md_options = ["Semua"] + mds
        if st.session_state.get(md_key) not in md_options:
            st.session_state[md_key] = "Semua"
        sel_md = st.selectbox("Main Dealer", md_options, key=md_key)
    # "Semua" tidak menyaring kolom Main Dealer sehingga M2Z dan M3Z tergabung.
    if sel_md != "Semua" and md_col:
        df_scope = df_scope[df_scope[md_col].astype(str) == sel_md]

    with c4:
        layers = _options(df_scope, layer_col)
        sel_layer = st.selectbox("Layer", ["Semua"] + layers, key=f"{key_prefix}_layer")
    if sel_layer != "Semua" and layer_col:
        df_scope = df_scope[df_scope[layer_col].astype(str) == sel_layer]

    with c5:
        kars = _options(df_scope, kar_col)
        sel_kar = st.selectbox("Karesidenan", ["Semua"] + kars, key=f"{key_prefix}_kar")
    if sel_kar != "Semua" and kar_col:
        df_scope = df_scope[df_scope[kar_col].astype(str) == sel_kar]

    with c6:
        kabs = sorted({
            _dashboard_region_name(value)
            for value in df_scope[kab_col].dropna().tolist()
            if _dashboard_region_name(value)
        }) if kab_col and kab_col in df_scope.columns else []
        kab_key = f"{key_prefix}_kab"
        if st.session_state.get(kab_key) not in (["Semua"] + kabs):
            st.session_state[kab_key] = "Semua"
        sel_kab = st.selectbox("Kab / Kota", ["Semua"] + kabs, key=kab_key)
    if sel_kab != "Semua" and kab_col:
        df_scope = df_scope[df_scope[kab_col].apply(_dashboard_region_name) == sel_kab]

    with c7:
        deals = _options(df_scope, dealer_col)
        sel_dealer = st.selectbox(dealer_label, ["Semua"] + deals, key=f"{key_prefix}_dealer")

    filters = {
        "year": None if sel_year == "Semua" else sel_year,
        "semester": 1 if "1" in sel_sem else 2,
        "main_dealer": sel_md,
        "layer": None if sel_layer == "Semua" else sel_layer,
        "karesidenan": None if sel_kar == "Semua" else sel_kar,
        "kab_kota": None if sel_kab == "Semua" else sel_kab,
        "dealer": None if sel_dealer == "Semua" else sel_dealer,
    }
    return filters


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
# MAP (PETA ZONA BUDAYA)
# ============================================================
def create_map_legacy(df: pd.DataFrame, cols: dict, indicator_cols: list, key: str):

    # ========================================================
    # 1. LOAD SHAPEFILE
    # ========================================================
    gdf_raw = load_shapefile()

    if gdf_raw is None or gdf_raw.empty:
        st.warning("Shapefile kabupaten/kota tidak ditemukan.")
        return

    kab_shape_col = _find_shp_col(
        gdf_raw,
        SHP_KAB_CANDIDATES
    )

    prov_shape_col = _find_shp_col(
        gdf_raw,
        SHP_PROV_CANDIDATES
    )

    if not kab_shape_col or not prov_shape_col:
        st.warning(
            "Kolom kabupaten/kota atau provinsi pada shapefile tidak ditemukan."
        )
        return

    gdf_target = gdf_raw.copy()

    # ========================================================
    # 2. PASTIKAN CRS WGS84
    # ========================================================
    try:
        if gdf_target.crs is None:
            gdf_target = gdf_target.set_crs(epsg=4326)

        elif gdf_target.crs.to_epsg() != 4326:
            gdf_target = gdf_target.to_crs(epsg=4326)

    except Exception:
        pass

    # ========================================================
    # 3. HANYA JAWA TIMUR + NTT
    #
    # Wilayah lain TIDAK masuk overlay.
    # Sumatera, Kalimantan, Bali dll hanya muncul sebagai
    # background basemap Leaflet.
    # ========================================================
    prov_norm = (
        gdf_target[prov_shape_col]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    gdf_target = gdf_target[
        prov_norm.str.contains(
            r"jawa timur|nusa tenggara timur|\bntt\b",
            regex=True,
            na=False
        )
    ].copy()

    if gdf_target.empty:
        st.warning("Wilayah Jawa Timur dan NTT tidak ditemukan.")
        return

    # ========================================================
    # 4. IDENTIFIKASI JATIM DAN NTT
    # ========================================================
    gdf_target["__prov_norm"] = (
        gdf_target[prov_shape_col]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    is_ntt = gdf_target["__prov_norm"].str.contains(
        r"nusa tenggara timur|\bntt\b",
        regex=True,
        na=False
    )

    # ========================================================
    # 5. NAMA WILAYAH
    # ========================================================
    gdf_target["__temp_kab"] = (
        gdf_target[kab_shape_col]
        .astype(str)
        .str.strip()
    )

    # Kota Batu digabung dengan Kabupaten Malang
    is_batu = (
        (~is_ntt)
        &
        gdf_target["__temp_kab"]
        .str.lower()
        .str.contains("batu", na=False)
    )

    gdf_target.loc[
        is_batu,
        "__temp_kab"
    ] = "Kabupaten Malang"

    # Seluruh NTT menjadi satu polygon
    gdf_target.loc[
        is_ntt,
        "__temp_kab"
    ] = "Nusa Tenggara Timur"

    # ========================================================
    # 6. DISSOLVE
    # ========================================================
    try:
        gdf_target = (
            gdf_target
            .dissolve(
                by="__temp_kab",
                as_index=False
            )
        )

        kab_shape_col = "__temp_kab"

    except Exception as e:
        st.warning(f"Gagal memproses geometri peta: {e}")
        return

    # ========================================================
    # 7. SHEET PENGELOMPOKKAN BUDAYA
    # ========================================================
    budaya_df = try_read_sheet(
        "pengelompokkan_budaya"
    )

    if budaya_df.empty:
        budaya_df = try_read_sheet(
            "pengelompokan_budaya"
        )

    if budaya_df.empty:
        st.warning(
            "Worksheet pengelompokkan_budaya tidak ditemukan."
        )
        return

    kab_budaya_col = find_col(
        budaya_df,
        [
            "kabupaten/kota",
            "kab/kota",
            "kabupaten",
            "kota",
            "wilayah",
        ]
    )

    zona_col = find_col(
        budaya_df,
        [
            "budaya_utama",
            "zona budaya",
            "budaya",
            "cluster budaya",
            "cluster_budaya",
            "kelompok budaya",
        ]
    )

    prof_col = find_col(
        budaya_df,
        [
            "profile dominan",
            "dominan profile",
            "profil dominan",
            "dominant profile",
            "profile",
            "profil",
        ]
    )

    if not kab_budaya_col or not zona_col:
        st.warning(
            "Kolom Kabupaten/Kota atau Zona Budaya tidak ditemukan."
        )
        return

    # ========================================================
    # 8. MAPPING BUDAYA
    # ========================================================
    budaya_clean = (
        budaya_df
        .drop_duplicates(
            subset=[kab_budaya_col]
        )
        .copy()
    )

    exact_zona = {}
    exact_profile = {}

    stripped_zona = {}
    stripped_profile = {}

    for _, row in budaya_clean.iterrows():

        nama = str(
            row[kab_budaya_col]
        ).strip()

        zona = (
            str(row[zona_col]).strip()
            if pd.notna(row[zona_col])
            else "Tidak Ada Data"
        )

        profile = (
            str(row[prof_col]).strip()
            if prof_col
            and pd.notna(row[prof_col])
            else "-"
        )

        nama_lower = nama.lower()

        exact_zona[nama_lower] = zona
        exact_profile[nama_lower] = profile

        nama_exact = _normalize_exact_location(
            nama
        )

        if nama_exact:
            exact_zona[nama_exact] = zona
            exact_profile[nama_exact] = profile

        nama_strip = _normalize_location_name(
            nama
        )

        if nama_strip:
            stripped_zona[nama_strip] = zona
            stripped_profile[nama_strip] = profile

    # NTT
    exact_zona["nusa tenggara timur"] = "NTT"
    exact_profile["nusa tenggara timur"] = "-"

    def get_budaya_info(nama_wilayah):

        nama = str(
            nama_wilayah
        ).strip()

        nama_lower = nama.lower()

        if nama_lower in exact_zona:
            return (
                exact_zona[nama_lower],
                exact_profile[nama_lower]
            )

        nama_exact = _normalize_exact_location(
            nama
        )

        if nama_exact in exact_zona:
            return (
                exact_zona[nama_exact],
                exact_profile[nama_exact]
            )

        nama_strip = _normalize_location_name(
            nama
        )

        if nama_strip in stripped_zona:
            return (
                stripped_zona[nama_strip],
                stripped_profile[nama_strip]
            )

        return "Tidak Ada Data", "-"

    result = (
        gdf_target[kab_shape_col]
        .apply(get_budaya_info)
    )

    gdf_target["Zona_Budaya"] = [
        x[0] for x in result
    ]

    gdf_target["Dominan_Profile"] = [
        x[1] for x in result
    ]

    gdf_target["Kabupaten_Kota"] = (
        gdf_target[kab_shape_col]
        .astype(str)
    )

    # ========================================================
    # 9. BUANG NO DATA
    #
    # Jadi tidak ada polygon abu-abu "Tidak Ada Data".
    # ========================================================
    gdf_target = gdf_target[
        gdf_target["Zona_Budaya"]
        != "Tidak Ada Data"
    ].copy()

    if gdf_target.empty:
        st.warning(
            "Tidak ada data budaya untuk Jawa Timur dan NTT."
        )
        return

    # ========================================================
    # 10. SIMPLIFY GEOMETRY
    #
    # Supaya Leaflet ringan.
    # ========================================================
    try:
        gdf_target["geometry"] = (
            gdf_target.geometry
            .simplify(
                tolerance=0.005,
                preserve_topology=True
            )
        )

    except Exception:
        pass

    # ========================================================
    # 11. WARNA
    # ========================================================
    CULTURE_COLORS = {
        "Arek": "#365EAE",
        "Madura": "#E65F61",
        "Mataraman": "#F2AD42",
        "Tengger": "#8665B5",
        "Pendaalungan": "#42AF9F",
        "Pendalungan": "#42AF9F",
        "Using": "#63AD48",
        "Osing": "#63AD48",
        "NTT": "#9A8376",
    }

    def zone_color(zone):

        z = str(zone).strip()
        low = z.lower()

        if z in CULTURE_COLORS:
            return CULTURE_COLORS[z]

        if "arek" in low:
            return CULTURE_COLORS["Arek"]

        if "madura" in low:
            return CULTURE_COLORS["Madura"]

        if "mataram" in low:
            return CULTURE_COLORS["Mataraman"]

        if "tengger" in low:
            return CULTURE_COLORS["Tengger"]

        if (
            "pendhalungan" in low
            or "pendalungan" in low
        ):
            return CULTURE_COLORS[
                "Pendaalungan"
            ]

        if (
            "using" in low
            or "osing" in low
        ):
            return CULTURE_COLORS["Using"]

        if (
            "ntt" in low
            or "nusa tenggara timur" in low
        ):
            return CULTURE_COLORS["NTT"]

        return "#90A4AE"

    # ========================================================
    # 12. LEAFLET MAP
    # ========================================================
    m = folium.Map(
        location=[-8.1, 116.0],
        zoom_start=6,
        tiles=None,
        zoom_control=True,
        prefer_canvas=True,
        control_scale=False,
    )

    # ========================================================
    # 13. CLEAN BASEMAP TANPA LABEL
    #
    # Penting:
    # memakai "light_nolabels", sehingga nama Sumatera,
    # Kalimantan, Bali, dll tidak muncul.
    # ========================================================
    folium.TileLayer(
        tiles=(
            "https://{s}.basemaps.cartocdn.com/"
            "light_nolabels/{z}/{x}/{y}{r}.png"
        ),
        attr=(
            '&copy; OpenStreetMap contributors '
            '&copy; CARTO'
        ),
        name="CARTO Light",
        control=False,
    ).add_to(m)

    # ========================================================
    # 14. POLYGON
    # ========================================================
    for _, row in gdf_target.iterrows():

        kabupaten = str(
            row["Kabupaten_Kota"]
        )

        zona = str(
            row["Zona_Budaya"]
        )

        profile = str(
            row["Dominan_Profile"]
        )

        warna = zone_color(
            zona
        )

        feature = {
            "type": "Feature",
            "properties": {
                "Kabupaten_Kota": kabupaten,
                "Zona_Budaya": zona,
                "Dominan_Profile": profile,
            },
            "geometry": row.geometry.__geo_interface__,
        }

        folium.GeoJson(
            feature,

            style_function=lambda feature, warna=warna: {
                "fillColor": warna,
                "color": "#FFFFFF",
                "weight": 1.5,
                "fillOpacity": 0.90,
            },

            highlight_function=lambda feature, warna=warna: {
                "fillColor": warna,
                "color": "#FFFFFF",
                "weight": 3,
                "fillOpacity": 1,
            },

            tooltip=folium.GeoJsonTooltip(
                fields=[
                    "Kabupaten_Kota",
                    "Zona_Budaya",
                    "Dominan_Profile",
                ],

                aliases=[
                    "Kabupaten/Kota:",
                    "Zona Budaya:",
                    "Dominan Profile:",
                ],

                sticky=True,

                style="""
                    background-color: white;
                    border: none;
                    border-radius: 8px;
                    box-shadow: 0px 3px 12px rgba(0,0,0,.18);
                    color: #334155;
                    font-family: Arial;
                    font-size: 13px;
                    padding: 8px 10px;
                    text-align: left;
                """
            )

        ).add_to(m)

    # ========================================================
    # 15. LABEL
    #
    # Karena overlay hanya Jawa Timur + NTT,
    # hanya wilayah tersebut yang diberi nama.
    # ========================================================
    for _, row in gdf_target.iterrows():

        nama = str(
            row["Kabupaten_Kota"]
        )

        if nama.lower() == "nusa tenggara timur":
            label = "Kupang"

        else:
            label = (
                nama
                .replace("Kabupaten ", "")
                .replace("Kota ", "")
                .replace("Kab. ", "")
                .strip()
            )

        try:
            titik = (
                row.geometry
                .representative_point()
            )

        except Exception:
            continue

        folium.Marker(
            location=[
                titik.y,
                titik.x
            ],

            icon=folium.DivIcon(
                icon_size=(100, 18),
                icon_anchor=(50, 9),

                html=f"""
                <div style="
                    width:100px;
                    text-align:center;
                    font-family:Arial, sans-serif;
                    font-size:11px;
                    font-weight:500;
                    color:#184C7A;
                    white-space:nowrap;
                    pointer-events:none;
                    text-shadow:
                        -1px -1px 0 rgba(255,255,255,.85),
                         1px -1px 0 rgba(255,255,255,.85),
                        -1px  1px 0 rgba(255,255,255,.85),
                         1px  1px 0 rgba(255,255,255,.85);
                ">
                    {label}
                </div>
                """
            )
        ).add_to(m)

    # ========================================================
    # 16. LEGENDA
    # ========================================================
    zones = (
        gdf_target["Zona_Budaya"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    legend_order = [
        "Arek",
        "Madura",
        "Mataraman",
        "Tengger",
        "Pendalungan",
        "Pendalungan",
        "Using",
        "Osing",
        "NTT",
    ]

    legend_items = []
    already_added = set()

    for desired in legend_order:

        match = None

        for actual in zones:

            if actual.lower() == desired.lower():
                match = actual
                break

        if match is None:
            continue

        normalized = (
            match.lower()
            .replace(
                "pendalungan",
                "pendhalungan"
            )
            .replace(
                "osing",
                "using"
            )
        )

        if normalized in already_added:
            continue

        already_added.add(
            normalized
        )

        if normalized == "pendhalungan":
            display = "Pendhalungan"

        elif normalized == "using":
            display = "Using"

        else:
            display = match

        legend_items.append(
            f"""
            <div style="
                display:flex;
                align-items:center;
                gap:5px;
                white-space:nowrap;
            ">
                <span style="
                    width:12px;
                    height:12px;
                    background:{zone_color(match)};
                    border-radius:2px;
                    display:inline-block;
                "></span>

                <span>{display}</span>
            </div>
            """
        )

    legend_html = """
    {% macro html(this, kwargs) %}

    <div style="
        position: fixed;
        bottom: 16px;
        left: 60px;
        z-index: 9999;

        background: rgba(255,255,255,.96);

        border: 1px solid #D9DEE5;
        border-radius: 8px;

        box-shadow:
            0 2px 8px rgba(0,0,0,.12);

        padding: 10px 14px;

        font-family: Arial, sans-serif;
        font-size: 13px;

        display:flex;
        align-items:center;
        gap:12px;
    ">

        <div style="
            font-weight:700;
            color:#475569;
            white-space:nowrap;
        ">
            Budaya Utama
        </div>

        """ + "".join(legend_items) + """

    </div>

    {% endmacro %}
    """

    legend = MacroElement()
    legend._template = Template(
        legend_html
    )

    m.get_root().add_child(
        legend
    )

    # ========================================================
    # 17. FIT BOUNDS
    #
    # Sedikit padding supaya Jawa Timur dan NTT tidak terlalu
    # mepet sisi kiri/kanan.
    # ========================================================
    try:

        minx, miny, maxx, maxy = (
            gdf_target.total_bounds
        )

        m.fit_bounds(
            [
                [
                    miny - 0.3,
                    minx - 0.5
                ],
                [
                    maxy + 0.3,
                    maxx + 0.5
                ],
            ]
        )

    except Exception:
        pass

    # ========================================================
    # 18. TAMPILKAN
    # ========================================================
    st_folium(
        m,
        height=560,
        use_container_width=True,
        key=key,
        returned_objects=[],
    )


# ============================================================
# MAP SATISFACTION: JAWA TIMUR + INSET NTT
# ============================================================
@st.cache_data(show_spinner=False)
def _load_h123_by_location():
    """Hitung %CSL H123 per wilayah sekali dan gunakan kembali saat rerun."""
    result = {}
    unit_sources = [
        ("sales", "sales_respondent", ["Indicator_metadata_H1", "Indikator_metadata_H1"]),
        ("service", "service_respondent", ["Indicator_metadata_H2", "Indikator_metadata_H2"]),
        ("parts", "parts_respondent", ["Indicator_metadata_H3", "Indikator_metadata_H3"]),
    ]
    for source_unit, source_sheet, metadata_sheets in unit_sources:
        source_df = try_read_sheet(source_sheet)
        if source_df.empty:
            continue
        source_cols = detect_columns(source_df, source_unit)
        source_location = source_cols.get("kab_kota")
        if not source_location or source_location not in source_df.columns:
            continue
        source_meta = pd.DataFrame()
        for metadata_sheet in metadata_sheets:
            source_meta = try_read_sheet(metadata_sheet)
            if not source_meta.empty:
                break
        source_indicators = indicator_columns(
            source_df, source_meta, unit_key=source_unit
        )
        source_region_data = source_df.dropna(subset=[source_location]).copy()
        source_region_data["__map_region"] = source_region_data[source_location].apply(
            _dashboard_region_name
        )
        for location, location_group in source_region_data.groupby("__map_region"):
            location_sat = calculate_satisfaction(location_group, source_indicators)
            if location_sat is not None:
                result.setdefault(location, []).append(float(location_sat))
    return result


def create_map(df: pd.DataFrame, cols: dict, indicator_cols: list, key: str):
    """Peta utama Jawa Timur dengan inset NTT dan warna berbasis satisfaction."""
    gdf_raw = load_shapefile()
    if gdf_raw is None or gdf_raw.empty:
        st.warning("Shapefile kabupaten/kota tidak ditemukan.")
        return

    kab_shape_col = _find_shp_col(gdf_raw, SHP_KAB_CANDIDATES)
    prov_shape_col = _find_shp_col(gdf_raw, SHP_PROV_CANDIDATES)
    location_col = cols.get("kab_kota") if cols else None
    profile_col = cols.get("profile") if cols else None

    if not kab_shape_col or not prov_shape_col:
        st.warning("Kolom kabupaten/kota atau provinsi pada shapefile tidak ditemukan.")
        return
    if not location_col or location_col not in df.columns:
        st.warning("Kolom kabupaten/kota pada data responden tidak ditemukan.")
        return

    gdf = gdf_raw.copy()
    try:
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
    except Exception:
        pass

    gdf["__prov"] = gdf[prov_shape_col].astype(str).str.strip().str.lower()
    gdf = gdf[gdf["__prov"].str.contains(r"jawa timur|nusa tenggara timur|\bntt\b", regex=True, na=False)].copy()
    if gdf.empty:
        st.warning("Wilayah Jawa Timur dan NTT tidak ditemukan pada shapefile.")
        return

    is_ntt = gdf["__prov"].str.contains(r"nusa tenggara timur|\bntt\b", regex=True, na=False)
    # Nama geometri disamakan dengan nama pada data dan pilihan filter.
    gdf["Kabupaten_Kota"] = gdf[kab_shape_col].apply(_dashboard_region_name)
    gdf.loc[is_ntt, "Kabupaten_Kota"] = "NTT"

    try:
        gdf = gdf.dissolve(by="Kabupaten_Kota", as_index=False)
        gdf["geometry"] = gdf.geometry.simplify(tolerance=0.005, preserve_topology=True)
    except Exception as exc:
        st.warning(f"Gagal memproses geometri peta: {exc}")
        return

    unit_from_key = str(key).split("_")[0].strip().lower()
    h_label = {"sales": "H1", "service": "H2", "parts": "H3"}.get(unit_from_key, "")

    # Hitung satisfaction dan profil dominan langsung dari scope hasil filter.
    region_data = df.dropna(subset=[location_col]).copy()
    region_data["__map_region"] = region_data[location_col].apply(_dashboard_region_name)
    region_stats = {}
    for location, group in region_data.groupby("__map_region"):
        sat = calculate_satisfaction(group, indicator_cols)
        if sat is None:
            continue

        dominant_profile = "-"
        if profile_col and profile_col in group.columns:
            profile_values = group[profile_col].dropna().astype(str).str.strip()
            if not profile_values.empty:
                dominant_profile = profile_values.value_counts().index[0]

        region_stats[location] = {
            "satisfaction": float(sat),
            "profile": dominant_profile,
        }

    def lookup_stats(name):
        return region_stats.get(
            _dashboard_region_name(name),
            {"satisfaction": None, "profile": "-"},
        )

    info_rows = gdf["Kabupaten_Kota"].apply(lookup_stats)
    gdf["Satisfaction"] = [x["satisfaction"] for x in info_rows]
    gdf["Dominan_Profile"] = [x["profile"] for x in info_rows]

    # %CSL H123 = rata-rata satisfaction H1, H2, dan H3 per wilayah.
    # Sheet dibaca melalui cache sehingga tidak mengulang unduhan setiap rerun.
    h123_by_location = _load_h123_by_location()

    def lookup_h123(name):
        loc_key = _dashboard_region_name(name)
        values = h123_by_location.get(loc_key, [])
        return float(np.mean(values)) if values else None

    gdf["CSL_H123"] = gdf["Kabupaten_Kota"].apply(lookup_h123)

    available = pd.to_numeric(gdf["Satisfaction"], errors="coerce").dropna()
    if available.empty:
        st.info("Nilai satisfaction per wilayah belum tersedia untuk filter yang dipilih.")
        return

    scale_min = float(available.min())
    scale_max = float(available.max())
    if math.isclose(scale_min, scale_max):
        scale_min = max(0.0, scale_min - 1.0)
        scale_max = min(100.0, scale_max + 1.0)

    def satisfaction_color(value):
        if value is None or pd.isna(value):
            return "#D9DEE5"
        ratio = max(0.0, min(1.0, (float(value) - scale_min) / (scale_max - scale_min)))
        stops = [(230, 0, 18), (255, 176, 0), (53, 168, 83)]
        if ratio <= 0.5:
            local, start, end = ratio * 2, stops[0], stops[1]
        else:
            local, start, end = (ratio - 0.5) * 2, stops[1], stops[2]
        rgb = tuple(round(start[i] + (end[i] - start[i]) * local) for i in range(3))
        return "#{:02X}{:02X}{:02X}".format(*rgb)

    gdf_jatim = gdf[gdf["__prov"].astype(str).str.contains("jawa timur", na=False)].copy()
    gdf_ntt = gdf[gdf["Kabupaten_Kota"] == "NTT"].copy()
    if gdf_jatim.empty:
        st.warning("Geometri Jawa Timur tidak tersedia.")
        return

    main_map = folium.Map(
        location=[-7.62, 112.45],
        zoom_start=8,
        min_zoom=6,
        max_zoom=12,
        tiles=None,
        zoom_control=True,
        prefer_canvas=True,
        control_scale=False,
    )
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="&copy; OpenStreetMap contributors",
        control=False,
    ).add_to(main_map)

    # Basemap dibuat abu-abu dan lebih lembut agar wilayah di luar
    # area dashboard tidak terlalu mencolok. Polygon satisfaction
    # Jawa Timur/NTT tetap mempertahankan warna aslinya.
    gray_basemap_css = """
    <style>
        .leaflet-tile-pane {
            filter: grayscale(100%) brightness(1.08) contrast(0.82);
            opacity: 0.62;
        }
    </style>
    """
    main_map.get_root().html.add_child(
        folium.Element(gray_basemap_css)
    )

    def add_polygons(target_map, frame, show_labels=True):
        for _, row in frame.iterrows():
            sat = row["Satisfaction"]
            sat_text = f"{float(sat):.1f}%" if sat is not None and not pd.isna(sat) else "Tidak ada data"
            csl_h123 = row.get("CSL_H123")
            csl_h123_text = f"{float(csl_h123):.1f}%" if csl_h123 is not None and not pd.isna(csl_h123) else "Tidak ada data"
            color = satisfaction_color(sat)
            feature = {
                "type": "Feature",
                "properties": {
                    "Kabupaten_Kota": str(row["Kabupaten_Kota"]),
                    "Filter_Region": _dashboard_region_name(row["Kabupaten_Kota"]),
                    "Satisfaction_Page": sat_text,
                    "CSL_H123": csl_h123_text,
                    "Dominan_Profile": str(row.get("Dominan_Profile", "-") or "-"),
                },
                "geometry": row.geometry.__geo_interface__,
            }
            folium.GeoJson(
                feature,
                style_function=lambda _, c=color: {"fillColor": c, "color": "#FFFFFF", "weight": 1.5, "fillOpacity": 0.92},
                highlight_function=lambda _, c=color: {"fillColor": c, "color": "#262626", "weight": 2.5, "fillOpacity": 1},
                tooltip=folium.GeoJsonTooltip(
                    fields=["Kabupaten_Kota", "Satisfaction_Page", "CSL_H123", "Dominan_Profile"],
                    aliases=["Kabupaten/Kota:", f"Satisfaction {h_label}:", "%CSL H123:", "Profile Dominan:"],
                    sticky=True,
                    style="background:#fff;border:0;border-radius:8px;box-shadow:0 3px 12px rgba(0,0,0,.18);color:#262626;font-family:Arial;font-size:13px;padding:8px 10px;text-align:left;",
                ),
            ).add_to(target_map)

            if show_labels:
                try:
                    point = row.geometry.representative_point()
                    label = str(row["Kabupaten_Kota"]).replace("Kabupaten ", "").replace("Kota ", "").replace("Kab. ", "")
                    folium.Marker(
                        [point.y, point.x],
                        icon=folium.DivIcon(
                            icon_size=(100, 18), icon_anchor=(50, 9),
                            html=f'<div style="width:100px;text-align:center;font:500 11px Arial;color:#184C7A;white-space:nowrap;pointer-events:none;text-shadow:-1px -1px #fff,1px -1px #fff,-1px 1px #fff,1px 1px #fff">{label}</div>',
                        ),
                    ).add_to(target_map)
                except Exception:
                    pass

    add_polygons(main_map, gdf_jatim, show_labels=True)
    # Tampilan awal H1, H2, dan H3 selalu fokus ke Provinsi Jawa Timur.
    # NTT tidak dimasukkan ke bounds karena ditampilkan melalui inset terpisah.
    JATIM_BOUNDS = [
        [-8.95, 110.75],  # Batas barat daya
        [-6.70, 114.65],  # Batas timur laut
    ]

    main_map.fit_bounds(
        JATIM_BOUNDS,
        padding_top_left=[15, 15],
        # Sisakan ruang kanan untuk inset NTT agar tidak menutupi wilayah
        # Jember dan Banyuwangi pada tampilan awal.
        padding_bottom_right=[320, 15],
        max_zoom=8,
    )

    # Inset NTT adalah Marker Folium asli yang diposisikan tetap di kanan bawah.
    # Karena marker itu sendiri yang diklik, tidak diperlukan JavaScript perantara.
    if not gdf_ntt.empty:
        ntt_row = gdf_ntt.iloc[0]
        ntt_color = satisfaction_color(ntt_row["Satisfaction"])
        ntt_sat = ntt_row["Satisfaction"]
        ntt_sat_text = (
            f"{float(ntt_sat):.1f}%"
            if ntt_sat is not None and not pd.isna(ntt_sat)
            else "Tidak ada data"
        )
        ntt_h123 = ntt_row.get("CSL_H123")
        ntt_h123_text = (
            f"{float(ntt_h123):.1f}%"
            if ntt_h123 is not None and not pd.isna(ntt_h123)
            else "Tidak ada data"
        )

        geom = gdf_ntt.geometry.unary_union
        minx_n, miny_n, maxx_n, maxy_n = geom.bounds
        svg_w, svg_h, svg_pad = 330.0, 175.0, 10.0
        span_x = max(maxx_n - minx_n, 1e-9)
        span_y = max(maxy_n - miny_n, 1e-9)
        svg_scale = min(
            (svg_w - 2 * svg_pad) / span_x,
            (svg_h - 2 * svg_pad) / span_y,
        )
        x_offset = (svg_w - span_x * svg_scale) / 2
        y_offset = (svg_h - span_y * svg_scale) / 2

        def polygon_svg_path(poly):
            rings = [poly.exterior] + list(poly.interiors)
            commands = []
            for ring in rings:
                coords = list(ring.coords)
                if not coords:
                    continue
                points = [
                    (
                        x_offset + (x - minx_n) * svg_scale,
                        y_offset + (maxy_n - y) * svg_scale,
                    )
                    for x, y in coords
                ]
                commands.append(
                    "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in points) + " Z"
                )
            return " ".join(commands)

        polygons = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        svg_paths = "".join(
            f'<path d="{polygon_svg_path(poly)}" fill="{ntt_color}" '
            'fill-opacity="0.94" stroke="#FFFFFF" stroke-width="1.2" '
            'fill-rule="evenodd"/>'
            for poly in polygons
            if getattr(poly, "geom_type", "") == "Polygon"
        )

        # Inset NTT tetap sama secara visual. Klik tidak lagi ditangani
        # dari JavaScript di dalam iframe Folium, melainkan oleh tombol
        # Streamlit transparan yang ditumpuk tepat di atas inset ini.
        inset_id = f"ntt_inset_{re.sub(r'[^a-zA-Z0-9_]', '_', key)}"
        inset_html = f"""
        {{% macro html(this, kwargs) %}}
        <div id="{inset_id}" title="Klik untuk memfilter Kupang"
             style="position:absolute;right:14px;bottom:18px;width:29%;min-width:255px;max-width:330px;height:198px;z-index:99999;border:3px solid #FFFFFF;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.25);overflow:hidden;background:#E9EEF2;box-sizing:border-box;padding:0;pointer-events:none">
          <div style="position:absolute;left:10px;top:8px;z-index:2;background:rgba(255,255,255,.95);padding:4px 8px;border-radius:5px;font:700 11px Arial;color:#262626">NTT · {ntt_sat_text}</div>
          <svg viewBox="0 0 {svg_w:.0f} {svg_h:.0f}" preserveAspectRatio="xMidYMid meet"
               style="position:absolute;left:0;right:0;bottom:0;width:100%;height:176px;background:#E9EEF2;pointer-events:none">
            {svg_paths}
          </svg>
        </div>
        {{% endmacro %}}
        """
        inset = MacroElement()
        inset._template = Template(inset_html)
        main_map.get_root().add_child(inset)

    legend_html = f"""
    {{% macro html(this, kwargs) %}}
    <div style="position:absolute;left:60px;bottom:18px;z-index:9998;background:rgba(255,255,255,.96);border:1px solid #D9DEE5;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.12);padding:9px 12px;font:12px Arial;color:#475569">
      <div style="font-weight:700;margin-bottom:5px">Nilai Satisfaction</div>
      <div style="width:210px;height:10px;border-radius:5px;background:linear-gradient(90deg,#E60012 0%,#FFB000 50%,#35A853 100%)"></div>
      <div style="display:flex;justify-content:space-between;margin-top:3px"><span>Rendah · {scale_min:.1f}%</span><span>Tinggi · {scale_max:.1f}%</span></div>
    </div>
    {{% endmacro %}}
    """
    legend = MacroElement()
    legend._template = Template(legend_html)
    main_map.get_root().add_child(legend)

    # ========================================================
    # TAMPILKAN PETA + AREA KLIK NTT
    # ========================================================
    with st.container(key=f"{unit_from_key}_map_interaction_wrapper"):
        map_result = st_folium(
            main_map,
            height=560,
            use_container_width=True,
            key=key,
            returned_objects=[
                "last_object_clicked_tooltip",
                "last_object_clicked_count",
                "last_clicked",
            ],
        )

        # Tombol ini transparan dan diletakkan tepat di atas gambar NTT kecil.
        # Karena ini widget Streamlit asli, klik masuk langsung ke Python.
        ntt_clicked = st.button(
            "Pilih Kupang",
            key=f"{unit_from_key}_ntt_overlay_click",
            help="Klik untuk menampilkan data Kupang",
            use_container_width=True,
        )

    # create_map() dipanggil sebelum render_filters(), jadi state filter dapat
    # diubah pada run yang sama sebelum dropdown Kab/Kota dibuat.
    if ntt_clicked:
        _set_map_region_filter(
            df,
            cols,
            unit_from_key,
            "NTT",
        )
        return

    # Klik polygon Jawa Timur tetap ditangani oleh st_folium seperti sebelumnya.
    tooltip_text = str((map_result or {}).get("last_object_clicked_tooltip") or "")
    last_clicked = (map_result or {}).get("last_clicked") or {}

    clicked_match = re.search(
        r"Kabupaten/Kota:\s*(.*?)\s*Satisfaction",
        tooltip_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    clicked_region = clicked_match.group(1).strip() if clicked_match else None

    click_count = (map_result or {}).get("last_object_clicked_count", 0)
    click_token = f"{clicked_region}|{click_count}|{last_clicked.get('lng')}"
    click_state_key = f"{unit_from_key}_last_polygon_click"

    if clicked_region and st.session_state.get(click_state_key) != click_token:
        st.session_state[click_state_key] = click_token
        _set_map_region_filter(
            df,
            cols,
            unit_from_key,
            clicked_region,
        )

# ============================================================
# RENDER: KPI
# ============================================================

def _kpi_card(label, value, sub, sub_color):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub" style="color:{sub_color};">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(sat_s1, sat_s2, n_responden):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        val = f"{sat_s1:.1f}%" if sat_s1 is not None else "N/A"
        label = "Baik" if (sat_s1 or 0) >= 70 else ("Cukup" if (sat_s1 or 0) >= 50 else "Kurang")
        _kpi_card("Satisfaction Semester 1", val, label if sat_s1 is not None else "-", "#2E7D32")
    with c2:
        val = f"{sat_s2:.1f}%" if sat_s2 is not None else "N/A"
        label = "Baik" if (sat_s2 or 0) >= 70 else ("Cukup" if (sat_s2 or 0) >= 50 else "Kurang")
        _kpi_card("Satisfaction Semester 2", val, label if sat_s2 is not None else "-", "#2E7D32")
    with c3:
        if sat_s1 is not None and sat_s2 is not None:
            diff = round(sat_s2 - sat_s1, 1)
            sign = "+" if diff >= 0 else ""
            label = "Meningkat" if diff >= 0 else "Menurun"
            color = "#2E7D32" if diff >= 0 else "#C62828"
            _kpi_card("Improvement", f"{sign}{diff:.1f}%", label, color)
        else:
            _kpi_card("Improvement", "N/A", "-", "#888888")
    with c4:
        val = f"{n_responden:,}".replace(",", ".") if n_responden is not None else "N/A"
        _kpi_card("Jumlah Responden", val, "Responden", "#555555")


# ============================================================
# RENDER: SATISFACTION PER ATRIBUT & TARGET GAP
# ============================================================

def render_satisfaction_chart(attr_sat: dict, indicator_names: dict, key: str):
    with st.container(key=f"{key}_scroll_chart_card", border=True):
        st.markdown('<div class="chart-title">Satisfaction Score by Attribute</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-subtitle">Data ditampilkan berdasarkan filter yang dipilih</div>', unsafe_allow_html=True)
        if not attr_sat:
            st.info("Data tidak tersedia.")
            return
        codes = list(attr_sat.keys())
        vals = list(attr_sat.values())
        names = [indicator_names.get(str(code).strip().upper(), "Nama indikator belum tersedia") for code in codes]
        max_val = max(vals) if vals else 100
        fig = go.Figure(go.Bar(
            x=vals, y=codes, orientation="h",
            marker=dict(color=RED),
            text=[f"{v:.0f}%" for v in vals], textposition="outside",
            customdata=np.array(names, dtype=object).reshape(-1, 1),
            hovertemplate=(
                "<b>Kode Indikator:</b> %{y}<br>"
                "<b>Nama Indikator:</b> %{customdata[0]}<br>"
                "<b>Satisfaction:</b> %{x:.1f}%<extra></extra>"
            ),
        ))
        fig.update_layout(
            xaxis=dict(range=[0, max(112, max_val + 12)], ticksuffix="%"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=30, t=10, b=10), height=max(280, 26 * len(codes)),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, key=key)


def render_target_gap_chart(gaps: dict, attr_sat: dict, indicator_names: dict, key: str):
    with st.container(key=f"{key}_scroll_chart_card", border=True):
        st.markdown('<div class="chart-title">Performance vs Attribute Target</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-subtitle">Data ditampilkan berdasarkan filter yang dipilih</div>', unsafe_allow_html=True)
        if not gaps:
            st.info("Data tidak tersedia.")
            return
        codes = list(gaps.keys())
        vals = list(gaps.values())
        names = [indicator_names.get(str(code).strip().upper(), "Nama indikator belum tersedia") for code in codes]
        satisfaction_values = [attr_sat.get(code) for code in codes]
        colors = [GREEN if v >= 0 else RED for v in vals]
        texts = [f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%" for v in vals]
        max_val = max(vals) if vals else 0
        min_val = min(vals) if vals else 0
        x_max = max(0.1, max_val + max(0.12, abs(max_val) * 0.25))
        x_min = min(0, min_val - max(0.05, abs(min_val) * 0.25))
        fig = go.Figure(go.Bar(
            x=vals, y=codes, orientation="h", marker=dict(color=colors),
            text=texts, textposition="outside",
            customdata=np.array([
                [name, sat if sat is not None else np.nan]
                for name, sat in zip(names, satisfaction_values)
            ], dtype=object),
            hovertemplate=(
                "<b>Kode Indikator:</b> %{y}<br>"
                "<b>Nama Indikator:</b> %{customdata[0]}<br>"
                "<b>%Satisfaction:</b> %{customdata[1]:.1f}%<br>"
                "<b>%Gap terhadap target:</b> %{x:+.1f}%<extra></extra>"
            ),
        ))
        fig.add_vline(x=0, line_color="#999999")
        fig.update_layout(
            xaxis=dict(range=[x_min, x_max]),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=30, t=10, b=10), height=max(280, 26 * len(codes)),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, key=key)


def render_semester_difference_chart(
    diffs,
    subtitle: str,
    key: str,
    attr_sat: dict = None,
    indicator_names: dict = None,
):
    with st.container(key=f"{key}_scroll_chart_card", border=True):
        st.markdown(
            '<div class="chart-title">Satisfaction Semester Ini vs Semester Sebelumnya</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="chart-subtitle">{subtitle}</div>',
            unsafe_allow_html=True
        )

        if diffs is None:
            st.info("Data periode sebelumnya tidak tersedia untuk filter ini.")
            return

        if not diffs:
            st.info("Data tidak tersedia.")
            return

        attr_sat = attr_sat or {}
        indicator_names = indicator_names or {}

        codes = list(diffs.keys())
        vals = list(diffs.values())

        colors = [
            GREEN if value >= 0 else RED
            for value in vals
        ]

        texts = [
            f"+{value:.1f}%"
            if value >= 0
            else f"{value:.1f}%"
            for value in vals
        ]

        # Nama indikator dan nilai satisfaction semester aktif
        names = [
            indicator_names.get(
                str(code).strip().upper(),
                "Nama indikator belum tersedia"
            )
            for code in codes
        ]

        current_satisfaction = [
            attr_sat.get(code, np.nan)
            for code in codes
        ]

        # Customdata:
        # [0] = nama indikator
        # [1] = satisfaction semester aktif
        customdata = np.array(
            [
                [
                    name,
                    sat if sat is not None else np.nan,
                ]
                for name, sat in zip(
                    names,
                    current_satisfaction,
                )
            ],
            dtype=object,
        )

        max_val = max(vals) if vals else 0
        min_val = min(vals) if vals else 0

        x_max = max(
            0.1,
            max_val + max(
                0.12,
                abs(max_val) * 0.25
            )
        )

        x_min = min(
            0,
            min_val - max(
                0.05,
                abs(min_val) * 0.25
            )
        )

        fig = go.Figure(
            go.Bar(
                x=vals,
                y=codes,
                orientation="h",
                marker=dict(color=colors),
                text=texts,
                textposition="outside",
                cliponaxis=False,
                customdata=customdata,
                hovertemplate=(
                    "<b>Kode Indikator:</b> %{y}<br>"
                    "<b>Nama Indikator:</b> %{customdata[0]}<br>"
                    "<b>%Satisfaction:</b> %{customdata[1]:.1f}%<br>"
                    "<b>%Gap semester sebelumnya:</b> %{x:+.1f}%"
                    "<extra></extra>"
                ),
            )
        )

        fig.add_vline(
            x=0,
            line_color="#999999"
        )

        fig.update_layout(
            xaxis=dict(
                range=[x_min, x_max],
                ticksuffix="%",
            ),
            yaxis=dict(
                autorange="reversed"
            ),
            margin=dict(
                l=10,
                r=45,
                t=10,
                b=10
            ),
            height=max(
                280,
                26 * len(codes)
            ),
            showlegend=False,
            hoverlabel=dict(
                align="left"
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=key,
            config={
                "displayModeBar": True
            },
        )

def render_performance_section(
    df_all,
    cols,
    meta_df,
    filters,
    indicator_cols,
    key_prefix
):
    indicator_names = build_indicator_name_map(meta_df)

    # ========================================================
    # SECTION 1 : CSL PERFORMANCE INDEX
    # Seluruh isi berada dalam SATU container
    # sehingga outline benar-benar membungkus semuanya.
    # ========================================================

    with st.container(
        key=f"{key_prefix}_csl_performance_section"
    ):

        # ====================================================
        # JUDUL SECTION
        # ====================================================

        st.markdown(
            """
            <div class="custom-section-title">
                <div class="custom-section-badge">SECTION 1</div>
                <div class="custom-section-text">CSL PERFORMANCE INDEX</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ====================================================
        # PETA
        # ====================================================

        st.markdown(
            """
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 8px;">
                <div style="font-size:12px;font-weight:800;color:#666;text-transform:uppercase;letter-spacing:.3px;">
                    Satisfaction Map
                </div>
                <div style="font-size:10.5px;font-weight:700;color:#C8102E;background:#FFF1F1;border:1px solid #FFD8D8;padding:4px 9px;border-radius:20px;">
                    CLICK MAP TO FILTER
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        create_map(
            df_all,
            cols,
            indicator_cols,
            key=f"{key_prefix}_map"
        )

        st.markdown(
            "<div style='height:16px'></div>",
            unsafe_allow_html=True
        )

        # ====================================================
        # FILTER
        # ====================================================

        new_filters = render_filters(
            df_all,
            cols,
            filters.get(
                "_dealer_label",
                "Dealer"
            ),
            key_prefix
        )

        new_filters["_dealer_label"] = (
            filters.get(
                "_dealer_label",
                "Dealer"
            )
        )

        filters = new_filters

        df_filtered = apply_filters(
            df_all,
            cols,
            filters
        )

        st.markdown(
            "<div style='height:16px'></div>",
            unsafe_allow_html=True
        )

        # ====================================================
        # KPI
        # ====================================================

        year_col = cols.get("year")
        sem_col = cols.get("semester")

        df_s1 = apply_filters(
            df_all,
            cols,
            filters,
            override_semester=1,
            ignore_period=True
        )

        df_s2 = apply_filters(
            df_all,
            cols,
            filters,
            override_semester=2,
            ignore_period=True
        )

        if filters.get("year") and year_col:

            df_s1 = df_s1[
                df_s1[year_col]
                .astype(str)
                == str(filters["year"])
            ]

            df_s2 = df_s2[
                df_s2[year_col]
                .astype(str)
                == str(filters["year"])
            ]

        sat_s1 = calculate_satisfaction(
            df_s1,
            indicator_cols
        )

        sat_s2 = calculate_satisfaction(
            df_s2,
            indicator_cols
        )

        n_responden = (
            len(df_filtered)
            if df_filtered is not None
            else 0
        )

        render_kpi_cards(
            sat_s1,
            sat_s2,
            n_responden
        )

        st.markdown(
            "<div style='height:16px'></div>",
            unsafe_allow_html=True
        )

        # ====================================================
        # SATISFACTION PER ATRIBUT
        # ====================================================

        attr_sat = (
            calculate_attribute_satisfaction(
                df_filtered,
                indicator_cols
            )
        )

        # ====================================================
        # GAP TERHADAP TARGET
        # ====================================================

        gaps = calculate_target_gap(
            attr_sat,
            meta_df,
            filters.get("main_dealer"),
            filters.get("layer")
        )

        # ====================================================
        # PERIODE SEBELUMNYA
        # ====================================================

        available_periods = get_available_periods(
            df_all,
            cols
        )

        prev_period = None

        if (
            filters.get("year")
            and filters.get("semester")
        ):

            prev_period = get_previous_period(
                filters["year"],
                filters["semester"],
                available_periods
            )

        # ====================================================
        # CHART
        # ====================================================

        if prev_period is None:

            c1, c2 = st.columns(
                2,
                gap="medium"
            )

            with c1:

                render_satisfaction_chart(
                    attr_sat,
                    indicator_names,
                    key=f"{key_prefix}_sat"
                )

            with c2:

                render_target_gap_chart(
                    gaps,
                    attr_sat,
                    indicator_names,
                    key=f"{key_prefix}_gap"
                )

        else:

            prev_year, prev_sem = (
                prev_period
            )

            df_prev = apply_filters(
                df_all,
                cols,
                filters,
                override_year=prev_year,
                override_semester=prev_sem,
                ignore_period=True,
            )

            diffs = (
                calculate_semester_difference(
                    df_filtered,
                    df_prev,
                    indicator_cols
                )
            )

            cur_label = period_label(
                filters["year"],
                filters["semester"]
            )

            prev_label = period_label(
                prev_year,
                prev_sem
            )

            subtitle = (
                f"{cur_label} − {prev_label}"
            )

            c1, c2, c3 = st.columns(
                3,
                gap="medium"
            )

            with c1:

                render_satisfaction_chart(
                    attr_sat,
                    indicator_names,
                    key=f"{key_prefix}_sat"
                )

            with c2:

                render_target_gap_chart(
                    gaps,
                    attr_sat,
                    indicator_names,
                    key=f"{key_prefix}_gap"
                )

            with c3:

                render_semester_difference_chart(
                    diffs,
                    subtitle,
                    key=f"{key_prefix}_diff",
                    attr_sat=attr_sat,
                    indicator_names=indicator_names,
                )

    # ========================================================
    # SUDAH DI LUAR OUTLINE MERAH
    # ========================================================

    return filters, df_filtered

# ============================================================
# RENDER: IMPORTANCE MATRIX (DARI WORKSHEET MATRIKS)
# ============================================================

def render_importance_matrix(unit_key: str, key: str, filters: dict = None):
    with st.container(key=f"{key}_matrix_section"):
        st.markdown(
            """
            <div class="custom-section-title">
                <div class="custom-section-badge">SECTION 2</div>
                <div class="custom-section-text">MATRIX SATISFACTION x IMPORTANCE</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            "Matriks ini menunjukkan posisi setiap atribut berdasarkan tingkat "
            "Satisfaction (X) dan Importance (Y)."
        )

        u_str = str(unit_key).strip().lower()
        if u_str in ["sales", "h1"]:
            sheet_candidates = ["matriks_h1", "matriks_H1", "matrix_h1", "matriks", "matrix"]
        elif u_str in ["service", "h2"]:
            sheet_candidates = ["matriks_h2", "matriks_H2", "matrix_h2", "matriks", "matrix"]
        elif u_str in ["parts", "h3"]:
            sheet_candidates = ["matriks_h3", "matriks_H3", "matrix_h3", "matriks", "matrix"]
        else:
            sheet_candidates = ["matriks_h1", "matriks_h2", "matriks_h3", "matriks", "matrix"]

        mat_df = pd.DataFrame()
        for s in sheet_candidates:
            mat_df = try_read_sheet(s)
            if not mat_df.empty:
                break

        if mat_df.empty:
            st.warning("Worksheet matriks tidak ditemukan.")
            return

        code_col = find_col(mat_df, ["Attribute", "attribute", "Kode_Indicator", "kode_indicator", "kode", "kode atribut", "code"])
        sat_col = find_col(mat_df, ["Performance", "performance", "satisfaction", "nilai satisfaction"])
        imp_col = find_col(mat_df, ["Relative_Importance", "relative_importance", "Weighting", "weighting", "importance", "nilai importance"])
        avg_sat_col = find_col(mat_df, [
            "AVG Satisfaction", "avg_satisfaction", "average satisfaction",
            "mean satisfaction", "rata-rata satisfaction", "avg performance",
        ])
        rank_sat_col = find_col(mat_df, [
            "Satisfaction_Rank", "satisfaction_rank", "Rank Satisfaction", "rank_satisfaction", "satisfaction rank",
            "peringkat satisfaction", "rank performance",
        ])
        rank_imp_col = find_col(mat_df, [
            "Importance_Rank", "importance_rank", "Rank Importance", "rank_importance", "importance rank",
            "peringkat importance", "rank weighting",
        ])

        if not code_col or not sat_col or not imp_col:
            st.warning("Kolom Kode, Satisfaction, atau Importance tidak ditemukan pada worksheet matriks.")
            return

        # Nama indikator untuk tooltip dan panel detail kuadran.
        # Metadata dipilih sesuai unit agar kode yang sama pada H1/H2/H3
        # tidak tertukar keterangannya.
        meta_candidates = {
            "sales": ["Indicator_metadata_H1", "indicator_metadata_H1"],
            "h1": ["Indicator_metadata_H1", "indicator_metadata_H1"],
            "service": ["Indicator_metadata_H2", "indicator_metadata_H2"],
            "h2": ["Indicator_metadata_H2", "indicator_metadata_H2"],
            "parts": ["Indicator_metadata_H3", "indicator_metadata_H3"],
            "h3": ["Indicator_metadata_H3", "indicator_metadata_H3"],
        }.get(u_str, []) + ["indicator_metadata"]
        indicator_name_map = {}
        for meta_sheet in meta_candidates:
            meta_lookup = try_read_sheet(meta_sheet)
            if meta_lookup.empty:
                continue
            meta_code_col = find_col(meta_lookup, [
                "Kode_Indikator", "kode indikator", "Kode Indicator",
                "kode_indicator", "indicator code", "kode", "code",
            ])
            meta_name_col = find_col(meta_lookup, [
                "Nama_Indikator", "nama indikator", "Indicator Name",
                "nama_indicator", "indicator", "atribut", "attribute",
                "description", "keterangan",
            ])
            if meta_code_col and meta_name_col:
                for _, meta_row in meta_lookup[[meta_code_col, meta_name_col]].dropna(subset=[meta_code_col]).iterrows():
                    code_key = str(meta_row[meta_code_col]).strip().upper()
                    name_val = str(meta_row[meta_name_col]).strip()
                    if code_key and name_val and name_val.lower() != "nan":
                        indicator_name_map[code_key] = name_val
                break

        df_sub = mat_df.copy()

        if filters:
            if "Tahun" in df_sub.columns and filters.get("year"):
                df_sub = df_sub[df_sub["Tahun"].astype(str) == str(filters["year"])]

            if "Semester" in df_sub.columns and filters.get("semester"):
                sem_val = str(filters["semester"])
                if not sem_val.lower().startswith("semester"):
                    sem_val = f"Semester {sem_val}"
                matched_sem = df_sub[df_sub["Semester"].astype(str).str.lower() == sem_val.lower()]
                if not matched_sem.empty:
                    df_sub = matched_sem

            cat_type_col = find_col(df_sub, ["Category_Type", "category_type"])
            cat_col = find_col(df_sub, ["Category", "category"])

            if cat_type_col and cat_col:
                target_type = None
                target_cat = None
                if filters.get("dealer"):
                    target_type = "DEALER"
                    target_cat = str(filters["dealer"])
                elif filters.get("kab_kota"):
                    target_type = "KOTA"
                    target_cat = str(filters["kab_kota"])
                elif filters.get("karesidenan"):
                    target_type = "KARES"
                    target_cat = str(filters["karesidenan"])
                elif filters.get("layer"):
                    target_type = "LAYER"
                    target_cat = str(filters["layer"])
                elif filters.get("main_dealer") and str(filters["main_dealer"]).strip().upper() in ["M2Z", "M3Z", "SEMUA"]:
                    target_type = "MAIN DEALER"
                    target_cat = str(filters["main_dealer"]).strip().upper()
                else:
                    col_sel1, _ = st.columns([1, 3])
                    with col_sel1:
                        target_cat = st.selectbox(
                            "Pilih Main Dealer (Matriks):",
                            options=["M2Z", "M3Z"],
                            key=f"{key}_md_selector"
                        )
                    target_type = "MAIN DEALER"

                if target_type and target_cat:
                    category_type = df_sub[cat_type_col].astype(str).str.strip().str.upper()
                    category = df_sub[cat_col].astype(str).str.strip().str.upper()
                    if target_type == "MAIN DEALER" and target_cat == "SEMUA":
                        # Utamakan baris agregat SEMUA bila tersedia. Jika worksheet
                        # matriks hanya memiliki M2Z dan M3Z, gabungkan keduanya.
                        m = df_sub[(category_type == target_type) & (category == "SEMUA")]
                        if m.empty:
                            m = df_sub[
                                (category_type == target_type)
                                & (category.isin(["M2Z", "M3Z"]))
                            ]
                    else:
                        m = df_sub[
                            (category_type == target_type)
                            & (category == target_cat.upper())
                        ]
                    if not m.empty:
                        df_sub = m

        if df_sub.empty:
            st.info("Data matriks tidak tersedia untuk filter yang dipilih.")
            return

        codes, xs, ys = [], [], []
        avg_sats, raw_sats, rank_sats, rank_imps = [], [], [], []
        grouped = df_sub.groupby(code_col, as_index=False)
        for c_code, group in grouped:
            try:
                perf_series = pd.to_numeric(group[sat_col].astype(str).str.replace("%", "").str.replace(",", "."), errors="coerce")
                imp_series = pd.to_numeric(group[imp_col].astype(str).str.replace("%", "").str.replace(",", "."), errors="coerce")

                avg_perf = perf_series.mean()
                avg_imp = imp_series.mean()

                if pd.isna(avg_perf) or pd.isna(avg_imp):
                    continue

                # Sumbu X = Satisfaction dan sumbu Y = Importance.
                x_val = round((avg_perf / 5.0 * 100), 1) if avg_perf <= 10 else round(avg_perf, 1)
                y_val = round(avg_imp, 2)

                avg_sat_series = (
                    pd.to_numeric(group[avg_sat_col].astype(str).str.replace("%", "").str.replace(",", "."), errors="coerce")
                    if avg_sat_col else perf_series
                )
                avg_sat_value = avg_sat_series.mean()
                if pd.notna(avg_sat_value) and avg_sat_value <= 10:
                    avg_sat_value = avg_sat_value / 5.0 * 100

                def first_numeric(column):
                    if not column:
                        return np.nan
                    values = pd.to_numeric(group[column], errors="coerce").dropna()
                    return float(values.iloc[0]) if not values.empty else np.nan

                codes.append(str(c_code).strip())
                xs.append(x_val)
                ys.append(y_val)
                avg_sats.append(float(avg_sat_value) if pd.notna(avg_sat_value) else x_val)
                raw_sats.append(float(avg_perf))
                rank_sats.append(first_numeric(rank_sat_col))
                rank_imps.append(first_numeric(rank_imp_col))
            except Exception:
                continue

        if not codes:
            st.info("Data matriks tidak tersedia.")
            return

        # Garis tengah kuadran menggunakan median agar tidak tertarik oleh
        # satu nilai Importance ekstrem seperti yang terjadi pada Pasuruan.
        x_mid = round(float(np.median(xs)), 2)
        y_mid = round(float(np.median(ys)), 2)

        QUADRANTS = {
            "keep": {"label": "Pertahankan", "roman": "Kuadran I", "color": ORANGE,
                     "test": lambda x, y: x >= x_mid and y >= y_mid},
            "priority": {"label": "Prioritas Utama", "roman": "Kuadran II", "color": RED,
                    "test": lambda x, y: x < x_mid and y >= y_mid},
            "gradual": {"label": "Perbaikan Bertahap", "roman": "Kuadran III", "color": "#C9A400",
                        "test": lambda x, y: x < x_mid and y < y_mid},
            "low": {"label": "Prioritas Rendah", "roman": "Kuadran IV", "color": GREEN,
                         "test": lambda x, y: x >= x_mid and y < y_mid},
        }

        def classify(x, y):
            for qk, info in QUADRANTS.items():
                if info["test"](x, y):
                    return qk
            return "gradual"

        quadrant_of_code = {}
        points_by_quadrant = {qk: [] for qk in QUADRANTS}
        for idx, (c_code, x_val, y_val) in enumerate(zip(codes, xs, ys)):
            qk = classify(x_val, y_val)
            quadrant_of_code[c_code] = qk
            points_by_quadrant[qk].append({
                "code": c_code, "name": indicator_name_map.get(c_code.upper(), "Nama indikator belum tersedia"),
                "x": x_val, "y": y_val,
                "avg_sat": avg_sats[idx], "raw_sat": raw_sats[idx],
                "rank_sat": rank_sats[idx], "rank_imp": rank_imps[idx],
            })

        colors = [QUADRANTS[quadrant_of_code[c]]["color"] for c in codes]

        sel_key = f"{key}_selected_quadrant"
        if sel_key not in st.session_state:
            # Default: tampilkan kuadran dengan jumlah indikator terbanyak.
            st.session_state[sel_key] = max(points_by_quadrant, key=lambda qk: len(points_by_quadrant[qk]))

        # Baca hasil klik titik pada chart dari render sebelumnya (state Plotly).
        prev_selection = st.session_state.get(key, {})
        clicked_points = []
        if isinstance(prev_selection, dict):
            clicked_points = prev_selection.get("selection", {}).get("points", [])
        if clicked_points:
            idx = clicked_points[0].get("point_index")
            if idx is not None and 0 <= idx < len(codes):
                st.session_state[sel_key] = quadrant_of_code[codes[idx]]

        selected_qk = st.session_state[sel_key]

        col_chart, col_detail = st.columns([2.3, 1])

        with col_chart:
            chip_cols = st.columns(4)
            for chip_col, (qk, info) in zip(chip_cols, QUADRANTS.items()):
                with chip_col:
                    is_sel = qk == selected_qk

                    if st.button(
                        f"{'●' if is_sel else '○'} {info['roman']} ({len(points_by_quadrant[qk])})",
                        key=f"{key}_chip_{qk}",
                        use_container_width=True,
                        help=info["label"],
                        type="primary" if is_sel else "secondary",
                    ):
                        st.session_state[sel_key] = qk

                        # Rerun langsung agar:
                        # 1. tombol yang dipilih langsung menjadi aktif,
                        # 2. panel kanan sinkron,
                        # 3. highlight grafik sinkron.
                        st.rerun()

            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            x_pad = max(0.50, (x_max - x_min) * 0.08)
            y_pad = max(0.80, (y_max - y_min) * 0.10)
            x_lo, x_hi = max(0.0, x_min - x_pad), x_max + x_pad
            y_lo, y_hi = max(0.0, y_min - y_pad), min(105.0, y_max + y_pad)

            fig = go.Figure()

            quad_bounds = {
                "priority": (x_lo, x_mid, y_mid, y_hi),
                "keep": (x_mid, x_hi, y_mid, y_hi),
                "gradual": (x_lo, x_mid, y_lo, y_mid),
                "low": (x_mid, x_hi, y_lo, y_mid),
            }
            for qk, (rx0, rx1, ry0, ry1) in quad_bounds.items():
                is_sel = qk == selected_qk

                fig.add_shape(
                    type="rect",
                    x0=rx0,
                    x1=rx1,
                    y0=ry0,
                    y1=ry1,
                    fillcolor=QUADRANTS[qk]["color"],

                    # Kuadran aktif jauh lebih terlihat.
                    opacity=0.26 if is_sel else 0.025,

                    line=dict(
                        width=2.4 if is_sel else 0.5,
                        color=(
                            QUADRANTS[qk]["color"]
                            if is_sel
                            else "rgba(180,180,180,0.30)"
                        ),
                    ),
                    layer="below",
                )

            # Titik pada kuadran aktif dibuat lebih kuat,
            # titik kuadran lain dibuat lebih redup.
            marker_opacity = [
                1.0 if quadrant_of_code[c] == selected_qk else 0.16
                for c in codes
            ]

            marker_line_width = [
                2.8 if quadrant_of_code[c] == selected_qk else 0.5
                for c in codes
            ]

            marker_size = [
                15 if quadrant_of_code[c] == selected_qk else 9
                for c in codes
            ]

            point_names = [indicator_name_map.get(c.upper(), "Nama indikator belum tersedia") for c in codes]
            hover_data = np.column_stack([
                point_names, avg_sats, raw_sats, rank_sats, rank_imps,
            ])
            fig.add_trace(go.Scatter(
                # Kode indikator tidak ditulis permanen di atas titik karena
                # wilayah dengan Importance berdekatan membuat label bertabrakan.
                # Kode dan nama lengkap tetap muncul saat titik di-hover.
                x=xs, y=ys, mode="markers", text=codes,
                customdata=hover_data,
                marker=dict(
                    size=marker_size,
                    color=colors,
                    opacity=marker_opacity,
                    line=dict(
                        width=marker_line_width,
                        color="white",
                    ),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "<b>Nama indikator:</b> %{customdata[0]}<br>"
                    "<b>AVG Satisfaction:</b> %{customdata[1]:.2f}%<br>"
                    "<b>Satisfaction:</b> %{customdata[2]:.2f}<br>"
                    "<b>Importance:</b> %{y:.2f}<br>"
                    "<b>Rank Satisfaction:</b> %{customdata[3]}<br>"
                    "<b>Rank Importance:</b> %{customdata[4]}"
                    "<extra></extra>"
                ),
            ))

            fig.add_vline(x=x_mid, line_dash="dash", line_width=1, line_color="#9AA0A6")
            fig.add_hline(y=y_mid, line_dash="dash", line_width=1, line_color="#9AA0A6")

            fig.update_layout(
                xaxis=dict(title="Satisfaction (%)", range=[x_lo, x_hi], tickformat=".1f", gridcolor="#F0F1F3"),
                yaxis=dict(title="Importance", range=[y_lo, y_hi], tickformat=".2f", gridcolor="#F0F1F3"),
                margin=dict(l=42, r=26, t=20, b=42), height=480,
                hovermode="closest",
                clickmode="event+select",
                annotations=[
                    dict(
                        x=x_lo, y=y_hi,
                        text=f"<b>{QUADRANTS['priority']['roman']} · Prioritas Utama</b>",
                        showarrow=False,
                        font=dict(
                            color=RED if selected_qk == "priority" else "rgba(120,120,120,0.55)",
                            size=15 if selected_qk == "priority" else 12,
                        ),
                        xanchor="left", yanchor="top",
                    ),
                    dict(
                        x=x_hi, y=y_hi,
                        text=f"<b>{QUADRANTS['keep']['roman']} · Pertahankan</b>",
                        showarrow=False,
                        font=dict(
                            color=ORANGE if selected_qk == "keep" else "rgba(120,120,120,0.55)",
                            size=15 if selected_qk == "keep" else 12,
                        ),
                        xanchor="right", yanchor="top",
                    ),
                    dict(
                        x=x_lo, y=y_lo,
                        text=f"<b>{QUADRANTS['gradual']['roman']} · Perbaikan Bertahap</b>",
                        showarrow=False,
                        font=dict(
                            color="#C9A400" if selected_qk == "gradual" else "rgba(120,120,120,0.55)",
                            size=15 if selected_qk == "gradual" else 12,
                        ),
                        xanchor="left", yanchor="bottom",
                    ),
                    dict(
                        x=x_hi, y=y_lo,
                        text=f"<b>{QUADRANTS['low']['roman']} · Prioritas Rendah</b>",
                        showarrow=False,
                        font=dict(
                            color=GREEN if selected_qk == "low" else "rgba(120,120,120,0.55)",
                            size=15 if selected_qk == "low" else 12,
                        ),
                        xanchor="right", yanchor="bottom",
                    ),
                ],
            )
            st.plotly_chart(
                fig, use_container_width=True, key=key,
                on_select="rerun", selection_mode="points",
            )
            st.caption("Klik titik pada matriks, atau klik salah satu tombol kuadran di atas, untuk melihat detail indikator di panel kanan.")

        with col_detail:
            info = QUADRANTS[selected_qk]
            pts = sorted(points_by_quadrant[selected_qk], key=lambda p: p["code"])
            if not pts:
                list_html = """
                    <div style="padding:16px 4px;color:#777;font-size:12px;">
                        Tidak ada indikator pada kuadran ini.
                    </div>
                """
            else:
                item_html = []
                for p in pts:
                    safe_code = html.escape(str(p["code"]))
                    safe_name = html.escape(str(p["name"]))
                    item_html.append(
                        f"""
                        <div title="{safe_code} · {safe_name}" style="display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px;
                                    border:1px solid #F0F1F3;border-left:4px solid {info['color']};border-radius:6px;
                                    padding:6px 10px;margin-bottom:6px;">
                            <span style="min-width:0;font-size:11.5px;color:#262626;line-height:1.25;overflow:hidden;">
                                <b style="font-size:12.5px;">{safe_code}</b><br>
                                <span style="display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{safe_name}</span>
                            </span>
                            <span style="font-size:11px;color:#666;text-align:right;">
                                Sat {p['x']:.2f}%<br>Imp {p['y']:.2f}
                            </span>
                        </div>
                        """
                    )
                list_html = "".join(item_html)

            # Tinggi panel disamakan dengan area tombol + matriks di sebelah kiri.
            # Jika indikator banyak, hanya daftar indikator yang bergerak/scroll.
            panel_html = f"""
                <div style="height:478px;border:1px solid #E7E9EC;border-radius:10px;
                            background:#FFFFFF;display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;">
                    <div style="flex:0 0 auto;padding:12px 14px 10px;border-bottom:1px solid #F0F1F3;">
                        <div style="font-size:11px;font-weight:800;letter-spacing:.4px;color:{info['color']};text-transform:uppercase;">
                            {html.escape(info['roman'])}
                        </div>
                        <div style="font-size:15px;font-weight:800;color:#262626;">
                            {html.escape(info['label'])}
                        </div>
                    </div>
                    <div style="flex:1 1 auto;min-height:0;overflow-y:auto;overflow-x:hidden;
                                padding:8px 10px 10px;scrollbar-gutter:stable;">
                        {list_html}
                    </div>
                </div>
                """
            # Hilangkan indentasi/baris baru agar Markdown tidak membaca item
            # indikator sebagai code block, terutama setelah HTML hasil join.
            panel_html = "".join(line.strip() for line in panel_html.splitlines())
            st.markdown(
                panel_html,
                unsafe_allow_html=True,
            )


# ============================================================
# RENDER: PROFILE CUSTOMER & DEMOGRAPHICS (OUTLINE BIRU UTUH)
# ============================================================

def render_profile_heatmap(unit_key: str, key: str):
    with st.container(key=f"{key}_heatmap_scroll"):
        st.markdown('<div class="chart-title">Customer Profile Heatmap vs Overall Average</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-subtitle">Kesenjangan Karakteristik Tiap Customer Profile Terhadap Rata-rata Keseluruhan</div>', unsafe_allow_html=True)

        u_str = str(unit_key).strip().lower()
        if u_str in ["sales", "h1"]:
            sheet_candidates = ["heatmap_h1", "heatmap_H1", "heatmap"]
            metadata_candidates = ["Indicator_metadata_H1", "Indikator_metadata_H1"]
        elif u_str in ["service", "h2"]:
            sheet_candidates = ["heatmap_h2", "heatmap_H2", "heatmap"]
            metadata_candidates = ["Indicator_metadata_H2", "Indikator_metadata_H2"]
        elif u_str in ["parts", "h3"]:
            sheet_candidates = ["heatmap_h3", "heatmap_H3", "heatmap"]
            metadata_candidates = ["Indicator_metadata_H3", "Indikator_metadata_H3"]
        else:
            sheet_candidates = ["heatmap_h1", "heatmap_h2", "heatmap_h3", "heatmap"]
            metadata_candidates = ["indicator_metadata"]

        heatmap_meta = pd.DataFrame()
        for metadata_sheet in metadata_candidates:
            heatmap_meta = try_read_sheet(metadata_sheet)
            if not heatmap_meta.empty:
                break
        heatmap_indicator_names = build_indicator_name_map(heatmap_meta)

        hm_df = pd.DataFrame()
        for s in sheet_candidates:
            hm_df = try_read_sheet(s)
            if not hm_df.empty and ("Profile" in hm_df.columns or "profile" in hm_df.columns or "Kode_Indikator" in hm_df.columns):
                break

        if hm_df.empty:
            st.warning("Worksheet heatmap tidak ditemukan.")
            return

        p_col = find_col(hm_df, ["Profile", "profile", "p", "profil"])
        k_col = find_col(hm_df, ["Kode_Indikator", "kode_indicator", "kode", "code", "attribute", "indikator"])
        v_col = find_col(hm_df, ["Nilai", "nilai", "value", "val", "selisih", "gap"])

        # Indikator metadata-only tetap tersedia untuk nama/tooltip matriks,
        # tetapi tidak boleh muncul pada heatmap atau visual profiling.
        excluded_heatmap_codes = excluded_calculation_indicators(unit_key)
        if k_col and excluded_heatmap_codes:
            hm_df = hm_df[
                ~hm_df[k_col].astype(str).str.strip().str.upper().isin(excluded_heatmap_codes)
            ].copy()

        profiles_label = []
        attr_codes = []
        matrix = []

        if p_col and k_col and v_col:
            df_clean = hm_df[[p_col, k_col, v_col]].dropna().copy()
            df_clean[p_col] = df_clean[p_col].astype(str).str.replace("P", "", case=False).str.replace("Profile", "", case=False).str.strip()
            df_clean[v_col] = pd.to_numeric(df_clean[v_col].astype(str).str.replace(",", "."), errors="coerce")
            df_clean = df_clean.dropna(subset=[v_col])

            # Vertikal (baris) = indikator, horizontal (kolom) = profile.
            piv = df_clean.pivot(index=k_col, columns=p_col, values=v_col)

            existing_p = [p for p in ["1", "2", "3", "4", "5"] if p in piv.columns]
            if not existing_p:
                existing_p = list(piv.columns)
            piv = piv.reindex(columns=existing_p)

            attr_codes = list(piv.index)
            profiles_label = [str(p) for p in piv.columns]

            # ============================================================
            # KONVERSI PROFILE GAP DARI SKALA LIKERT 1–5 KE PERSENTASE
            # ============================================================
            matrix = piv.values.astype(float)

            # Gap Likert → Persentase
            # Skala maksimum satisfaction = 5
            matrix = (matrix / 5) * 100

            matrix = matrix.tolist()
        else:
            prof_cols = [c for c in hm_df.columns if str(c).strip().upper() in ["P1", "P2", "P3", "P4", "P5", "PROFILE 1", "PROFILE 2", "PROFILE 3", "PROFILE 4", "PROFILE 5"]]
            if not k_col or not prof_cols:
                st.warning("Struktur kolom heatmap tidak ditemukan pada worksheet heatmap.")
                return

            profiles_label = [re.sub(r"[^0-9]", "", str(pc)) or str(pc) for pc in prof_cols]
            matrix = []
            for _, r in hm_df.iterrows():
                c_code = str(r[k_col]).strip()
                row_vals = []
                for pc in prof_cols:
                    try:
                        val = float(str(r[pc]).replace(",", ".").strip())
                        row_vals.append(val)
                    except Exception:
                        row_vals.append(0.0)
                attr_codes.append(c_code)
                matrix.append(row_vals)

        if not matrix or not attr_codes:
            st.info("Data heatmap tidak tersedia.")
            return

        text_matrix = []
        for row in matrix:
            row_text = []
            for v in row:
                if pd.isna(v) or v is None:
                    row_text.append("")
                elif round(v, 2) == 0:
                    row_text.append("0%")
                else:
                    value_text = f"{v:.2f}".rstrip("0").rstrip(".")
                    row_text.append(f"{value_text}%")
            text_matrix.append(row_text)

        colorscale = [
            [0.0, "#B71C1C"],  # Merah (Semakin Negatif)
            [0.35, "#EF5350"], # Merah Muda
            [0.5, "#FFFFFF"],  # Putih (Netral / 0)
            [0.65, "#81C784"], # Hijau Muda
            [1.0, "#2E7D32"]   # Hijau (Semakin Positif)
        ]

        heatmap_names = [
            heatmap_indicator_names.get(str(code).strip().upper(), "Nama indikator belum tersedia")
            for code in attr_codes
        ]
        heatmap_customdata = [
            [[str(code), str(name)] for _ in profiles_label]
            for code, name in zip(attr_codes, heatmap_names)
        ]

        fig = go.Figure(go.Heatmap(
            z=matrix,
            x=[f"P{p}" for p in profiles_label],
            y=attr_codes,
            text=text_matrix,
            texttemplate="%{text}",
            textfont=dict(size=12, color="#212121"),
            colorscale=colorscale,
            zmid=0,
            xgap=1.5,
            ygap=1.5,
            customdata=heatmap_customdata,
            colorbar=dict(title="Selisih", thickness=15),
            hovertemplate=(
                "<b>Kode Indikator:</b> %{customdata[0]}<br>"
                "<b>Nama Indikator:</b> %{customdata[1]}<br>"
                "<b>Selisih satisfaction rata-rata keseluruhan:</b> %{z:.2f}%"
                "<extra></extra>"
            )
        ))

        chart_height = max(340, 34 * len(attr_codes) + 90)
        fig.update_layout(
            xaxis=dict(title="Profile", tickangle=0, side="top"),
            yaxis=dict(title="Indikator", autorange="reversed"),
            margin=dict(l=30, r=20, t=40, b=20),
            height=chart_height,
        )
        st.plotly_chart(fig, use_container_width=True, key=key)


def render_profile_list(df_filtered, cols, key_prefix, profile_meta_df=None):
    with st.container(border=True):
        st.markdown('<div class="chart-title">Profile List</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-subtitle">Klik kartu profil untuk memilih</div>', unsafe_allow_html=True)

        profile_col = cols.get("profile") if cols else None
        selected = st.session_state.get(f"{key_prefix}_selected_profile", "P1")

        meta_names = {}
        if profile_meta_df is not None and not profile_meta_df.empty:
            code_col = find_col(profile_meta_df, ["profile", "profil", "code", "no"])
            name_col = find_col(profile_meta_df, ["profile name", "nama profil", "nama", "name"])
            if code_col and name_col:
                for _, r in profile_meta_df.iterrows():
                    p_raw = str(r[code_col]).replace(".0", "").strip()
                    p_match = re.search(r"(\d+)", p_raw)
                    if not p_match:
                        continue
                    p_key = f"P{p_match.group(1)}"
                    n_val = str(r[name_col]).strip()
                    if n_val and n_val.lower() != "nan":
                        meta_names[p_key] = n_val

        total = len(df_filtered) if df_filtered is not None else 0
        profile_codes = ["P1", "P2", "P3", "P4", "P5"]
        profile_counts = {}

        # Hitung jumlah profil setelah seluruh filter halaman diterapkan.
        # Hasil ini sekaligus menentukan profil mana yang boleh dipilih.
        for p in profile_codes:
            count = 0
            if profile_col and df_filtered is not None and not df_filtered.empty and profile_col in df_filtered.columns:
                count = df_filtered[profile_col].astype(str).str.contains(p, case=False, na=False).sum()
                if count == 0:
                    p_num = p.replace("P", "")
                    count = df_filtered[profile_col].astype(str).str.contains(rf"\b{p_num}\b", case=False, na=False).sum()
            profile_counts[p] = int(count)

        available_profiles = [p for p in profile_codes if profile_counts[p] > 0]

        # Jika profil aktif menjadi 0% karena filter berubah, otomatis pilih
        # profil pertama yang masih mempunyai responden.
        if available_profiles and selected not in available_profiles:
            selected = available_profiles[0]
            st.session_state[f"{key_prefix}_selected_profile"] = selected

        for p in profile_codes:
            count = profile_counts[p]

            pct = round(count / total * 100, 0) if total > 0 else 0
            is_disabled = count == 0
            is_active = (p == selected) and not is_disabled
            p_num = p.replace("P", "")
            name = meta_names.get(p, PROFILE_NAMES.get(p, f"Profil {p_num}"))

            state_tag = "_disabled" if is_disabled else ("_active" if is_active else "_inactive")
            card_key = f"{key_prefix}_prof_card_{p}{state_tag}"
            
            with st.container(key=card_key):
                st.markdown(
                    f"""
                    <div class="profile-card-inner">
                        <div class="profile-card-header">
                            <span class="profile-card-title">Profil {p_num} – {name}</span>
                            <span class="profile-card-pct">{pct:.0f}%</span>
                        </div>
                        <div class="profile-bar-bg">
                            <div class="profile-bar-fill" style="width:{pct}%; background:{PROFILE_COLORS[p]};"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    " ",
                    key=f"{key_prefix}_btn_select_{p}",
                    use_container_width=True,
                    disabled=is_disabled,
                    help=(
                        f"Profil {p_num} – {name}: tidak tersedia pada filter ini"
                        if is_disabled else
                        f"Profil {p_num} – {name}: {int(count)} orang ({pct:.0f}%)"
                    ),
                ):
                    st.session_state[f"{key_prefix}_selected_profile"] = p
                    selected = p
        return selected


def render_profile_explanation(profile_meta_df, selected_profile):
    with st.container(border=True):
        p_num = selected_profile.replace("P", "").strip()
        p_key = f"P{p_num}"

        name = PROFILE_NAMES.get(p_key, f"Profil {p_num}")
        insight, reco = None, None

        if profile_meta_df is not None and not profile_meta_df.empty:
            code_col = find_col(profile_meta_df, ["profile", "profil", "code", "no"])
            name_col = find_col(profile_meta_df, ["profile name", "nama profil", "nama", "name"])
            insight_col = find_col(profile_meta_df, ["business insight", "insight"])
            reco_col = find_col(profile_meta_df, ["recommendation", "rekomendasi"])

            if code_col:
                match = profile_meta_df[profile_meta_df[code_col].astype(str).str.contains(rf"\b{p_num}\b", case=False, na=False)]
                if not match.empty:
                    row = match.iloc[0]
                    if name_col and pd.notna(row.get(name_col)):
                        n_val = str(row.get(name_col)).strip()
                        if n_val and n_val.lower() != "nan":
                            name = n_val
                    if insight_col and pd.notna(row.get(insight_col)):
                        insight = str(row.get(insight_col)).strip()
                    if reco_col and pd.notna(row.get(reco_col)):
                        reco = str(row.get(reco_col)).strip()

        st.markdown(f'<div class="chart-title" style="font-size:14px; margin-bottom:10px;">Profile Description: Profile {p_num} – {name}</div>', unsafe_allow_html=True)

        insight_text = insight if insight and insight.lower() != "nan" else "Business insight tidak tersedia untuk profil ini."
        st.markdown(
            f"""
            <div class="insight-box">
                <div class="insight-box-header">
                    <span></span><span>Business Insight</span>
                </div>
                <div class="insight-box-body">
                    {insight_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        reco_text = reco if reco and reco.lower() != "nan" else "Rekomendasi tidak tersedia untuk profil ini."
        st.markdown(
            f"""
            <div class="reco-box">
                <div class="reco-box-header">
                    <span></span><span>Rekomendasi Strategis</span>
                </div>
                <div class="reco-box-body">
                    {reco_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# RENDER: DEMOGRAPHIC & NPS CHARTS
# ============================================================

def _simple_pie(df, col, title, key, colors=None):
    with st.container(
        key=f"{key}_demographic_chart_card",
        border=True,
    ):
        st.markdown(
            f'<div class="chart-title">{title}</div>',
            unsafe_allow_html=True,
        )

        with st.container(key=f"{key}_chart_viewport"):
            if (
                not col
                or df is None
                or df.empty
                or col not in df.columns
            ):
                st.info("Data tidak tersedia.")
                return

            counts = (
                df[col]
                .dropna()
                .astype(str)
                .value_counts()
            )

            if counts.empty:
                st.info("Data tidak tersedia.")
                return

            fig = go.Figure(
                go.Pie(
                    labels=counts.index,
                    values=counts.values,
                    hole=0.35,
                    marker=dict(colors=colors) if colors else None,
                    textinfo="percent",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Persentase: %{percent}<br>"
                        "Responden: %{value} orang"
                        "<extra></extra>"
                    ),
                )
            )

            fig.update_layout(
                # Legenda dipindahkan ke bawah agar tidak menumpuk dengan pie
                # ketika empat chart ditampilkan dalam satu baris.
                height=315,
                margin=dict(l=6, r=6, t=8, b=66),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    x=0.5,
                    xanchor="center",
                    y=-0.10,
                    yanchor="top",
                    font=dict(size=10),
                    itemwidth=30,
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                key=key,
                config={"displayModeBar": False},
            )


def _age_group_hbar(df, col, title, key):
    with st.container(
        key=f"{key}_demographic_chart_card",
        border=True,
    ):
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)

        with st.container(key=f"{key}_chart_viewport"):
            if not col or df is None or df.empty or col not in df.columns:
                st.info("Data tidak tersedia.")
                return

            counts = df[col].dropna().astype(str).value_counts()
            if counts.empty:
                st.info("Data tidak tersedia.")
                return

            total = counts.sum()
            pct = (counts / total * 100).round(1)

            def age_sort_key(label):
                m = re.search(r"(\d+)", str(label))
                if m:
                    return int(m.group(1))
                if "<" in str(label):
                    return 0
                if ">" in str(label):
                    return 999
                return 500

            sorted_indices = sorted(pct.index, key=age_sort_key, reverse=True)
            pct_sorted = pct.reindex(sorted_indices).dropna()
            counts_sorted = counts.reindex(pct_sorted.index).fillna(0).astype(int)
            max_val = max(pct_sorted.values) if not pct_sorted.empty else 100

            # Tinggi grafik tidak diperkecil. Jika kategori bertambah,
            # figure menjadi lebih tinggi dan viewport menampilkan scrollbar.
            chart_h = max(330, 32 * len(pct_sorted) + 60)

            fig = go.Figure(go.Bar(
                x=pct_sorted.values,
                y=pct_sorted.index,
                orientation="h",
                marker=dict(color=RED),
                text=[f"{v:.1f}%" for v in pct_sorted.values],
                textposition="outside",
                customdata=np.array(counts_sorted.values, dtype=int).reshape(-1, 1),
                hovertemplate=(
                    "<b>Kelompok Usia:</b> %{y}<br>"
                    "<b>Persentase:</b> %{x:.1f}%<br>"
                    "<b>Responden:</b> %{customdata[0]} orang<extra></extra>"
                ),
            ))
            fig.update_layout(
                xaxis=dict(range=[0, max(112, max_val + 12)], ticksuffix="%"),
                margin=dict(l=10, r=30, t=10, b=10),
                height=chart_h,
                showlegend=False,
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                key=key,
                config={"displayModeBar": False},
            )


def _motor_type_hbar(df, col, title, key):
    with st.container(
        key=f"{key}_demographic_chart_card",
        border=True,
    ):
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        with st.container(key=f"{key}_chart_viewport"):
            if not col or df is None or df.empty or col not in df.columns:
                st.info("Data tidak tersedia.")
                return

            def motor_series(value):
                raw = str(value).strip()
                norm = re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()
                if re.search(r"\bbeat\b", norm):
                    return "Beat Series"
                if re.search(r"\bpcx\b", norm):
                    return "PCX Series"
                return raw

            counts = df[col].dropna().map(motor_series).value_counts()
            if counts.empty:
                st.info("Data tidak tersedia.")
                return
            total = counts.sum()
            pct = (counts / total * 100).round(1)

            pct_sorted = pct.sort_values(ascending=True)
            counts_sorted = counts.reindex(pct_sorted.index).fillna(0).astype(int)
            max_val = max(pct_sorted.values) if not pct_sorted.empty else 100

            # Grafik tetap proporsional. Jika kategorinya banyak, tinggi figure
            # bertambah dan viewport yang akan menampilkan scrollbar.
            chart_h = max(330, 32 * len(pct_sorted) + 60)
            fig = go.Figure(go.Bar(
                x=pct_sorted.values, y=pct_sorted.index, orientation="h",
                marker=dict(color=RED), text=[f"{v:.1f}%" for v in pct_sorted.values], textposition="outside",
                customdata=np.array(counts_sorted.values, dtype=int).reshape(-1, 1),
                hovertemplate=(
                    "<b>Tipe Motor:</b> %{y}<br>"
                    "<b>Persentase:</b> %{x:.1f}%<br>"
                    "<b>Responden:</b> %{customdata[0]} orang<extra></extra>"
                ),
            ))
            fig.update_layout(
                xaxis=dict(range=[0, max(112, max_val + 15)], ticksuffix="%"),
                margin=dict(l=10, r=30, t=10, b=10),
                height=chart_h, showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True, key=key, config={"displayModeBar": False})


def _simple_hbar(df, col, title, key):
    with st.container(key=f"{key}_scroll_chart_card", border=True):
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        if not col or df is None or df.empty or col not in df.columns:
            st.info("Data tidak tersedia.")
            return
        counts = df[col].dropna().astype(str).value_counts()
        if counts.empty:
            st.info("Data tidak tersedia.")
            return
        total = counts.sum()
        pct = (counts / total * 100).round(0)
        max_val = max(pct.values) if not pct.empty else 100
        fig = go.Figure(go.Bar(
            x=pct.values, y=pct.index, orientation="h",
            marker=dict(color=RED), text=[f"{v:.0f}%" for v in pct.values], textposition="outside",
        ))
        fig.update_layout(
            xaxis=dict(range=[0, max(112, max_val + 12)], ticksuffix="%"),
            margin=dict(l=10, r=30, t=10, b=10),
            height=240, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, key=key)


def _stacked_pct(df, col, title, key, is_ses=False, is_retention=False):
    with st.container(key=f"{key}_fixed_chart_card", border=True):
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        if not col or df is None or df.empty or col not in df.columns:
            st.info("Data tidak tersedia.")
            return
        counts = df[col].dropna().astype(str).value_counts()
        if counts.empty:
            st.info("Data tidak tersedia.")
            return
        total = counts.sum()
        pct = (counts / total * 100).round(0)
        palette = [RED, ORANGE, YELLOW, GREEN, "#1E88E5", "#8E24AA", "#D81B60"]
        fig = go.Figure()
        ses_ranges = {
            "A": "> 6 Juta", "A1": "> 6 Juta", "A2": "4 – 6 Juta",
            "B": "2,5 – 4 Juta", "C1": "1,75 – 2,5 Juta",
            "C2": "1,25 – 1,75 Juta", "D": "0,9 – 1,25 Juta",
            "E": "≤ 0,9 Juta",
        }
        retention_labels = {
            5: "Sangat mungkin membeli kembali",
            4: "Mungkin membeli kembali",
            3: "Cukup mungkin membeli kembali",
            2: "Kurang mungkin membeli kembali",
            1: "Sangat tidak mungkin membeli kembali",
        }
        # Gunakan tone warna utama dashboard agar chart Retention menyatu
        # dengan seluruh visual H1, H2, dan H3.
        retention_colors = {
            5: GREEN,
            4: YELLOW,
            3: ORANGE,
            2: RED,
            1: "#C8102E",  # merah tua dari colorway dashboard
        }

        def retention_score(value):
            text = str(value).strip().lower()
            numeric = pd.to_numeric(text.replace(",", "."), errors="coerce")
            if pd.notna(numeric) and 1 <= int(round(float(numeric))) <= 5:
                return int(round(float(numeric)))
            if "sangat mungkin" in text:
                return 5
            if "cukup" in text:
                return 3
            if "sangat tidak" in text or "tidak mungkin" in text:
                return 1
            if "kurang" in text:
                return 2
            if "mungkin" in text:
                return 4
            return None

        # Normalisasi dahulu sebelum menghitung persentase. Nilai mentah seperti
        # 4, 4.0, "4 ", dan "Mungkin membeli kembali" harus menjadi satu
        # kategori yang sama, bukan beberapa segmen dengan label 4.
        if is_retention:
            normalized_retention = (
                df[col]
                .dropna()
                .map(retention_score)
                .dropna()
                .astype(int)
            )
            if normalized_retention.empty:
                st.info("Data tidak tersedia.")
                return
            counts = normalized_retention.value_counts()
            total = counts.sum()
            pct = (counts / total * 100).round(0)

        items = list(pct.items())
        if is_retention:
            items = sorted(items, key=lambda item: retention_score(item[0]) or 0, reverse=True)

        ses_color_map = {}
        for i, (label, v) in enumerate(items):
            label_text = str(label).strip()
            range_text = ses_ranges.get(label_text.upper(), "Rentang tidak tersedia")
            respondents = int(counts.get(label, 0))
            score = retention_score(label) if is_retention else None
            display_label = str(score) if score else label_text
            bar_color = retention_colors.get(score, palette[i % len(palette)])
            if is_ses:
                ses_color_map[label_text.upper()] = bar_color
            if is_ses:
                segment_hover = (
                    f"<b>{label_text}: %{{customdata[0]}}</b><br>"
                    "Persentase: %{x:.1f}%<br>"
                    "Responden: %{customdata[1]} orang<extra></extra>"
                )
            elif is_retention:
                segment_hover = (
                    f"<b>{display_label}: {retention_labels.get(score, label_text)}</b><br>"
                    "Persentase: %{x:.1f}%<br>"
                    "Responden: %{customdata[1]} orang<extra></extra>"
                )
            else:
                segment_hover = (
                    f"<b>{label_text}</b><br>"
                    "Persentase: %{x:.1f}%<br>"
                    "Responden: %{customdata[1]} orang<extra></extra>"
                )
            fig.add_trace(go.Bar(x=[v], y=[""], orientation="h", name=str(label),
                                  marker=dict(color=bar_color),
                                  text=f"{v:.0f}%<br>{display_label}", textposition="inside",
                                  customdata=[[range_text, respondents]],
                                  hovertemplate=segment_hover))
        fig.update_layout(barmode="stack", showlegend=False, height=110,
                           margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig, use_container_width=True, key=key)
        if is_ses:
            available_levels = [str(x).strip().upper() for x in counts.index]
            legend_items = []
            for level in ["A", "A1", "A2", "B", "C1", "C2", "D", "E"]:
                if level in available_levels and level in ses_ranges:
                    box_color = ses_color_map.get(level, "#D0D5DD")
                    legend_items.append(
                        '<span style="display:inline-flex;align-items:center;gap:5px;'
                        'white-space:nowrap;margin:2px 14px 2px 0;">'
                        f'<span style="display:inline-block;width:10px;height:10px;'
                        f'border-radius:1px;background:{box_color};flex:0 0 10px;"></span>'
                        f'<span><b>{level}</b>: {ses_ranges[level]}</span></span>'
                    )
            if legend_items:
                st.markdown(
                    '<div style="display:flex;flex-wrap:wrap;align-items:center;'
                    'font-size:10.5px;line-height:1.45;color:#667085;'
                    'padding:0 4px 4px;">' + "".join(legend_items) + "</div>",
                    unsafe_allow_html=True,
                )


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


def _top_reasons_hbar(df, col, title, key, top_n=5, separator=";"):
    """Top 5 alasan NPS dengan label dua baris dan angka yang tidak terpotong."""

    with st.container(key=f"{key}_demographic_chart_card", border=True):
        st.markdown(
            f'<div class="chart-title">{title}</div>',
            unsafe_allow_html=True,
        )

        with st.container(key=f"{key}_chart_viewport"):

            if (
                not col
                or df is None
                or df.empty
                or col not in df.columns
            ):
                st.info("Data tidak tersedia.")
                return

            # ====================================================
            # NORMALISASI ALASAN
            # ====================================================

            reason_labels = {}
            normalized_reasons = []

            for raw_value in df[col].dropna():
                for raw_reason in str(raw_value).split(separator):

                    clean_reason = re.sub(
                        r"\s+",
                        " ",
                        raw_reason
                    ).strip(" ;,.-")

                    if (
                        not clean_reason
                        or clean_reason.lower() in {"nan", "none", "-"}
                    ):
                        continue

                    normalized_reason = clean_reason.casefold()
                    reason_labels.setdefault(
                        normalized_reason,
                        clean_reason
                    )
                    normalized_reasons.append(
                        normalized_reason
                    )

            if not normalized_reasons:
                st.info("Data tidak tersedia.")
                return

            counts = (
                pd.Series(normalized_reasons)
                .value_counts()
                .head(top_n)
            )

            labels = [
                reason_labels[index]
                for index in counts.index
            ]

            total_respondents = max(
                int(df[col].notna().sum()),
                1
            )

            percentages = (
                counts
                / total_respondents
                * 100
            ).round(1)

            # Balik agar item terbesar berada paling atas pada bar horizontal.
            labels = labels[::-1]
            count_values = counts.to_numpy(dtype=int)[::-1]
            percentage_values = percentages.to_numpy(dtype=float)[::-1]

            # ====================================================
            # WRAP LABEL MAKSIMAL 2 BARIS
            # ====================================================

            def wrap_reason_label(label, width=23):
                label = re.sub(
                    r"\s+",
                    " ",
                    str(label)
                ).strip()

                lines = textwrap.wrap(
                    label,
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )

                if len(lines) <= 2:
                    return "<br>".join(lines)

                second_line = " ".join(lines[1:])

                if len(second_line) > width + 5:
                    second_line = (
                        second_line[:width + 2]
                        .rstrip()
                        + "…"
                    )

                return lines[0] + "<br>" + second_line

            wrapped_labels = [
                wrap_reason_label(label)
                for label in labels
            ]

            max_count = (
                int(max(count_values))
                if len(count_values)
                else 1
            )

            # Lebar area plot dipertahankan seperti versi sebelumnya.
            # Ruang ekstra di sisi kanan hanya dipakai untuk kolom angka.
            x_limit = max(
                1.6,
                max_count * 1.34
            )

            # Kolom angka dibuat pada posisi tetap di sebelah kanan bar terpanjang.
            # Dengan cara ini angka tidak akan terpotong meskipun chart berada
            # dalam kolom yang sempit.
            label_x = max_count * 1.03

            chart_height = max(
                315,
                54 * len(labels) + 65
            )

            # ====================================================
            # BAR CHART
            # ====================================================

            fig = go.Figure(
                go.Bar(
                    x=count_values,
                    y=wrapped_labels,
                    orientation="h",
                    marker=dict(color=ORANGE),

                    # Angka tidak lagi memakai text di dalam trace agar
                    # tidak dipotong oleh batas area Plotly.
                    text=None,

                    customdata=np.column_stack([
                        labels,
                        percentage_values,
                    ]),

                    hovertemplate=(
                        "<b>Alasan:</b> %{customdata[0]}<br>"
                        "<b>Frekuensi dipilih:</b> %{x} kali<br>"
                        "<b>Persentase responden:</b> "
                        "%{customdata[1]:.1f}%"
                        "<extra></extra>"
                    ),
                )
            )

            # Persentase dibuat sebagai annotation sehingga selalu terbaca.
            for y_label, pct in zip(
                wrapped_labels,
                percentage_values
            ):
                fig.add_annotation(
                    x=label_x,
                    y=y_label,
                    text=f"{pct:.1f}%",
                    showarrow=False,
                    xanchor="left",
                    yanchor="middle",
                    font=dict(
                        size=10.5,
                        color="#667085",
                    ),
                    align="left",
                )

            # Sumbu X dibuat sangat ringkas karena chart berada di kolom sempit.
            # Hanya tampilkan nilai awal dan nilai maksimum agar tidak menumpuk.
            tickvals = [0, max_count] if max_count > 0 else [0]

            fig.update_layout(
                xaxis=dict(
                    range=[0, x_limit],
                    title=dict(
                        text="Frekuensi Dipilih",
                        font=dict(size=11),
                        standoff=8,
                    ),
                    tickmode="array",
                    tickvals=tickvals,
                    ticktext=[str(v) for v in tickvals],
                    tickfont=dict(size=9),
                    tickangle=0,
                    automargin=True,
                    fixedrange=True,
                    showgrid=False,
                    zeroline=False,
                ),

                yaxis=dict(
                    automargin=True,
                    tickfont=dict(size=10.5),
                    fixedrange=True,
                ),

                # Margin dipertahankan compact sehingga lebar bagan bagian
                # dalam tetap seperti screenshot yang diinginkan.
                margin=dict(
                    l=18,
                    r=18,
                    t=8,
                    b=42,
                ),

                height=chart_height,
                showlegend=False,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                key=key,
                config={
                    "displayModeBar": False,
                    "responsive": True,
                },
            )

def render_nps_gauge(value, title, key):
    with st.container(key=f"{key}_nps_chart_card", border=True):
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        if value is None:
            st.info("Data tidak tersedia.")
            return

        val_clamped = max(0.0, min(100.0, float(value)))
        label = "Sangat Baik" if val_clamped >= 85 else ("Baik" if val_clamped >= 70 else ("Cukup" if val_clamped >= 50 else "Kurang"))

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=val_clamped,
            number=dict(suffix="", font=dict(size=30, color="#212121")),
            gauge=dict(
                axis=dict(range=[0, 100], tickwidth=1, tickcolor="#666"),
                bar=dict(color="#212121", thickness=0.25),
                threshold=dict(
                    line=dict(color="#000000", width=4),
                    thickness=0.8,
                    value=val_clamped
                ),
                steps=[
                    dict(range=[0, 50], color=RED),
                    dict(range=[50, 70], color=ORANGE),
                    dict(range=[70, 85], color=YELLOW),
                    dict(range=[85, 100], color=GREEN),
                ],
            ),
        ))
        fig.update_layout(margin=dict(l=15, r=15, t=10, b=10), height=250)
        st.plotly_chart(fig, use_container_width=True, key=key)
        st.caption(f"Status NPS: {label} ({val_clamped:.1f})")


def render_overall_profile_insight(
    df_filtered, df_prof, cols, selected_profile, unit, key_prefix,
    profile_meta_df=None,
):
    """Ringkasan singkat profil pelanggan aktif yang lebih management-friendly."""

    if df_prof is None or df_prof.empty:
        st.info("Ringkasan profil belum tersedia karena tidak ada responden pada filter ini.")
        return

    def dominant(column, transform=None):
        if not column or column not in df_prof.columns:
            return None

        values = df_prof[column].dropna()

        if transform is not None:
            values = values.map(transform)

        values = values.astype(str).str.strip()
        values = values[~values.str.lower().isin(["", "nan", "none", "-"])]

        if values.empty:
            return None

        counts = values.value_counts()
        label = str(counts.index[0])
        count = int(counts.iloc[0])
        pct = count / len(values) * 100
        return label, count, pct

    def short_label(value, max_length=58):
        value = re.sub(r"\s+", " ", str(value)).strip()
        return value if len(value) <= max_length else value[:max_length - 1].rstrip() + "…"

    def retention_text(value):
        text = str(value).strip()
        numeric = pd.to_numeric(text.replace(",", "."), errors="coerce")

        labels = {
            5: "sangat mungkin membeli kembali",
            4: "mungkin membeli kembali",
            3: "cukup mungkin membeli kembali",
            2: "kurang mungkin membeli kembali",
            1: "sangat tidak mungkin membeli kembali",
        }

        if pd.notna(numeric):
            score = int(round(float(numeric)))
            if score in labels:
                return labels[score]

        return text.lower() if text else text

    def motor_group(value):
        raw = str(value).strip()
        norm = re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()

        if re.search(r"\bbeat\b", norm):
            return "Beat Series"

        if re.search(r"\bpcx\b", norm):
            return "PCX Series"

        return raw

    def nps_value(column):
        if not column or column not in df_prof.columns:
            return None
        return compute_nps(df_prof[column])

    ses_ranges = {
        "A": "> Rp6 juta",
        "A1": "> Rp6 juta",
        "A2": "Rp4–6 juta",
        "B": "Rp2,5–4 juta",
        "C1": "Rp1,75–2,5 juta",
        "C2": "Rp1,25–1,75 juta",
        "D": "Rp0,9–1,25 juta",
        "E": "≤ Rp0,9 juta",
    }

    total_filtered = len(df_filtered) if df_filtered is not None else 0
    profile_count = len(df_prof)
    profile_pct = profile_count / total_filtered * 100 if total_filtered else 0

    profile_number = str(selected_profile or "").replace("P", "").strip()
    profile_name = f"Profil {profile_number}"

    if profile_meta_df is not None and not profile_meta_df.empty:
        meta_profile_col = find_col(
            profile_meta_df,
            ["Profile", "Profil", "Code", "No"]
        )

        meta_name_col = find_col(
            profile_meta_df,
            ["Profile Name", "Nama Profil", "Profile_Name", "nama", "name"]
        )

        if meta_profile_col and meta_name_col:
            for _, meta_row in profile_meta_df[
                [meta_profile_col, meta_name_col]
            ].iterrows():

                raw_code = str(meta_row[meta_profile_col]).strip()
                code_match = re.search(r"(\d+)", raw_code)

                if not code_match or code_match.group(1) != profile_number:
                    continue

                raw_name = str(meta_row[meta_name_col]).strip()

                if raw_name and raw_name.lower() not in {"nan", "none", "-"}:
                    profile_name = raw_name
                    break

    gender = dominant(cols.get("gender"))
    age = dominant(cols.get("age"))
    motor = dominant(cols.get("motor_type"), motor_group)
    ses = dominant(cols.get("ses"))

    sentence_1 = (
        f"<b>Profil {profile_number} – {html.escape(profile_name)}</b> "
        f"mencakup <b>{profile_pct:.1f}%</b> dari total pelanggan "
        f"pada filter yang dipilih."
    )

    demographic_parts = []

    if gender:
        demographic_parts.append(
            f"{short_label(gender[0]).lower()} ({gender[2]:.1f}%)"
        )

    if age:
        demographic_parts.append(
            f"kelompok usia {short_label(age[0])} ({age[2]:.1f}%)"
        )

    if motor:
        demographic_parts.append(
            f"pengguna {short_label(motor[0])} ({motor[2]:.1f}%)"
        )

    sentence_2 = ""

    if demographic_parts:
        if len(demographic_parts) == 1:
            demo_text = demographic_parts[0]
        elif len(demographic_parts) == 2:
            demo_text = " dan ".join(demographic_parts)
        else:
            demo_text = ", ".join(demographic_parts[:-1]) + ", dan " + demographic_parts[-1]

        sentence_2 = (
            "Profil ini didominasi oleh "
            + html.escape(demo_text)
            + "."
        )

    behavior_parts = []

    if ses:
        ses_code = short_label(ses[0]).upper().strip()
        ses_range = ses_ranges.get(ses_code)

        if ses_range:
            behavior_parts.append(
                f"SES {ses_code} ({ses_range}) sebesar {ses[2]:.1f}%"
            )
        else:
            behavior_parts.append(
                f"SES {ses_code} sebesar {ses[2]:.1f}%"
            )

    if unit == "sales":
        payment = dominant(cols.get("payment"))
        showroom = dominant(_find_exact_data_col(df_prof, "Showroom"))

        if payment:
            behavior_parts.append(
                f"menggunakan pembayaran {short_label(payment[0]).lower()} "
                f"({payment[2]:.1f}%)"
            )

        if showroom:
            behavior_parts.append(
                f"memilih {short_label(showroom[0])} sebagai lokasi "
                f"pembelian berikutnya ({showroom[2]:.1f}%)"
            )

    elif unit == "service":
        frequency = dominant(
            _find_exact_data_col(
                df_prof,
                "Frequency Visit to AHASS"
            )
        )

        if frequency:
            behavior_parts.append(
                f"memiliki pola kunjungan AHASS "
                f"{short_label(frequency[0]).lower()} "
                f"({frequency[2]:.1f}%)"
            )

    else:
        future_part = dominant(
            _find_exact_data_col(
                df_prof,
                "Future Purchase Part"
            )
        )

        if future_part:
            behavior_parts.append(
                f"memilih {short_label(future_part[0])} "
                f"untuk pembelian part berikutnya "
                f"({future_part[2]:.1f}%)"
            )

    sentence_3 = ""

    if behavior_parts:
        if len(behavior_parts) == 1:
            behavior_text = behavior_parts[0]
        elif len(behavior_parts) == 2:
            behavior_text = " dan ".join(behavior_parts)
        else:
            behavior_text = ", ".join(behavior_parts[:-1]) + ", dan " + behavior_parts[-1]

        sentence_3 = (
            "Dari sisi ekonomi dan perilaku, mayoritas pelanggan berada pada "
            + html.escape(behavior_text)
            + "."
        )

    # RETENSI DIPISAH MENJADI KALIMAT TERSENDIRI
    retention_parts = []

    if unit == "sales":
        retention = dominant(
            cols.get("retention"),
            retention_text
        )

        if retention:
            retention_parts.append(
                f"<b>{html.escape(short_label(retention[0]))}</b> "
                f"sebesar <b>{retention[2]:.1f}%</b>"
            )

    elif unit == "service":
        retention_unit = dominant(
            _find_exact_data_col(
                df_prof,
                "Retention Unit"
            ),
            retention_text
        )

        retention_service = dominant(
            _find_exact_data_col(
                df_prof,
                "Retention Service"
            ),
            retention_text
        )

        if retention_unit:
            retention_parts.append(
                f"untuk pembelian unit, <b>{html.escape(short_label(retention_unit[0]))}</b> "
                f"sebesar <b>{retention_unit[2]:.1f}%</b>"
            )

        if retention_service:
            retention_parts.append(
                f"untuk layanan AHASS, <b>{html.escape(short_label(retention_service[0]))}</b> "
                f"sebesar <b>{retention_service[2]:.1f}%</b>"
            )

    else:
        retention_unit = dominant(
            _find_exact_data_col(
                df_prof,
                "Retention Unit"
            ),
            retention_text
        )

        retention_part = dominant(
            _find_exact_data_col(
                df_prof,
                "Retention Part"
            ),
            retention_text
        )

        if retention_unit:
            retention_parts.append(
                f"untuk pembelian unit, <b>{html.escape(short_label(retention_unit[0]))}</b> "
                f"sebesar <b>{retention_unit[2]:.1f}%</b>"
            )

        if retention_part:
            retention_parts.append(
                f"untuk pembelian part, <b>{html.escape(short_label(retention_part[0]))}</b> "
                f"sebesar <b>{retention_part[2]:.1f}%</b>"
            )

    sentence_4 = ""

    if retention_parts:
        retention_text_summary = (
            retention_parts[0]
            if len(retention_parts) == 1
            else " dan ".join(retention_parts)
        )

        sentence_4 = (
            "Dari sisi retensi, mayoritas pelanggan menunjukkan kecenderungan "
            "untuk kembali menggunakan produk atau layanan Honda; "
            + retention_text_summary
            + "."
        )

    nps_unit_score = nps_value(cols.get("nps_unit"))
    nps_dealer_score = nps_value(cols.get("nps_dealer"))

    nps_parts = []

    if nps_unit_score is not None:
        nps_parts.append(
            f"NPS Unit <b>{nps_unit_score:.1f}</b>"
        )

    if nps_dealer_score is not None:
        if unit == "sales":
            nps_label = "NPS Dealer"
        elif unit == "service":
            nps_label = "NPS AHASS"
        else:
            nps_label = "NPS Part"

        nps_parts.append(
            f"{nps_label} <b>{nps_dealer_score:.1f}</b>"
        )

    sentence_5 = ""

    if nps_parts:
        valid_scores = [
            score
            for score in [nps_unit_score, nps_dealer_score]
            if score is not None
        ]

        avg_nps = np.mean(valid_scores) if valid_scores else None

        if avg_nps is not None:
            if avg_nps >= 85:
                loyalty_label = "sangat baik"
            elif avg_nps >= 70:
                loyalty_label = "baik"
            elif avg_nps >= 50:
                loyalty_label = "cukup baik"
            else:
                loyalty_label = "masih perlu diperkuat"

            sentence_5 = (
                "Nilai "
                + " dan ".join(nps_parts)
                + " menunjukkan tingkat loyalitas pelanggan yang "
                f"<b>{loyalty_label}</b>."
            )

    narrative = " ".join(
        part
        for part in [
            sentence_1,
            sentence_2,
            sentence_3,
            sentence_4,
            sentence_5,
        ]
        if part
    )

    summary_html = (
        '<div style="'
        'width:100%;'
        'box-sizing:border-box;'
        'margin:14px 0 4px;'
        'padding:14px 16px;'
        'background:linear-gradient(135deg,#FFF7F2,#FFFFFF);'
        'border:1px solid #FFD7BF;'
        'border-left:4px solid #FF6B00;'
        'border-radius:10px;'
        'color:#3F3F46;'
        'font-size:13px;'
        'line-height:1.65;'
        '">'
        '<div style="'
        'font-size:11px;'
        'font-weight:800;'
        'letter-spacing:.5px;'
        'color:#C8102E;'
        'text-transform:uppercase;'
        'margin-bottom:5px;'
        '">Ringkasan Profil</div>'
        f'<div>{narrative}</div>'
        '</div>'
    )

    st.markdown(
        summary_html,
        unsafe_allow_html=True,
    )

def render_demographic_charts(
    df_filtered, cols, dealer_label, key_prefix,
    selected_profile=None, unit_key=None,
):
    df_prof = df_filtered
    profile_col = cols.get("profile") if cols else None
    if selected_profile and profile_col and df_filtered is not None and not df_filtered.empty and profile_col in df_filtered.columns:
        p_num = str(selected_profile).replace("P", "").strip()
        matched = df_filtered[
            df_filtered[profile_col].astype(str).str.contains(rf"\b{p_num}\b", case=False, na=False) |
            df_filtered[profile_col].astype(str).str.contains(selected_profile, case=False, na=False)
        ]
        if not matched.empty:
            df_prof = matched

    unit = str(unit_key or key_prefix).strip().lower()

    # H1 mempunyai data Payment, sehingga baris demografi dibuat 4 kolom.
    # H2 dan H3 tetap 3 kolom karena tidak mempunyai chart Payment.
    demographic_columns = st.columns(4 if unit == "sales" else 3, gap="small")
    with demographic_columns[0]:
        _simple_pie(df_prof, cols.get("gender"), "Number of Respondents by Gender",
                    key=f"{key_prefix}_gender", colors=[RED, ORANGE])
    with demographic_columns[1]:
        _age_group_hbar(df_prof, cols.get("age"), "Number of Respondents by Age", key=f"{key_prefix}_age")
    with demographic_columns[2]:
        _motor_type_hbar(df_prof, cols.get("motor_type"), "Motor Type", key=f"{key_prefix}_motor")
    if unit == "sales":
        with demographic_columns[3]:
            _simple_pie(
                df_prof, cols.get("payment"), "Payment Type Distribution",
                key=f"{key_prefix}_payment",
                colors=[RED, ORANGE, YELLOW, GREEN, "#1E88E5"],
            )

    nps_col = cols.get("nps")
    nps_unit_col = cols.get("nps_unit")
    nps_dealer_col = cols.get("nps_dealer")

    def nps_value(column):
        if not column or df_prof is None or column not in df_prof.columns:
            return None
        return compute_nps(df_prof[column])

    if unit == "sales":
        # Baris SES dan Retention lama tetap dipertahankan.
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            _stacked_pct(
                df_prof, cols.get("ses"), "SES",
                key=f"{key_prefix}_ses", is_ses=True,
            )
        with r2c2:
            _stacked_pct(
                df_prof, cols.get("retention"), "Retention",
                key=f"{key_prefix}_retention", is_retention=True,
            )

        # Grafik tambahan Sales: Period berada di bawah SES dan Showroom
        # berada tepat di sisi kanannya.
        period_col = _find_exact_data_col(df_prof, "Period")
        showroom_col = _find_exact_data_col(df_prof, "Showroom")
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            _stacked_pct(
                df_prof, period_col, "Next Purchase Period",
                key=f"{key_prefix}_purchase_period",
            )
        with r3c2:
            _stacked_pct(
                df_prof, showroom_col, "Next Purchase Location",
                key=f"{key_prefix}_showroom",
            )

        # Baris paling bawah dibuat compact dalam 4 kolom:
        # NPS Unit | Reason Unit | NPS Dealer | Reason Dealer.
        r4c1, r4c2, r4c3, r4c4 = st.columns(4, gap="small")
        reason_unit_col = _find_exact_data_col(df_prof, "Reasons_Unit")
        reason_dealer_col = _find_exact_data_col(df_prof, "Reasons_Dealer")
        with r4c1:
            render_nps_gauge(
                nps_value(nps_unit_col), "NPS Unit",
                key=f"{key_prefix}_nps_unit",
            )
        with r4c2:
            _top_reasons_hbar(
                df_prof, reason_unit_col, "Top 5 Reason NPS Unit",
                key=f"{key_prefix}_reason_unit",
            )
        with r4c3:
            render_nps_gauge(
                nps_value(nps_dealer_col), "NPS Dealer",
                key=f"{key_prefix}_nps_dealer",
            )
        with r4c4:
            _top_reasons_hbar(
                df_prof, reason_dealer_col, "Top 5 Reason NPS Dealer",
                key=f"{key_prefix}_reason_dealer",
            )

    elif unit == "service":
        frequency_col = _find_exact_data_col(df_prof, "Frequency Visit to AHASS")
        retention_unit_col = _find_exact_data_col(df_prof, "Retention Unit")
        retention_service_col = _find_exact_data_col(df_prof, "Retention Service")

        # Frequency Visit to AHASS ditempatkan di sisi kanan SES.
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            _stacked_pct(
                df_prof, cols.get("ses"), "SES",
                key=f"{key_prefix}_ses", is_ses=True,
            )
        with r2c2:
            _stacked_pct(
                df_prof, frequency_col, "Frequency Visit to AHASS",
                key=f"{key_prefix}_frequency_ahass",
            )

        # Kedua jenis retention ditampilkan bersampingan pada baris berikutnya.
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            _stacked_pct(
                df_prof, retention_unit_col, "Retention Unit",
                key=f"{key_prefix}_retention_unit", is_retention=True,
            )
        with r3c2:
            _stacked_pct(
                df_prof, retention_service_col, "Retention Service",
                key=f"{key_prefix}_retention_service", is_retention=True,
            )

        # NPS dan alasannya berada dalam satu baris 4 kolom.
        reason_unit_col = _find_exact_data_col(df_prof, "Reasons NPS.1")
        reason_ahass_col = _find_exact_data_col(df_prof, "Reasons NPS")
        r4c1, r4c2, r4c3, r4c4 = st.columns(4, gap="small")
        with r4c1:
            render_nps_gauge(
                nps_value(nps_unit_col), "NPS Unit",
                key=f"{key_prefix}_nps_unit",
            )
        with r4c2:
            _top_reasons_hbar(
                df_prof, reason_unit_col, "Top 5 Reason NPS Unit",
                key=f"{key_prefix}_reason_unit",
            )
        with r4c3:
            render_nps_gauge(
                nps_value(nps_dealer_col), "NPS AHASS",
                key=f"{key_prefix}_nps_dealer",
            )
        with r4c4:
            _top_reasons_hbar(
                df_prof, reason_ahass_col, "Top 5 Reason NPS AHASS",
                key=f"{key_prefix}_reason_ahass",
            )

    else:
        future_purchase_col = _find_exact_data_col(df_prof, "Future Purchase Part")
        retention_unit_col = _find_exact_data_col(df_prof, "Retention Unit")
        retention_part_col = _find_exact_data_col(df_prof, "Retention Part")

        # Future Purchase Part ditempatkan di sisi kanan SES.
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            _stacked_pct(
                df_prof, cols.get("ses"), "SES",
                key=f"{key_prefix}_ses", is_ses=True,
            )
        with r2c2:
            _stacked_pct(
                df_prof, future_purchase_col, "Future Purchase Part Location",
                key=f"{key_prefix}_future_purchase_part",
            )

        # Retention Unit dan Retention Parts berada pada satu baris.
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            _stacked_pct(
                df_prof, retention_unit_col, "Retention Unit",
                key=f"{key_prefix}_retention_unit", is_retention=True,
            )
        with r3c2:
            _stacked_pct(
                df_prof, retention_part_col, "Retention Parts",
                key=f"{key_prefix}_retention_parts", is_retention=True,
            )

        # NPS dan alasannya berada dalam satu baris 4 kolom.
        reason_unit_col = _find_exact_data_col(df_prof, "Reasons NPS.1")
        reason_parts_col = _find_exact_data_col(df_prof, "Reasons NPS")
        r4c1, r4c2, r4c3, r4c4 = st.columns(4, gap="small")
        with r4c1:
            render_nps_gauge(
                nps_value(nps_unit_col), "NPS Unit",
                key=f"{key_prefix}_nps_unit",
            )
        with r4c2:
            _top_reasons_hbar(
                df_prof, reason_unit_col, "Top 5 Reason NPS Unit",
                key=f"{key_prefix}_reason_unit",
            )
        with r4c3:
            render_nps_gauge(
                nps_value(nps_dealer_col), "NPS Part",
                key=f"{key_prefix}_nps_dealer",
            )
        with r4c4:
            _top_reasons_hbar(
                df_prof, reason_parts_col, "Top 5 Reason NPS Parts",
                key=f"{key_prefix}_reason_parts",
            )



def render_top_bottom_dealer_satisfaction(
    df_profile,
    cols,
    indicator_cols,
    unit_key,
    key_prefix,
    filters=None,
):
    """
    Menampilkan Top 5 dan Bottom 5 dealer/unit berdasarkan Satisfaction
    untuk filter + customer profile yang sedang aktif.

    Satisfaction dihitung konsisten dengan dashboard:
    rata-rata skor indikator / 5 * 100%.

    Ranking hanya ditampilkan ketika filter Kabupaten/Kota = Semua.
    Data dihitung langsung dari dataframe aktif, sehingga daftar Top/Bottom 5
    otomatis menyesuaikan saat sumber data atau filter lain berubah.
    """

    # Ranking Top 5 / Bottom 5 hanya berlaku sampai level Karesidenan.
    # Jika pengguna sudah memilih Kab/Kota atau Dealer tertentu,
    # ranking tidak ditampilkan karena scope sudah terlalu spesifik.
    if filters is not None:
        kab_selected = filters.get("kab_kota") not in (None, "Semua", "")
        dealer_selected = filters.get("dealer") not in (None, "Semua", "")

        if kab_selected or dealer_selected:
            return

    if df_profile is None or df_profile.empty:
        st.info("Data dealer tidak tersedia untuk profil yang dipilih.")
        return

    dealer_code_col = cols.get("dealer_code") if cols else None

    if not dealer_code_col or dealer_code_col not in df_profile.columns:
        st.info("Kolom kode dealer tidak ditemukan.")
        return

    # Deteksi nama unit sesuai H1/H2/H3
    unit = str(unit_key).strip().lower()

    if unit == "sales":
        dealer_name_col = find_col(
            df_profile,
            ["Dealer Name", "Name of Dealer", "Nama Dealer", "Dealer"]
        )
        entity_label = "Dealer"

    elif unit == "service":
        dealer_name_col = find_col(
            df_profile,
            ["AHASS Name", "Name of AHASS", "Nama AHASS", "AHASS"]
        )
        entity_label = "AHASS"

    else:
        dealer_name_col = find_col(
            df_profile,
            [
                "Parts Shop Name", "Part Shop Name", "Name of Parts Shop",
                "Nama Parts Shop", "Parts Shop", "Part Shop"
            ]
        )
        entity_label = "Part Shop"

    # Gunakan hanya indikator yang memang masuk perhitungan dashboard
    valid_indicators = [
        col for col in indicator_cols
        if col in df_profile.columns
    ]

    if not valid_indicators:
        st.info("Indikator satisfaction tidak tersedia.")
        return

    df_rank = df_profile.copy()

    numeric_indicator = df_rank[valid_indicators].apply(
        pd.to_numeric,
        errors="coerce"
    )

    # Satisfaction per responden dalam persen
    df_rank["_satisfaction_pct"] = (
        numeric_indicator.mean(axis=1) / 5 * 100
    )

    # Label display: Nama Unit (Kode)
    if dealer_name_col and dealer_name_col in df_rank.columns:
        df_rank["_dealer_name"] = (
            df_rank[dealer_name_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        df_rank["_dealer_code"] = (
            df_rank[dealer_code_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        df_rank["_dealer_name"] = (
            df_rank[dealer_code_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        df_rank["_dealer_code"] = df_rank["_dealer_name"]

    df_rank = df_rank[df_rank["_dealer_code"].ne("")].copy()

    if df_rank.empty:
        st.info("Data dealer tidak tersedia.")
        return

    dealer_summary = (
        df_rank
        .groupby(["_dealer_code", "_dealer_name"], dropna=False)
        .agg(
            Satisfaction=("_satisfaction_pct", "mean"),
            Jumlah_Responden=("_satisfaction_pct", "count"),
        )
        .reset_index()
    )

    dealer_summary = dealer_summary[
        dealer_summary["Satisfaction"].notna()
    ].copy()

    if dealer_summary.empty:
        st.info("Nilai satisfaction dealer tidak tersedia.")
        return

    def make_dealer_label(row):
        name = str(row["_dealer_name"]).strip()
        code = str(row["_dealer_code"]).strip()

        if not name or name.lower() in {"nan", "none"}:
            return code
        if name == code:
            return name
        return f"{name} ({code})"

    dealer_summary["Dealer_Label"] = dealer_summary.apply(
        make_dealer_label,
        axis=1
    )

    top_5 = (
        dealer_summary
        .sort_values(
            ["Satisfaction", "Jumlah_Responden"],
            ascending=[False, False]
        )
        .head(5)
        .reset_index(drop=True)
    )

    bottom_5 = (
        dealer_summary
        .sort_values(
            ["Satisfaction", "Jumlah_Responden"],
            ascending=[True, False]
        )
        .head(5)
        .reset_index(drop=True)
    )

    # Style mengikuti palette dashboard saat ini: merah, orange, putih
    st.markdown(
        """
        <style>
        .dealer-ranking-card {
        background: #FFFFFF !important;

       /* Outline masing-masing card dibuat terlihat */
        border: 1.5px solid #D9DDE3 !important;

        border-radius: 12px !important;

        padding: 0 !important;

        overflow: hidden !important;

        box-shadow:
            0 2px 7px rgba(38, 38, 38, 0.07) !important;
        margin: 0 !important;
    }

        .dealer-ranking-title {
            padding: 14px 16px;
            font-size: 12px;
            font-weight: 800;
            color: #262626;
            border-bottom: 1px solid #F0F1F3;
            background: #FFFFFF;
        }

        .dealer-ranking-title-high {
            border-left: 4px solid #FF6B00;
        }

        .dealer-ranking-title-low {
            border-left: 4px solid #E60012;
        }

        .dealer-ranking-row {
            min-height: 42px;
            display: grid;
            grid-template-columns: 34px minmax(0, 1fr) auto;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            border-bottom: 1px dashed #E7E9EC;
        }

        .dealer-ranking-row:last-child {
            border-bottom: none;
        }

        .dealer-rank {
            font-size: 11.5px;
            font-weight: 800;
            color: #C8102E;
        }

        .dealer-rank {
            font-size: 11.5px;
            font-weight: 800;
            color: #D75B00;
        }

        .dealer-rank-low {
            color: #C8102E;
        }

        .dealer-ranking-value {
            font-size: 12px;
            font-weight: 800;
            color: #D75B00;
            white-space: nowrap;
        }

        .dealer-ranking-value-low {
            color: #C8102E;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    def build_ranking_html(data, lowest=False):
        rows = []

        for i, row in data.iterrows():
            rank_class = (
                "dealer-rank dealer-rank-low"
                if lowest else "dealer-rank"
            )
            value_class = (
                "dealer-ranking-value dealer-ranking-value-low"
                if lowest else "dealer-ranking-value"
            )

            dealer_text = html.escape(str(row["Dealer_Label"]))
            satisfaction = float(row["Satisfaction"])

            rows.append(
                f'<div class="dealer-ranking-row">'
                f'<div class="{rank_class}">#{i + 1}</div>'
                f'<div class="dealer-ranking-name" title="{dealer_text}">{dealer_text}</div>'
                f'<div class="{value_class}">{satisfaction:.1f}%</div>'
                f'</div>'
            )

        return "".join(rows)

    c_high, c_low = st.columns(2, gap="small")
    with c_high:
        top_html = build_ranking_html(top_5, lowest=False)
        st.html(
            f'<div class="dealer-ranking-card">'
            f'<div class="dealer-ranking-title dealer-ranking-title-high">'
            f'5 {entity_label} dengan Satisfaction Tertinggi'
            f'</div>'
            f'{top_html}'
            f'</div>'
        )

    with c_low:
        bottom_html = build_ranking_html(bottom_5, lowest=True)
        st.html(
            f'<div class="dealer-ranking-card">'
            f'<div class="dealer-ranking-title dealer-ranking-title-low">'
            f'5 {entity_label} dengan Satisfaction Terendah'
            f'</div>'
            f'{bottom_html}'
            f'</div>'
        )


# ============================================================
# UNIT PAGE
# ============================================================

def render_unit_page(unit_key: str, unit_label: str, sheet_name: str, dealer_label: str):
    df_raw = try_read_sheet(sheet_name)
    if df_raw.empty:
        st.warning(f"Data '{sheet_name}' tidak ditemukan atau gagal dimuat dari Google Sheets.")
        return

    # Load Metadata Sheets
    meta_h1 = try_read_sheet("Indicator_metadata_H1")
    meta_h2 = try_read_sheet("Indicator_metadata_H2")
    meta_h3 = try_read_sheet("Indicator_metadata_H3")
    meta_gen = try_read_sheet("indicator_metadata")

    if unit_key == "sales" and not meta_h1.empty:
        meta_df = meta_h1
    elif unit_key == "service" and not meta_h2.empty:
        meta_df = meta_h2
    elif unit_key == "parts" and not meta_h3.empty:
        meta_df = meta_h3
    else:
        meta_df = meta_gen if not meta_gen.empty else (meta_h1 if not meta_h1.empty else (meta_h2 if not meta_h2.empty else meta_h3))

    profile_meta_h1 = try_read_sheet("profile_metadata_H1")
    profile_meta_h2 = try_read_sheet("profile_metadata_H2")
    profile_meta_h3 = try_read_sheet("profile_metadata_H3")
    profile_meta_gen = try_read_sheet("profile_metadata")

    if unit_key == "sales" and not profile_meta_h1.empty:
        profile_meta_df = profile_meta_h1
    elif unit_key == "service" and not profile_meta_h2.empty:
        profile_meta_df = profile_meta_h2
    elif unit_key == "parts" and not profile_meta_h3.empty:
        profile_meta_df = profile_meta_h3
    else:
        profile_meta_df = profile_meta_gen if not profile_meta_gen.empty else (profile_meta_h1 if not profile_meta_h1.empty else (profile_meta_h2 if not profile_meta_h2.empty else profile_meta_h3))

    cols = detect_columns(df_raw, unit_key)
    df_raw = add_karesidenan(df_raw, cols)
    indicator_cols = indicator_columns(df_raw, meta_df, unit_key=unit_key)

    key_prefix = f"{unit_key}"

    filters = {"_dealer_label": dealer_label}
    filters, df_filtered = render_performance_section(
        df_raw, cols, meta_df, filters, indicator_cols, key_prefix
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    render_importance_matrix(unit_key, key=f"{key_prefix}_matrix", filters=filters)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # BLUE SECTION START: Encompasses ALL Profile & Demographic & NPS charts
    with st.container(key=f"{key_prefix}_profile_customer_section"):
        st.markdown(
            """
            <div class="custom-section-title">
                <div class="custom-section-badge">SECTION 3</div>
                <div class="custom-section-text">PROFILE CUSTOMER</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        r1_col1, r1_col2, r1_col3 = st.columns(
            [1, 1, 1],
            gap="medium",
            vertical_alignment="top",
        )

        # ============================================================
        # HEATMAP
        # ============================================================
        with r1_col1:
            with st.container(
                key=f"{key_prefix}_profile_equal_height_profile_heatmap_column",
                border=True,
            ):
                render_profile_heatmap(
                    unit_key,
                    key=f"{key_prefix}_heatmap"
                )

        # ============================================================
        # DAFTAR PROFIL
        # ============================================================
        with r1_col2:
            with st.container(
                key=f"{key_prefix}_profile_equal_height_profile_list_column",
                border=True,
            ):
                selected_profile = render_profile_list(
                    df_filtered,
                    cols,
                    key_prefix,
                    profile_meta_df=profile_meta_df,
                )

        # ============================================================
        # INSIGHT DINAMIS, TEPAT DI BAWAH HEATMAP
        # ============================================================
        profile_col = cols.get("profile") if cols else None
        df_profile_insight = df_filtered
        if (
            selected_profile and profile_col and
            df_filtered is not None and not df_filtered.empty and
            profile_col in df_filtered.columns
        ):
            selected_number = str(selected_profile).replace("P", "").strip()
            profile_mask = (
                df_filtered[profile_col].astype(str).str.contains(
                    rf"\b{selected_number}\b", case=False, na=False
                ) |
                df_filtered[profile_col].astype(str).str.contains(
                    selected_profile, case=False, na=False
                )
            )
            matched_profile = df_filtered[profile_mask]
            if not matched_profile.empty:
                df_profile_insight = matched_profile

        # ============================================================
        # PENJELASAN PROFIL
        # ============================================================
        with r1_col3:
            with st.container(
                key=f"{key_prefix}_profile_equal_height_profile_explanation_column",
                border=True,
            ):
                render_profile_explanation(
                    profile_meta_df,
                    selected_profile,
                )

        # Insight berada di luar context ketiga kolom sehingga lebarnya
        # mengikuti seluruh area halaman, tepat di bawah baris heatmap.
        render_overall_profile_insight(
            df_filtered=df_filtered,
            df_prof=df_profile_insight,
            cols=cols,
            selected_profile=selected_profile,
            unit=unit_key,
            key_prefix=key_prefix,
            profile_meta_df=profile_meta_df,
        )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        render_demographic_charts(
            df_filtered,
            cols,
            dealer_label,
            key_prefix,
            selected_profile=selected_profile,
            unit_key=unit_key,
        )

        # ============================================================
        # TOP 5 & BOTTOM 5 SATISFACTION DEALER / AHASS / PART SHOP
        # Dinamis mengikuti data + seluruh filter aktif + customer profile.
        # Hanya tampil ketika filter Kab/Kota = Semua.
        # ============================================================
        if filters.get("kab_kota") in (None, "Semua", ""):
            render_top_bottom_dealer_satisfaction(
                df_profile=df_profile_insight,
                cols=cols,
                indicator_cols=indicator_cols,
                unit_key=unit_key,
                key_prefix=key_prefix,
                filters=filters,
            )


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


def rw_create_region_stacked_bar(data: pd.DataFrame, profile_name_map: dict) -> go.Figure:
    figure = go.Figure()
    for profile in RW_PROFILE_ORDER:
        profile_label = profile_name_map.get(profile, f"Profile {profile}")
        figure.add_trace(go.Bar(
            name=f"Profile {profile}",
            y=data["Kabupaten/Kota"],
            x=data[f"Persen_Profile_{profile}"],
            orientation="h",
            marker=dict(color=RW_PROFILE_COLORS[profile]),
            customdata=np.column_stack([data[f"Jumlah_Profile_{profile}"], data["Jumlah_Responden"]]),
            hovertemplate=(
                "<b>%{y}</b><br>"
                + f"<b>Profile {profile} — {profile_label}</b><br>"
                + "Persentase: %{x:.1f}%<br>"
                + "Jumlah responden profile: %{customdata[0]:,.0f}<br>"
                + "Total responden wilayah: %{customdata[1]:,.0f}"
                + "<extra></extra>"
            ),
        ))

    figure.update_layout(
        barmode="stack",
        xaxis_title="Persentase Responden",
        yaxis_title=None,
        xaxis=dict(range=[0, 100], ticksuffix="%"),
        legend_title="Customer Profile",
        margin=dict(l=10, r=10, t=20, b=10),
        height=max(420, len(data) * 32),
        hoverlabel=dict(align="left"),
    )
    return figure


def rw_create_profile_heatmap(data: pd.DataFrame) -> go.Figure:
    profile_percent_columns = [f"Persen_Profile_{p}" for p in RW_PROFILE_ORDER]
    profile_count_columns = [f"Jumlah_Profile_{p}" for p in RW_PROFILE_ORDER]

    percent_values = data[profile_percent_columns].to_numpy(dtype=float)
    profile_count_values = data[profile_count_columns].to_numpy(dtype=float)
    total_respondents = np.repeat(
        data["Jumlah_Responden"].to_numpy(dtype=float).reshape(-1, 1), len(RW_PROFILE_ORDER), axis=1
    )
    custom_data = np.stack([profile_count_values, total_respondents], axis=-1)

    figure = go.Figure(data=go.Heatmap(
        z=percent_values,
        x=[f"Profile {p}" for p in RW_PROFILE_ORDER],
        y=data["Kabupaten/Kota"],
        colorscale=[[0.0, "#FFF3E0"], [0.5, "#FFB000"], [1.0, "#E60012"]],
        zmin=0, zmax=100,
        text=np.round(percent_values, 1),
        texttemplate="%{text:.1f}%",
        customdata=custom_data,
        hovertemplate=(
            "<b>%{y}</b><br>%{x}<br>Persentase: %{z:.1f}%<br>"
            "Jumlah responden profile: %{customdata[0]:,.0f}<br>"
            "Total responden wilayah: %{customdata[1]:,.0f}<extra></extra>"
        ),
        colorbar=dict(title="% Responden"),
    ))
    figure.update_layout(
        xaxis_title=None, yaxis_title=None,
        margin=dict(l=10, r=10, t=30, b=10),
        height=max(420, len(data) * 32),
    )
    return figure


def rw_create_cluster_dominant_chart(region_summary: pd.DataFrame) -> go.Figure:
    dominant_distribution = (
        region_summary.groupby([RW_CLUSTER_PROFILE_COLUMN, "Profile_Dominan"], observed=True)
        .size().rename("Jumlah_Wilayah").reset_index()
    )
    cluster_totals = dominant_distribution.groupby(RW_CLUSTER_PROFILE_COLUMN)["Jumlah_Wilayah"].transform("sum")
    dominant_distribution["Persentase_Wilayah"] = dominant_distribution["Jumlah_Wilayah"] / cluster_totals * 100
    dominant_distribution["Profile_Label"] = "Profile " + dominant_distribution["Profile_Dominan"].astype(str)

    figure = px.bar(
        dominant_distribution, x=RW_CLUSTER_PROFILE_COLUMN, y="Persentase_Wilayah",
        color="Profile_Label", barmode="stack",
        color_discrete_map=RW_CLUSTER_PROFILE_COLORS,
        text="Persentase_Wilayah",
        labels={RW_CLUSTER_PROFILE_COLUMN: "Cluster Wilayah", "Persentase_Wilayah": "Persentase Wilayah", "Profile_Label": "Profile"},
    )
    figure.update_traces(
        width=0.45, texttemplate="%{text:.1f}", textposition="inside",
        hovertemplate="<b>%{x}</b><br>%{fullData.name}<br>Persentase wilayah: %{y:.1f}%<extra></extra>",
    )
    figure.update_layout(
        height=300,
        yaxis=dict(range=[0, 100], ticksuffix="%", title="Persentase Wilayah"),
        xaxis=dict(title="Cluster Wilayah"),
        legend=dict(title="Profile Dominan", orientation="v"),
        margin=dict(l=40, r=20, t=15, b=40),
    )
    return figure


def rw_create_culture_dominant_chart(region_summary: pd.DataFrame, culture_df: pd.DataFrame) -> go.Figure:
    culture_summary = region_summary.merge(
        culture_df[["Region_Key", "Kelompok_Budaya"]], on="Region_Key", how="left", validate="one_to_one"
    )
    culture_summary = culture_summary.dropna(subset=["Kelompok_Budaya"]).copy()

    dominant_distribution = (
        culture_summary.groupby(["Kelompok_Budaya", "Profile_Dominan"], observed=True)
        .size().rename("Jumlah_Wilayah").reset_index()
    )
    culture_totals = dominant_distribution.groupby("Kelompok_Budaya")["Jumlah_Wilayah"].transform("sum")
    dominant_distribution["Persentase_Wilayah"] = dominant_distribution["Jumlah_Wilayah"] / culture_totals * 100
    dominant_distribution["Profile_Label"] = "Profile " + dominant_distribution["Profile_Dominan"].astype(str)

    figure = px.bar(
        dominant_distribution, x="Kelompok_Budaya", y="Persentase_Wilayah",
        color="Profile_Label", barmode="stack",
        color_discrete_map=RW_CLUSTER_PROFILE_COLORS,
        text="Persentase_Wilayah",
        labels={"Kelompok_Budaya": "Kelompok Budaya", "Persentase_Wilayah": "Persentase Wilayah", "Profile_Label": "Profile Dominan"},
    )
    figure.update_traces(
        width=0.50, texttemplate="%{text:.1f}", textposition="inside",
        hovertemplate="<b>%{x}</b><br>%{fullData.name}<br>Persentase wilayah: %{y:.1f}%<extra></extra>",
    )
    figure.update_layout(
        height=300,
        yaxis=dict(range=[0, 100], ticksuffix="%", title="Persentase Wilayah"),
        xaxis=dict(title="Kelompok Budaya"),
        legend=dict(title="Profile Dominan"),
        margin=dict(l=35, r=15, t=10, b=35),
    )
    return figure


def rw_render_cluster_region_details(cluster_df: pd.DataFrame):
    """Keterangan daftar wilayah per Cluster Wilayah (BPS), gaya kotak disamakan dashboard."""
    with st.expander("**Keterangan Anggota Wilayah per Cluster BPS**", expanded=True):
        if cluster_df.empty:
            st.info("Data cluster BPS tidak tersedia.")
            return

        grouped = cluster_df.groupby([RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN], observed=True)
        sorted_groups = sorted(grouped, key=lambda x: x[0][0])

        for (c_num, c_name), group in sorted_groups:
            regions = sorted(group[RW_CLUSTER_REGION_COLUMN].dropna().unique().tolist())
            region_count = len(regions)
            region_str = ", ".join(regions)
            st.markdown(
                f"""
                <div class="region-detail-box">
                    <div class="region-detail-title">Cluster {c_num} – {c_name}
                        <span class="region-detail-count">({region_count} Wilayah)</span>
                    </div>
                    <div class="region-detail-body">{region_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def rw_render_culture_region_details(culture_df: pd.DataFrame):
    """Keterangan daftar wilayah per Kelompok Budaya, gaya kotak disamakan dashboard."""
    with st.expander("**Keterangan Anggota Wilayah per Kelompok Budaya**", expanded=True):
        if culture_df.empty:
            st.info("Data pengelompokkan budaya tidak tersedia.")
            return

        if "Cluster_Budaya" in culture_df.columns:
            culture_order = (
                culture_df[["Cluster_Budaya", "Kelompok_Budaya"]]
                .dropna(subset=["Kelompok_Budaya"])
                .drop_duplicates(subset=["Kelompok_Budaya"])
                .sort_values(by="Cluster_Budaya", na_position="last")
            )
            culture_list = culture_order["Kelompok_Budaya"].tolist()
        else:
            culture_list = sorted(culture_df["Kelompok_Budaya"].dropna().unique().tolist())

        for budaya in culture_list:
            group = culture_df[culture_df["Kelompok_Budaya"] == budaya]
            regions = sorted(group["Kabupaten/Kota_Budaya"].dropna().unique().tolist())
            region_count = len(regions)
            region_str = ", ".join(regions)

            c_num = (
                group["Cluster_Budaya"].iloc[0]
                if "Cluster_Budaya" in group.columns and not pd.isna(group["Cluster_Budaya"].iloc[0])
                else None
            )
            cluster_prefix = f"Cluster Budaya {int(c_num)} – " if c_num is not None else ""

            st.markdown(
                f"""
                <div class="region-detail-box culture">
                    <div class="region-detail-title">{cluster_prefix}{budaya}
                        <span class="region-detail-count">({region_count} Wilayah)</span>
                    </div>
                    <div class="region-detail-body">{region_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def rw_render_data_diagnostic(diagnostic: dict, h_code: str):
    config = RW_H_CONFIG[h_code]
    with st.expander("Pemeriksaan Kelengkapan Data", expanded=False):
        diagnostic_df = pd.DataFrame({
            "Ukuran": [
                "Total Baris", f"Wilayah Terisi ({config['region_column']})",
                "Profile Terisi", "Baris Valid Wilayah + Profile", "Jumlah Wilayah Valid",
            ],
            "Nilai": [
                diagnostic.get("total_rows", 0), diagnostic.get("region_non_null", 0),
                diagnostic.get("profile_non_null", 0), diagnostic.get("valid_rows", 0),
                diagnostic.get("valid_regions", 0),
            ],
        })
        st.dataframe(diagnostic_df, hide_index=True, use_container_width=True)
        if diagnostic.get("profile_non_null", 0) > diagnostic.get("region_non_null", 0):
            st.warning(
                "Kolom Profile lebih banyak terisi daripada kolom wilayah. Wilayah setiap "
                "responden tidak boleh ditebak (tidak dilakukan forward-fill). Gunakan data "
                "responden yang kolom wilayahnya terisi pada setiap baris."
            )


def rw_render_region_profile_page():
    """Page Profil Wilayah: Cluster BPS & Kelompok Budaya vs Customer Profile.
    Style disamakan dengan SECTION 1/2/3 pada dashboard utama (badge, kpi-card, chart-title)."""
    with st.container(key="wilayah_profile_customer_section"):
        st.markdown(
            """
            <div class="custom-section-title">
                <div class="custom-section-badge">SECTION 4</div>
                <div class="custom-section-text">PROFIL WILAYAH &amp; CLUSTER BUDAYA</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            "Menunjukkan pengelompokan kabupaten/kota berdasarkan karakteristik wilayah "
            "(Cluster BPS) dan kelompok budaya, serta kesesuaiannya dengan distribusi "
            "Customer Profile hasil survei."
        )

        filter_col_1, filter_col_2 = st.columns(2)
        with filter_col_1:
            selected_h = st.selectbox(
                "Pilih Bagian",
                options=list(RW_H_CONFIG.keys()),
                format_func=lambda value: f"{value} — {RW_H_CONFIG[value]['title']}",
                key="rw_selected_h",
            )

        minimum_respondents = 30

        try:
            cluster_df = rw_load_cluster_data()
            culture_df = rw_load_culture_data()
            metadata_df = rw_load_profile_metadata(selected_h)
            respondent_df, diagnostic = rw_load_csl_profile_data(selected_h)
        except (KeyError, ValueError, RuntimeError) as error:
            st.error(str(error))
            st.info(
                "Periksa nama worksheet 'Hasil_Cluster', 'Pengelompokkan_budaya', dan "
                "'profile_metadata_H1/H2/H3' pada Google Sheets."
            )
            return

        if respondent_df.empty:
            st.error(
                "Tidak ada baris yang memiliki wilayah dan Profile secara bersamaan "
                "untuk bagian ini."
            )
            return

        region_summary, merged_respondents = rw_calculate_region_profile_distribution(
            respondent_df=respondent_df,
            metadata_df=metadata_df,
            cluster_df=cluster_df,
            minimum_respondents=int(minimum_respondents),
        )

        if region_summary.empty:
            unmatched_regions = sorted(
                merged_respondents.loc[merged_respondents[RW_CLUSTER_COLUMN].isna(), "Region_Key"]
                .dropna().unique().tolist()
            )
            st.error("Tidak ada wilayah CSL yang berhasil dipasangkan dengan data cluster BPS.")
            if unmatched_regions:
                st.write("Nama wilayah yang belum cocok:")
                st.code("\n".join(unmatched_regions))
            return

        unmatched_regions = sorted(
            merged_respondents.loc[merged_respondents[RW_CLUSTER_COLUMN].isna(), "Region_Key"]
            .dropna().unique().tolist()
        )
        if unmatched_regions:
            with st.expander(f"{len(unmatched_regions)} nama wilayah belum cocok", expanded=False):
                st.write(
                    "Tambahkan nama berikut ke `RW_REGION_ALIASES` jika wilayah tersebut "
                    "seharusnya tersedia pada data cluster:"
                )
                st.code("\n".join(unmatched_regions))

        cluster_options = ["Semua"] + sorted(region_summary[RW_CLUSTER_PROFILE_COLUMN].dropna().unique().tolist())
        with filter_col_2:
            selected_cluster = st.selectbox("Filter Cluster Wilayah", options=cluster_options, key="rw_selected_cluster")

        filtered_summary = region_summary.copy()
        if selected_cluster != "Semua":
            filtered_summary = filtered_summary[filtered_summary[RW_CLUSTER_PROFILE_COLUMN] == selected_cluster].copy()

        sorted_summary = filtered_summary.sort_values(
            by=[RW_CLUSTER_COLUMN, "Persen_Dominan"], ascending=[True, True]
        ).copy()

        # ----------------------------
        # KPI
        # ----------------------------
        eligible_summary = filtered_summary[filtered_summary["Jumlah_Responden"] >= minimum_respondents].copy()
        cluster_similarity_all = rw_calculate_cluster_similarity(region_summary, int(minimum_respondents))

        region_summary_culture = region_summary.merge(
            culture_df[["Region_Key", "Kelompok_Budaya"]], on="Region_Key", how="left"
        )
        culture_similarity_all = rw_calculate_culture_similarity(region_summary_culture, int(minimum_respondents))

        dominant_overall = (
            eligible_summary["Profile_Dominan"].mode().iloc[0] if not eligible_summary.empty else np.nan
        )
        dominant_overall_name = (
            metadata_df.set_index("Profile")["Profile Name"].to_dict().get(int(dominant_overall), "-")
            if not pd.isna(dominant_overall) else "-"
        )

        if selected_cluster == "Semua":
            relevant_similarity = cluster_similarity_all
        else:
            relevant_similarity = cluster_similarity_all[cluster_similarity_all["Profil_Wilayah"] == selected_cluster]

        average_distribution_similarity = (
            relevant_similarity["Kemiripan_Distribusi"].mean() if not relevant_similarity.empty else np.nan
        )

        jumlah_wilayah = filtered_summary["Kabupaten/Kota"].nunique()
        jumlah_responden = int(filtered_summary["Jumlah_Responden"].sum())
        dominant_value = f"Profile {int(dominant_overall)}" if not pd.isna(dominant_overall) else "-"
        similarity_pct = average_distribution_similarity * 100 if not pd.isna(average_distribution_similarity) else None
        similarity_value = f"{similarity_pct:.1f}%" if similarity_pct is not None else "N/A"
        similarity_category = rw_classify_similarity(average_distribution_similarity)
        similarity_color = (
            GREEN if similarity_category == "Sangat Mirip"
            else (ORANGE if similarity_category == "Cukup Mirip" else (RED if similarity_category == "Beragam" else "#888888"))
        )
        dominant_color = RW_PROFILE_COLORS.get(int(dominant_overall), "#555555") if not pd.isna(dominant_overall) else "#888888"

        kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
        with kpi_1:
            _kpi_card("Jumlah Wilayah", f"{jumlah_wilayah:,}".replace(",", "."), "Wilayah Tercakup", "#555555")
        with kpi_2:
            _kpi_card("Jumlah Responden", f"{jumlah_responden:,}".replace(",", "."), "Responden Tervalidasi", "#555555")
        with kpi_3:
            _kpi_card("Profile Dominan Umum", dominant_value, dominant_overall_name, dominant_color)
        with kpi_4:
            _kpi_card("Kemiripan Distribusi", similarity_value, similarity_category, similarity_color)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ----------------------------
        # STACKED BAR PER WILAYAH
        # ----------------------------
        profile_name_map = metadata_df.set_index("Profile")["Profile Name"].to_dict()
        with st.container(key="rw_stacked_chart_card", border=True):
            st.markdown('<div class="chart-title">Distribusi Customer Profile per Kabupaten/Kota</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="chart-subtitle">Komposisi Profile 1–5 pada masing-masing kabupaten/kota '
                'berdasarkan persentase responden</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                rw_create_region_stacked_bar(sorted_summary, profile_name_map),
                use_container_width=True,
                key=f"rw_stacked_region_profile_{selected_h}_{selected_cluster}",
            )

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ----------------------------
        # DOMINASI PROFILE: CLUSTER BPS vs BUDAYA
        # ----------------------------
        chart_left, chart_right = st.columns(2, gap="medium")

        with chart_left:
            with st.container(key="rw_cluster_dominant_chart_card", border=True):
                st.markdown('<div class="chart-title">Dominasi Profile berdasarkan Cluster Wilayah</div>', unsafe_allow_html=True)
                st.markdown(
                    '<div class="chart-subtitle">Proporsi kabupaten/kota berdasarkan customer profile '
                    'dominan pada cluster karakteristik wilayah (BPS)</div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    rw_create_cluster_dominant_chart(
                        region_summary[region_summary["Jumlah_Responden"] >= minimum_respondents]
                    ),
                    use_container_width=True,
                    key=f"rw_cluster_dominant_{selected_h}",
                )
                rw_render_cluster_region_details(cluster_df)

        with chart_right:
            with st.container(key="rw_culture_dominant_chart_card", border=True):
                st.markdown('<div class="chart-title">Dominasi Profile berdasarkan Kelompok Budaya</div>', unsafe_allow_html=True)
                st.markdown(
                    '<div class="chart-subtitle">Proporsi kabupaten/kota berdasarkan customer profile '
                    'dominan pada masing-masing kelompok budaya</div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    rw_create_culture_dominant_chart(
                        region_summary[region_summary["Jumlah_Responden"] >= minimum_respondents], culture_df,
                    ),
                    use_container_width=True,
                    key=f"rw_culture_dominant_{selected_h}",
                )
                rw_render_culture_region_details(culture_df)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ----------------------------
        # TABEL DOMINAN PER WILAYAH
        # ----------------------------
        display_table = filtered_summary[[
            "Kabupaten/Kota", RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN, "Jumlah_Responden",
            "Profile_Dominan", "Nama_Profile_Dominan", "Persen_Dominan",
            "Profile_Kedua", "Nama_Profile_Kedua", "Persen_Kedua",
            "Margin_Dominasi", "Status_Sampel",
        ]].copy()

        display_table = display_table.rename(columns={
            RW_CLUSTER_COLUMN: "Cluster",
            RW_CLUSTER_PROFILE_COLUMN: "Profil Wilayah",
            "Jumlah_Responden": "Jumlah Responden",
            "Profile_Dominan": "Profile Dominan",
            "Nama_Profile_Dominan": "Nama Profile Dominan",
            "Persen_Dominan": "% Dominan",
            "Profile_Kedua": "Profile Kedua",
            "Nama_Profile_Kedua": "Nama Profile Kedua",
            "Persen_Kedua": "% Profile Kedua",
            "Margin_Dominasi": "Margin Dominasi",
            "Status_Sampel": "Status Sampel",
        })

        with st.container(key="rw_table_chart_card", border=True):
            st.markdown('<div class="chart-title">Tabel Profile Dominan per Wilayah</div>', unsafe_allow_html=True)
            st.markdown('<div class="chart-subtitle">Detail profil dominan dan kedua untuk setiap kabupaten/kota</div>', unsafe_allow_html=True)
            st.dataframe(display_table, hide_index=True, use_container_width=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        rw_render_data_diagnostic(diagnostic, selected_h)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ----------------------------
        # INSIGHT CLUSTER & BUDAYA
        # ----------------------------
        left_insight, right_insight = st.columns(2, gap="large")

        with left_insight:
            st.markdown('<div class="chart-title" style="font-size:14px;">Insight Cluster Wilayah</div>', unsafe_allow_html=True)
            if cluster_similarity_all.empty:
                st.info("Kemiripan belum dapat dinilai.")
            else:
                for row in cluster_similarity_all.itertuples(index=False):
                    maj_prof = f"Profile {row.Profile_Mayoritas}" if not pd.isna(row.Profile_Mayoritas) else "-"
                    sim_pct = f"{row.Kemiripan_Distribusi * 100:.1f}%" if not pd.isna(row.Kemiripan_Distribusi) else "-"
                    cons_pct = f"{row.Konsistensi_Profile_Dominan:.1f}%" if not pd.isna(row.Konsistensi_Profile_Dominan) else "-"
                    st.markdown(
                        f"""
                        <div class="insight-box">
                            <div class="insight-box-header"><span></span><span>Cluster {row.Cluster} – {row.Profil_Wilayah}</span></div>
                            <div class="insight-box-body">
                                <b>Mayoritas Profile:</b> {maj_prof} ({row.Jumlah_Wilayah_Sesuai}/{row.Jumlah_Wilayah_Valid} Wilayah, {cons_pct})<br>
                                <b>Kemiripan Distribusi:</b> {sim_pct} ({row.Kategori_Kemiripan})
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with right_insight:
            st.markdown('<div class="chart-title" style="font-size:14px;">Insight Kelompok Budaya</div>', unsafe_allow_html=True)
            if culture_similarity_all.empty:
                st.info("Belum ada insight.")
            else:
                for row in culture_similarity_all.itertuples(index=False):
                    maj_prof = f"Profile {row.Profile_Mayoritas}" if not pd.isna(row.Profile_Mayoritas) else "-"
                    sim_pct = f"{row.Kemiripan_Distribusi * 100:.1f}%" if not pd.isna(row.Kemiripan_Distribusi) else "-"
                    cons_pct = f"{row.Konsistensi_Profile_Dominan:.1f}%" if not pd.isna(row.Konsistensi_Profile_Dominan) else "-"
                    st.markdown(
                        f"""
                        <div class="reco-box">
                            <div class="reco-box-header"><span></span><span>{row.Kelompok_Budaya}</span></div>
                            <div class="reco-box-body">
                                <b>Mayoritas Profile:</b> {maj_prof} ({row.Jumlah_Wilayah_Sesuai}/{row.Jumlah_Wilayah_Valid} Wilayah, {cons_pct})<br>
                                <b>Kemiripan Distribusi:</b> {sim_pct} ({row.Kategori_Kemiripan})
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


# ============================================================
# MAIN
# ============================================================

PAGE_OPTIONS = ["H1 SALES", "H2 SERVICE", "H3 SPARE PART", "PROFIL WILAYAH", "FRAMEWORK"]


def _format_update_time(value):
    """Format waktu pembaruan terakhir menggunakan WIB / GMT+7."""
    if not isinstance(value, datetime):
        value = datetime.now(WIB)

    # Jika datetime belum memiliki timezone, anggap sebagai WIB.
    if value.tzinfo is None:
        value = value.replace(tzinfo=WIB)
    else:
        value = value.astimezone(WIB)

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
        "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
    ]

    return (
        f"{value.day:02d} "
        f"{month_names[value.month - 1]} "
        f"{value.year}, {value:%H:%M} WIB"
    )


def _reset_active_page_filters(selected_page):
    """Hapus state filter halaman aktif tanpa mengubah pilihan halaman."""
    prefix_by_page = {
        "H1 SALES": ("sales_",), "H2 SERVICE": ("service_",),
        "H3 SPARE PART": ("parts_",), "PROFIL WILAYAH": ("rw_",),
    }
    prefixes = prefix_by_page.get(selected_page, ())
    for state_key in list(st.session_state.keys()):
        if state_key not in {"main_page_selector", "last_data_refresh"} and any(state_key.startswith(prefix) for prefix in prefixes):
            del st.session_state[state_key]
    for param in ("map_region", "map_unit", "map_click_token"):
        if param in st.query_params:
            del st.query_params[param]


def render_top_navigation():
    """Render header dan navigasi utama seperti rancangan dashboard."""
    if "last_data_refresh" not in st.session_state:
        st.session_state.last_data_refresh = datetime.now(WIB)
    active_page = st.session_state.get("main_page_selector", "H1 SALES")
    with st.container(key="top_header"):
        brand_col, time_col, refresh_col, reset_col = st.columns([6.8, 1.55, 1.15, 1.05], vertical_alignment="center", gap="small")
        with brand_col:
            st.markdown('''<div class="csl-header-brand"><div class="csl-logo">CSL</div><div class="csl-brand"><div><h1>CUSTOMER SATISFACTION LEVEL ANALYTICS</h1></div></div></div>''', unsafe_allow_html=True)
        with time_col:
            st.markdown('<div class="csl-update-time">Data terakhir diperbarui<br>' f'<b>{_format_update_time(st.session_state.last_data_refresh)}</b></div>', unsafe_allow_html=True)
        with refresh_col:
            if st.button("⟳  Refresh Data", key="header_refresh", use_container_width=True):
                st.cache_data.clear()
                st.session_state.last_data_refresh = datetime.now(WIB)
                st.rerun()
        with reset_col:
            if st.button("Reset Filter", key="header_reset", use_container_width=True):
                _reset_active_page_filters(active_page)
                st.rerun()

    with st.container(key="page_selector_card"):
        return st.segmented_control("Pilih Page", options=PAGE_OPTIONS, default="H1 SALES", key="main_page_selector", label_visibility="collapsed")


def render_framework_placeholder():
    """Alur analitik CSL: (A) Perhitungan Matrix Satisfaction x Importance,
    (B) Customer Profiling dengan GMM/LPA, ditutup (C) insight praktis dari dashboard."""

    # ========================================================
    # BAGIAN A — PERHITUNGAN MATRIX (SATISFACTION x IMPORTANCE)
    # Gaya, ikon, dan isi langkah dipertahankan sama seperti versi awal.
    # ========================================================
    matrix_steps = [
        {
            "no": "01", "icon": "fa-solid fa-chart-column", "title": "STEP 1<br>SATISFACTION SCORE<br>CALCULATION",
            "items": [
                ("fa-solid fa-chart-column", "1. Hitung rata-rata score setiap atribut", "A1–Axx, B1–Bxx, dan seterusnya."),
                ("fa-solid fa-sitemap", "2. Kelompokkan atribut berdasarkan Moment of Truth (MOT)", "Setiap atribut dikelompokkan ke dalam MOT yang sesuai."),
                ("fa-solid fa-chart-line", "3. Hitung rata-rata score masing-masing MOT", "Rata-rata atribut membentuk score setiap MOT."),
                ("fa-solid fa-chart-pie", "4. Hitung Total Score", "Total Score merupakan rata-rata seluruh MOT."),
            ],
            "output": ["Score Total", "Score MOT", "Score Atribut"],
        },
        {
            "no": "02", "icon": "fa-solid fa-bullseye", "title": "STEP 2<br>CUSTOMER SATISFACTION<br>DRIVER MODELLING",
            "items": [
                ("fa-solid fa-bullseye", "Target", "Total CSL Score."),
                ("fa-solid fa-table-cells", "Predictor", "Seluruh atribut CSL."),
                ("fa-solid fa-tree", "Random Forest Regression", "Model hubungan atribut dengan Total CSL Score."),
                ("fa-solid fa-braille", "SHAP Analysis", "Mengukur kontribusi masing-masing atribut."),
                ("fa-solid fa-magnifying-glass-chart", "Hitung Mean Absolute SHAP Value", "Besarnya pengaruh rata-rata setiap atribut."),
                ("fa-solid fa-trophy", "Ranking Satisfaction Driver", "Urutan atribut berdasarkan pengaruhnya."),
            ],
            "output": ["SHAP Importance", "Satisfaction Rank"],
        },
        {
            "no": "03", "icon": "fa-solid fa-users", "title": "STEP 3<br>CUSTOMER IMPORTANCE<br>ANALYSIS",
            "items": [
                ("fa-solid fa-users", "Data", "Transformasi rank dari Top 5 Importance Attributes: 5 = paling penting, 4 = rank kedua, 3 = rank ketiga, 2 = rank keempat, 1 = rank kelima, dan 0 = tidak dipilih."),
                ("fa-solid fa-scale-balanced", "Weighted Ranking Method", "Memberikan bobot berdasarkan posisi atribut."),
                ("fa-solid fa-chart-column", "Weighting Score", "Menghitung score hasil pembobotan."),
                ("fa-solid fa-list-ol", "Importance Rank", "Mengurutkan atribut berdasarkan weighting score."),
            ],
            "output": ["Importance Score", "Importance Rank"],
        },
        {
            "no": "04", "icon": "fa-solid fa-sliders", "title": "STEP 4<br>PRIORITY IMPROVEMENT<br>MATRIX",
            "items": [
                ("fa-solid fa-xmarks-lines", "Input", "X Axis = Importance Rank; Y Axis = Satisfaction Driver Rank."),
                ("fa-solid fa-sliders", "Hitung Median Importance Rank", "Median menjadi garis pembagi vertikal."),
                ("fa-solid fa-sliders", "Hitung Median Satisfaction Rank", "Median menjadi garis pembagi horizontal."),
                ("fa-solid fa-table-cells-large", "Pemetaan 4 Kuadran Matrix", "Kuadran I Pertahankan, II Prioritas Rendah, III Perbaikan Bertahap, dan IV Prioritas Utama."),
            ],
            "output": ["Matriks 4 Kuadran", "Daftar Prioritas"],
        },
        {
            "no": "05", "icon": "fa-solid fa-cart-shopping", "title": "STEP 5<br>INTERACTIVE<br>DASHBOARD",
            "items": [
                ("fa-solid fa-cart-shopping", "Sales [H1]", "Analisis kepuasan pembelian unit."),
                ("fa-solid fa-screwdriver-wrench", "Service [H2]", "Analisis kepuasan layanan AHASS."),
                ("fa-solid fa-gears", "Spare Part [H3]", "Analisis kepuasan suku cadang."),
                ("fa-solid fa-users", "TOTAL (ALL)", "Ringkasan performa keseluruhan."),
                ("fa-solid fa-store", "MAIN DEALER", "M2Z dan M3Z."),
                ("fa-solid fa-layer-group", "LAYER", "Reguler H123, Reguler H23, Wing, dan Big Wing."),
                ("fa-solid fa-location-dot", "KARESIDENAN", "Surabaya, Kediri, Madiun, dan wilayah lainnya."),
            ],
            "output_label": "OUTPUT DASHBOARD",
            "output": ["Quadrant Matrix", "Focus Item Table", "Analysis Summary"],
        },
        {
            "no": "06", "icon": "fa-solid fa-bullseye", "title": "STEP 6<br>FOCUS ITEM<br>IDENTIFICATION",
            "items": [
                ("fa-solid fa-bullseye", "Ambil atribut pada Kuadran III", "Priority Improvement."),
                ("fa-solid fa-chart-line", "Importance Tinggi × Satisfaction Rendah", "Menentukan atribut yang paling perlu diperbaiki."),
                ("fa-solid fa-clipboard-check", "Generate Focus Item List", "Menyusun daftar akhir fokus perbaikan."),
            ],
            "output": ["Top Priority Attributes", "Focus Improvement Area"],
        },
    ]

    # ========================================================
    # BAGIAN B — CUSTOMER PROFILING (CLUSTERING / GMM-LPA)
    # Disusun berdasarkan alur notebook (EDA → model selection AIC/BIC/
    # Silhouette → fit GMM final → posterior probability → profile gap).
    # Ditulis lebih rinci & bahasa awam supaya mudah dipahami.
    # ========================================================
    profiling_steps = [
        {
            "no": "01", "icon": "☰", "title": "STEP 1<br>PERSIAPAN<br>DATA",
            "items": [
                ("Kumpulkan indikator kepuasan", "Seluruh atribut satisfaction (A1–H23, dst) dijadikan variabel input clustering."),
                ("Bersihkan data kosong", "Nilai kosong/spasi diubah menjadi missing value agar tidak mengganggu model."),
                ("Cek kelengkapan data", "Menghitung jumlah & persentase data hilang tiap indikator sebagai kontrol kualitas."),
            ],
            "output": ["Dataset indikator siap dianalisis"],
        },
        {
            "no": "02", "icon": "⌕", "title": "STEP 2<br>EKSPLORASI<br>DATA (EDA)",
            "items": [
                ("Lihat sebaran jawaban", "Distribusi tiap indikator diperiksa untuk memahami pola respon pelanggan."),
                ("Cek hubungan antar indikator", "Correlation matrix dipakai agar tidak ada indikator yang terlalu tumpang tindih."),
            ],
            "output": ["Pola distribusi & korelasi indikator"],
        },
        {
            "no": "03", "icon": "⚖", "title": "STEP 3<br>PENENTUAN JUMLAH<br>PROFIL (MODEL SELECTION)",
            "items": [
                ("Coba beberapa jumlah kelompok", "Gaussian Mixture Model (GMM) dijalankan untuk k = 2 sampai 8 kelompok pelanggan."),
                ("Bandingkan 3 ukuran kualitas", "AIC & BIC (semakin rendah semakin baik) serta Silhouette Score (semakin tinggi semakin baik)."),
                ("Pilih jumlah terbaik", "Kombinasi ketiga ukuran menunjukkan 5 kelompok sebagai jumlah Customer Profile paling optimal."),
            ],
            "output": ["Jumlah profil optimal (k = 5)"],
        },
        {
            "no": "04", "icon": "◈", "title": "STEP 4<br>PEMBENTUKAN PROFIL<br>(GMM / LATENT PROFILE)",
            "items": [
                ("Latih model final", "GMM dilatih dengan 5 kelompok dan covariance type \"full\" agar tiap kelompok punya pola sebarannya sendiri."),
                ("Beri label profil", "Setiap pelanggan diberi label Profile 1–5 sesuai kelompok yang paling mungkin ia miliki."),
                ("Hitung tingkat keyakinan", "Posterior probability & Confidence Score menunjukkan seberapa yakin model menempatkan pelanggan pada profil tersebut."),
            ],
            "output": ["Label Customer Profile 1–5", "Confidence score"],
        },
        {
            "no": "05", "icon": "▦", "title": "STEP 5<br>INTERPRETASI<br>KARAKTERISTIK PROFIL",
            "items": [
                ("Hitung profile gap", "Rata-rata tiap indikator per profil dibandingkan dengan rata-rata seluruh pelanggan."),
                ("Visualisasi heatmap", "Merah menunjukkan indikator di bawah rata-rata, hijau menunjukkan di atas rata-rata."),
                ("Lengkapi dengan demografi", "Gender, usia, SES, tipe motor, NPS, dan retention dianalisis untuk melengkapi karakter tiap profil."),
            ],
            "output": ["Heatmap profile gap", "Insight karakteristik tiap profil"],
        },
        {
            "no": "06", "icon": "⌖", "title": "STEP 6<br>PEMETAAN WILAYAH<br>& VALIDASI",
            "items": [
                ("Hitung proporsi profil per wilayah", "Persentase Profile 1–5 dihitung untuk tiap kabupaten/kota."),
                ("Bandingkan dengan cluster wilayah", "Dicocokkan dengan Cluster Karakteristik Wilayah (BPS) dan Kelompok Budaya."),
                ("Ukur kemiripan distribusi", "Jensen–Shannon Similarity dipakai untuk melihat seberapa konsisten profil dalam satu cluster/budaya."),
            ],
            "output": ["Distribusi profil per wilayah", "Tingkat kemiripan cluster/budaya"],
        },
    ]

    def _build_cards(steps):
        cards = []
        for step in steps:
            item_parts = []
            for item in step["items"]:
                if len(item) == 3:
                    item_icon, label, desc = item
                    icon_html = f'<i class="{html.escape(item_icon)}"></i>'
                else:
                    label, desc = item
                    icon_html = html.escape(step["icon"])
                item_parts.append(
                    f'<div class="fw-item"><div class="fw-mini-icon">{icon_html}</div>'
                    f'<div><b>{html.escape(label)}</b><span>{html.escape(desc)}</span></div></div>'
                )
            item_html = "".join(item_parts)
            output_html = "".join(f"<li>{html.escape(value)}</li>" for value in step["output"])
            output_label = html.escape(step.get("output_label", "OUTPUT"))
            cards.append(
                f'''<article class="fw-step">
                    <div class="fw-step-head"><span>{step["no"]}</span><h3>{step["title"]}</h3></div>
                    <div class="fw-step-body">{item_html}<div class="fw-output"><b>{output_label}</b><ul>{output_html}</ul></div></div>
                </article>'''
            )
        return "".join(cards)

    matrix_cards_html = _build_cards(matrix_steps)
    profiling_cards_html = _build_cards(profiling_steps)

    # ========================================================
    # BAGIAN C — INSIGHT YANG BISA DIDAPAT DARI DASHBOARD
    # Disusun berdasarkan fitur yang benar-benar ada di app.py:
    # peta satisfaction, gap target, matrix kuadran, NPS, profil
    # wilayah, dan demografi.
    # ========================================================
    insights = [
        {
            "icon": "↗", "color": RED,
            "title": "Bandingkan Performa Antar Semester",
            "desc": "Chart \"Selisih Satisfaction Antar Semester\" dan KPI Improvement pada Section 1 menunjukkan atribut mana yang naik/turun dibanding semester sebelumnya, sehingga tren performa terlihat jelas.",
        },
        {
            "icon": "⚑", "color": ORANGE,
            "title": "Temukan Wilayah / Dealer yang Butuh Perhatian",
            "desc": "Peta Satisfaction diwarnai merah–kuning–hijau berdasarkan nilai kepuasan tiap kabupaten/kota. Klik wilayahnya (termasuk inset NTT) atau pakai filter Dealer/AHASS/Part Shop untuk fokus ke titik terlemah.",
        },
        {
            "icon": "◉", "color": YELLOW,
            "title": "Prioritaskan Atribut yang Perlu Diperbaiki",
            "desc": "Kuadran II \"Prioritas Utama\" pada Matrix Satisfaction x Importance (Section 2) menunjukkan atribut dengan importance tinggi tapi satisfaction rendah.",
        },
        {
            "icon": "⌦", "color": GREEN,
            "title": "Pantau Capaian terhadap Target",
            "desc": "Chart \"Capaian terhadap Target Atribut\" membandingkan nilai satisfaction aktual dengan target Main Dealer/Layer, sehingga atribut yang belum mencapai standar langsung terlihat.",
        },
        {
            "icon": "◐", "color": BLUE_OUTLINE,
            "title": "Kenali Karakteristik Dominan Tiap Wilayah",
            "desc": "Heatmap Customer Profile (Section 3) dan halaman Profil Wilayah menunjukkan tipe pelanggan dominan pada tiap kabupaten/kota, dealer, dan karesidenan.",
        },
        {
            "icon": "◔", "color": "#00897B",
            "title": "Ukur Loyalitas Pelanggan (NPS & Retention)",
            "desc": "Gauge NPS Unit/Dealer/AHASS/Part Shop serta chart Retention menunjukkan seberapa besar pelanggan yang loyal dan berpotensi merekomendasikan dealer ke orang lain.",
        },
        {
            "icon": "❖", "color": "#8E24AA",
            "title": "Sesuaikan Strategi dengan Budaya & Karakter Wilayah",
            "desc": "Halaman Profil Wilayah membandingkan distribusi Customer Profile dengan Cluster Karakteristik Wilayah (BPS) dan Kelompok Budaya, lengkap dengan tingkat kemiripan antar wilayah dalam satu cluster.",
        },
        {
            "icon": "◆", "color": "#C9A400",
            "title": "Pahami Profil Demografis Pelanggan",
            "desc": "Chart gender, usia, SES, tipe motor, dan metode pembayaran pada Section 3 membantu memetakan segmen pasar tiap dealer, wilayah, maupun customer profile.",
        },
    ]

    insight_cards_html = "".join(
        f'''<article class="fw-insight" style="--c:{item['color']}">
            <div class="fw-insight-icon">{item['icon']}</div>
            <div class="fw-insight-title">{html.escape(item['title'])}</div>
            <div class="fw-insight-desc">{html.escape(item['desc'])}</div>
        </article>'''
        for item in insights
    )

    # ========================================================
    # STYLE + RENDER
    # ========================================================
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap');
        @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css');

        /* Seluruh elemen pada halaman Framework menggunakan font Poppins. */
        .fw-shell,
        .fw-shell * {
            font-family:"Poppins",sans-serif!important;
            box-sizing:border-box;
            text-align:center!important;
        }

        .fw-shell{background:#fff;border:1px solid #ececec;border-radius:18px;padding:22px 18px 24px;margin:10px 0 22px;box-shadow:0 8px 24px rgba(36,20,10,.06)}
        .fw-title{display:block!important;width:100%!important;text-align:center!important;margin:0!important;color:#222;font-size:23px;font-weight:800;letter-spacing:.2px}
        .fw-title a,.fw-title svg,.fw-title [data-testid="stHeaderActionElements"]{display:none!important}
        .fw-subtitle{position:relative!important;left:50%!important;transform:translateX(-50%)!important;display:block!important;width:min(760px,calc(100% - 32px))!important;max-width:none!important;text-align:center!important;color:#777;font-size:13px;margin:6px 0 22px!important;line-height:1.55}
        .fw-subtitle-gmm{width:min(940px,calc(100% - 32px))!important;max-width:none!important;text-align:center!important;text-align-last:center!important;line-height:1.75;color:#666;margin:8px 0 24px!important}
        .fw-grid{display:grid;gap:14px;overflow-x:auto;padding:2px 2px 12px;scrollbar-color:#ff7a1a #fff1e8}
        .fw-grid-a{grid-template-columns:repeat(6,minmax(185px,1fr));gap:26px}
        .fw-grid-b{grid-template-columns:repeat(6,minmax(200px,1fr))}
        .fw-step{--accent:#e60012;--tint:#fff3f3;position:relative;min-width:200px;border:1.5px solid var(--accent);border-radius:15px;background:#fff;overflow:hidden;box-shadow:0 5px 14px rgba(80,34,10,.08);display:flex;flex-direction:column}
        .fw-step:nth-child(even){--accent:#ff6b00;--tint:#fff6ee}
        .fw-grid-b .fw-step{--accent:#E60012;--tint:#FFF3F3;border-color:#E60012}
        .fw-grid-b .fw-step:nth-child(even){--accent:#FF6B00;--tint:#FFF5EC;border-color:#FF6B00}
        .fw-step-head{position:relative;height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px!important;box-sizing:border-box!important;background:linear-gradient(135deg,var(--accent),#ff8a21);color:#fff;display:flex!important;align-items:center!important;justify-content:center!important;padding:12px 42px 12px 52px!important}
        .fw-step:nth-child(odd) .fw-step-head{background:linear-gradient(135deg,#c90012,#f13a20)}
        .fw-grid-b .fw-step:nth-child(odd) .fw-step-head{background:linear-gradient(135deg,#C8102E 0%,#E60012 55%,#F13A20 100%)!important}
        .fw-grid-b .fw-step:nth-child(even) .fw-step-head{background:linear-gradient(135deg,#E65100 0%,#FF6B00 55%,#FF9A3D 100%)!important}
        .fw-step-head>span{position:absolute;left:12px;top:50%;transform:translateY(-50%);display:grid;place-items:center;width:36px;height:36px;border-radius:50%;background:#fff;color:var(--accent);font-size:15px;font-weight:900;box-shadow:0 2px 8px rgba(0,0,0,.13)}
        .fw-step-head h3{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;width:100%;margin:0!important;padding:0!important;font-size:13px;line-height:1.35;font-weight:800;color:#fff;text-align:center!important}
        .fw-step-body{padding:11px;background:linear-gradient(180deg,var(--tint),#fff 28%);display:flex;flex:1;flex-direction:column;border-radius:0 0 13px 13px}
        .fw-item{display:flex;flex-direction:column;gap:7px;align-items:center;justify-content:flex-start;border:1px solid color-mix(in srgb,var(--accent) 24%,white);border-radius:10px;background:#fff;padding:9px 8px;margin-bottom:9px;min-height:78px}
        .fw-item>div:last-child{width:100%;text-align:center!important}
        .fw-mini-icon{display:grid;place-items:center;flex:0 0 27px;height:27px;border-radius:8px;background:var(--tint);color:var(--accent);font-weight:900;font-size:16px}
        .fw-mini-icon i{font-family:"Font Awesome 6 Free"!important;font-weight:900!important}
        .fw-item b{display:block;width:100%;color:#343434;font-size:11.5px;line-height:1.25;margin:1px 0 4px;text-align:center!important}
        .fw-item span{display:block;width:100%;color:#666;font-size:10.5px;line-height:1.38;text-align:center!important}
        .fw-output{border-radius:10px;background:var(--tint);border:1px solid color-mix(in srgb,var(--accent) 30%,white);padding:10px 11px;min-height:70px;margin-top:0}
        .fw-output b{display:block;width:100%;color:var(--accent);font-size:11px;text-align:center!important}.fw-output ul{list-style:none;margin:6px 0 0;padding:0;color:#444;font-size:10.5px;line-height:1.55;text-align:center!important}
        .fw-output li{text-align:center!important;padding:0}
        .fw-insight-grid{display:grid;grid-template-columns:repeat(4,minmax(230px,1fr));gap:14px}
        .fw-insight{border:1px solid #eee;border-left:5px solid var(--c);border-radius:12px;background:#fff;padding:14px 15px;box-shadow:0 3px 10px rgba(20,20,20,.05)}
        .fw-insight-icon{width:30px;height:30px;border-radius:8px;display:grid;place-items:center;background:color-mix(in srgb,var(--c) 14%,white);color:var(--c);font-weight:900;font-size:16px;margin:0 auto 8px}
        .fw-insight-title{font-size:12.5px;font-weight:800;color:#262626;margin-bottom:5px;line-height:1.3}
        .fw-insight-desc{font-size:11px;color:#666;line-height:1.55}
        /* Alur Matrix dibuat seperti referensi: enam kolom, ikon proses,
           panah vertikal di dalam card, dan panah penghubung antar-step. */
        .fw-grid-a .fw-step{min-width:185px;overflow:visible}
        .fw-grid-a .fw-step-head{border-radius:13px 13px 0 0}
        .fw-grid-a .fw-step:not(:last-child)::after{content:"➜";position:absolute;right:-24px;top:38px;z-index:8;color:#181818;font-size:24px;font-weight:900;line-height:1}
        .fw-grid-a .fw-item{position:relative;flex-direction:row;align-items:center;justify-content:flex-start;min-height:82px;margin-bottom:22px;padding:10px 8px}
        .fw-grid-a .fw-item>div:last-child{flex:1;min-width:0}
        .fw-grid-a .fw-mini-icon{flex:0 0 36px;width:36px;height:36px;border-radius:50%;font-size:19px}
        .fw-grid-a .fw-item:not(:last-child)::after{content:"↓";position:absolute;left:50%;bottom:-20px;transform:translateX(-50%);color:#181818;font-size:17px;font-weight:900;line-height:1}
        @media(max-width:1100px){.fw-grid-a{grid-template-columns:repeat(2,minmax(220px,1fr))}.fw-grid-b{grid-template-columns:repeat(3,minmax(220px,1fr))}.fw-insight-grid{grid-template-columns:repeat(2,minmax(220px,1fr))}}
        @media(max-width:720px){.fw-grid-a,.fw-grid-b{grid-template-columns:1fr;overflow-x:visible}.fw-insight-grid{grid-template-columns:1fr}.fw-step{min-width:0}.fw-shell{padding:17px 12px}.fw-title{font-size:19px}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Section A — Perhitungan Matrix
    st.markdown(
        f"""
        <section class="fw-shell">
          <h2 class="fw-title">ALUR PERHITUNGAN MATRIX SATISFACTION x IMPORTANCE</h2>
          <p class="fw-subtitle">Enam tahap pengolahan data survei kepuasan menjadi Priority Improvement Matrix,
          mulai dari perhitungan skor sampai pemetaan atribut ke dalam empat kuadran prioritas.</p>
          <div class="fw-grid fw-grid-a">{matrix_cards_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # Section B — Customer Profiling (GMM)
    st.markdown(
        f"""
        <section class="fw-shell">
          <h2 class="fw-title">ALUR CUSTOMER PROFILING (CLUSTERING GMM)</h2>
          <p class="fw-subtitle fw-subtitle-gmm">Pengelompokan pelanggan menjadi 5 Customer Profile menggunakan
          <b>Gaussian Mixture Model (GMM)</b>, yaitu metode clustering yang mengelompokkan pelanggan
          berdasarkan kemiripan pola jawaban survei. Selanjutnya, setiap pelanggan ditempatkan pada
          profil yang paling sesuai dengan karakteristiknya beserta tingkat keyakinan hasil
          pengelompokannya.</p>
          <div class="fw-grid fw-grid-b">{profiling_cards_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # Section C — Insight dari Dashboard
    st.markdown(
        f"""
        <section class="fw-shell">
          <h2 class="fw-title">APA YANG BISA DIDAPATKAN DARI DASHBOARD INI?</h2>
          <div class="fw-insight-grid">{insight_cards_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def main():
    inject_css()
    selected_page = render_top_navigation()

    if selected_page == "H2 SERVICE":
        render_unit_page(
            "service", "Service", "service_respondent", "AHASS"
        )
    elif selected_page == "H3 SPARE PART":
        render_unit_page(
            "parts", "Spare Part", "parts_respondent", "Part Shop"
        )
    elif selected_page == "PROFIL WILAYAH":
        rw_render_region_profile_page()
    elif selected_page == "FRAMEWORK":
        render_framework_placeholder()
    else:
        render_unit_page(
            "sales", "Sales", "sales_respondent", "Dealer"
        )
if __name__ == "__main__":
    main()
