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

# ----------------------------------------------------------------------------
# KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Port Activity Snapshot - Tren Tanker",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

VESSEL_TYPES = ["tanker", "container", "dry_bulk", "general_cargo", "roro"]
VESSEL_LABELS = {
    "tanker": "Tanker",
    "container": "Container",
    "dry_bulk": "Dry Bulk",
    "general_cargo": "General Cargo",
    "roro": "RoRo",
}


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

date_range = st.sidebar.date_input(
    "Rentang tanggal",
    value=(MAX_DATE - timedelta(days=365), MAX_DATE),
    min_value=MIN_DATE,
    max_value=MAX_DATE,
)
if len(date_range) != 2:
    st.stop()
start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])

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

freq_label = st.sidebar.radio("Agregasi waktu", ["Harian", "Mingguan", "Bulanan"], index=2)
freq_map = {"Harian": "D", "Mingguan": "W", "Bulanan": "MS"}
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
# HEADER & KPI
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
# TREN PORT CALLS TANKER
# ----------------------------------------------------------------------------
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
fig_calls.update_traces(line_color="#0B5394", fill="tozeroy", fillcolor="rgba(11,83,148,0.12)")
fig_calls.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig_calls, use_container_width=True)

# ----------------------------------------------------------------------------
# IMPORT VS EXPORT VOLUME
# ----------------------------------------------------------------------------
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
fig_io.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig_io, use_container_width=True)

# ----------------------------------------------------------------------------
# TOP PELABUHAN
# ----------------------------------------------------------------------------
st.markdown("### 🏆 Peringkat Pelabuhan")

rank_metric = st.radio(
    "Urutkan berdasarkan",
    ["Port Calls Tanker", "Volume Import", "Volume Export", "Total Volume (Import+Export)"],
    horizontal=True,
)
rank_col_map = {
    "Port Calls Tanker": "portcalls_tanker",
    "Volume Import": "import_tanker",
    "Volume Export": "export_tanker",
    "Total Volume (Import+Export)": "tanker_volume",
}
rank_col = rank_col_map[rank_metric]

top_ports = (
    dff.groupby("portname")[rank_col].sum().sort_values(ascending=False).head(15).reset_index()
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
fig_top.update_layout(height=480, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
st.plotly_chart(fig_top, use_container_width=True)

# ----------------------------------------------------------------------------
# PERBANDINGAN ANTAR PELABUHAN
# ----------------------------------------------------------------------------
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
        dff_cmp.groupby(["portname", pd.Grouper(key="date", freq=freq)])["portcalls_tanker"]
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
    fig_cmp.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_cmp, use_container_width=True)
else:
    st.info("Pilih minimal satu pelabuhan untuk melihat perbandingan.")

# ----------------------------------------------------------------------------
# SEASONALITY HEATMAP
# ----------------------------------------------------------------------------
st.markdown("### 🗓️ Pola Musiman Aktivitas Tanker (Bulan x Tahun)")

season = (
    dff.groupby(["year", "month"])["portcalls_tanker"].sum().reset_index()
)
season_pivot = season.pivot(index="year", columns="month", values="portcalls_tanker").fillna(0)
month_names = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]
season_pivot = season_pivot.reindex(columns=range(1, 13))
season_pivot.columns = month_names

fig_heat = px.imshow(
    season_pivot,
    labels=dict(x="Bulan", y="Tahun", color="Port Calls Tanker"),
    color_continuous_scale="Blues",
    aspect="auto",
    text_auto=True,
)
fig_heat.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig_heat, use_container_width=True)

# ----------------------------------------------------------------------------
# KOMPOSISI JENIS KAPAL
# ----------------------------------------------------------------------------
st.markdown("### 🚢 Komposisi Jenis Kapal (Port Calls)")

mix = (
    dff.set_index("date")
    .resample(freq)[[f"portcalls_{v}" for v in VESSEL_TYPES]]
    .sum()
    .reset_index()
)
mix_long = mix.melt(id_vars="date", var_name="jenis", value_name="calls")
mix_long["jenis"] = mix_long["jenis"].str.replace("portcalls_", "").map(VESSEL_LABELS)

fig_mix = px.area(
    mix_long,
    x="date",
    y="calls",
    color="jenis",
    groupnorm="fraction",
    labels={"date": "Tanggal", "calls": "Proporsi", "jenis": "Jenis Kapal"},
)
fig_mix.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_tickformat=".0%")
st.plotly_chart(fig_mix, use_container_width=True)

st.caption(
    "Grafik menunjukkan proporsi port calls tanker dibandingkan jenis kapal lain "
    "(container, dry bulk, general cargo, roro) dari waktu ke waktu."
)

# ----------------------------------------------------------------------------
# TABEL DATA & DOWNLOAD
# ----------------------------------------------------------------------------
st.markdown("### 📋 Data Rinci")
with st.expander("Lihat & unduh data terfilter"):
    table = dff[
        ["date", "portname", "portcalls_tanker", "import_tanker", "export_tanker"]
    ].sort_values("date", ascending=False)
    st.dataframe(table, use_container_width=True, height=350)
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
