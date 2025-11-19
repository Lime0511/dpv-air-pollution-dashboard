import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Global Air Pollution Dashboard",
    page_icon="🌍",
    layout="wide",
)

# ------------------------------------------------------------------
# Global CSS for layout / look
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Reduce default page padding so we can use space better */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 1.5rem;
        padding-left: 0rem;
        padding-right: 0rem;
    }

    /* Top bar (like VizHub title strip) */
    .top-bar {
        width: 100%;
        background-color: #020617; /* very dark */
        border-bottom: 1px solid #1f2937;
        padding: 0.45rem 1.75rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-sizing: border-box;
    }
    .top-bar-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #F9FAFB;
        letter-spacing: 0.03em;
    }
    .top-bar-subtitle {
        font-size: 0.75rem;
        color: #9CA3AF;
    }

    /* Left vertical nav column – make it tight */
    .nav-sidebar {
        padding-top: 0.6rem;
        padding-left: 0.75rem;
        padding-right: 0.25rem;
    }

    /* Make radio options look like small stacked pills, no bullets */
    .nav-sidebar div[role="radiogroup"] > label {
        display: block;
        padding: 0.35rem 0.55rem;
        margin-bottom: 0.45rem;
        border-radius: 0.6rem;
        background-color: #020617;
        border: 1px solid #111827;
        cursor: pointer;
        font-size: 0.78rem;
    }
    .nav-sidebar div[role="radiogroup"] > label:hover {
        background-color: #111827;
        border-color: #1f2937;
    }
    /* Selected state: slightly brighter border / bg */
    .nav-sidebar div[role="radiogroup"] > label[data-baseweb="radio"] > div:first-child {
        display: none;  /* hide the round bullet */
    }
    .nav-sidebar div[role="radiogroup"] > label[data-baseweb="radio"][aria-checked="true"] {
        background-color: #111827;
        border-color: #3B82F6;
    }

    /* Filter panel card */
    .filter-card {
        background-color: #020617;
        padding: 1.1rem 1.2rem 1.0rem 1.2rem;
        border-radius: 0.75rem;
        box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.25);
        margin-top: 0.75rem;
    }
    .filter-title {
        font-weight: 600;
        font-size: 1.0rem;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }
    .filter-title span.icon {
        font-size: 1.0rem;
    }
    .filter-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9CA3AF;
        margin-bottom: 0.2rem;
        margin-top: 0.55rem;
    }

    /* Small label above map */
    .map-summary {
        text-align: center;
        font-size: 0.8rem;
        color: #D1D5DB;
        margin-bottom: 0.6rem;
        margin-top: 0.3rem;
    }

    /* Make expander match the dark theme a bit better */
    .streamlit-expanderHeader {
        font-size: 0.82rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Data loading
# ------------------------------------------------------------------
@st.cache_data
def load_base_data():
    df = pd.read_csv("data/raw/global_air_pollution.csv")
    # Normalise column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
    )
    return df


@st.cache_data
def load_pm25_data():
    try:
        df = pd.read_csv("data/raw/pm25-air-pollution.csv")
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace("(", "", regex=False)
            .str.replace(")", "", regex=False)
        )
        return df
    except Exception:
        return None


base_df = load_base_data()
pm25_df = load_pm25_data()

# ------------------------------------------------------------------
# Helper: build metric options safely from whatever columns exist
# ------------------------------------------------------------------
def get_metric_options(df: pd.DataFrame):
    col_map = {}

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
    if "o3_aqi_value" in df.columns:
        col_map["O₃ AQI Value"] = "o3_aqi_value"

    # Fallback: any numeric column
    if not col_map:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        for c in numeric_cols:
            pretty = c.replace("_", " ").title()
            col_map[pretty] = c

    return col_map


# ------------------------------------------------------------------
# Session state for navigation
# ------------------------------------------------------------------
if "active_page" not in st.session_state:
    st.session_state.active_page = "map"

# ------------------------------------------------------------------
# TOP BAR (always visible, full width)
# ------------------------------------------------------------------
st.markdown(
    """
    <div class="top-bar">
        <div class="top-bar-title">🌍 Global Air Pollution Dashboard</div>
        <div class="top-bar-subtitle">
            Interactive exploration of global air quality, pollutants and PM2.5 trends
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# MAIN LAYOUT: [left icon nav] | [page content]
# ------------------------------------------------------------------
nav_col, content_col = st.columns([0.07, 0.93])

# ----------------- LEFT NAV -----------------
with nav_col:
    st.markdown("<div class='nav-sidebar'>", unsafe_allow_html=True)

    # Use radio so you can see which view is active
    choice = st.radio(
        "Navigation",
        [
            "🗺 Global Map",
            "📊 AQI Summary",
            "🏙 Country Pollutants",
            "📈 PM2.5 Trends",
        ],
        index=[
            "map",
            "summary",
            "country",
            "pm25",
        ].index(st.session_state.active_page),
        label_visibility="collapsed",
    )

    if "Global Map" in choice:
        st.session_state.active_page = "map"
    elif "AQI Summary" in choice:
        st.session_state.active_page = "summary"
    elif "Country Pollutants" in choice:
        st.session_state.active_page = "country"
    elif "PM2.5 Trends" in choice:
        st.session_state.active_page = "pm25"

    st.markdown("</div>", unsafe_allow_html=True)

# ----------------- RIGHT CONTENT -----------------
with content_col:
    page = st.session_state.active_page

    # ==============================================================
    # PAGE 1 – GLOBAL MAP (INTERACTIVE)
    # ==============================================================
    if page == "map":
        # Page subtitle (just text, top-left)
        st.markdown(
            "#### 🗺 Global Air Pollution Map (Interactive)",
        )

        metric_options = get_metric_options(base_df)
        default_metric_label = (
            "Overall AQI Value"
            if "Overall AQI Value" in metric_options
            else list(metric_options.keys())[0]
        )

        # Layout for this page: [filters | map], both inside the right content column
        filters_col, map_col = st.columns([0.30, 0.70])

        # ---------- FILTER PANEL ----------
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
            st.markdown(
                "<div class='filter-label'>Pollution metric</div>",
                unsafe_allow_html=True,
            )
            metric_label = st.selectbox(
                "",
                list(metric_options.keys()),
                index=list(metric_options.keys()).index(default_metric_label),
                key="map_metric",
            )
            metric_col = metric_options[metric_label]

            # AQI categories
            if "aqi_category" in base_df.columns:
                st.markdown(
                    "<div class='filter-label'>AQI category</div>",
                    unsafe_allow_html=True,
                )
                categories = (
                    base_df["aqi_category"].dropna().unique().tolist()
                )
                categories = sorted(categories)
                selected_cats = st.multiselect(
                    "",
                    categories,
                    default=categories,
                    key="map_categories",
                )
            else:
                selected_cats = None

            # Min overall AQI slider
            if "aqi_value" in base_df.columns:
                st.markdown(
                    "<div class='filter-label'>Minimum overall AQI value</div>",
                    unsafe_allow_html=True,
                )
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

        # ---------- MAP ----------
        with map_col:
            df_map = base_df.copy()

            # Apply filters
            if selected_cats:
                df_map = df_map[df_map["aqi_category"].isin(selected_cats)]

            if min_threshold is not None and "aqi_value" in df_map.columns:
                df_map = df_map[df_map["aqi_value"] >= min_threshold]

            # Aggregate by country
            if "country" not in df_map.columns:
                st.error("Column 'country' is missing in the dataset.")
            else:
                agg = (
                    df_map.groupby("country", as_index=False)[metric_col]
                    .mean()
                    .dropna()
                )

                n_countries = agg["country"].nunique()

                summary_text = f"Showing {n_countries} countries · Metric: {metric_label}"
                if min_threshold is not None:
                    summary_text += f" · Min overall AQI: {min_threshold:.0f}"

                st.markdown(
                    f"<div class='map-summary'>{summary_text}</div>",
                    unsafe_allow_html=True,
                )

                vmin = float(agg[metric_col].min())
                vmax = float(agg[metric_col].max())

                fig = px.choropleth(
                    agg,
                    locations="country",
                    locationmode="country names",
                    color=metric_col,
                    color_continuous_scale="Blues",
                    range_color=(vmin, vmax),
                )
                fig.update_layout(
                    height=560,
                    margin=dict(l=0, r=0, t=10, b=0),
                    coloraxis_colorbar=dict(
                        title=metric_label,
                        orientation="h",
                        y=-0.18,
                        x=0.5,
                        thickness=10,
                        len=0.7,
                    ),
                )

                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Show aggregated data table"):
                    st.dataframe(agg.rename(columns={metric_col: metric_label}))

    # ==============================================================
    # PAGE 2 – AQI SUMMARY
    # ==============================================================
    elif page == "summary":
        st.markdown("#### 📊 AQI Summary (Method 1)")

        metric_options = get_metric_options(base_df)
        metric_label = st.selectbox(
            "Metric to summarise",
            list(metric_options.keys()),
            key="summary_metric",
        )
        metric_col = metric_options[metric_label]

        left, right = st.columns([0.5, 0.5])

        with left:
            st.markdown("##### Distribution")
            st.write(
                "Histogram of the selected metric across all cities/countries "
                "to see typical air quality levels and outliers."
            )
            fig_hist = px.histogram(
                base_df,
                x=metric_col,
                nbins=40,
                title=None,
            )
            fig_hist.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with right:
            st.markdown("##### Basic statistics")
            desc = base_df[metric_col].describe()[
                ["mean", "std", "min", "25%", "50%", "75%", "max"]
            ]
            st.dataframe(desc.to_frame("value"))

    # ==============================================================
    # PAGE 3 – COUNTRY POLLUTANTS
    # ==============================================================
    elif page == "country":
        st.markdown("#### 🏙 Country Pollutant Breakdown")

        if "country" not in base_df.columns:
            st.error("Column 'country' is missing in the dataset.")
        else:
            countries = sorted(base_df["country"].dropna().unique().tolist())
            selected_country = st.selectbox(
                "Choose a country", countries, key="country_select"
            )

            df_c = base_df[base_df["country"] == selected_country]

            pollutant_cols = [
                c
                for c in base_df.columns
                if "_aqi_value" in c and c != "aqi_value"
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
                fig_bar.update_layout(
                    height=440,
                    margin=dict(l=0, r=0, t=40, b=0),
                )

                st.plotly_chart(fig_bar, use_container_width=True)

                with st.expander("Show underlying values"):
                    st.dataframe(avg_pollutants)

    # ==============================================================
    # PAGE 4 – PM2.5 TRENDS (2010–2019)
    # ==============================================================
    elif page == "pm25":
        st.markdown("#### 📈 PM2.5 Trends (2010–2019)")

        if pm25_df is None:
            st.warning(
                "The PM2.5 dataset (`pm25-air-pollution.csv`) was not found in "
                "`data/raw/`. Please add it to enable this tab."
            )
        else:
            # Try to infer generic columns
            candidate_country = (
                "country" if "country" in pm25_df.columns else pm25_df.columns[0]
            )
            candidate_year = "year" if "year" in pm25_df.columns else pm25_df.columns[1]

            numeric_cols = pm25_df.select_dtypes(include="number").columns.tolist()
            if candidate_year in numeric_cols:
                numeric_cols.remove(candidate_year)
            pm_col = numeric_cols[0] if numeric_cols else None

            if not pm_col:
                st.error("Could not find a numeric PM2.5 column in the PM dataset.")
            else:
                countries = sorted(
                    pm25_df[candidate_country].dropna().unique().tolist()
                )
                selected_country = st.selectbox(
                    "Choose a country", countries, key="pm25_country"
                )

                df_c = pm25_df[pm25_df[candidate_country] == selected_country].copy()
                df_c = df_c.sort_values(candidate_year)

                fig_line = px.line(
                    df_c,
                    x=candidate_year,
                    y=pm_col,
                    markers=True,
                    labels={candidate_year: "Year", pm_col: "PM2.5"},
                    title=f"PM2.5 trend over time – {selected_country}",
                )
                fig_line.update_layout(
                    height=440,
                    margin=dict(l=0, r=0, t=40, b=0),
                )

                st.plotly_chart(fig_line, use_container_width=True)

                with st.expander("Show data table"):
                    st.dataframe(df_c[[candidate_country, candidate_year, pm_col]])
