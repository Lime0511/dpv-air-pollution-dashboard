# app.py
import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------
# Streamlit page config
# -----------------------------------------------------------
st.set_page_config(
    page_title="Global Air Pollution Dashboard",
    page_icon="🌍",
    layout="wide",
)

# -----------------------------------------------------------
# Styling helpers
# -----------------------------------------------------------

def inject_css():
    st.markdown(
        """
        <style>
        /* Make the whole app look a bit tighter and cleaner */
        .main blockquote { border-left: 0.25rem solid #444; }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1.5rem;
            padding-left: 2.5rem;
            padding-right: 2.5rem;
        }

        /* Left navigation icons */
        .nav-icon {
            width: 46px;
            height: 46px;
            border-radius: 12px;
            background: #151921;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            margin-bottom: 0.6rem;
            border: 1px solid #202632;
            transition: all 0.15s ease-out;
            font-size: 22px;
        }
        .nav-icon.active {
            background: #2563eb;
            border-color: #3b82f6;
        }
        .nav-icon:hover {
            border-color: #4b5563;
        }

        /* Card-like panels */
        .panel {
            background: #0f172a;
            border-radius: 14px;
            padding: 1.1rem 1.2rem 1.2rem 1.2rem;
            border: 1px solid #1f2937;
        }

        .panel-title {
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.03em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase & snake_case columns, remove dots (so PM2.5 → pm25)."""
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(".", "", regex=False)
    )
    return df


# -----------------------------------------------------------
# Data loading
# -----------------------------------------------------------

@st.cache_data
def load_global_aqi() -> pd.DataFrame:
    """
    Main AQI dataset used for the global map and summary pages.
    Adjust the path if your CSV lives somewhere else.
    """
    path = "data/raw/global_air_pollution.csv"
    df = pd.read_csv(path)
    df = standardise_columns(df)
    return df


@st.cache_data
def load_pm25_data() -> pd.DataFrame:
    """
    PM2.5 dataset from data/raw/pm25-air-pollution.csv.
    This is the OWID file you asked about.
    """
    path = "data/raw/pm25-air-pollution.csv"
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        st.error(f"Could not find PM2.5 dataset at `{path}`.")
        return pd.DataFrame()

    df = standardise_columns(df)

    # Entity → country
    if "entity" in df.columns and "country" not in df.columns:
        df = df.rename(columns={"entity": "country"})

    # Long PM2.5 column → pm25
    pm25_raw = (
        "concentrations_of_fine_particulate_matter_(pm25)_-_residence_area_type:_total"
    )
    if pm25_raw in df.columns:
        df = df.rename(columns={pm25_raw: "pm25"})
    else:
        # Fallback: pick a numeric column that looks like PM2.5
        for c in df.columns:
            if "pm25" in c or "particulate" in c:
                df = df.rename(columns={c: "pm25"})
                break

    return df


inject_css()
aqi_df = load_global_aqi()
pm25_df = load_pm25_data()

# -----------------------------------------------------------
# Navigation state
# -----------------------------------------------------------

NAV_PAGES = {
    "map": {"icon": "🌍", "label": "Global Map"},
    "summary": {"icon": "📊", "label": "AQI Summary"},
    "country": {"icon": "🧪", "label": "Country Pollutants"},
    "pm25": {"icon": "📈", "label": "PM2.5 Trends"},
}

if "active_page" not in st.session_state:
    st.session_state.active_page = "map"


def nav_icon(key: str):
    """Render one nav icon and handle click."""
    page = NAV_PAGES[key]
    is_active = st.session_state.active_page == key
    css_class = "nav-icon active" if is_active else "nav-icon"
    # Use HTML to get the square icon look
    if st.button(
        page["icon"],
        key=f"nav_{key}",
        help=page["label"],
    ):
        st.session_state.active_page = key
    st.markdown(
        f"<div class='{css_class}'>{page['icon']}</div>",
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------
# Page renderers
# -----------------------------------------------------------

def page_global_map(df: pd.DataFrame):
    st.markdown("### 🌍 Global Air Pollution Map (Interactive)")

    if df.empty:
        st.info("Global AQI dataset is empty or failed to load.")
        return

    # Guess metric columns
    metric_options = {
        "Overall AQI Value": "overall_aqi_value",
        "PM2.5 (Fine Particulate Matter)": "pm25",
        "NO₂ (Nitrogen Dioxide)": "no2",
        "O₃ (Ozone)": "o3",
        "CO (Carbon Monoxide)": "co",
    }
    # Keep only metrics that actually exist
    metric_options = {
        label: col for label, col in metric_options.items() if col in df.columns
    }

    left, right = st.columns([0.42, 0.58], gap="large")

    with left:
        st.markdown("<div class='panel'><div class='panel-title'>Settings</div>", unsafe_allow_html=True)

        metric_label = st.selectbox(
            "Pollution metric",
            list(metric_options.keys()),
            index=0,
        )
        metric_col = metric_options[metric_label]

        # AQI category filter if available
        categories = (
            sorted(df["aqi_category"].dropna().unique().tolist())
            if "aqi_category" in df.columns
            else []
        )
        selected_categories = []
        if categories:
            selected_categories = st.multiselect(
                "AQI Category",
                categories,
                default=categories,
            )

        min_val = float(df[metric_col].min())
        max_val = float(df[metric_col].max())
        min_filter = st.slider(
            "Minimum Overall AQI Value",
            min_value=min_val,
            max_value=max_val,
            value=min_val,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        # Filter
        map_df = df.copy()
        if selected_categories and "aqi_category" in map_df.columns:
            map_df = map_df[map_df["aqi_category"].isin(selected_categories)]
        map_df = map_df[map_df[metric_col] >= min_filter]

        if "country" not in map_df.columns:
            st.error("Dataset is missing a `country` column for the map.")
            st.write("Available columns:", list(map_df.columns))
            return

        agg = (
            map_df.groupby("country", as_index=False)[metric_col]
            .mean()
            .rename(columns={metric_col: "metric_value"})
        )

        st.caption(
            f"Showing {len(agg)} countries · Metric: **{metric_label}** · "
            f"Min overall AQI: {min_filter:.1f}"
        )

        fig = px.choropleth(
            agg,
            locations="country",
            locationmode="country names",
            color="metric_value",
            color_continuous_scale="Blues",
            labels={"metric_value": metric_label, "country": "Country"},
        )
        fig.update_layout(
            height=520,
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_colorbar=dict(title=metric_label),
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show aggregated data table"):
        st.dataframe(
            agg.sort_values("metric_value", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


def page_aqi_summary(df: pd.DataFrame):
    st.markdown("### 📊 AQI Summary (Method 1)")

    if df.empty:
        st.info("Global AQI dataset is empty or failed to load.")
        return

    col1, col2 = st.columns(2)

    with col1:
        if "overall_aqi_value" in df.columns:
            st.metric(
                "Global mean AQI",
                f"{df['overall_aqi_value'].mean():.1f}",
            )
        if "pm25" in df.columns:
            st.metric(
                "Global mean PM2.5 (µg/m³)",
                f"{df['pm25'].mean():.1f}",
            )

    with col2:
        if "aqi_category" in df.columns:
            cat_counts = (
                df.groupby("aqi_category")["aqi_category"]
                .count()
                .rename("count")
                .reset_index()
            )
            fig = px.bar(
                cat_counts,
                x="aqi_category",
                y="count",
                labels={"aqi_category": "AQI Category", "count": "Number of records"},
            )
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)


def page_country_pollutants(df: pd.DataFrame):
    st.markdown("### 🧪 Country Pollutant Breakdown")

    if df.empty:
        st.info("Global AQI dataset is empty or failed to load.")
        return

    if "country" not in df.columns:
        st.error("Dataset is missing a `country` column.")
        st.write("Available columns:", list(df.columns))
        return

    countries = sorted(df["country"].dropna().unique().tolist())
    country = st.selectbox("Select country", countries, index=countries.index("Malaysia") if "Malaysia" in countries else 0)

    subset = df[df["country"] == country]

    pollutant_cols = [c for c in ["pm25", "no2", "o3", "co"] if c in subset.columns]
    if not pollutant_cols:
        st.info("No pollutant columns (PM2.5, NO₂, O₃, CO) found in this dataset.")
        return

    pollutant_means = (
        subset[pollutant_cols].mean().rename("value").reset_index().rename(columns={"index": "pollutant"})
    )
    fig = px.bar(
        pollutant_means,
        x="pollutant",
        y="value",
        labels={"pollutant": "Pollutant", "value": "Mean value"},
    )
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(f"Show raw data for {country}"):
        st.dataframe(subset, use_container_width=True)


def page_pm25_trends(df: pd.DataFrame):
    st.markdown("### 📈 PM2.5 Trends (2010–2019)")

    if df.empty:
        st.info("PM2.5 dataset is empty or failed to load.")
        return

    required_cols = {"country", "year"}
    if not required_cols.issubset(df.columns):
        st.error(
            "PM2.5 dataset does not have the expected `country` and `year` columns "
            "after cleaning."
        )
        st.write("Available columns:", list(df.columns))
        return

    left, right = st.columns([0.35, 0.65], gap="large")

    with left:
        st.markdown("<div class='panel'><div class='panel-title'>Settings</div>", unsafe_allow_html=True)

        countries = sorted(df["country"].dropna().unique().tolist())
        default_countries = [c for c in ["Malaysia", "China", "India", "United States"] if c in countries]
        if not default_countries:
            default_countries = countries[:3]

        selected_countries = st.multiselect(
            "Select countries",
            countries,
            default=default_countries,
        )

        year_min = int(df["year"].min())
        year_max = int(df["year"].max())
        year_range = st.slider(
            "Year range",
            min_value=year_min,
            max_value=year_max,
            value=(max(year_min, 2010), year_max),
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        if not selected_countries:
            st.info("Select at least one country to see PM2.5 trends.")
            return

        plot_df = df[
            (df["country"].isin(selected_countries))
            & (df["year"].between(year_range[0], year_range[1]))
        ].copy()

        if "pm25" not in plot_df.columns:
            # Fallback: choose first numeric column except year/code
            num_cols = plot_df.select_dtypes("number").columns.tolist()
            num_cols = [c for c in num_cols if c not in ("year", "code")]
            if not num_cols:
                st.error("Could not find a numeric PM2.5 column in the dataset.")
                st.write("Available columns:", list(plot_df.columns))
                return
            value_col = num_cols[0]
        else:
            value_col = "pm25"

        fig = px.line(
            plot_df,
            x="year",
            y=value_col,
            color="country",
            markers=True,
            labels={"year": "Year", value_col: "PM2.5 (µg/m³)", "country": "Country"},
        )
        fig.update_layout(
            height=520,
            margin=dict(l=0, r=0, t=10, b=0),
            legend_title=None,
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Show underlying PM2.5 data"):
            st.dataframe(plot_df.sort_values(["country", "year"]), use_container_width=True)


# -----------------------------------------------------------
# Layout: left nav + right content
# -----------------------------------------------------------

nav_col, main_col = st.columns([0.08, 0.92], gap="large")

with nav_col:
    # A bit of space at the top
    st.markdown("<br/>", unsafe_allow_html=True)
    # Navigation icons (top to bottom)
    for key in ["map", "summary", "country", "pm25"]:
        # render clickable icon + visual box
        is_active = st.session_state.active_page == key
        button_label = NAV_PAGES[key]["icon"]
        if st.button(button_label, key=f"btn_{key}", help=NAV_PAGES[key]["label"]):
            st.session_state.active_page = key
        # Style box
        css_class = "nav-icon active" if is_active else "nav-icon"
        st.markdown(f"<div class='{css_class}'>{button_label}</div>", unsafe_allow_html=True)

with main_col:
    st.markdown("## Global Air Pollution Dashboard")

    active = st.session_state.active_page
    if active == "map":
        page_global_map(aqi_df)
    elif active == "summary":
        page_aqi_summary(aqi_df)
    elif active == "country":
        page_country_pollutants(aqi_df)
    elif active == "pm25":
        page_pm25_trends(pm25_df)
