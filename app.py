import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Optional

# ==============================
# PAGE CONFIG & GLOBAL STYLING
# ==============================

st.set_page_config(
    page_title="Global Air Pollution Dashboard",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* Reduce top padding & widen content */
    .main .block-container {
        max-width: 1500px;
        padding-top: 0.5rem;
        padding-bottom: 2rem;
    }

    h1 {
        margin-bottom: 0.4rem !important;
    }

    /* Reusable card style */
    .card {
        background-color: rgba(255,255,255,0.03);
        padding: 1.0rem 1.2rem;
        border-radius: 0.9rem;
        border: 1px solid rgba(255,255,255,0.10);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================
# HELPER: CLEAN COLUMN NAMES
# ==============================

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        c.strip()
        .lower()
        .replace(" ", "_")
        .replace(".", "_")
        for c in df.columns
    ]
    return df


# ==============================
# DATA LOADING
# ==============================

@st.cache_data
def load_aqi_data() -> pd.DataFrame:
    df = pd.read_csv("data/raw/global_air_pollution.csv")
    df = clean_columns(df)

    if "country" in df.columns:
        df = df.dropna(subset=["country"])
        df["country"] = df["country"].astype(str)

    for col in df.columns:
        if col.endswith("aqi_value") or col == "aqi_value":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "aqi_value" in df.columns:
        df = df.dropna(subset=["aqi_value"])

    return df


@st.cache_data
def load_pm25_data() -> pd.DataFrame:
    df = pd.read_csv("data/raw/pm25-air-pollution.csv")
    df = clean_columns(df)

    if "entity" in df.columns:
        df = df.rename(columns={"entity": "country"})
    if "pm2_5" in df.columns:
        df = df.rename(columns={"pm2_5": "pm25"})
    elif "pm25" not in df.columns:
        possible_pm_cols = [c for c in df.columns if "pm2" in c]
        if possible_pm_cols:
            df = df.rename(columns={possible_pm_cols[0]: "pm25"})

    df["year"] = pd.to_numeric(df.get("year", pd.NA), errors="coerce")
    df["pm25"] = pd.to_numeric(df.get("pm25", pd.NA), errors="coerce")

    df = df.dropna(subset=["country", "year", "pm25"])
    df["country"] = df["country"].astype(str)
    df = df[(df["year"] >= 2010) & (df["year"] <= 2019)]
    return df


def get_merged_pm25_aqi(aqi_df: pd.DataFrame, pm_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if "aqi_value" not in aqi_df.columns:
        return None

    aqi_country = (
        aqi_df.groupby("country", as_index=False)["aqi_value"]
        .mean()
        .rename(columns={"aqi_value": "mean_aqi_value"})
    )
    merged = pm_df.merge(aqi_country, on="country", how="inner")
    return merged


# ==============================
# GLOBAL MAP (HERO VIEW)
# ==============================

def show_global_map(aqi_df: pd.DataFrame):
    if "country" not in aqi_df.columns:
        st.warning("No 'country' column found in AQI dataset.")
        return

    # Metrics that can be mapped
    metric_options = {}
    if "aqi_value" in aqi_df.columns:
        metric_options["Overall AQI Value"] = "aqi_value"

    for col in aqi_df.columns:
        if col.endswith("_aqi_value") and col != "aqi_value":
            label = col.replace("_aqi_value", "").upper().replace("_", " ") + " AQI"
            metric_options[label] = col

    if not metric_options:
        st.warning("No AQI metric columns found for mapping.")
        return

    # Main split: left = controls, right = map
    left_col, right_col = st.columns([1.2, 3.8])

    # ---------- LEFT: SETTINGS PANEL ----------
    with left_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### Settings")

        metric_label = st.selectbox(
            "Pollution metric",
            list(metric_options.keys()),
        )
        metric_col = metric_options[metric_label]

        cat_filter = None
        if "aqi_category" in aqi_df.columns:
            categories = sorted(aqi_df["aqi_category"].dropna().unique().tolist())
            cat_filter = st.multiselect(
                "AQI Category",
                options=categories,
                default=categories,
            )

        metric_series = pd.to_numeric(aqi_df[metric_col], errors="coerce")
        metric_min = float(metric_series.min())
        metric_max = float(metric_series.max())

        threshold = st.slider(
            f"Minimum {metric_label}",
            min_value=float(round(metric_min, 1)),
            max_value=float(round(metric_max, 1)),
            value=float(round(metric_min, 1)),
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- FILTER DATA ----------
    filtered = aqi_df.copy()
    filtered[metric_col] = pd.to_numeric(filtered[metric_col], errors="coerce")
    filtered = filtered.dropna(subset=[metric_col])

    if cat_filter is not None and len(cat_filter) > 0:
        filtered = filtered[filtered["aqi_category"].isin(cat_filter)]

    filtered = filtered[filtered[metric_col] >= threshold]

    country_metric = (
        filtered
        .groupby("country", as_index=False)[metric_col]
        .mean()
        .rename(columns={metric_col: "metric_value"})
    )

    # ---------- RIGHT: BIG MAP ----------
    with right_col:
        # centered status line right above map
        st.markdown(
            f"""
            <p style="text-align:center; font-weight:600; margin-bottom:0.4rem;">
                Showing {len(country_metric)} countries · Metric: {metric_label} · Min: {threshold}
            </p>
            """,
            unsafe_allow_html=True,
        )

        fig = px.choropleth(
            country_metric,
            locations="country",
            locationmode="country names",
            color="metric_value",
            labels={"metric_value": metric_label, "country": "Country"},
            height=900,  # big, tall map
            color_continuous_scale="Blues",
        )

        fig.update_geos(
            showframe=False,
            showcoastlines=False,
            projection_type="natural earth",
        )

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(
                orientation="h",
                y=-0.20,
                thickness=14,
                len=0.85,
                title=metric_label,
            ),
        )

        st.plotly_chart(fig, width="stretch")

    # ---------- TABLE ----------
    with st.expander("Show aggregated data table"):
        st.dataframe(
            country_metric.sort_values("metric_value", ascending=False),
            use_container_width=True,
        )


# ==============================
# SUMMARY VIEW
# ==============================

def show_data_preview(aqi_df: pd.DataFrame):
    st.subheader("📄 AQI Dataset Preview")
    st.write(f"Total rows: **{aqi_df.shape[0]}**")
    st.dataframe(aqi_df.head())


def show_top_polluted(aqi_df: pd.DataFrame):
    st.subheader("🔥 Top 10 Most Polluted Countries (Average Overall AQI)")

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
        title="",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")


# ==============================
# COUNTRY POLLUTANTS VIEW
# ==============================

def show_country_pollutants(aqi_df: pd.DataFrame):
    st.subheader("🏙 Country-Level Pollutant Breakdown")

    if "country" not in aqi_df.columns:
        st.info("Column 'country' not found.")
        return

    df_clean = aqi_df.dropna(subset=["country"]).copy()
    countries = sorted(df_clean["country"].astype(str).unique().tolist())
    selected = st.selectbox("Choose a country", countries)

    filtered = df_clean[df_clean["country"] == selected]

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
        title=f"Average pollutant AQI in {selected}",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, width="stretch")


# ==============================
# PM2.5 TRENDS VIEW
# ==============================

def show_pm25_trends(pm_df: pd.DataFrame, merged_df: Optional[pd.DataFrame]):
    st.subheader("📈 PM2.5 Exposure Trend (2010–2019)")

    countries = sorted(pm_df["country"].unique())
    default_selection = ["India", "China"] if "India" in countries and "China" in countries else countries[:2]

    selected = st.multiselect(
        "Select countries to compare",
        options=countries,
        default=default_selection,
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
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")

    if merged_df is not None and "mean_aqi_value" in merged_df.columns:
        st.subheader("PM2.5 vs Mean AQI (latest available year)")
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
                labels={"pm25": "PM2.5 (μg/m³)", "mean_aqi_value": "Mean AQI"},
                title="",
            )
            fig2.update_traces(textposition="top center")
            fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig2, width="stretch")


# ==============================
# MAIN APP WITH CUSTOM ICON NAV
# ==============================

def main():
    st.title("🌍 Global Air Pollution Dashboard")

    # Session state for custom navigation
    if "active_view" not in st.session_state:
        st.session_state["active_view"] = "map"
    if "menu_open" not in st.session_state:
        st.session_state["menu_open"] = True

    # --- NAV ROW (hamburger + icon radio) ---
    nav_col, _ = st.columns([0.22, 0.78])
    with nav_col:
        c1, c2 = st.columns([0.25, 0.75])
        with c1:
            if st.button("☰", key="menu_toggle"):
                st.session_state["menu_open"] = not st.session_state["menu_open"]

        with c2:
            if st.session_state["menu_open"]:
                view = st.radio(
                    "",
                    ["map", "summary", "country", "pm25"],
                    index=["map", "summary", "country", "pm25"].index(
                        st.session_state["active_view"]
                    ),
                    format_func=lambda x: {
                        "map": "🗺 Global Map",
                        "summary": "📊 AQI Summary",
                        "country": "🏙 Country Pollutants",
                        "pm25": "📈 PM2.5 Trends",
                    }[x],
                    horizontal=True,
                )
                st.session_state["active_view"] = view

    # Load data once
    aqi_df = load_aqi_data()
    pm_df = load_pm25_data()
    merged_df = get_merged_pm25_aqi(aqi_df, pm_df)

    view = st.session_state["active_view"]

    if view == "map":
        st.subheader("🗺 Global Air Pollution Map (Interactive)")
        show_global_map(aqi_df)
    elif view == "summary":
        show_data_preview(aqi_df)
        show_top_polluted(aqi_df)
    elif view == "country":
        show_country_pollutants(aqi_df)
    elif view == "pm25":
        show_pm25_trends(pm_df, merged_df)


if __name__ == "__main__":
    main()
