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
# Minimal styling (cards, spacing, dark theme polish)
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Tighten padding so visuals are higher and wider */
    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 1.2rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
    }

    /* Top header band */
    .top-header {
        background: linear-gradient(90deg, #020617, #020617);
        border-bottom: 1px solid rgba(148, 163, 184, 0.35);
        padding: 0.75rem 0.9rem 0.7rem 0.9rem;
        margin-bottom: 0.8rem;
    }
    .top-title {
        font-size: 1.6rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }
    .top-subtitle {
        font-size: 0.82rem;
        color: #9CA3AF;
        margin-top: 0.15rem;
    }

    /* Left filter panel look */
    .filter-card {
        background-color: #020617;
        padding: 1.05rem 1.15rem;
        border-radius: 0.75rem;
        box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.25);
    }

    .filter-title {
        font-weight: 600;
        font-size: 1.0rem;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }

    .filter-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9CA3AF;
        margin-bottom: 0.15rem;
    }

    /* Small label above map */
    .map-summary {
        text-align: center;
        font-size: 0.8rem;
        color: #D1D5DB;
        margin-bottom: 0.5rem;
        margin-top: 0.1rem;
    }

    /* --- ICON RAIL --- */
    /* Make the left column visually a rail */
    .icon-rail .stRadio > div {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .icon-rail label {
        width: 44px;
        height: 44px;
        border-radius: 0.9rem;
        border: 1px solid rgba(148, 163, 184, 0.40);
        background: #020617;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.15s ease-out;
        padding: 0;
    }
    .icon-rail label:hover {
        border-color: #38bdf8;
        box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.5);
    }
    .icon-rail input {
        display: none;
    }
    .icon-rail .stRadio [aria-checked="true"] + div label {
        background: #0f172a;
        border-color: #38bdf8;
        box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.7);
    }

    /* Shrink nav column so it acts like the IHME left strip */
    /* (Streamlit uses dynamic classes, so we only rely on ratios in st.columns) */
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
# Helpers
# ------------------------------------------------------------------
def get_metric_options(df: pd.DataFrame):
    """
    Build a dict of friendly label -> column name
    based on what actually exists in the dataset.
    """
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

    # Fallback: if nothing above exists, just pick any numeric column
    if not col_map:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        for c in numeric_cols:
            pretty = c.replace("_", " ").title()
            col_map[pretty] = c

    return col_map


# ------------------------------------------------------------------
# Navigation – vertical icon menu on the far left
# ------------------------------------------------------------------
if "active_page" not in st.session_state:
    st.session_state.active_page = "map"

# Icon mapping (icons only; labels used for tooltips + logic)
ICON_MAP = {
    "map": "🗺",
    "summary": "📊",
    "country": "🏙",
    "pm25": "📈",
}
ICON_HELP = {
    "map": "Global Map",
    "summary": "AQI Summary",
    "country": "Country Pollutants",
    "pm25": "PM2.5 Trends (2010–2019)",
}

rail_col, content_col = st.columns([0.06, 0.94])

with rail_col:
    st.markdown("<div class='icon-rail'>", unsafe_allow_html=True)

    icons = list(ICON_MAP.values())
    # Figure out default index from current active_page
    current_icon = ICON_MAP.get(st.session_state.active_page, "🗺")
    default_index = icons.index(current_icon)

    # Radio with icons only; show a generic label but hide in CSS style
    selected_icon = st.radio(
        "Navigation",
        icons,
        index=default_index,
        label_visibility="collapsed",
        help="🗺 Global Map · 📊 AQI Summary · 🏙 Country Pollutants · 📈 PM2.5 Trends",
        key="icon_nav",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Map icon back to page key
    for key, icon in ICON_MAP.items():
        if icon == selected_icon:
            st.session_state.active_page = key
            break

with content_col:
    page = st.session_state.active_page

    # ------------------------------------------------------------------
    # Top header band
    # ------------------------------------------------------------------
    if page == "map":
        subtitle = "Global Air Pollution Map (Interactive)"
    elif page == "summary":
        subtitle = "Distribution and basic statistics of selected AQI metric"
    elif page == "country":
        subtitle = "Average pollutant AQI levels by country"
    else:
        subtitle = "Long-term PM2.5 trends from the secondary dataset"

    st.markdown(
        f"""
        <div class="top-header">
            <div class="top-title">
                🌍 <span>Global Air Pollution Dashboard</span>
            </div>
            <div class="top-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ==============================================================
    # PAGE 1 – GLOBAL MAP (INTERACTIVE)
    # ==============================================================
    if page == "map":
        metric_options = get_metric_options(base_df)

        # Safe default metric label
        if "Overall AQI Value" in metric_options:
            default_metric_label = "Overall AQI Value"
        else:
            default_metric_label = list(metric_options.keys())[0]

        # --------- Layout: Filters (left) | Map (right)
        filters_col, map_col = st.columns([0.32, 0.68])

        with filters_col:
            st.markdown(
                "<div class='filter-card'>"
                "<div class='filter-title'>⚙️ Settings</div>",
                unsafe_allow_html=True,
            )

            # 1. Metric
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
            # Safety: if something weird happens, fall back to first column
            metric_col = metric_options.get(metric_label, list(metric_options.values())[0])

            # 2. AQI categories
            if "aqi_category" in base_df.columns:
                st.markdown(
                    "<div class='filter-label' style='margin-top:0.6rem;'>AQI category</div>",
                    unsafe_allow_html=True,
                )
                categories = sorted(base_df["aqi_category"].dropna().unique().tolist())
                selected_cats = st.multiselect(
                    "",
                    categories,
                    default=categories,
                    key="map_categories",
                )
            else:
                selected_cats = None

            # 3. Min overall AQI threshold (if we have aqi_value at all)
            if "aqi_value" in base_df.columns:
                st.markdown(
                    "<div class='filter-label' style='margin-top:0.6rem;'>Minimum overall AQI value</div>",
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

        # --------------------- MAP COLUMN -------------------------
        with map_col:
            df_map = base_df.copy()

            # Apply filters
            if selected_cats is not None and selected_cats:
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

                # Summary text above the map
                summary_text = f"Showing {n_countries} countries · Metric: {metric_label}"
                if min_threshold is not None:
                    summary_text += f" · Min overall AQI: {min_threshold:.0f}"

                st.markdown(
                    f"<div class='map-summary'>{summary_text}</div>",
                    unsafe_allow_html=True,
                )

                # Build choropleth
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
                    height=580,
                    margin=dict(l=0, r=0, t=8, b=0),
                    coloraxis_colorbar=dict(
                        title=metric_label,
                        orientation="h",
                        y=-0.19,
                        x=0.5,
                        thickness=10,
                        len=0.7,
                    ),
                )

                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Show aggregated data table"):
                    st.dataframe(
                        agg.rename(columns={metric_col: metric_label}),
                    )

    # ==============================================================
    # PAGE 2 – AQI SUMMARY
    # ==============================================================
    elif page == "summary":
        st.subheader("📊 AQI Summary (Method 1)")

        metric_options = get_metric_options(base_df)
        metric_label = st.selectbox(
            "Metric to summarise", list(metric_options.keys()), key="summary_metric"
        )
        metric_col = metric_options.get(metric_label, list(metric_options.values())[0])

        left, right = st.columns([0.5, 0.5])

        with left:
            st.markdown("#### Distribution")
            st.write(
                "Histogram of the selected metric across all cities/countries "
                "(helps see typical air quality levels and outliers)."
            )
            fig_hist = px.histogram(
                base_df,
                x=metric_col,
                nbins=40,
                title=None,
            )
            fig_hist.update_layout(
                height=420,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with right:
            st.markdown("#### Basic statistics")
            desc = base_df[metric_col].describe()[
                ["mean", "std", "min", "25%", "50%", "75%", "max"]
            ]
            st.dataframe(desc.to_frame("value"))

    # ==============================================================
    # PAGE 3 – COUNTRY POLLUTANTS
    # ==============================================================
    elif page == "country":
        st.subheader("🏙 Country Pollutant Breakdown")

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

                avg_pollutants["pollutant"] = avg_pollutants[
                    "pollutant"
                ].str.replace("_aqi_value", "", regex=False).str.upper()

                fig_bar = px.bar(
                    avg_pollutants,
                    x="pollutant",
                    y="aqi_value",
                    labels={"aqi_value": "Average AQI"},
                    title=f"Average pollutant AQI levels in {selected_country}",
                )
                fig_bar.update_layout(
                    height=460,
                    margin=dict(l=0, r=0, t=40, b=0),
                )

                st.plotly_chart(fig_bar, use_container_width=True)

                with st.expander("Show underlying values"):
                    st.dataframe(avg_pollutants)

    # ==============================================================
    # PAGE 4 – PM2.5 TRENDS (2010–2019)
    # ==============================================================
    elif page == "pm25":
        st.subheader("📈 PM2.5 Trends (2010–2019)")

        if pm25_df is None:
            st.warning(
                "The PM2.5 dataset (`pm25-air-pollution.csv`) was not found in "
                "`data/raw/`. Please add it to enable this tab."
            )
        else:
            # Expecting columns like: country, year, pm25 or similar
            candidate_country = "country" if "country" in pm25_df.columns else pm25_df.columns[0]
            candidate_year = "year" if "year" in pm25_df.columns else pm25_df.columns[1]

            numeric_cols = pm25_df.select_dtypes(include="number").columns.tolist()
            # Remove year if numeric
            if candidate_year in numeric_cols:
                numeric_cols.remove(candidate_year)
            pm_col = numeric_cols[0] if numeric_cols else None

            if not pm_col:
                st.error("Could not find a numeric PM2.5 column in the PM dataset.")
            else:
                countries = sorted(pm25_df[candidate_country].dropna().unique().tolist())
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
                    height=460,
                    margin=dict(l=0, r=0, t=40, b=0),
                )

                st.plotly_chart(fig_line, use_container_width=True)

                with st.expander("Show data table"):
                    st.dataframe(df_c[[candidate_country, candidate_year, pm_col]])
