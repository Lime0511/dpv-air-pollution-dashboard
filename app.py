import streamlit as st
import pandas as pd
import plotly.express as px

# ---------- DATA LOADING & BASELINE CLEANING ----------

@st.cache_data
def load_data():
    df = pd.read_csv("data/raw/global_air_pollution.csv")

    # Baseline cleaning: standardise column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Drop clearly unusable rows
    if "country" in df.columns:
        df = df.dropna(subset=["country"])
        df["country"] = df["country"].astype(str)

    # Try to ensure aqi_value is numeric
    if "aqi_value" in df.columns:
        df["aqi_value"] = pd.to_numeric(df["aqi_value"], errors="coerce")

    return df


# ---------- GLOBAL MAP (METHOD 2 MAIN FEATURE) ----------

def show_global_map(df: pd.DataFrame):
    st.subheader("🌍 Global Air Pollution Map (Method 2: User-Defined Exploration)")

    if "country" not in df.columns:
        st.warning("No 'country' column found in dataset.")
        return

    # Detect possible pollutant metric columns
    candidate_metrics = {}
    if "aqi_value" in df.columns:
        candidate_metrics["Overall AQI Value"] = "aqi_value"

    # Any column ending with _aqi_value (e.g. pm2_5_aqi_value, no2_aqi_value, etc.)
    for col in df.columns:
        if col.endswith("_aqi_value") and col != "aqi_value":
            # make a nicer label
            label = col.replace("_aqi_value", "").upper().replace("_", " ") + " AQI"
            candidate_metrics[label] = col

    if not candidate_metrics:
        st.warning("No AQI metric columns found for mapping.")
        return

    # Sidebar controls = user-defined preprocessing / filtering
    st.sidebar.markdown("### Map Controls (Method 2)")
    metric_label = st.sidebar.selectbox(
        "Pollution metric to visualise:", list(candidate_metrics.keys())
    )
    metric_col = candidate_metrics[metric_label]

    # Optional AQI category filter (if exists)
    category_filter = None
    if "aqi_category" in df.columns:
        categories = sorted(df["aqi_category"].dropna().unique().tolist())
        category_filter = st.sidebar.multiselect(
            "Filter by AQI Category (optional):",
            options=categories,
            default=categories,  # all selected by default
        )

    # Threshold slider for the chosen metric
    metric_series = pd.to_numeric(df[metric_col], errors="coerce")
    metric_min = float(metric_series.min())
    metric_max = float(metric_series.max())

    threshold = st.sidebar.slider(
        f"Minimum {metric_label}:",
        min_value=float(round(metric_min, 1)),
        max_value=float(round(metric_max, 1)),
        value=float(round(metric_min, 1)),
    )

    # Apply user-defined filters
    filtered = df.copy()
    filtered[metric_col] = pd.to_numeric(filtered[metric_col], errors="coerce")
    filtered = filtered.dropna(subset=[metric_col])

    if category_filter is not None and len(category_filter) > 0:
        filtered = filtered[filtered["aqi_category"].isin(category_filter)]

    filtered = filtered[filtered[metric_col] >= threshold]

    # Aggregate by country (mean of chosen metric)
    country_metric = (
        filtered
        .groupby("country", as_index=False)[metric_col]
        .mean()
        .rename(columns={metric_col: "metric_value"})
    )

    st.write(
        f"Showing **{len(country_metric)}** countries after filtering "
        f"(metric: **{metric_label}**, min: **{threshold}**)."
    )

    # Choropleth map using country names
    fig = px.choropleth(
        country_metric,
        locations="country",
        locationmode="country names",
        color="metric_value",
        labels={"metric_value": metric_label, "country": "Country"},
        title=f"Global Map of {metric_label}",
    )
    st.plotly_chart(fig, width="stretch")

    # Optional table of results
    with st.expander("Show aggregated data table"):
        st.dataframe(country_metric.sort_values("metric_value", ascending=False))


# ---------- OTHER VISUALS (SUPPORTING CHAETS) ----------

def show_data_preview(df: pd.DataFrame):
    st.subheader("Dataset Preview")
    st.write(f"Total rows: {df.shape[0]}")
    st.dataframe(df.head())


def show_top_polluted(df: pd.DataFrame):
    st.subheader("Top 10 Most Polluted Countries (by Overall AQI)")

    if "country" not in df.columns or "aqi_value" not in df.columns:
        st.info("Columns 'country' or 'aqi_value' not found.")
        return

    top10 = (
        df.groupby("country", as_index=False)["aqi_value"]
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
    st.plotly_chart(fig, width="stretch")


def show_country_pollutants(df: pd.DataFrame):
    st.subheader("Pollutant Breakdown by Country")

    if "country" not in df.columns:
        st.info("Column 'country' not found.")
        return

    df_clean = df.dropna(subset=["country"]).copy()
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
    st.plotly_chart(fig, width="stretch")


# ---------- APP ENTRY POINT ----------

def main():
    st.title("🌍 Global Air Pollution Dashboard (Method 2 Focus)")

    df = load_data()

    # Optional: tabs for structure
    tab_map, tab_summary, tab_country = st.tabs(
        ["🗺 Global Map (Method 2)", "📊 Summary", "🏙 Country Pollutants"]
    )

    with tab_map:
        show_global_map(df)

    with tab_summary:
        show_data_preview(df)
        show_top_polluted(df)

    with tab_country:
        show_country_pollutants(df)


if __name__ == "__main__":
    main()
