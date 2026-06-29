"""
MONEV MONITOR v12.0 - Absolute Metric Correction (UI/UX Refreshed)
==================================================================
Perbaikan total definisi evaluasi: Menghitung riwayat baris secara murni,
sinkronisasi otomatis tanpa hardcode angka, dan tab audit tetap di posisi terakhir.
Tampilan diperbarui menjadi lebih modern, bersih, dan informatif.
"""

import streamlit as st
import pandas as pd
import re
import io
from difflib import SequenceMatcher

# ════════════════════════════════════════════════════════════════════
# 1. KONFIGURASI UTAMA & THEME KUSTOM (REFRESHED)
# ════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Monev Monitor", layout="wide", page_icon="📊")

st.markdown("""
    <style>
    /* Global Reset & Padding */
    .block-container { padding-top: 2.5rem; padding-bottom: 3rem; max-width: 95%; }
    h1, h2, h3 { font-weight: 700 !important; color: #F8FAFC !important; letter-spacing: -0.02em; }
    
    /* Modern Metric Cards */
    .metric-container {
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-container:hover {
        transform: translateY(-2px);
        border-color: #475569;
    }
    .metric-val {
        font-size: 1.85rem;
        font-weight: 700;
        color: #3B82F6;
        margin-bottom: 4px;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .metric-lbl {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        font-weight: 600;
    }

    /* Modern Audit Alert Card */
    .audit-card {
        background: rgba(239, 68, 68, 0.06);
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 22px;
        border-left: 5px solid #EF4444;
    }
    .card-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 6px;
        color: #FCA5A5;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .card-desc {
        font-size: 0.92rem;
        color: #CBD5E1;
        line-height: 1.5;
        margin-bottom: 0px;
    }

    /* Minimalist Info Card */
    .info-stat-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }

    /* Customizing Streamlit Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; padding-bottom: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 20px; 
        background-color: #1E293B; 
        border-radius: 6px; 
        border: 1px solid #334155;
        color: #94A3B8;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] { 
        background: #3B82F6 !important; 
        color: #FFFFFF !important;
        border-color: #3B82F6 !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
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
# 2. ENGINE DATA (CLEANSING, AUDITOR & RESOLUTION) - TIDAK DIUBAH
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
def create_summary(df_cleaned_final):
    summary_list = []
    df_display_grouped = df_cleaned_final.drop_duplicates(subset=['badan_canonical', 'region', 'tahun'])
    
    for (name, reg), sub in df_display_grouped.groupby(['badan_canonical', 'region']):
        years = sorted(sub['tahun'].unique())
        inf_years = sorted(sub[(sub['kualifikasi'] == 'Informatif')]['tahun'].unique())
        latest_status = sub.sort_values('tahun').iloc[-1]['kualifikasi']
        
        summary_list.append({
            'Nama Badan Publik': name, 
            'Wilayah': reg, 
            'Jumlah Monev': len(years),
            'Tahun Monev': ', '.join(map(str, years)),
            'Tahun Informatif': ', '.join(map(str, inf_years)) if inf_years else '-',
            'Status Terakhir': latest_status,
        })
    return pd.DataFrame(summary_list).sort_values(['Wilayah', 'Nama Badan Publik']).reset_index(drop=True)

def style_summary_row(df_row):
    styles = [''] * len(df_row)
    status_idx = df_row.index.get_loc('Status Terakhir')
    
    status_val = df_row['Status Terakhir']
    status_color = STATUS_COLORS.get(status_val, '#FFFFFF')
    styles[status_idx] = f'color: {status_color}; font-weight: 700;'
    return styles

# ════════════════════════════════════════════════════════════════════
# 3. INTERFACE DASHBOARD UTAMA (REFRESHED VIEW)
# ════════════════════════════════════════════════════════════════════
st.markdown("<h1 style='margin-bottom: 0rem;'>📊 Monev Monitor</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94A3B8; font-size: 1rem; margin-top: -5px; margin-bottom: 1.5rem;'>Sistem Sinkronisasi & Audit Data Keterbukaan Informasi Publik</p>", unsafe_allow_html=True)

# Bungkus file uploader agar rapi
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
        summary_data = create_summary(df_cleaned_final)

        for a in alerts: st.warning(a)

        # Perhitungan Metrik Efisiensi
        total_evaluasi = len(df_cleaned_final) 
        total_badan = summary_data['Nama Badan Publik'].nunique()
        total_informatif_rows = len(df_cleaned_final[df_cleaned_final['kualifikasi'] == 'Informatif'])
        informatif_rate = (total_informatif_rows / total_evaluasi * 100) if total_evaluasi > 0 else 0.0
        pernah_informatif = (summary_data['Tahun Informatif'] != '-').sum()

        # Render 5 KPI Cards Menggunakan HTML Kustom yang Segar
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.markdown(f'<div class="metric-container"><div class="metric-val" style="color:#64748B;">{total_rows_csv:,}</div><div class="metric-lbl">Total Data CSV</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-container"><div class="metric-val" style="color:#3B82F6;">{total_badan:,}</div><div class="metric-lbl">Badan Publik</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-container"><div class="metric-val" style="color:#A855F7;">{total_evaluasi:,}</div><div class="metric-lbl">Total Evaluasi</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="metric-container"><div class="metric-val" style="color:#10B981;">{informatif_rate:.1f}%</div><div class="metric-lbl">Informatif Rate</div></div>', unsafe_allow_html=True)
        m5.markdown(f'<div class="metric-container"><div class="metric-val" style="color:#F59E0B;">{pernah_informatif:,}</div><div class="metric-lbl">Pernah Informatif</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

        # Tab Menu Utama (Audit tetap pada posisi terakhir)
        tab_summary, tab_charts, tab_profile, tab_export, tab_audit = st.tabs([
            "📋 Ringkasan Data", "📈 Analisis Grafik", "🏛️ Profil Instansi", "💾 Ekspor Laporan", "🔍 Hasil Audit Data"
        ])

        # ── TAB 1: RINGKASAN DATA ─────────────────────────────────────
        with tab_summary:
            with st.container(border=True):
                f1, f2, f3 = st.columns([1, 1, 2])
                with f1: f_wilayah = st.selectbox("Saring Wilayah", ["Semua"] + sorted(summary_data['Wilayah'].unique()))
                with f2: f_status = st.selectbox("Saring Status Akhir", ["Semua"] + STATUS_RANK)
                with f3: search_text = st.text_input("Cari Nama Instansi", placeholder="Masukkan kata kunci nama badan publik...")

            f_df = summary_data.copy()
            if f_wilayah != "Semua": f_df = f_df[f_df['Wilayah'] == f_wilayah]
            if f_status != "Semua":  f_df = f_df[f_df['Status Terakhir'] == f_status]
            if search_text:          f_df = f_df[f_df['Nama Badan Publik'].str.contains(search_text, case=False, na=False)]

            styled_df = f_df.reset_index(drop=True).style.apply(style_summary_row, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # ── TAB 2: ANALISIS GRAFIK ────────────────────────────────────
        with tab_charts:
            g1, g2 = st.columns(2)
            with g1:
                with st.container(border=True):
                    st.markdown("<h3 style='font-size:1.1rem; margin-bottom:1rem;'>📈 Tren Perkembangan Status Kualifikasi</h3>", unsafe_allow_html=True)
                    trend = df_cleaned_final.groupby(['tahun', 'kualifikasi']).size().reset_index(name='Jumlah')
                    trend_pivot = trend.pivot(index='tahun', columns='kualifikasi', values='Jumlah').fillna(0)
                    st.bar_chart(trend_pivot[[c for c in STATUS_RANK if c in trend_pivot.columns]], use_container_width=True, height=320)
            with g2:
                with st.container(border=True):
                    st.markdown("<h3 style='font-size:1.1rem; margin-bottom:0.4rem;'>🗺️ Distribusi Status per Wilayah</h3>", unsafe_allow_html=True)
                    selected_year = st.selectbox("Tahun Evaluasi", sorted(df_cleaned_final['tahun'].unique(), reverse=True), label_visibility="collapsed")
                    region_dist = df_cleaned_final[df_cleaned_final['tahun'] == selected_year].groupby(['region', 'kualifikasi']).size().reset_index(name='Jumlah')
                    region_pivot = region_dist.pivot(index='region', columns='kualifikasi', values='Jumlah').fillna(0)
                    st.bar_chart(region_pivot[[c for c in STATUS_RANK if c in region_pivot.columns]], use_container_width=True, height=320)

        # ── TAB 3: PROFIL INSTANSI ────────────────────────────────────
        with tab_profile:
            with st.container(border=True):
                p1, p2 = st.columns([1, 2])
                with p1: p_wil = st.selectbox("Pilih Wilayah Kerja", sorted(df_cleaned_final['region'].unique()), key="p_wil")
                filtered_pool = summary_data[summary_data['Wilayah'] == p_wil]
                with p2: p_badan = st.selectbox("Nama Badan Publik", sorted(filtered_pool['Nama Badan Publik'].unique()), key="p_badan")

            if p_badan:
                instansi_info = summary_data[summary_data['Nama Badan Publik'] == p_badan].iloc[0]
                history_records = df_cleaned_final[df_cleaned_final['badan_canonical'] == p_badan].sort_values('tahun')
                
                st.markdown(f"<h2 style='font-size:1.4rem; margin-top:1rem;'>🏛️ {p_badan}</h2>", unsafe_allow_html=True)
                
               
                c_prof1, c_prof2, c_prof3 = st.columns(3)
                with c_prof1:
                    st.markdown(f'<div class="info-stat-card"><small style="color:#94A3B8;">PARTISIPASI MONEV</small><br><b>{instansi_info["Jumlah Monev"]} Kali Indeks Berjalan</b></div>', unsafe_allow_html=True)
                with c_prof2:
                    st.markdown(f'<div class="info-stat-card"><small style="color:#94A3B8;">TAHUN AKTIF DATA</small><br><b>{instansi_info["Tahun Monev"]}</b></div>', unsafe_allow_html=True)
                with c_prof3:
                    target_color = STATUS_COLORS.get(instansi_info['Status Terakhir'], '#FFFFFF')
                    st.markdown(f'<div class="info-stat-card"><small style="color:#94A3B8;">KUALIFIKASI TERAKHIR</small><br><span style="color:{target_color}; font-weight:700;">{instansi_info["Status Terakhir"]}</span></div>', unsafe_allow_html=True)
                
                hist_table = history_records[['tahun', 'kualifikasi']].rename(columns={'tahun': 'Tahun', 'kualifikasi': 'Hasil Kualifikasi'}).drop_duplicates()
                
                def style_hist_text(val):
                    return f"color: {STATUS_COLORS.get(val, '#FFFFFF')}; font-weight: 700;"
                
                styled_hist = hist_table.set_index('Tahun').style.map(style_hist_text, subset=['Hasil Kualifikasi'])
                st.markdown("<p style='margin-bottom:0.5rem; font-weight:600; color:#94A3B8;'>Histori Lembar Penilaian:</p>", unsafe_allow_html=True)
                st.table(styled_hist)

        # ── TAB 4: EKSPOR LAPORAN ─────────────────────────────────────
        with tab_export:
            with st.container(border=True):
                st.markdown("<h3 style='font-size:1.2rem;'>💾 Unduh Dokumen Hasil Olah Data</h3>", unsafe_allow_html=True)
                st.write("Dapatkan file kompilasi bersih yang siap digunakan untuk keperluan pelaporan resmi eksekutif atau analisis lanjutan.")
                
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as excel_writer:
                    summary_data.to_excel(excel_writer, sheet_name='Ringkasan_Monev', index=False)
                    raw_export = df_cleaned_final[['badan_canonical', 'region', 'tahun', 'kualifikasi']].rename(
                        columns={'badan_canonical': 'Nama Badan Publik', 'region': 'Wilayah', 'tahun': 'Tahun', 'kualifikasi': 'Status'}
                    ).drop_duplicates()
                    raw_export.to_excel(excel_writer, sheet_name='Data_Cleaned_Lengkap', index=False)
                    
                st.download_button(
                    label="📥 Unduh Laporan Format Excel (.xlsx)",
                    data=excel_buffer.getvalue(),
                    file_name="Laporan_Sinkronisasi_Monev.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    
        with tab_audit:
            st.markdown("<h3 style='font-size:1.2rem; margin-bottom:1rem;'>🔍 Validasi & Integritas Berkas CSV</h3>", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="audit-card">
                <div class="card-title">🚨 Tipe 1 — Duplikat Identik Berkas ({len(df_tipe1)} Baris Terdeteksi)</div>
                <div class="card-desc">Ditemukan baris dengan parameter data <b>Nama Instansi + Wilayah + Tahun + Hasil Kualifikasi</b> yang 100% duplikat pada file mentah. Satu entitas dipertahankan dan baris kembarannya otomatis direduksi demi menjaga akurasi kalkulasi performa.</div>
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
    # Tampilan Landing Page Awal saat CSV belum dimasukkan
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.info("Silakan unggah file CSV data Monev Anda terlebih dahulu di atas untuk memunculkan dashboard analisis interaktif.")