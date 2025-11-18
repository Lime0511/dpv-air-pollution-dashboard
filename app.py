import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Optional

# ---------- PAGE CONFIG (WIDE LAYOUT) ----------

st.set_page_config(
    page_title="Global Air Pollution Dashboard",
    layout="wide",
)


# ---------- HELPER: CLEAN COLUMN NAMES ----------

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise column names: lower case, underscores, no dots.
    """
    df = df.copy()
    df.columns = [
        c.strip()
         .lower()
         .replace(" ", "_")
         .replace(".", "_")
        for c in df.columns
    ]
    return df


# ---------- DATA LOADING & BASELINE CLEANING ----------

@st.cache_data
def load_aqi_data() -> pd.DataFrame:
    """
    Load the main global air pollution (AQI) dataset.
    """
    df = pd.read_csv("data/raw/global_air_pollution.csv")
    df = clean_columns(df)

    # Basic sanity cleaning
    if "country" in df.columns:
        df = df.dropna(subset=["country"])
        df["country"] = df["country"].astype(str)

    # Convert AQI numeric columns where possible
    for col in df.columns:
        if col.endswith("aqi_value") or col == "aqi_value":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with missing overall AQI if that column exists
    if "aqi_value" in df.columns:
        df = df.dropna(subset=["aqi_value"])

    return df


@st.cache_data
def load_pm25_data() -> pd.DataFrame:
    """
    Load the PM2.5 time-series dataset (2010–2019).
    Expected columns before cleaning: Entity, Code, Year, PM2.5
    """
    df = pd.read_csv("data/raw/pm25-air-pollution.csv")
    df = clean_columns(df)  # now should have: entity, code, year, pm2_5

    # Rename to consistent names
    if "entity" in df.columns:
        df = df.rename(columns={"entity": "country"})
    if "pm2_5" in df.columns:
        df = df.rename(columns={"pm2_5": "pm25"})
    elif "pm25" not in df.columns:
        possible_pm_cols = [c for c in df.columns if "pm2" in c]
        if possible_pm_cols:
            df = df.rename(columns={possible_pm_cols[0]: "pm25"})

    # Ensure numeric types
    df["year"] = pd.to_numeric(df.get("year", pd.NA), errors="coerce")
    df["pm25"] = pd.to_numeric(df.get("pm25", pd.NA), errors="coerce")

    # Clean rows
    df = df.dropna(subset=["country", "year", "pm25"])
    df["country"] = df["country"].astype(str)

    # Restrict to 2010–2019 (because that’s what the file actually has)
    df = df[(df["year"] >= 2010) & (df["year"] <= 2019)]

    return df


def get_merged_pm25_aqi(aqi_df: pd.DataFrame, pm_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Merge PM2.5 time-series with country-level mean AQI (for scatter plot).
    """
    if "aqi_value" not in aqi_df.columns:
        return None

    aqi_country = (
        aqi_df.groupby("country", as_index=False)["aqi_value"]
        .mean()
        .rename(columns={"aqi_value": "mean_aqi_value"})
    )
    merged = pm_df.merge(aqi_country, on="country", how="inner")
    return merged


# ---------- VISUAL 1: GLOBAL MAP (METHOD 2 CORE) ----------

def show_global_map(aqi_df: pd.DataFrame):
    st.markdown("### 🌍 Global Air Pollution Map")

    if "country" not in aqi_df.columns:
        st.warning("No 'country' column found in AQI dataset.")
        return

    # candidate metrics = overall AQI + pollutant AQI subindices
    candidate_metrics = {}
    if "aqi_value" in aqi_df.columns:
        candidate_metrics["Overall AQI Value"] = "aqi_value"

    for col in aqi_df.columns:
        if col.endswith("_aqi_value") and col != "aqi_value":
            label = col.replace("_aqi_value", "").upper().replace("_", " ") + " AQI"
            candidate_metrics[label] = col

    if not candidate_metrics:
        st.warning("No AQI metric columns found for mapping.")
        return

    # small CSS so left panel looks more like a proper control box
    st.markdown(
        """
        <style>
        .control-panel {
            background-color: rgba(255,255,255,0.02);
            padding: 1.1rem 1.2rem;
            border-radius: 0.75rem;
            border: 1px solid rgba(255,255,255,0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    controls_col, map_col = st.columns([1.1, 3.2])

    # ---------- LEFT: CONTROL PANEL ----------
    with controls_col:
        st.markdown("<div class='control-panel'>", unsafe_allow_html=True)
        st.markdown("##### Settings")

        metric_label = st.selectbox(
            "Pollution metric:",
            list(candidate_metrics.keys())
        )
        metric_col = candidate_metrics[metric_label]

        category_filter = None
        if "aqi_category" in aqi_df.columns:
            categories = sorted(aqi_df["aqi_category"].dropna().unique().tolist())
            category_filter = st.multiselect(
                "AQI Category:",
                options=categories,
                default=categories,
            )

        metric_series = pd.to_numeric(aqi_df[metric_col], errors="coerce")
        metric_min = float(metric_series.min())
        metric_max = float(metric_series.max())

        threshold = st.slider(
            f"Minimum {metric_label}:",
            min_value=float(round(metric_min, 1)),
            max_value=float(round(metric_max, 1)),
            value=float(round(metric_min, 1)),
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- FILTER DATA (shared by map + table) ----------
    filtered = aqi_df.copy()
    filtered[metric_col] = pd.to_numeric(filtered[metric_col], errors="coerce")
    filtered = filtered.dropna(subset=[metric_col])

    if category_filter is not None and len(category_filter) > 0:
        filtered = filtered[filtered["aqi_category"].isin(category_filter)]

    filtered = filtered[filtered[metric_col] >= threshold]

    country_metric = (
        filtered
        .groupby("country", as_index=False)[metric_col]
        .mean()
        .rename(columns={metric_col: "metric_value"})
    )

    # ---------- RIGHT: MAP ----------
    with map_col:
        st.markdown(
            f"**Showing {len(country_metric)} countries · Metric: {metric_label} · Min: {threshold}**"
        )

        fig = px.choropleth(
            country_metric,
            locations="country",
            locationmode="country names",
            color="metric_value",
            labels={"metric_value": metric_label, "country": "Country"},
            title="",
            height=620,
        )
        # Natural earth style + colourbar at bottom (IHME-ish)
        fig.update_geos(
            showframe=False,
            showcoastlines=False,
            projection_type="natural earth",
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(
                orientation="h",
                y=-0.16,
                thickness=15,
                len=0.7,
                title=metric_label,
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------- TABLE UNDER THE WHOLE THING ----------
    with st.expander("Show aggregated data table"):
        st.dataframe(
            country_metric.sort_values("metric_value", ascending=False),
            use_container_width=True,
        )


# ---------- VISUAL 2: SNAPSHOT SUMMARY (TOP 10) ----------

def show_data_preview(aqi_df: pd.DataFrame):
    st.subheader("AQI Dataset Preview")
    st.write(f"Total rows: {aqi_df.shape[0]}")
    st.dataframe(aqi_df.head())


def show_top_polluted(aqi_df: pd.DataFrame):
    st.subheader("Top 10 Most Polluted Countries (by Overall AQI)")

    if "country" not in aqi_df.columns or "aqi_value" not in aqi_df.columns:
        st.info("Columns 'country' or 'aqi_value' not found.")
        return

    top10 = (
        aqi_df.groupby("country", as_index=False)["aqi_value"]
        .mean()
        .sort_values("aqi_value", ascending=False)
        .head(10)
    )

    fig = px.bar(
        top10,
        x="country",
        y="aqi_value",
        labels={"aqi_value": "Average AQI"},
        title="Top 10 Countries by Average AQI",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------- VISUAL 3: COUNTRY POLLUTANT BREAKDOWN ----------

def show_country_pollutants(aqi_df: pd.DataFrame):
    st.subheader("Pollutant Breakdown by Country")

    if "country" not in aqi_df.columns:
        st.info("Column 'country' not found.")
        return

    df_clean = aqi_df.dropna(subset=["country"]).copy()
    countries = sorted(df_clean["country"].astype(str).unique().tolist())
    selected_country = st.selectbox("Choose a country:", countries)

    filtered = df_clean[df_clean["country"] == selected_country]

    pollutant_cols = [
        col for col in filtered.columns
        if col.endswith("_aqi_value") and col != "aqi_value"
    ]

    if not pollutant_cols:
        st.info("No pollutant AQI columns found for this country.")
        return

    pollutant_data = filtered[pollutant_cols].mean().reset_index()
    pollutant_data.columns = ["pollutant", "average_aqi"]

    fig = px.bar(
        pollutant_data,
        x="pollutant",
        y="average_aqi",
        labels={"average_aqi": "AQI"},
        title=f"Average pollutant AQI in {selected_country}",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------- VISUAL 4: PM2.5 TRENDS (2010–2019) ----------

def show_pm25_trends(pm_df: pd.DataFrame, merged_df: Optional[pd.DataFrame]):
    st.subheader("PM2.5 Exposure Trend (2010–2019)")

    countries = sorted(pm_df["country"].unique())
    default_selection = ["India", "China"] if "India" in countries and "China" in countries else countries[:2]

    selected = st.multiselect(
        "Select countries to compare:",
        options=countries,
        default=default_selection
    )

    if not selected:
        st.info("Pick at least one country to see the trend.")
        return

    filtered = pm_df[pm_df["country"].isin(selected)]

    fig = px.line(
        filtered,
        x="year",
        y="pm25",
        color="country",
        title="PM2.5 Levels Over Time (2010–2019)",
        labels={"pm25": "PM2.5 (μg/m³)", "year": "Year"},
    )
    st.plotly_chart(fig, use_container_width=True)

    # Optional: show relationship between PM2.5 and AQI snapshot
    if merged_df is not None and "mean_aqi_value" in merged_df.columns:
        st.subheader("PM2.5 vs Mean AQI (per country, latest year in trend)")
        latest = (
            merged_df.sort_values("year")
            .groupby("country", as_index=False)
            .tail(1)
        )
        latest_sel = latest[latest["country"].isin(selected)]

        if not latest_sel.empty:
            fig2 = px.scatter(
                latest_sel,
                x="pm25",
                y="mean_aqi_value",
                text="country",
                labels={"pm25": "PM2.5 (μg/m³)", "mean_aqi_value": "Mean AQI (snapshot)"},
                title="PM2.5 vs Mean AQI (Selected Countries)",
            )
            fig2.update_traces(textposition="top center")
            st.plotly_chart(fig2, use_container_width=True)


# ---------- APP ENTRY POINT ----------

def main():
    st.title("🌍 Global Air Pollution Dashboard")

    aqi_df = load_aqi_data()
    pm_df = load_pm25_data()
    merged_df = get_merged_pm25_aqi(aqi_df, pm_df)

    tab_map, tab_summary, tab_country, tab_pm25 = st.tabs(
        [
            "🗺 Global Map (Method 2)",
            "📊 AQI Summary (Method 1)",
            "🏙 Country Pollutants",
            "📈 PM2.5 Trends (2010–2019)",
        ]
    )

    with tab_map:
        show_global_map(aqi_df)

    with tab_summary:
        show_data_preview(aqi_df)
        show_top_polluted(aqi_df)

    with tab_country:
        show_country_pollutants(aqi_df)

    with tab_pm25:
        show_pm25_trends(pm_df, merged_df)


if __name__ == "__main__":
    main()
