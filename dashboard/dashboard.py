from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Air Quality Dashboard",
    page_icon="🌬️",
    layout="wide",
)

st.title("Air Quality Dashboard")
st.write("Visualisasi berikut menampilkan analisis kualitas udara di China pada Tahun 2013-2017.")


@st.cache_data
def load_data() -> pd.DataFrame:
    data_path = Path(__file__).parent / "main_data.csv"
    df = pd.read_csv(data_path)

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    for column in ["year", "month", "day", "hour"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


df = load_data()

if df.empty:
    st.warning("Dataset kosong.")
    st.stop()

analysis_df = df.copy()
if "datetime" in analysis_df.columns:
    analysis_df = analysis_df.dropna(subset=["datetime"])
    analysis_df["date"] = analysis_df["datetime"].dt.date
elif {"year", "month", "day"}.issubset(analysis_df.columns):
    analysis_df["date"] = pd.to_datetime(
        analysis_df[["year", "month", "day"]], errors="coerce"
    ).dt.date
else:
    analysis_df["date"] = pd.NaT

st.sidebar.header("Filter Tampilan")
station_options = ["Semua"]
if "station" in df.columns:
    station_options.extend(sorted(df["station"].dropna().astype(str).unique().tolist()))

selected_station = st.sidebar.selectbox("Pilih stasiun", station_options)

date_min = analysis_df["date"].min() if analysis_df["date"].notna().any() else None
date_max = analysis_df["date"].max() if analysis_df["date"].notna().any() else None
selected_date_range = None
if date_min is not None and date_max is not None:
    selected_date_range = st.sidebar.date_input(
        "Pilih rentang tanggal",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )

def apply_filters(frame: pd.DataFrame) -> pd.DataFrame:
    filtered_frame = frame.copy()

    if selected_station != "Semua" and "station" in filtered_frame.columns:
        filtered_frame = filtered_frame[filtered_frame["station"].astype(str) == selected_station]

    if selected_date_range and isinstance(selected_date_range, tuple) and len(selected_date_range) == 2 and "datetime" in filtered_frame.columns:
        start_date, end_date = selected_date_range
        filtered_frame = filtered_frame[filtered_frame["datetime"].dt.date.between(start_date, end_date)]

    return filtered_frame


summary_df = apply_filters(df)

st.sidebar.caption("Filter ini hanya memengaruhi ringkasan data di atas.")

st.markdown("---")
st.header("1. Pola Harian")
st.caption("Menunjukkan jam puncak PM2.5 dan NO2 serta pergerakan pada jam sibuk pagi dan malam.")

v1_df = df.copy()
v1_df = apply_filters(v1_df)

if {"hour", "PM2.5", "NO2"}.issubset(v1_df.columns):
    hourly_avg = (
        v1_df.groupby("hour", as_index=False)[["PM2.5", "NO2"]]
        .mean(numeric_only=True)
        .melt(id_vars="hour", var_name="polutan", value_name="rata_rata")
        .dropna()
    )

    peak_points = hourly_avg.loc[hourly_avg.groupby("polutan")["rata_rata"].idxmax()].sort_values("polutan")
    peak_pm25 = peak_points.loc[peak_points["polutan"] == "PM2.5"].iloc[0]
    peak_no2 = peak_points.loc[peak_points["polutan"] == "NO2"].iloc[0]

    v1_col1, v1_col2 = st.columns(2)
    v1_col1.metric("Puncak PM2.5", f"{int(peak_pm25['hour']):02d}.00")
    v1_col2.metric("Puncak NO2", f"{int(peak_no2['hour']):02d}.00")

    fig_v1 = px.line(
        hourly_avg,
        x="hour",
        y="rata_rata",
        color="polutan",
        markers=True,
        title="Rata-rata per Jam",
        labels={"hour": "Jam", "rata_rata": "Rata-rata konsentrasi", "polutan": "Polutan"},
    )
    fig_v1.add_vrect(x0=7, x1=9, fillcolor="orange", opacity=0.12, line_width=0)
    fig_v1.add_vrect(x0=17, x1=19, fillcolor="red", opacity=0.12, line_width=0)
    fig_v1.update_layout(xaxis=dict(dtick=1), hovermode="x unified")
    st.plotly_chart(fig_v1, use_container_width=True)

else:
    st.warning("Kolom hour, PM2.5, atau NO2 tidak ditemukan.")

st.markdown("---")
st.header("2. Tren Musiman")
st.caption("Membandingkan rata-rata bulanan PM2.5 dan SO2 dari musim panas ke musim dingin.")

v2_df = df.copy()
v2_df = apply_filters(v2_df)

if {"month", "PM2.5", "SO2"}.issubset(v2_df.columns):
    monthly_pollution = v2_df.groupby("month", observed=False)[["PM2.5", "SO2"]].mean(numeric_only=True).reindex(range(1, 13)).reset_index()
    monthly_pollution["month_name"] = monthly_pollution["month"].map(
        {
            1: "Jan",
            2: "Feb",
            3: "Mar",
            4: "Apr",
            5: "Mei",
            6: "Jun",
            7: "Jul",
            8: "Agu",
            9: "Sep",
            10: "Okt",
            11: "Nov",
            12: "Des",
        }
    )
    monthly_pollution["season_group"] = monthly_pollution["month"].isin([1, 2, 11, 12]).map(
        {True: "Musim Dingin (Nov - Feb)", False: "Bulan Lainnya"}
    )

    monthly_melted = monthly_pollution.melt(
        id_vars=["month", "month_name", "season_group"],
        value_vars=["PM2.5", "SO2"],
        var_name="polutan",
        value_name="rata_rata",
    )

    fig_v2 = px.line(
        monthly_melted,
        x="month_name",
        y="rata_rata",
        color="polutan",
        markers=True,
        title="Tren Musiman PM2.5 dan SO2 (2013-2017)",
        labels={"month_name": "Bulan", "rata_rata": "Rata-Rata Konsentrasi", "polutan": "Polutan"},
    )
    fig_v2.add_vrect(x0=0.5, x1=2.5, fillcolor="#e67e22", opacity=0.12, line_width=0)
    fig_v2.add_vrect(x0=10.5, x1=12.5, fillcolor="#e67e22", opacity=0.12, line_width=0)
    fig_v2.add_vrect(x0=4.5, x1=8.5, fillcolor="#2ecc71", opacity=0.08, line_width=0)
    fig_v2.update_layout(
        xaxis=dict(title="Bulan"),
        yaxis=dict(title="Rata-Rata Konsentrasi (µg/m³)"),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig_v2, use_container_width=True)

else:
    st.warning("Kolom month, PM2.5, atau SO2 tidak ditemukan.")

st.markdown("---")
st.header("3. Stasiun Seluruh Tahun")
st.caption("Menampilkan stasiun dengan rata-rata PM2.5 tertinggi sepanjang seluruh tahun.")

if {"year", "station", "PM2.5"}.issubset(df.columns):
    v3_df = apply_filters(df)

    if v3_df.empty:
        st.warning("Tidak ada data untuk analisis stasiun.")
    else:
        station_avg_all_years = (
            v3_df.groupby("station", as_index=False)["PM2.5"]
            .mean(numeric_only=True)
            .sort_values("PM2.5", ascending=False)
        )

        top3 = station_avg_all_years.head(3)
        metric_cols = st.columns(3)
        for idx, (_, row) in enumerate(top3.iterrows()):
            metric_cols[idx].metric(f"#{idx + 1} {row['station']}", f"{row['PM2.5']:.2f}")

        fig_v3 = px.bar(
            station_avg_all_years.sort_values("PM2.5", ascending=True),
            x="station",
            y="PM2.5",
            title="Rata-rata PM2.5 per Stasiun (Seluruh Tahun)",
            labels={"station": "Stasiun", "PM2.5": "Rata-Rata PM2.5"},
            text_auto=".2f",
        )
        fig_v3.update_layout(
            xaxis=dict(title="Stasiun", categoryorder="total ascending"),
            yaxis=dict(title="Rata-Rata PM2.5 (µg/m³)"),
            margin=dict(l=20, r=20, t=60, b=20),
            hovermode="x unified",
        )
        st.plotly_chart(fig_v3, use_container_width=True)

else:
    st.warning("Kolom year, station, atau PM2.5 tidak ditemukan.")