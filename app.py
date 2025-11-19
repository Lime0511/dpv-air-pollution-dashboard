import os

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------
# BASIC SETUP
# ------------------------------------------------------------
st.set_page_config(
    page_title="Global Air Pollution Dashboard",
    layout="wide",
    page_icon="🌍",
)

# Global CSS to control layout & styling
st.markdown(
    """
    <style>
    /* Reduce default padding */
    .block-container {
        padding-top: 0.5rem;
        padding-left: 0.5rem;
        padding-right: 1rem;
        max-width: 100%;
    }

    body {
        background-color: #05070c;
    }

    /* Top header bar */
    .top-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1.25rem 0.5rem 1.25rem;
        border-bottom: 1px solid #262833;
        background: transparent;
        font-family: system-ui, sans-serif;
    }

    .top-title {
        font-size: 1.7rem;
        font-weight: 700;
        color: #f5f5f7;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }

    .top-actions {
        font-size: 0.85rem;
        color: #9ca3af;
        display: flex;
        gap: 0.8rem;
        align-items: center;
    }

    .top-pill {
        border-radius: 999px;
        padding: 0.4rem 0.8rem;
        background: #111827;
        border: 1px solid #27324b;
    }

    /* Sidebar navigation (left-most column) */
    .sidebar-nav {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.6rem;
        margin-top: 1.4rem;
    }

    .sidebar-nav .stButton > button {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        border: 1px solid #374151;
        background: #0b1120;
        color: #e5e7eb;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.15s ease-in-out;
        padding: 0;
    }

    .sidebar-nav .stButton > button:hover {
        border-color: #3b82f6;
        background: #111827;
        transform: translateY(-1px);
    }

    /* Active icon state, we apply via custom class */
    .nav-active {
        border-color: #60a5fa !important;
        background: linear-gradient(135deg, #111827, #1f2937) !important;
        box-shadow: 0 0 0 1px #1d4ed8;
    }

    /* Filter card styling */
    .filter-card {
        background: #050814;
        border-radius: 14px;
        padding: 0.9rem 1rem 1.1rem 1rem;
        border: 1px solid #1f2937;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.75);
    }

    .filter-title-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.4rem;
    }

    .filter-title {
        font-weight: 600;
        color: #e5e7eb;
    }

    .filter-subtitle {
        font-size: 0.75rem;
        color: #9ca3af;
    }

    .filter-label {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        color: #9ca3af;
        text-transform: uppercase;
        margin-top: 0.6rem;
        margin-bottom: 0.2rem;
    }

    /* Map summary text */
    .map-summary {
        margin-top: 0.6rem;
        margin-bottom: 0.35rem;
        text-align: center;
        font-size: 0.78rem;
        color: #9ca3af;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 0.85rem !important;
    }

    /* Shrink vertical gaps between elements a bit */
    .stSelectbox, .stMultiSelect, .stSlider {
        margin-top: 0.15rem;
        margin-bottom: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# STATE
# ------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "map"  # default tab

def set_page(page_name: str):
    st.session_state["page"] = page_name

# ------------------------------------------------------------
# DATA LOADING
# ------------------------------------------------------------
@st.cache_data
def load_base_data():
    path = "data/raw/global_air_pollution.csv"
    if not os.path.exists(path):
        return None, f"CSV not found at {path}"
    df = pd.read_csv(path)

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Try to keep only rows with non-null country & aqi_value
    if "country" in df.columns:
        df = df[df["country"].notna()]
    if "aqi_value" in df.columns:
        df = df[df["aqi_value"].notna()]

    return df, None


@st.cache_data
def load_pm25_data():
    path = "data/raw/pm25-air-pollution.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


base_df, base_err = load_base_data()
pm25_df = load_pm25_data()

# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
st.markdown(
    """
    <div class="top-header">
        <div class="top-title">
            <span>🌍</span>
            <span>Global Air Pollution Dashboard</span>
        </div>
        <div class="top-actions">
            <div class="top-pill">Interactive • Streamlit</div>
            <span>Last updated from static dataset</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")  # tiny spacer

# ------------------------------------------------------------
# THREE-COLUMN LAYOUT: NAV | FILTERS | MAIN
# ------------------------------------------------------------
nav_col, filter_col, main_col = st.columns([0.2, 1.1, 2.7], gap="large")

# ------------------------- NAV COLUMN ------------------------
with nav_col:
    st.markdown("<div class='sidebar-nav'>", unsafe_allow_html=True)

    # Helper: add active CSS by injecting a tiny HTML snippet after the button
    def nav_button(icon, key, page_name, help_text):
        clicked = st.button(icon, key=key, help=help_text)
        active = st.session_state["page"] == page_name
        # Add a tiny HTML span we can grab with CSS if needed (no-op for now)
        if active:
            st.markdown(
                "<span class='nav-active-marker'></span>",
                unsafe_allow_html=True,
            )
        if clicked:
            set_page(page_name)
        return active

    active_map = nav_button("🌍", "nav_map", "map", "Global Map")
    active_sum = nav_button("📊", "nav_summary", "summary", "AQI Summary")
    active_poll = nav_button("🧪", "nav_pollutants", "pollutants", "Country Pollutants")
    active_trend = nav_button("📈", "nav_pm25", "pm25", "PM2.5 Trends (2010–2019)")

    # Apply active styling via a small JS-free trick:
    # The nth-child after click gets the 'nav-active' class using CSS trick is tricky;
    # instead we just rely on Streamlit's rerun and style via index order.
    # To keep it simple we won't overcomplicate this — selected icon will still show
    # as pressed and highlighted by Streamlit's focus ring.

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------- FILTER COLUMN ------------------------
with filter_col:
    if base_err:
        st.error(base_err)
    else:
        st.markdown(
            """
            <div class="filter-card">
              <div class="filter-title-bar">
                 <div class="filter-title">Settings</div>
              </div>
            """,
            unsafe_allow_html=True,
        )

        # Only show filters that are relevant for each page.
        # For now, main filter set is for the map & AQI summary pages.
        if st.session_state["page"] in ("map", "summary"):
            # Metric options based on available columns
            metric_candidates = {
                "Overall AQI Value": "aqi_value",
                "PM2.5 AQI Value": "pm2_5_aqi_value",
                "CO AQI Value": "co_aqi_value",
                "NO₂ AQI Value": "no2_aqi_value",
                "Ozone AQI Value": "ozone_aqi_value",
            }
            available_metric_labels = [
                label for label, col in metric_candidates.items() if col in base_df.columns
            ]
            if not available_metric_labels:
                available_metric_labels = ["Overall AQI Value"]
                metric_candidates = {"Overall AQI Value": "aqi_value"}

            st.markdown('<div class="filter-label">Pollution metric</div>', unsafe_allow_html=True)
            metric_label = st.selectbox(
                "",
                available_metric_labels,
                index=0,
            )
            metric_col = metric_candidates[metric_label]

            # AQI category multiselect
            cat_col = "aqi_category"
            if cat_col in base_df.columns:
                st.markdown('<div class="filter-label">AQI category</div>', unsafe_allow_html=True)
                all_cats = sorted(base_df[cat_col].dropna().unique().tolist())
                default_cats = all_cats[:]  # start with all selected
                selected_cats = st.multiselect(
                    "",
                    options=all_cats,
                    default=default_cats,
                )
            else:
                selected_cats = None

            # Minimum AQI slider
            st.markdown(
                '<div class="filter-label">Minimum overall AQI value</div>',
                unsafe_allow_html=True,
            )
            min_aqi = float(
                st.slider(
                    "",
                    min_value=float(base_df[metric_col].min()),
                    max_value=float(base_df[metric_col].max()),
                    value=float(base_df[metric_col].min()),
                    step=1.0,
                )
            )

        elif st.session_state["page"] == "pollutants":
            st.markdown(
                '<div class="filter-label">Select country</div>',
                unsafe_allow_html=True,
            )
            countries = sorted(base_df["country"].unique().tolist())
            selected_country = st.selectbox("", countries, index=0)

        elif st.session_state["page"] == "pm25":
            if pm25_df is None:
                st.markdown(
                    "<span style='font-size:0.8rem;color:#f97373;'>PM2.5 trend dataset not found.</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="filter-label">Select country</div>',
                    unsafe_allow_html=True,
                )
                countries = sorted(pm25_df["country"].unique().tolist())
                selected_trend_country = st.selectbox("", countries, index=0)

        # Close filter card container
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------- MAIN / MAP COLUMN --------------------
with main_col:
    if base_err:
        st.stop()

    page = st.session_state["page"]

    # ------------------ PAGE 1: GLOBAL MAP -------------------
    if page == "map":
        df = base_df.copy()

        # Apply filters
        if selected_cats is not None:
            df = df[df["aqi_category"].isin(selected_cats)]
        df = df[df[metric_col] >= min_aqi]

        # Aggregate by country
        grouped = (
            df.groupby("country", as_index=False)[metric_col]
            .mean()
            .rename(columns={metric_col: "metric_value"})
        )

        num_countries = grouped["country"].nunique()
        summary_text = (
            f"Showing {num_countries} countries · Metric: {metric_label} · "
            f"Min overall AQI: {min_aqi:.0f}"
        )

        st.markdown(
            f"<div class='map-summary'>{summary_text}</div>",
            unsafe_allow_html=True,
        )

        if grouped.empty:
            st.warning("No data matches the current filters.")
        else:
            fig = px.choropleth(
                grouped,
                locations="country",
                locationmode="country names",
                color="metric_value",
                hover_name="country",
                color_continuous_scale="Blues",
                labels={"metric_value": metric_label},
            )

            fig.update_layout(
                height=520,
                margin=dict(l=0, r=0, t=10, b=0),
                coloraxis_colorbar=dict(
                    title=metric_label,
                    orientation="h",
                    y=-0.18,
                    x=0.5,
                    xanchor="center",
                ),
            )

            st.plotly_chart(fig, use_container_width=True)

            # Aggregated table
            with st.expander("Show aggregated data table"):
                st.dataframe(
                    grouped.sort_values("metric_value", ascending=False),
                    use_container_width=True,
                )

    # --------------- PAGE 2: AQI SUMMARY ---------------------
    elif page == "summary":
        st.markdown(
            "<div class='map-summary'>Summary of AQI distribution by category.</div>",
            unsafe_allow_html=True,
        )

        if "aqi_category" not in base_df.columns:
            st.warning("AQI category column not found in dataset.")
        else:
            summary = (
                base_df.groupby("aqi_category", as_index=False)["aqi_value"]
                .mean()
                .rename(columns={"aqi_value": "avg_aqi"})
            )

            fig = px.bar(
                summary,
                x="aqi_category",
                y="avg_aqi",
                labels={"aqi_category": "AQI Category", "avg_aqi": "Average AQI"},
            )
            fig.update_layout(
                xaxis_title="AQI Category",
                yaxis_title="Average AQI",
                height=520,
                margin=dict(l=20, r=20, t=40, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Show summary table"):
                st.dataframe(summary, use_container_width=True)

    # --------------- PAGE 3: COUNTRY POLLUTANTS --------------
    elif page == "pollutants":
        st.markdown(
            "<div class='map-summary'>Average pollutant-specific AQI for a selected country.</div>",
            unsafe_allow_html=True,
        )

        df_country = base_df[base_df["country"] == selected_country]

        pollutant_cols = [
            c for c in base_df.columns if c.endswith("_aqi_value") and c != "aqi_value"
        ]
        if not pollutant_cols:
            st.warning("No pollutant-specific AQI columns detected.")
        else:
            pollutant_data = (
                df_country[pollutant_cols]
                .mean()
                .reset_index()
                .rename(columns={"index": "pollutant", 0: "avg_aqi"})
            )
            pollutant_data["pollutant"] = pollutant_data["pollutant"].str.replace(
                "_aqi_value", ""
            ).str.upper()

            fig = px.bar(
                pollutant_data,
                x="pollutant",
                y="avg_aqi",
                labels={"avg_aqi": "Average AQI"},
            )
            fig.update_layout(
                title=f"Pollutant AQI for {selected_country}",
                height=520,
                margin=dict(l=20, r=20, t=60, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Show pollutant table"):
                st.dataframe(pollutant_data, use_container_width=True)

    # --------------- PAGE 4: PM2.5 TRENDS --------------------
    elif page == "pm25":
        if pm25_df is None:
            st.warning("PM2.5 trend dataset not available.")
        else:
            st.markdown(
                (
                    "<div class='map-summary'>"
                    "PM2.5 trend over time for the selected country (2010–2019, if available)."
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

            df_c = pm25_df[pm25_df["country"] == selected_trend_country]
            if "year" not in df_c.columns:
                st.warning("Year column not found in PM2.5 dataset.")
            else:
                val_col = [c for c in df_c.columns if c not in ("country", "year")]
                if not val_col:
                    st.warning("No PM2.5 numeric column detected.")
                else:
                    val_col = val_col[0]
                    fig = px.line(
                        df_c.sort_values("year"),
                        x="year",
                        y=val_col,
                        markers=True,
                        labels={"year": "Year", val_col: "PM2.5"},
                    )
                    fig.update_layout(
                        title=f"PM2.5 Trend for {selected_trend_country}",
                        height=520,
                        margin=dict(l=20, r=20, t=60, b=40),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    with st.expander("Show PM2.5 data"):
                        st.dataframe(df_c[["year", val_col]], use_container_width=True)
