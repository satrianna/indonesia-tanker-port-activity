"""
Port Activity Snapshot - Analisis Tren Tanker
Dashboard interaktif untuk menganalisis tren aktivitas kapal tanker
di pelabuhan-pelabuhan Indonesia (port calls, volume import & export).

Sumber data: indonesia_data_shipment.csv (2019 - 2026)
"""

from pathlib import Path

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import timedelta

APP_DIR = Path(__file__).parent

MONTH_NAMES_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

# ----------------------------------------------------------------------------
# KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Port Activity Snapshot - Tren Tanker",
    page_icon="🛢️",
    layout="wide",
    # "auto" (bukan "expanded"): sidebar otomatis collapsed di layar sempit
    # (HP) dan tetap terbuka di layar lebar (laptop/desktop), tanpa perlu
    # deteksi device manual.
    initial_sidebar_state="auto",
)

# Sedikit CSS untuk merapikan tampilan di layar sempit (HP):
# - padding halaman dipangkas biar tidak boros ruang
# - ukuran angka/label metric dikecilkan sedikit di layar <640px biar tidak wrap
# - menu titik-tiga bawaan Streamlit (Deploy/Settings) disembunyikan karena
#   tidak relevan untuk pengunjung publik; hapus blok #stToolbar ini kalau
#   Anda (sebagai developer) masih perlu mengaksesnya lewat UI app.
# - touch-action: pan-y pada grafik Plotly & tabel data supaya saat pengguna
#   scroll halaman di HP dan jarinya tidak sengaja "kepencet" grafik/tabel,
#   browser tetap memperlakukan gesture itu sebagai scroll vertikal biasa,
#   bukan drag/zoom/geser internal milik komponennya. Ini yang menyebabkan
#   tampilan terlihat "kegeser" sebelumnya.
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        @media (max-width: 640px) {
            .block-container {
                padding-top: 1rem;
                padding-left: 0.6rem;
                padding-right: 0.6rem;
            }
            [data-testid="stMetricValue"] { font-size: 1.25rem; }
            [data-testid="stMetricLabel"] { font-size: 0.72rem; }
            h1 { font-size: 1.35rem !important; }
            h3 { font-size: 1.05rem !important; }
        }
        [data-testid="stToolbar"] { visibility: hidden; }

        /* Kunci gesture sentuh agar chart & tabel tidak ikut "kegeser"
           saat tersenggol jari ketika pengguna sedang scroll halaman. */
        .js-plotly-plot, .js-plotly-plot .plot-container, .js-plotly-plot .svg-container {
            touch-action: pan-y !important;
        }
        [data-testid="stDataFrame"], [data-testid="stDataFrame"] * {
            touch-action: pan-y !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# displayModeBar: toolbar zoom/pan Plotly dimatikan -> lebih bersih di HP
# scrollZoom & doubleClick dimatikan juga supaya scroll/double-tap pengguna
# tidak pernah ditangkap sebagai perintah zoom oleh grafik.
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False}


def lock_figure(fig):
    """Kunci interaksi drag/zoom pada chart Plotly supaya saat pengguna scroll
    dan jarinya tidak sengaja menyentuh grafik di HP, tampilan (skala/posisi
    sumbu) tidak ikut berubah. Hover tooltip tetap berfungsi normal."""
    fig.update_layout(dragmode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


# ----------------------------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Memuat data pelabuhan...")
def load_data() -> pd.DataFrame:
    df = pd.read_csv(APP_DIR / "indonesia_shipment.csv.gz", parse_dates=["date"])
    df["tanker_volume"] = df["import_tanker"] + df["export_tanker"]
    df["total_volume"] = df["import"] + df["export"]
    return df


df = load_data()
MIN_DATE, MAX_DATE = df["date"].min().date(), df["date"].max().date()

# ----------------------------------------------------------------------------
# SIDEBAR - FILTER
# ----------------------------------------------------------------------------
st.sidebar.title("🛢️ Filter Analisis")

# --- Rentang tanggal ---------------------------------------------------------
# Dipilih lewat slider per-bulan (bukan kalender date_input) supaya pengguna
# bisa langsung "melompat" dari data paling awal ke paling akhir (2019-2026)
# dengan menggeser satu handle, tanpa perlu klik mundur bulan-per-bulan
# seperti kalender pemesanan tiket pesawat. Empat tombol pintasan di atasnya
# untuk rentang yang paling sering dipakai.
month_index = pd.period_range(
    start=pd.Timestamp(MIN_DATE).to_period("M"),
    end=pd.Timestamp(MAX_DATE).to_period("M"),
    freq="M",
)


def _period_label(p: pd.Period) -> str:
    return f"{MONTH_NAMES_ID[p.month - 1]} {p.year}"


period_by_label = {_period_label(p): p for p in month_index}
month_labels = list(period_by_label.keys())


def _range_for(months_back):
    """months_back=None artinya seluruh data yang tersedia."""
    end_p = month_index[-1]
    start_p = month_index[0] if months_back is None else max(end_p - (months_back - 1), month_index[0])
    return (_period_label(start_p), _period_label(end_p))


def _set_range(months_back):
    st.session_state["date_range_slider"] = _range_for(months_back)


if "date_range_slider" not in st.session_state:
    st.session_state["date_range_slider"] = _range_for(12)

st.sidebar.markdown("**Rentang tanggal**")
bcol1, bcol2 = st.sidebar.columns(2)
bcol1.button("Semua Data", use_container_width=True, on_click=_set_range, args=(None,))
bcol2.button("1 Thn Terakhir", use_container_width=True, on_click=_set_range, args=(12,))
bcol3, bcol4 = st.sidebar.columns(2)
bcol3.button("3 Thn Terakhir", use_container_width=True, on_click=_set_range, args=(36,))
bcol4.button("5 Thn Terakhir", use_container_width=True, on_click=_set_range, args=(60,))

start_label, end_label = st.sidebar.select_slider(
    "Geser untuk memilih rentang bulan",
    options=month_labels,
    key="date_range_slider",
)
start_period = period_by_label[start_label]
end_period = period_by_label[end_label]
start_date = start_period.start_time
end_date = (end_period + 1).start_time - pd.Timedelta(days=1)

all_ports = sorted(df["portname"].unique())
default_ports = (
    df.groupby("portname")["portcalls_tanker"].sum().nlargest(10).index.tolist()
)
selected_ports = st.sidebar.multiselect(
    "Pilih pelabuhan (kosongkan = semua pelabuhan)",
    options=all_ports,
    default=[],
    help="Jika tidak dipilih, seluruh pelabuhan dalam data akan dianalisis.",
)
ports_in_scope = selected_ports if selected_ports else all_ports

freq_label = st.sidebar.radio(
    "Agregasi waktu", ["Harian", "Mingguan", "Bulanan", "Tahunan"], index=2
)
freq_map = {"Harian": "D", "Mingguan": "W", "Bulanan": "MS", "Tahunan": "YS"}
freq = freq_map[freq_label]

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Data tersedia: **{MIN_DATE}** s/d **{MAX_DATE}** • {len(all_ports)} pelabuhan"
)

# ----------------------------------------------------------------------------
# FILTER DATA SESUAI PILIHAN
# ----------------------------------------------------------------------------
mask = (
    (df["date"] >= start_date)
    & (df["date"] <= end_date)
    & (df["portname"].isin(ports_in_scope))
)
dff = df.loc[mask].copy()

period_len = end_date - start_date
prev_start = start_date - period_len - timedelta(days=1)
prev_end = start_date - timedelta(days=1)
mask_prev = (
    (df["date"] >= prev_start)
    & (df["date"] <= prev_end)
    & (df["portname"].isin(ports_in_scope))
)
dff_prev = df.loc[mask_prev]


def pct_delta(curr, prev):
    if prev == 0:
        return None
    return (curr - prev) / prev * 100


# ----------------------------------------------------------------------------
# HEADER & KPI (selalu tampil di atas, di luar tab)
# ----------------------------------------------------------------------------
st.title("🛢️ Port Activity Snapshot")
st.subheader("Analisis Tren Kapal Tanker di Pelabuhan Indonesia")
st.caption(
    f"Periode: **{start_date.date()}** — **{end_date.date()}** • "
    f"{len(ports_in_scope)} pelabuhan dianalisis"
)

total_calls = int(dff["portcalls_tanker"].sum())
total_import = int(dff["import_tanker"].sum())
total_export = int(dff["export_tanker"].sum())
share_tanker = (
    dff["portcalls_tanker"].sum() / dff["portcalls"].sum() * 100
    if dff["portcalls"].sum() > 0
    else 0
)

prev_calls = int(dff_prev["portcalls_tanker"].sum())
prev_import = int(dff_prev["import_tanker"].sum())
prev_export = int(dff_prev["export_tanker"].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Total Port Calls Tanker",
    f"{total_calls:,}",
    f"{pct_delta(total_calls, prev_calls):.1f}% vs periode sebelumnya"
    if pct_delta(total_calls, prev_calls) is not None
    else None,
)
c2.metric(
    "Volume Import Tanker (ton)",
    f"{total_import:,.0f}",
    f"{pct_delta(total_import, prev_import):.1f}% vs periode sebelumnya"
    if pct_delta(total_import, prev_import) is not None
    else None,
)
c3.metric(
    "Volume Export Tanker (ton)",
    f"{total_export:,.0f}",
    f"{pct_delta(total_export, prev_export):.1f}% vs periode sebelumnya"
    if pct_delta(total_export, prev_export) is not None
    else None,
)
c4.metric("Pangsa Tanker dari Total Port Calls", f"{share_tanker:.1f}%")

st.markdown("---")

# ----------------------------------------------------------------------------
# TAB NAVIGASI
# Dipecah jadi tab (bukan satu halaman panjang) supaya di HP orang tinggal
# tap untuk pindah bagian, tidak perlu scroll panjang seperti sebelumnya.
# ----------------------------------------------------------------------------
tab_tren, tab_rank, tab_musiman, tab_data = st.tabs(
    ["📈 Tren", "🏆 Peringkat & Perbandingan", "🗓️ Musiman", "📋 Data"]
)

# ----------------------------------------------------------------------------
# TAB 1: TREN PORT CALLS & VOLUME IMPORT/EKSPOR
# ----------------------------------------------------------------------------
with tab_tren:
    st.markdown("### 📈 Tren Port Calls Tanker")

    trend = (
        dff.set_index("date")
        .resample(freq)[["portcalls_tanker", "import_tanker", "export_tanker"]]
        .sum()
        .reset_index()
    )

    fig_calls = px.line(
        trend,
        x="date",
        y="portcalls_tanker",
        markers=True,
        labels={"date": "Tanggal", "portcalls_tanker": "Jumlah Port Calls Tanker"},
    )
    fig_calls.update_traces(
        line_color="#0B5394", fill="tozeroy", fillcolor="rgba(11,83,148,0.12)"
    )
    fig_calls.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
    fig_calls = lock_figure(fig_calls)
    st.plotly_chart(fig_calls, use_container_width=True, config=PLOTLY_CONFIG)

    st.markdown("### ⚖️ Volume Import vs Export Tanker")

    trend_long = trend.melt(
        id_vars="date",
        value_vars=["import_tanker", "export_tanker"],
        var_name="jenis",
        value_name="volume",
    )
    trend_long["jenis"] = trend_long["jenis"].map(
        {"import_tanker": "Import", "export_tanker": "Export"}
    )
    fig_io = px.bar(
        trend_long,
        x="date",
        y="volume",
        color="jenis",
        barmode="group",
        labels={"date": "Tanggal", "volume": "Volume (ton)", "jenis": "Jenis"},
        color_discrete_map={"Import": "#1F77B4", "Export": "#FF7F0E"},
    )
    fig_io.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
    fig_io = lock_figure(fig_io)
    st.plotly_chart(fig_io, use_container_width=True, config=PLOTLY_CONFIG)

# ----------------------------------------------------------------------------
# TAB 2: PERINGKAT PELABUHAN & PERBANDINGAN ANTAR PELABUHAN
# ----------------------------------------------------------------------------
with tab_rank:
    st.markdown("### 🏆 Peringkat Pelabuhan")

    rank_metric = st.selectbox(
        "Urutkan berdasarkan",
        ["Port Calls Tanker", "Volume Import", "Volume Export", "Total Volume (Import+Export)"],
    )
    rank_col_map = {
        "Port Calls Tanker": "portcalls_tanker",
        "Volume Import": "import_tanker",
        "Volume Export": "export_tanker",
        "Total Volume (Import+Export)": "tanker_volume",
    }
    rank_col = rank_col_map[rank_metric]

    top_ports = (
        dff.groupby("portname")[rank_col]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .reset_index()
    )
    fig_top = px.bar(
        top_ports.sort_values(rank_col),
        x=rank_col,
        y="portname",
        orientation="h",
        labels={rank_col: rank_metric, "portname": "Pelabuhan"},
        color=rank_col,
        color_continuous_scale="Blues",
    )
    fig_top.update_layout(
        height=460, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False
    )
    fig_top = lock_figure(fig_top)
    st.plotly_chart(fig_top, use_container_width=True, config=PLOTLY_CONFIG)

    st.markdown("### 🔍 Bandingkan Tren Antar Pelabuhan")

    compare_ports = st.multiselect(
        "Pilih hingga 6 pelabuhan untuk dibandingkan",
        options=all_ports,
        default=top_ports["portname"].head(3).tolist(),
        max_selections=6,
    )

    if compare_ports:
        dff_cmp = df[
            (df["date"] >= start_date)
            & (df["date"] <= end_date)
            & (df["portname"].isin(compare_ports))
        ]
        trend_cmp = (
            dff_cmp.groupby(["portname", pd.Grouper(key="date", freq=freq)])[
                "portcalls_tanker"
            ]
            .sum()
            .reset_index()
        )
        fig_cmp = px.line(
            trend_cmp,
            x="date",
            y="portcalls_tanker",
            color="portname",
            markers=True,
            labels={
                "date": "Tanggal",
                "portcalls_tanker": "Port Calls Tanker",
                "portname": "Pelabuhan",
            },
        )
        fig_cmp.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
        fig_cmp = lock_figure(fig_cmp)
        st.plotly_chart(fig_cmp, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("Pilih minimal satu pelabuhan untuk melihat perbandingan.")

# ----------------------------------------------------------------------------
# TAB 3: POLA MUSIMAN
# ----------------------------------------------------------------------------
with tab_musiman:
    st.markdown("### 🗓️ Pola Musiman Aktivitas Tanker (Bulan x Tahun)")
    st.caption(
        "Heatmap ini selalu menampilkan seluruh riwayat data yang tersedia untuk "
        "pelabuhan terpilih (tidak mengikuti filter rentang tanggal di sidebar), "
        "supaya pola musiman antar tahun bisa dibandingkan secara utuh."
    )

    # PENTING: pakai `df` penuh (hanya difilter pelabuhan), BUKAN `dff`.
    # `dff` sudah dipotong oleh filter rentang tanggal di sidebar (mis. "1 tahun
    # terakhir"), sehingga bulan-bulan di luar rentang itu tidak punya baris sama
    # sekali. Saat di-pivot, kombinasi (tahun, bulan) yang tidak ada barisnya jadi
    # NaN, lalu fillna(0) mengubahnya jadi 0 -- seolah tidak ada aktivitas tanker,
    # padahal datanya sebenarnya ada, hanya tidak ikut filter tanggal.
    season_source = df[df["portname"].isin(ports_in_scope)]
    season = (
        season_source.groupby(["year", "month"])["portcalls_tanker"].sum().reset_index()
    )
    # Bulan dijadikan BARIS dan tahun dijadikan KOLOM (dibalik dari versi
    # sebelumnya) supaya jumlah kolom tetap 12 walau data terus bertambah
    # tahun ke tahun -- lebih pas untuk lebar layar HP yang sempit, karena
    # yang bertambah cukup di sumbu vertikal (scroll ke bawah itu wajar di HP).
    season_pivot = season.pivot(index="month", columns="year", values="portcalls_tanker")
    season_pivot = season_pivot.reindex(index=range(1, 13)).sort_index(axis=1)
    season_pivot.index = MONTH_NAMES_ID
    # NaN sengaja dibiarkan (bukan fillna(0)) supaya bulan yang memang belum
    # terjadi (mis. Okt-Des tahun berjalan) tampil kosong/abu-abu di heatmap,
    # bukan seolah-olah nol aktivitas.

    fig_heat = px.imshow(
        season_pivot,
        labels=dict(x="Tahun", y="Bulan", color="Port Calls"),
        color_continuous_scale="Blues",
        aspect="auto",
        text_auto=True,
    )
    fig_heat.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_showscale=False,  # skala warna dilepas -> lebih banyak ruang untuk kotak heatmap di HP
    )
    fig_heat.update_traces(textfont_size=12)
    fig_heat.update_xaxes(side="bottom", type="category")
    fig_heat = lock_figure(fig_heat)
    st.plotly_chart(fig_heat, use_container_width=True, config=PLOTLY_CONFIG)

# ----------------------------------------------------------------------------
# TAB 4: TABEL DATA & DOWNLOAD
# ----------------------------------------------------------------------------
with tab_data:
    st.markdown("### 📋 Data Rinci")
    st.caption(
        f"Menampilkan data sesuai filter **Rentang tanggal** di sidebar, saat ini "
        f"**{start_date.date()}** – **{end_date.date()}**. Data lengkap tersedia dari "
        f"**{MIN_DATE}** s/d **{MAX_DATE}** — klik **\"Semua Data\"** di sidebar atau "
        f"geser slider untuk melihat tahun-tahun lain."
    )
    table = (
        dff[["date", "portname", "portcalls_tanker", "import_tanker", "export_tanker"]]
        .sort_values("date", ascending=False)
        .rename(
            columns={
                "date": "Tanggal",
                "portname": "Pelabuhan",
                "portcalls_tanker": "Port Calls",
                "import_tanker": "Import (ton)",
                "export_tanker": "Export (ton)",
            }
        )
    )
    st.dataframe(
        table,
        use_container_width=True,
        height=380,
        hide_index=True,
        column_config={
            "Tanggal": st.column_config.DateColumn("Tanggal", width="small"),
            "Port Calls": st.column_config.NumberColumn("Port Calls", width="small"),
            "Import (ton)": st.column_config.NumberColumn("Import (ton)", width="small", format="%d"),
            "Export (ton)": st.column_config.NumberColumn("Export (ton)", width="small", format="%d"),
        },
    )
    st.download_button(
        "⬇️ Unduh CSV",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="tren_tanker_terfilter.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption(
    "Port Activity Snapshot • Data port calls & volume shipment pelabuhan Indonesia (2019–2026). "
    "Dibangun dengan Streamlit."
)
