"""
MONEV MONITOR v12.1 - Enhanced UI/UX with Flaticon Elements & True PDF Graphics
==================================================================
Sistem Sinkronisasi & Audit Data Keterbukaan Informasi Publik.
"""

import streamlit as st
import pandas as pd
import re
import io
import plotly.express as px  
import plotly.graph_objects as go  
from difflib import SequenceMatcher

# Import ReportLab & Komponen Gambar PDF Cetak Resmi
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ════════════════════════════════════════════════════════════════════
# 1. KONFIGURASI UTAMA & THEME KUSTOM
# ════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Monev Monitor", layout="wide", page_icon="📊")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 95%; }
    h1, h2, h3, h4 { font-weight: 700 !important; color: #F8FAFC !important; letter-spacing: -0.02em; }
    
    .header-container { display: flex; align-items: center; gap: 16px; margin-bottom: 1.5rem; }
    .header-icon { width: 50px; height: 50px; }

    .metric-container {
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 22px 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
    }
    .metric-container:hover {
        transform: translateY(-3px); border-color: #475569;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
    }
    .metric-icon { width: 32px; height: 32px; margin-bottom: 10px; }
    .metric-val { font-size: 1.9rem; font-weight: 700; margin-bottom: 2px; font-family: system-ui; }
    .metric-lbl { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: #94A3B8; font-weight: 600; }

    .audit-card {
        background: rgba(239, 68, 68, 0.03); border: 1px solid rgba(239, 68, 68, 0.15);
        border-radius: 12px; padding: 20px; margin-bottom: 22px; border-left: 5px solid #EF4444;
    }
    .card-title { font-size: 1.15rem; font-weight: 600; margin-bottom: 8px; color: #FCA5A5; display: flex; align-items: center; gap: 10px; }
    .card-title img { width: 24px; height: 24px; }
    .card-desc { font-size: 0.92rem; color: #CBD5E1; line-height: 1.6; }

    .info-stat-card {
        background: #1E293B; border: 1px solid #334155; border-radius: 10px;
        padding: 16px 20px; margin-bottom: 12px; display: flex; align-items: center; gap: 14px;
    }
    .info-stat-icon { width: 28px; height: 28px; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; padding-bottom: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 24px; background-color: #1E293B; border-radius: 8px; 
        border: 1px solid #334155; color: #94A3B8; font-weight: 500;
    }
    .stTabs [aria-selected="true"] { 
        background: #3B82F6 !important; color: #FFFFFF !important; border-color: #3B82F6 !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

WILAYAH_BALI = ['badung', 'buleleng', 'gianyar', 'tabanan', 'klungkung', 'karangasem', 'bangli', 'jembrana', 'denpasar', 'bali']

SINGKATAN_MAP = {
    r'\bbappeda\b': 'badan perencanaan pembangunan daerah',
    r'\bbalitbang\b': 'badan penelitian dan pengembangan',
    r'\bbkpsdm\b': 'badan kepegawaian dan pengembangan sumber daya manusia',
    r'\bdpmptsp\b': 'dinas penanaman modal dan pelayanan terpadu satu pintu',
    r'\bdpmd\b': 'dinas pemberdayaan masyarakat desa',
    r'\bbapenda\b': 'badan pendapatan daerah',
    r'\bdiskominfo\b': 'dinas komunikasi dan informatika',
    r'\batr/bpn\b': 'kantor pertanahan badan pertanahan nasional',
    r'\bsatpol pp\b': 'satuan polisi pamong praja',
    r'\bbpbd\b': 'badan penanggulangan bencana daerah',
    r'\bbpkad\b': 'badan pengelola keuangan dan aset daerah',
    r'\bbakeuda\b': 'badan keuangan daerah',
    r'\bbapedalibang\b': 'badan perencanaan penelitian dan pengembangan',
    r'\bdprd\b': 'dewan perwakilan rakyat daerah',
}

STATUS_RANK = ['Informatif', 'Menuju Informatif', 'Cukup Informatif', 'Kurang Informatif', 'Tidak Informatif', 'Tidak Diketahui']
STATUS_COLORS = {
    'Informatif': '#10B981', 'Menuju Informatif': '#3B82F6', 'Cukup Informatif': '#F59E0B', 
    'Kurang Informatif': '#F97316', 'Tidak Informatif': '#EF4444', 'Tidak Diketahui': '#64748B'
}

# ════════════════════════════════════════════════════════════════════
# 2. DATA PROCESSING ENGINE
# ════════════════════════════════════════════════════════════════════
@st.cache_data
def transform_pipeline(df_raw):
    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.lower()
    
    rename_rules = {
        'badan publik': 'badan', 'provinsi/kabupaten/kota': 'region',
        'provinsi': 'region', 'kabupaten/kota': 'region'
    }
    df = df.rename(columns=rename_rules)
    
    required = ['badan', 'region', 'tahun', 'kualifikasi']
    if not all(col in df.columns for col in required):
        return None, ["Struktur file tidak sesuai. Pastikan file CSV memiliki kolom: 'Badan Publik', 'Region', 'Tahun', dan 'Kualifikasi'."]

    df = df[required].copy()
    df['badan'] = df['badan'].astype(str).apply(lambda x: re.sub(r'\s+', ' ', re.sub(r'([a-z])([A-Z])', r'\1 \2', x)).strip())
    df['region'] = df['region'].astype(str).apply(lambda x: re.sub(r'^(Kabupaten|Kota)\s+', '', x.strip(), flags=re.IGNORECASE).title())
    
    def generate_match_key(row):
        key = str(row['badan']).lower()
        key = re.sub(r'\b(kabupaten|kota|provinsi)\b', '', key)
        reg = str(row['region']).lower()
        key = re.sub(r'\b' + re.escape(reg) + r'\b', '', key)
        for w in WILAYAH_BALI:
            key = re.sub(r'\b' + re.escape(w) + r'\b', '', key)
        for pattern, replacement in SINGKATAN_MAP.items():
            key = re.sub(pattern, replacement, key)
        return re.sub(r'\s+', ' ', key).strip()

    df['badan_key'] = df.apply(generate_match_key, axis=1)
    
    k_map = {k.lower(): k for k in STATUS_RANK}
    df['kualifikasi'] = df['kualifikasi'].astype(str).str.strip().str.lower().map(k_map).fillna('Tidak Diketahui')
    
    df['tahun'] = pd.to_numeric(df['tahun'], errors='coerce')
    df = df.dropna(subset=['tahun'])
    df['tahun'] = df['tahun'].astype(int)
    
    return df, []

@st.cache_data
def resolve_entities(df, tolerance=0.92):
    uniques = df[['badan_key', 'badan', 'region']].drop_duplicates(subset=['badan_key', 'region']).to_dict('records')
    parent = {i: i for i in range(len(uniques))}
    
    def find(i):
        if parent[i] == i: return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        root_i, root_j = find(i), find(j)
        if root_i != root_j: parent[root_i] = root_j

    for i in range(len(uniques)):
        for j in range(i + 1, len(uniques)):
            if uniques[i]['region'] != uniques[j]['region']:
                continue
            ki, kj = uniques[i]['badan_key'], uniques[j]['badan_key']
            if ki == kj:
                union(i, j)
            elif SequenceMatcher(None, ki, kj).ratio() >= tolerance:
                union(i, j)

    group_clusters = {}
    for idx in range(len(uniques)):
        root = find(idx)
        group_clusters.setdefault(root, []).append(uniques[idx]['badan'])
        
    canonical_names = {root: max(names, key=len) for root, names in group_clusters.items()}
    lookup = {(uniques[idx]['badan_key'], uniques[idx]['region']): canonical_names[find(idx)] for idx in range(len(uniques))}
    
    df = df.copy()
    df['badan_canonical'] = df.apply(lambda r: lookup.get((r['badan_key'], r['region']), r['badan']), axis=1)
    return df

@st.cache_data
def run_data_auditor(df_resolved):
    duplicate_mask = df_resolved.duplicated(subset=['badan_canonical', 'region', 'tahun', 'kualifikasi'], keep=False)
    df_tipe1 = df_resolved[duplicate_mask].copy()
    
    df_cleaned_final = df_resolved.drop_duplicates(subset=['badan_canonical', 'region', 'tahun', 'kualifikasi'])
    return df_tipe1, df_cleaned_final

@st.cache_data
def create_summary(df_cleaned_final, tahun_filter="Semua"):
    summary_list = []
    
    # Memotong data kerja dasar agar sinkron penuh dengan visualisasi grafik
    if tahun_filter != "Semua":
        df_working = df_cleaned_final[df_cleaned_final['tahun'] == int(tahun_filter)]
    else:
        df_working = df_cleaned_final
        
    # PERBAIKAN: JANGAN pakai drop_duplicates lintasan kolom tahun di sini, 
    # melainkan langsung looping berbasis rekaman baris riwayat yang aktif di database grafik
    for idx, row in df_working.iterrows():
        name_canonical = row['badan_canonical']
        name_real = row['badan']
        reg = row['region']
        current_year = row['tahun']
        current_status = row['kualifikasi']
        
        # Ambil keseluruhan histori instansi terkait dari master data bersih
        master_sub = df_cleaned_final[(df_cleaned_final['badan_canonical'] == name_canonical) & (df_cleaned_final['region'] == reg)]
        years = sorted(master_sub['tahun'].unique())
        inf_years = sorted(master_sub[(master_sub['kualifikasi'] == 'Informatif')]['tahun'].unique())
        
        # Jika filter per tahun diaktifkan, tampilkan Nama Real dan Status Spesifik tahun itu.
        # Jika semua tahun, tampilkan Nama Baku (Canonical) dan Status Paling Baru.
        if tahun_filter != "Semua":
            display_name = name_real
            display_status = current_status
        else:
            display_name = name_canonical
            # Ambil status paling baru dari seluruh rekam jejak tahun
            display_status = master_sub.sort_values('tahun').iloc[-1]['kualifikasi']
            
        summary_list.append({
            'Nama Badan Publik': display_name, 
            'Wilayah': reg, 
            'Jumlah Monev': len(years),
            'Tahun Monev': ', '.join(map(str, years)),
            'Tahun Informatif': ', '.join(map(str, inf_years)) if inf_years else '-',
            'Status Terakhir': display_status,
            'tahun_aktif': current_year # Kolom bantu internal pengaman pencarian data ganda
        })
        
    if not summary_list:
        return pd.DataFrame(columns=['Nama Badan Publik', 'Wilayah', 'Jumlah Monev', 'Tahun Monev', 'Tahun Informatif', 'Status Terakhir'])
        
    # Buat DataFrame awal dan bersihkan duplikasi bentukan rekaman baris hasil loop internal tabel jika semua tahun aktif
    df_res = pd.DataFrame(summary_list)
    if tahun_filter == "Semua":
        df_res = df_res.drop_duplicates(subset=['Nama Badan Publik', 'Wilayah'])
        
    return df_res.sort_values(['Wilayah', 'Nama Badan Publik']).reset_index(drop=True)

def style_summary_row(df_row):
    styles = [''] * len(df_row)
    if 'Status Terakhir' in df_row.index:
        status_idx = df_row.index.get_loc('Status Terakhir')
        status_val = df_row['Status Terakhir']
        status_color = STATUS_COLORS.get(status_val, '#FFFFFF')
        styles[status_idx] = f'color: {status_color}; font-weight: 700;'
    return styles

# ════════════════════════════════════════════════════════════════════
# 3. INTERFACE DASHBOARD UTAMA
# ════════════════════════════════════════════════════════════════════
with st.container(border=True):
    uploaded_file = st.file_uploader("Unggah Berkas CSV Data Monev", type=["csv"], help="Pastikan file memiliki kolom Nama Badan Publik, Region, Tahun, dan Kualifikasi")

if uploaded_file is not None:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=None, engine='python', on_bad_lines='skip')
        total_rows_csv = len(df_raw)
        
        df_clean, alerts = transform_pipeline(df_raw)
        if df_clean is None:
            st.error(alerts[0])
            st.stop()

        df_resolved = resolve_entities(df_clean)
        df_tipe1, df_cleaned_final = run_data_auditor(df_resolved)
        
        summary_data_master = create_summary(df_cleaned_final, tahun_filter="Semua")

        for a in alerts: st.warning(a)

        total_evaluasi = len(df_cleaned_final) 
        total_badan = summary_data_master['Nama Badan Publik'].nunique()
        total_informatif_rows = len(df_cleaned_final[df_cleaned_final['kualifikasi'] == 'Informatif'])
        informatif_rate = (total_informatif_rows / total_evaluasi * 100) if total_evaluasi > 0 else 0.0
        pernah_informatif = (summary_data_master['Tahun Informatif'] != '-').sum()

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.markdown(f'<div class="metric-container"><img src="https://cdn-icons-png.flaticon.com/512/2875/2875433.png" class="metric-icon"><div class="metric-val" style="color:#64748B;">{total_rows_csv:,}</div><div class="metric-lbl">Total Data CSV</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-container"><img src="https://cdn-icons-png.flaticon.com/512/9167/9167014.png" class="metric-icon"><div class="metric-val" style="color:#3B82F6;">{total_badan:,}</div><div class="metric-lbl">Badan Publik</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-container"><img src="https://cdn-icons-png.flaticon.com/512/2618/2618245.png" class="metric-icon"><div class="metric-val" style="color:#A855F7;">{total_evaluasi:,}</div><div class="metric-lbl">Total Evaluasi</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="metric-container"><img src="https://cdn-icons-png.flaticon.com/512/3125/3125856.png" class="metric-icon"><div class="metric-val" style="color:#10B981;">{informatif_rate:.1f}%</div><div class="metric-lbl">Informatif Rate</div></div>', unsafe_allow_html=True)
        m5.markdown(f'<div class="metric-container"><img src="https://cdn-icons-png.flaticon.com/512/16542/16542456.png" class="metric-icon"><div class="metric-val" style="color:#F59E0B;">{pernah_informatif:,}</div><div class="metric-lbl">Pernah Informatif</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

        tab_summary, tab_charts, tab_profile, tab_export, tab_audit = st.tabs([
            "📋 Ringkasan Data", "📈 Analisis Grafik", "🏛️ Profil Instansi", "💾 Ekspor Laporan", "🔍 Hasil Audit Data"
        ])

        # ── TAB 1: RINGKASAN DATA ─────────────────────────────────────
        with tab_summary:
            with st.container(border=True):
                f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
                with f1: f_wilayah = st.selectbox("Saring Wilayah", ["Semua"] + sorted(summary_data_master['Wilayah'].unique()))
                with f2: f_status = st.selectbox("Saring Status Akhir", ["Semua"] + STATUS_RANK)
                with f3: 
                    available_years_list = sorted(df_cleaned_final['tahun'].unique(), reverse=True)
                    f_tahun = st.selectbox("Saring Tahun", ["Semua"] + [str(y) for y in available_years_list])
                with f4: search_text = st.text_input("Cari Nama Instansi", placeholder="Masukkan kata kunci nama badan publik...")

            # Membangun summary dinamis yang isinya 1:1 mengikuti data bersih milik grafik
            summary_data_filtered = create_summary(df_cleaned_final, tahun_filter=f_tahun)
            f_df = summary_data_filtered.copy()
            
            if f_wilayah != "Semua": f_df = f_df[f_df['Wilayah'] == f_wilayah]
            if f_status != "Semua":  f_df = f_df[f_df['Status Terakhir'] == f_status]
            if search_text:          f_df = f_df[f_df['Nama Badan Publik'].str.contains(search_text, case=False, na=False)]

            f_df = f_df.reset_index(drop=True)
            f_df.insert(0, 'No', f_df.index + 1)

            # Buang kolom pembantu internal sebelum dirender ke user interface
            if 'tahun_aktif' in f_df.columns:
                f_render = f_df.drop(columns=['tahun_aktif'])
            else:
                f_render = f_df.copy()

            styled_df = f_render.style.apply(style_summary_row, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

       # ── TAB 2: ANALISIS GRAFIK ────────────────────────────────────
        with tab_charts:
            st.markdown("<h3 style='font-size:1.2rem; margin-bottom:1.5rem;'>📈 Grafik Analisis Keterbukaan Informasi</h3>", unsafe_allow_html=True)
            
            # Kontainer Grafik 1: Grafik Batang Komparasi Tahunan
            with st.container(border=True):
                st.markdown(
                    "<h4 style='font-size:1.1rem; margin-bottom:1rem; color:#F8FAFC;'>📊 Tren Kualifikasi Badan Publik Per Tahun</h4>",
                    unsafe_allow_html=True
                )

                years_range = list(range(2016, 2026))
                summary_list = []
                
                for yr in years_range:
                    sub_yr = df_cleaned_final[df_cleaned_final['tahun'] == yr]
                    total_dm = len(sub_yr)
                    
                    if yr in [2016, 2017, 2018]:
                        inf = 0
                        menuju = 0
                        cukup = 0
                        kurang = 0
                        tidak_inf = 0
                        tidak_diketahui = 0
                        belum_inf = total_dm
                    else:
                        inf = len(sub_yr[sub_yr['kualifikasi'] == 'Informatif'])
                        menuju = len(sub_yr[sub_yr['kualifikasi'] == 'Menuju Informatif'])
                        cukup = len(sub_yr[sub_yr['kualifikasi'] == 'Cukup Informatif'])
                        kurang = len(sub_yr[sub_yr['kualifikasi'] == 'Kurang Informatif'])
                        tidak_inf = len(sub_yr[sub_yr['kualifikasi'] == 'Tidak Informatif'])
                        tidak_diketahui = len(sub_yr[sub_yr['kualifikasi'] == 'Tidak Diketahui'])
                        belum_inf = total_dm - inf
                    
                    summary_list.append({
                        "tahun": yr,
                        "Jumlah_Dimonev": total_dm,
                        "Informatif": inf,
                        "Menuju Informatif": menuju,
                        "Cukup Informatif": cukup,
                        "Kurang Informatif": kurang,
                        "Tidak Informatif": tidak_inf,
                        "Tidak Diketahui": tidak_diketahui,
                        "Jumlah_Belum_Informatif": belum_inf
                    })
                
                summary = pd.DataFrame(summary_list)

                fig_trend = go.Figure()

                fig_trend.add_trace(go.Bar(
                    x=summary["tahun"], y=summary["Jumlah_Dimonev"],
                    name="Total Dimonev", marker_color="#64748B",
                    text=summary["Jumlah_Dimonev"], textposition="outside"
                ))
                
                fig_trend.add_trace(go.Bar(
                    x=summary["tahun"], y=summary["Informatif"],
                    name="Informatif", marker_color=STATUS_COLORS['Informatif'],
                    text=summary["Informatif"], textposition="outside"
                ))

                fig_trend.add_trace(go.Bar(
                    x=summary["tahun"], y=summary["Menuju Informatif"],
                    name="Menuju Informatif", marker_color=STATUS_COLORS['Menuju Informatif'],
                    text=summary["Menuju Informatif"], textposition="outside"
                ))

                fig_trend.add_trace(go.Bar(
                    x=summary["tahun"], y=summary["Cukup Informatif"],
                    name="Cukup Informatif", marker_color=STATUS_COLORS['Cukup Informatif'],
                    text=summary["Cukup Informatif"], textposition="outside"
                ))

                fig_trend.add_trace(go.Bar(
                    x=summary["tahun"], y=summary["Kurang Informatif"],
                    name="Kurang Informatif", marker_color=STATUS_COLORS['Kurang Informatif'],
                    text=summary["Kurang Informatif"], textposition="outside"
                ))

                fig_trend.add_trace(go.Bar(
                    x=summary["tahun"], y=summary["Tidak Informatif"],
                    name="Tidak Informatif", marker_color=STATUS_COLORS['Tidak Informatif'],
                    text=summary["Tidak Informatif"], textposition="outside"
                ))

                fig_trend.update_layout(
                    barmode="group", height=550, bargap=0.2,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#F8FAFC", family="system-ui"),
                    xaxis=dict(
                        title="Tahun", showgrid=False, 
                        tickmode='array', tickvals=years_range, ticktext=[str(y) for y in years_range],
                        tickfont=dict(size=13)
                    ),
                    yaxis=dict(title="Jumlah Badan Publik", showgrid=True, gridcolor="#334155"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    margin=dict(l=40, r=40, t=80, b=40)
                )

                fig_trend.update_traces(
                    textfont=dict(size=10, color="white"),
                    marker_line_color="white", marker_line_width=0.3,
                    hovertemplate="<b>Tahun:</b> %{x} &nbsp;&nbsp;•&nbsp;&nbsp; <b>Jumlah:</b> %{y} Instansi<extra></extra>"
                )

                st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

                st.markdown("---")
                st.markdown("<h5 style='color:#94A3B8; margin-bottom:10px;'>📝 Keterangan & Penjelasan Analisis:</h5>", unsafe_allow_html=True)
                
                narasi_dashboard = ""
                pdf_table_data = [["Tahun", "Total Dimonev", "Informatif", "Menuju Inf.", "Cukup Inf.", "Kurang Inf.", "Tidak Inf."]]
                pdf_narasi_konten = []
                
                available_years = sorted(df_cleaned_final["tahun"].unique(), reverse=True)
                fallback_year = available_years[0] if available_years else 2025

                for idx, row in summary.sort_values("tahun", ascending=False).iterrows():
                    yr = int(row['tahun'])
                    total = int(row['Jumlah_Dimonev'])
                    inf = int(row['Informatif'])
                    menuju = int(row['Menuju Informatif'])
                    cukup = int(row['Cukup Informatif'])
                    kurang = int(row['Kurang Informatif'])
                    tidak_inf = int(row['Tidak Informatif'])
                    
                    if yr in [2016, 2017, 2018]:
                        item_text = f"Tahun {yr}: Terdata sebanyak {total} Badan Publik yang diaudit. (Pada tahun {yr} belum diterbitkan kualifikasi informatif secara resmi)."
                        pdf_table_data.append([str(yr), str(total), "-", "-", "-", "-", "-"])
                    else:
                        if total == 0:
                            item_text = f"Tahun {yr}: Tidak ada pelaksanaan Monev (0 Instansi diaudit)."
                        else:
                            rate = (inf / total * 100) if total > 0 else 0.0
                            item_text = f"Tahun {yr}: Terdata sebanyak {total} Badan Publik diaudit. Hasil Kualifikasi detail: {inf} Informatif ({rate:.1f}%), {menuju} Menuju Informatif, {cukup} Cukup Informatif, {kurang} Kurang Informatif, dan {tidak_inf} Tidak Informatif."
                        pdf_table_data.append([str(yr), str(total), str(inf), str(menuju), str(cukup), str(kurang), str(tidak_inf)])
                    
                    narasi_dashboard += f"* {item_text}\n"
                    pdf_narasi_konten.append(item_text)

                st.markdown(narasi_dashboard)

                try:
                    fig_trend_pdf = go.Figure(fig_trend)
                    fig_trend_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white", font=dict(color="black"))
                    fig_trend_pdf.update_traces(textposition="outside", textfont=dict(color="black", size=8))
                    img_trend_bytes = fig_trend_pdf.to_image(format="png", width=780, height=380, engine="kaleido")

                    pdf_buffer = io.BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=40)
                    styles = getSampleStyleSheet()
                    
                    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=15, leading=18, textColor=colors.HexColor('#0F172A'), spaceAfter=15)
                    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=11, leading=14, textColor=colors.HexColor('#1E293B'), spaceBefore=12, spaceAfter=6)
                    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#334155'))
                    
                    story = []
                    story.append(Paragraph("LAPORAN CAPAIAN MONEV KETERBUKAAN INFORMASI MULTI-TAHUN", title_style))
                    story.append(Spacer(1, 10))
                    
                    story.append(Paragraph("1. TABEL DATA RAGAM KUALIFIKASI HISTORIS", h2_style))
                    t = Table(pdf_table_data, colWidths=[45, 85, 70, 75, 75, 75, 75])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                        ('FONTSIZE', (0,0), (-1,-1), 8),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 15))
                    
                    story.append(Paragraph("2. DIAGRAM VISUALISASI PERKEMBANGAN STRATIFIKASI KUALIFIKASI", h2_style))
                    story.append(Image(io.BytesIO(img_trend_bytes), width=540, height=260))
                    story.append(Spacer(1, 15))
                    
                    story.append(Paragraph("3. KETERANGAN & CATATAN AUDIT:", h2_style))
                    for teks in pdf_narasi_konten:
                        story.append(Paragraph(f"• {teks}", body_style))
                        story.append(Spacer(1, 3))
                    
                    doc.build(story)
                    
                    st.download_button(
                        label=f"📥 Unduh Laporan PDF Lengkap (+Grafik & Analisis Rinci)",
                        data=pdf_buffer.getvalue(),
                        file_name=f"Laporan_Kinerja_Monev_{fallback_year}.pdf",
                        mime="application/pdf"
                    )
                except Exception as pdf_err:
                    st.error(f"Gagal menyiapkan dokumen ekspor PDF: {str(pdf_err)}")

            st.markdown("<br>", unsafe_allow_html=True)

            tahun_terpilih = st.selectbox(
                "Pilih Tahun Evaluasi Global",
                options=available_years,
                key="sb_tahun_global"
            )

            # Kontainer Grafik 2: Distribusi Per Wilayah
            with st.container(border=True):
                st.markdown(
                    f"<h4 style='font-size:1.1rem; color:#F8FAFC; margin-bottom:1rem;'>🗺️ Distribusi Status per Wilayah (Tahun {tahun_terpilih})</h4>",
                    unsafe_allow_html=True
                )

                df_filtered_year = df_cleaned_final[df_cleaned_final["tahun"] == tahun_terpilih]

                df_region_chart = (
                    df_filtered_year
                    .groupby(["region", "kualifikasi"])
                    .size()
                    .reset_index(name="Jumlah")
                )

                fig_region = px.bar(
                    df_region_chart,
                    x="region", y="Jumlah", color="kualifikasi",
                    barmode="stack",
                    category_orders={"kualifikasi": STATUS_RANK},
                    color_discrete_map=STATUS_COLORS,
                    labels={"region": "Wilayah", "Jumlah": "Jumlah Instansi", "kualifikasi": "Status Kualifikasi"},
                    height=550
                )

                fig_region.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#F8FAFC", family="system-ui"),
                    hoverlabel=dict(bgcolor="#1E293B", font_size=13, font_family="system-ui"),
                    xaxis=dict(tickangle=0, automargin=True, showgrid=False, tickfont=dict(size=12)),
                    yaxis=dict(showgrid=True, gridcolor="#334155"),
                    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                    margin=dict(l=40, r=40, t=20, b=60)
                )

                fig_region.update_traces(
                    marker_line_color="#0F172A", marker_line_width=0.5,
                    hovertemplate="<b>Kab/Kota:</b> %{x} &nbsp;&nbsp;•&nbsp;&nbsp; <b>Predikat:</b> %{customdata[0]} &nbsp;&nbsp;•&nbsp;&nbsp; <b>Hasil:</b> %{y} Instansi<extra></extra>",
                    customdata=df_region_chart[["kualifikasi"]]
                )

                st.plotly_chart(fig_region, use_container_width=True, config={"displayModeBar": False})
        # ── TAB 3: PROFIL INSTANSI ────────────────────────────────────
        with tab_profile:
            with st.container(border=True):
                p1, p2 = st.columns([1, 2])
                with p1: p_wil = st.selectbox("Pilih Wilayah Kerja", sorted(df_cleaned_final['region'].unique()), key="p_wil")
                filtered_pool = summary_data_master[summary_data_master['Wilayah'] == p_wil]
                with p2: p_badan = st.selectbox("Nama Badan Publik", sorted(filtered_pool['Nama Badan Publik'].unique()), key="p_badan")

            if p_badan:
                instansi_info = summary_data_master[summary_data_master['Nama Badan Publik'] == p_badan].iloc[0]
                history_records = df_cleaned_final[df_cleaned_final['badan_canonical'] == p_badan].sort_values('tahun')
                
                st.markdown(f"<h2 style='font-size:1.4rem; margin-top:1rem;'>🏛️ {p_badan}</h2>", unsafe_allow_html=True)
                
                c_prof1, c_prof2, c_prof3 = st.columns(3)
                with c_prof1:
                    st.markdown(f'<div class="info-stat-card"><img src="https://cdn-icons-png.flaticon.com/512/3652/3652191.png" class="info-stat-icon"><div><small style="color:#94A3B8; display:block; margin-bottom:2px;">PARTISIPASI MONEV</small><b>{instansi_info["Jumlah Monev"]} Kali Indeks Berjalan</b></div></div>', unsafe_allow_html=True)
                with c_prof2:
                    st.markdown(f'<div class="info-stat-card"><img src="https://cdn-icons-png.flaticon.com/512/747/747310.png" class="info-stat-icon"><div><small style="color:#94A3B8; display:block; margin-bottom:2px;">TAHUN AKTIF DATA</small><b>{instansi_info["Tahun Monev"]}</b></div></div>', unsafe_allow_html=True)
                with c_prof3:
                    target_color = STATUS_COLORS.get(instansi_info['Status Terakhir'], '#FFFFFF')
                    st.markdown(f'<div class="info-stat-card"><img src="https://cdn-icons-png.flaticon.com/512/6532/6532019.png" class="info-stat-icon"><div><small style="color:#94A3B8; display:block; margin-bottom:2px;">KUALIFIKASI TERAKHIR</small><span style="color:{target_color}; font-weight:700;">{instansi_info["Status Terakhir"]}</span></div></div>', unsafe_allow_html=True)
                
                hist_table = history_records[['tahun', 'kualifikasi']].rename(columns={'tahun': 'Tahun', 'kualifikasi': 'Hasil Kualifikasi'}).drop_duplicates()
                
                def style_hist_text(val):
                    return f"color: {STATUS_COLORS.get(val, '#FFFFFF')}; font-weight: 700;"
                
                styled_hist = hist_table.set_index('Tahun').style.map(style_hist_text, subset=['Hasil Kualifikasi'])
                st.markdown("<p style='margin-top:1rem; margin-bottom:0.5rem; font-weight:600; color:#94A3B8;'>Histori Lembar Penilaian:</p>", unsafe_allow_html=True)
                st.table(styled_hist)

        # ── TAB 4: EKSPOR LAPORAN ─────────────────────────────────────
        with tab_export:
            with st.container(border=True):
                st.markdown("<h3 style='font-size:1.2rem;'>💾 Unduh Dokumen Hasil Olah Data</h3>", unsafe_allow_html=True)
                st.write("Dapatkan file kompile bersih yang siap digunakan untuk pelaporan resmi atau analisis lanjutan.")
                
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as excel_writer:
                    summary_data_master.to_excel(excel_writer, sheet_name='Ringkasan_Monev', index=False)
                    raw_export = df_cleaned_final[['badan_canonical', 'region', 'tahun', 'kualifikasi']].rename(
                        columns={'badan_canonical': 'Nama Badan Publik', 'region': 'Wilayah', 'tahun': 'Tahun', 'kualifikasi': 'Status'}
                    ).drop_duplicates()
                    raw_export.to_excel(excel_writer, sheet_name='Data_Cleaned_Lengkap', index=False)
                    
                st.download_button(
                    label="📥 Unduh Laporan Kumpulan Data Format Excel (.xlsx)",
                    data=excel_buffer.getvalue(),
                    file_name="Laporan_Sinkronisasi_Monev.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        # ── TAB 5: HASIL AUDIT DATA ────────────────────────────────────
        with tab_audit:
            st.markdown("<h3 style='font-size:1.2rem; margin-bottom:1rem;'>🔍 Validasi & Integritas Berkas CSV</h3>", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="audit-card">
                <div class="card-title">
                    <img src="https://cdn-icons-png.flaticon.com/512/564/564619.png" alt="Warning Icon">
                    🚨 Tipe 1 — Duplikat Identik Berkas ({len(df_tipe1)} Baris Terdeteksi)
                </div>
                <div class="card-desc">Ditemukan baris dengan parameter data <b>Nama Instansi + Wilayah + Tahun + Hasil Kualifikasi</b> yang 100% duplikat sejati pada file mentah. Satu entitas dipertahankan demi keandalan data.</div>
            </div>
            """, unsafe_allow_html=True)
            
            if not df_tipe1.empty:
                st.dataframe(df_tipe1[['badan', 'region', 'tahun', 'kualifikasi']], use_container_width=True, hide_index=True)
            else:
                st.info("Sempurna! Tidak ada duplikat entri data sejati yang terdeteksi dalam berkas.")

            st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                st.markdown("<p style='font-weight:600; margin-bottom:0.8rem; color:#94A3B8;'>Statistik Rekonsiliasi Log Audit:</p>", unsafe_allow_html=True)
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.markdown(f"📦 **Total Baris Mentah:** {total_rows_csv:,} Baris")
                col_r2.markdown(f"✂️ **Reduksi Duplikat Identik:** {len(df_tipe1)//2} Baris")
                col_r3.markdown(f"✅ **Total Riwayat Bersih:** {total_evaluasi:,} Baris")
            
    except Exception as e:
        st.error(f"Gagal memproses file CSV: {str(e)}")
else:
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.info("Silakan unggah file CSV data Monev Anda terlebih dahulu di atas untuk memunculkan dashboard analisis interaktif.")
