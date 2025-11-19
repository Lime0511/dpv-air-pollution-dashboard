import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------
# Data loading helpers
# -----------------------------------------------------------
@st.cache_data
def load_base_data() -> pd.DataFrame:
    """Global AQI dataset (Kaggle global air pollution)."""
    df = pd.read_csv("data/raw/global_air_pollution.csv")

    # Normalise column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
        .str.replace(".", "", regex=False)  # pm2.5 -> pm25
    )

    # Standardise some key column names if present
    rename_map = {}
    for c in df.columns:
        if c in ["entity", "country_name"]:
            rename_map[c] = "country"
        if c in ["overall_aqi_value", "overall_aqi", "aqi"]:
            rename_map[c] = "aqi_value"
        if c in ["overall_aqi_category"]:
            rename_map[c] = "aqi_category"
        if "pm25" in c and "aqi_value" in c:
            rename_map[c] = "pm25_aqi_value"
        if "pm10" in c and "aqi_value" in c:
            rename_map[c] = "pm10_aqi_value"
        if "no2" in c and "aqi_value" in c:
            rename_map[c] = "no2_aqi_value"
        if ("ozone" in c or "o3" in c) and "aqi_value" in c:
            rename_map[c] = "ozone_aqi_value"
        if "co" in c and "aqi_value" in c and c != "aqi_value":
            rename_map[c] = "co_aqi_value"

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


@st.cache_data
def load_pm25_data() -> pd.DataFrame | None:
    """PM2.5 exposure dataset (time-series)."""
    try:
        df = pd.read_csv("data/raw/pm25-air-pollution.csv")
    except FileNotFoundError:
        return None

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
        .str.replace(".", "", regex=False)
    )
    return df


base_df = load_base_data()
pm25_df = load_pm25_data()


def get_metric_options(df: pd.DataFrame) -> dict[str, str]:
    """Map pretty labels -> column names for numeric AQI metrics."""
    col_map: dict[str, str] = {}

    if "aqi_value" in df.columns:
        col_map["Overall AQI Value"] = "aqi_value"
    if "pm25_aqi_value" in df.columns:
        col_map["PM2.5 AQI Value"] = "pm25_aqi_value"
    if "pm10_aqi_value" in df.columns:
        col_map["PM10 AQI Value"] = "pm10_aqi_value"
    if "co_aqi_value" in df.columns:
        col_map["CO AQI Value"] = "co_aqi_value"
    if "no2_aqi_value" in df.columns:
        col_map["NO₂ AQI Value"] = "no2_aqi_value"
    if "ozone_aqi_value" in df.columns:
        col_map["O₃ AQI Value"] = "ozone_aqi_value"

    # Fallback – any numeric col
    if not col_map:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        for c in numeric_cols:
            pretty = c.replace("_", " ").title()
            col_map[pretty] = c

    return col_map


# -----------------------------------------------------------
# Page config + global CSS
# -----------------------------------------------------------
st.set_page_config(
    page_title="Global Air Pollution Dashboard",
    page_icon="🌍",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f3f4f6;
    }
    .block-container {
        padding-top: 0rem;
        padding-bottom: 1.5rem;
        padding-left: 0rem;
        padding-right: 0rem;
    }
    .top-bar {
        width: 100%;
        background-color: #b9f2f0;
        border-bottom: 1px solid #cbd5e1;
        padding: 0.5rem 1.75rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-sizing: border-box;
    }
    .top-bar-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #0f172a;
        letter-spacing: 0.03em;
    }
    .top-bar-subtitle {
        font-size: 0.78rem;
        color: #1f2933;
    }
    .nav-sidebar {
        padding-top: 0.6rem;
        padding-left: 0.75rem;
        padding-right: 0.25rem;
    }
    .nav-sidebar div[role="radiogroup"] > label {
        display: block;
        padding: 0.35rem 0.55rem;
        margin-bottom: 0.45rem;
        border-radius: 0.35rem;
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        cursor: pointer;
        font-size: 0.78rem;
    }
    .nav-sidebar div[role="radiogroup"] > label:hover {
        background-color: #f3f4f6;
        border-color: #cbd5e1;
    }
    .nav-sidebar div[role="radiogroup"] > label[data-baseweb="radio"] > div:first-child {
        display: none;
    }
    .nav-sidebar div[role="radiogroup"] > label[data-baseweb="radio"][aria-checked="true"] {
        background-color: #e0f2fe;
        border-color: #3b82f6;
    }
    .filter-card {
        background-color: #ffffff;
        padding: 1.0rem 1.0rem 0.9rem 1.0rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
        border: 1px solid #e5e7eb;
        margin-top: 0.75rem;
    }
    .filter-title {
        font-weight: 600;
        font-size: 0.98rem;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.35rem;
        color: #111827;
    }
    .filter-title span.icon {
        font-size: 1.0rem;
    }
    .filter-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #6b7280;
        margin-bottom: 0.18rem;
        margin-top: 0.55rem;
    }
    .map-summary {
        text-align: center;
        font-size: 0.78rem;
        color: #4b5563;
        margin-bottom: 0.2rem;
        margin-top: 0.2rem;
    }
    .kpi-card {
        padding: 0.7rem 0.9rem;
        background-color: #ffffff;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.15rem;
    }
    .kpi-value {
        font-size: 1.1rem;
        font-weight: 600;
        color: #111827;
    }
    .kpi-sub {
        font-size: 0.75rem;
        color: #6b7280;
    }
    .streamlit-expanderHeader {
        font-size: 0.82rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Top strip
st.markdown(
    """
    <div class="top-bar">
        <div class="top-bar-title">GBD-style Global Air Pollution Dashboard</div>
        <div class="top-bar-subtitle">
            Visualising worldwide air quality (AQI) and PM2.5 exposure with interactive maps and charts
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------
# Navigation
# -----------------------------------------------------------
nav_col, content_col = st.columns([0.08, 0.92])

with nav_col:
    st.markdown("<div class='nav-sidebar'>", unsafe_allow_html=True)
    choice = st.radio(
        "Navigation",
        [
            "🗺 Global Map",
            "📊 AQI Summary",
            "🏙 Country Pollutants",
            "🔍 Country Deep Dive",
            "📈 PM2.5 Trends",
        ],
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

if "Global Map" in choice:
    page = "map"
elif "AQI Summary" in choice:
    page = "summary"
elif "Country Pollutants" in choice:
    page = "country"
elif "Country Deep Dive" in choice:
    page = "deep_dive"
else:
    page = "pm25"

metric_options = get_metric_options(base_df)

# -----------------------------------------------------------
# Content
# -----------------------------------------------------------
with content_col:

    # =======================================================
    # PAGE 1 – Global Map
    # =======================================================
    if page == "map":
        st.markdown("### 🗺 Global Air Pollution Map (Interactive)")

        default_metric_label = (
            "Overall AQI Value"
            if "Overall AQI Value" in metric_options
            else list(metric_options.keys())[0]
        )

        filters_col, map_col = st.columns([0.26, 0.74])

        # ---- Filters
        with filters_col:
            st.markdown(
                """
                <div class='filter-card'>
                    <div class='filter-title'>
                        <span class='icon'>⚙️</span><span>Settings</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            # Metric selector
            st.markdown("<div class='filter-label'>Pollution metric</div>", unsafe_allow_html=True)
            metric_label = st.selectbox(
                "",
                list(metric_options.keys()),
                index=list(metric_options.keys()).index(default_metric_label),
                key="map_metric",
            )
            metric_col = metric_options[metric_label]

            # AQI categories filter
            if "aqi_category" in base_df.columns:
                st.markdown("<div class='filter-label'>AQI category</div>", unsafe_allow_html=True)
                categories = sorted(base_df["aqi_category"].dropna().unique().tolist())
                selected_cats = st.multiselect(
                    "",
                    categories,
                    default=categories,
                    key="map_categories",
                )
            else:
                selected_cats = None

            # Minimum overall AQI
            if "aqi_value" in base_df.columns:
                st.markdown("<div class='filter-label'>Minimum overall AQI value</div>", unsafe_allow_html=True)
                min_val = float(base_df["aqi_value"].min())
                max_val = float(base_df["aqi_value"].max())
                min_threshold = st.slider(
                    "",
                    min_value=float(round(min_val, 1)),
                    max_value=float(round(max_val, 1)),
                    value=float(round(min_val, 1)),
                    step=1.0,
                    key="map_min_aqi",
                )
            else:
                min_threshold = None

            st.markdown("</div>", unsafe_allow_html=True)  # close filter-card

        # ---- Map
        with map_col:
            df_map = base_df.copy()

            if selected_cats:
                df_map = df_map[df_map["aqi_category"].isin(selected_cats)]
            if min_threshold is not None and "aqi_value" in df_map.columns:
                df_map = df_map[df_map["aqi_value"] >= min_threshold]

            if df_map.empty:
                st.warning("No data matches the current filters. Try relaxing them.")
            elif "country" not in df_map.columns:
                st.error("Column 'country' is missing in the dataset.")
            else:
                agg = df_map.groupby("country", as_index=False)[metric_col].mean().dropna()

                if agg.empty:
                    st.warning("No countries found after aggregation.")
                else:
                    # KPI cards
                    avg_val = agg[metric_col].mean()
                    worst_row = agg.loc[agg[metric_col].idxmax()]
                    best_row = agg.loc[agg[metric_col].idxmin()]

                    k1, k2, k3 = st.columns(3)
                    with k1:
                        st.markdown(
                            f"""
                            <div class="kpi-card">
                                <div class="kpi-label">Global average</div>
                                <div class="kpi-value">{avg_val:.1f}</div>
                                <div class="kpi-sub">{metric_label}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with k2:
                        st.markdown(
                            f"""
                            <div class="kpi-card">
                                <div class="kpi-label">Most polluted</div>
                                <div class="kpi-value">{worst_row['country']}</div>
                                <div class="kpi-sub">{worst_row[metric_col]:.1f} {metric_label}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with k3:
                        st.markdown(
                            f"""
                            <div class="kpi-card">
                                <div class="kpi-label">Cleanest</div>
                                <div class="kpi-value">{best_row['country']}</div>
                                <div class="kpi-sub">{best_row[metric_col]:.1f} {metric_label}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    n_countries = agg["country"].nunique()
                    summary_text = f"Showing {n_countries} countries · Metric: {metric_label}"
                    if min_threshold is not None:
                        summary_text += f" · Min overall AQI: {min_threshold:.0f}"
                    st.markdown(f"<div class='map-summary'>{summary_text}</div>", unsafe_allow_html=True)

                    vmin = float(agg[metric_col].min())
                    vmax = float(agg[metric_col].max())

                    fig = px.choropleth(
                        agg,
                        locations="country",
                        locationmode="country names",
                        color=metric_col,
                        color_continuous_scale="RdYlBu_r",
                        range_color=(vmin, vmax),
                        hover_name="country",
                        hover_data={metric_col: ":.1f"},
                    )
                    fig.update_geos(
                        showframe=False,
                        showcoastlines=True,
                        projection_type="natural earth",
                    )
                    fig.update_layout(
                        height=610,
                        margin=dict(l=0, r=0, t=10, b=10),
                        coloraxis_colorbar=dict(
                            title=metric_label,
                            orientation="h",
                            y=-0.18,
                            x=0.5,
                            thickness=12,
                            len=0.80,
                        ),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    with st.expander("Show aggregated data table"):
                        st.dataframe(agg.rename(columns={metric_col: metric_label}))

    # =======================================================
    # PAGE 2 – AQI Summary + correlations
    # =======================================================
    elif page == "summary":
        st.markdown("### 📊 AQI Summary")

        metric_label = st.selectbox(
            "Metric to summarise",
            list(metric_options.keys()),
            key="summary_metric",
        )
        metric_col = metric_options[metric_label]

        left, right = st.columns([0.5, 0.5])

        with left:
            st.markdown("#### Distribution")
            fig_hist = px.histogram(
                base_df,
                x=metric_col,
                nbins=40,
                title=None,
            )
            fig_hist.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_hist, use_container_width=True)

        with right:
            st.markdown("#### Basic statistics")
            desc = base_df[metric_col].describe()[["mean", "std", "min", "25%", "50%", "75%", "max"]]
            st.dataframe(desc.to_frame("value"))

        pollutant_cols = [
            c for c in base_df.columns if c.endswith("_aqi_value") and c != "aqi_value"
        ]
        if len(pollutant_cols) >= 2:
            st.markdown("#### Correlation between pollutant-specific AQI values")
            corr = base_df[pollutant_cols].corr()
            labels = [c.replace("_aqi_value", "").upper() for c in pollutant_cols]
            fig_corr = px.imshow(
                corr,
                x=labels,
                y=labels,
                color_continuous_scale="RdBu",
                zmin=-1,
                zmax=1,
                aspect="auto",
            )
            fig_corr.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_corr, use_container_width=True)

    # =======================================================
    # PAGE 3 – Country pollutants (bar chart)
    # =======================================================
    elif page == "country":
        st.markdown("### 🏙 Country Pollutant Breakdown")

        if "country" not in base_df.columns:
            st.error("Column 'country' is missing in the dataset.")
        else:
            countries = sorted(base_df["country"].dropna().unique().tolist())
            selected_country = st.selectbox("Choose a country", countries, key="country_select")

            df_c = base_df[base_df["country"] == selected_country]

            pollutant_cols = [
                c for c in base_df.columns if c.endswith("_aqi_value") and c != "aqi_value"
            ]
            if not pollutant_cols:
                st.warning("No pollutant-specific AQI columns found in the dataset.")
            else:
                avg_pollutants = df_c[pollutant_cols].mean().reset_index()
                avg_pollutants.columns = ["pollutant", "aqi_value"]
                avg_pollutants["pollutant"] = (
                    avg_pollutants["pollutant"]
                    .str.replace("_aqi_value", "", regex=False)
                    .str.upper()
                )

                fig_bar = px.bar(
                    avg_pollutants,
                    x="pollutant",
                    y="aqi_value",
                    labels={"aqi_value": "Average AQI"},
                    title=f"Average pollutant AQI levels in {selected_country}",
                )
                fig_bar.update_layout(height=440, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_bar, use_container_width=True)

                with st.expander("Show underlying values"):
                    st.dataframe(avg_pollutants)

    # =======================================================
    # PAGE 4 – Country Deep Dive (uses both datasets)
    # =======================================================
    elif page == "deep_dive":
        st.markdown("### 🔍 Country Deep Dive")

        if pm25_df is None:
            st.warning("The PM2.5 dataset (`pm25-air-pollution.csv`) was not found in `data/raw/`.")
        else:
            # Guess columns for PM dataset
            pm_country_col = "country" if "country" in pm25_df.columns else pm25_df.columns[0]
            pm_year_col = "year" if "year" in pm25_df.columns else pm25_df.columns[1]

            numeric_cols = pm25_df.select_dtypes(include="number").columns.tolist()
            if pm_year_col in numeric_cols:
                numeric_cols.remove(pm_year_col)
            pm_value_col = numeric_cols[0] if numeric_cols else None

            if pm_value_col is None:
                st.error("Could not find a numeric PM2.5 column in `pm25-air-pollution.csv`.")
            else:
                base_countries = set(base_df["country"].dropna().unique()) if "country" in base_df.columns else set()
                pm_countries = set(pm25_df[pm_country_col].dropna().unique())
                common_countries = sorted(list(base_countries & pm_countries)) or sorted(list(pm_countries))

                selected_country = st.selectbox("Select a country", common_countries, key="deep_dive_country")

                left, right = st.columns(2)

                # ----- Left: current AQI + pollutant mix
                with left:
                    st.markdown(f"#### Current Air Quality – {selected_country}")
                    df_c = base_df[base_df["country"] == selected_country]
                    if df_c.empty:
                        st.info("No AQI data found for this country in the global air pollution dataset.")
                    else:
                        if "aqi_value" in df_c.columns:
                            avg_aqi = df_c["aqi_value"].mean()
                            st.metric("Average AQI (overall)", f"{avg_aqi:.1f}")

                        pollutant_cols = [
                            c for c in df_c.columns if c.endswith("_aqi_value") and c != "aqi_value"
                        ]
                        if pollutant_cols:
                            poll_avg = df_c[pollutant_cols].mean().reset_index()
                            poll_avg.columns = ["pollutant", "aqi_value"]
                            poll_avg["pollutant"] = (
                                poll_avg["pollutant"]
                                .str.replace("_aqi_value", "", regex=False)
                                .str.upper()
                            )

                            fig_poll = px.bar(
                                poll_avg,
                                x="pollutant",
                                y="aqi_value",
                                labels={"aqi_value": "Average AQI"},
                                title="Average pollutant-specific AQI",
                            )
                            fig_poll.update_layout(height=350, margin=dict(l=0, r=0, t=45, b=0))
                            st.plotly_chart(fig_poll, use_container_width=True)
                        else:
                            st.write("No pollutant-specific AQI columns to summarise.")

                # ----- Right: PM2.5 history
                with right:
                    st.markdown(f"#### PM2.5 Exposure Over Time – {selected_country}")
                    df_pm = pm25_df[pm25_df[pm_country_col] == selected_country].copy()
                    df_pm = df_pm.sort_values(pm_year_col)

                    if df_pm.empty:
                        st.info("No PM2.5 data available for this country in `pm25-air-pollution.csv`.")
                    else:
                        latest_row = df_pm.iloc[-1]
                        latest_year = int(latest_row[pm_year_col])
                        latest_val = float(latest_row[pm_value_col])
                        st.metric(f"Latest PM2.5 (μg/m³) – {latest_year}", f"{latest_val:.1f}")

                        fig_pm = px.line(
                            df_pm,
                            x=pm_year_col,
                            y=pm_value_col,
                            markers=True,
                            labels={pm_year_col: "Year", pm_value_col: "PM2.5 (μg/m³)"},
                            title="PM2.5 trend (historical exposure)",
                        )
                        fig_pm.update_layout(height=350, margin=dict(l=0, r=0, t=45, b=0))
                        st.plotly_chart(fig_pm, use_container_width=True)

                        with st.expander("Show PM2.5 data table"):
                            st.dataframe(df_pm[[pm_country_col, pm_year_col, pm_value_col]])

    # =======================================================
    # PAGE 5 – PM2.5 Trends (simple)
    # =======================================================
    else:  # page == "pm25"
        st.markdown("### 📈 PM2.5 Trends (2010–2019)")

        if pm25_df is None:
            st.warning("The PM2.5 dataset (`pm25-air-pollution.csv`) was not found in `data/raw/`.")
        else:
            pm_country_col = "country" if "country" in pm25_df.columns else pm25_df.columns[0]
            pm_year_col = "year" if "year" in pm25_df.columns else pm25_df.columns[1]

            numeric_cols = pm25_df.select_dtypes(include="number").columns.tolist()
            if pm_year_col in numeric_cols:
                numeric_cols.remove(pm_year_col)
            pm_value_col = numeric_cols[0] if numeric_cols else None

            if pm_value_col is None:
                st.error("Could not find a numeric PM2.5 column in `pm25-air-pollution.csv`.")
            else:
                countries = sorted(pm25_df[pm_country_col].dropna().unique().tolist())
                selected_country = st.selectbox("Choose a country", countries, key="pm25_country")

                df_c = pm25_df[pm25_df[pm_country_col] == selected_country].copy()
                df_c = df_c.sort_values(pm_year_col)

                if df_c.empty:
                    st.info("No PM2.5 data available for this country.")
                else:
                    fig_line = px.line(
                        df_c,
                        x=pm_year_col,
                        y=pm_value_col,
                        markers=True,
                        labels={pm_year_col: "Year", pm_value_col: "PM2.5 (μg/m³)"},
                        title=f"PM2.5 trend over time – {selected_country}",
                    )
                    fig_line.update_layout(height=440, margin=dict(l=0, r=0, t=40, b=0))
                    st.plotly_chart(fig_line, use_container_width=True)

                    with st.expander("Show data table"):
                        st.dataframe(df_c[[pm_country_col, pm_year_col, pm_value_col]])
