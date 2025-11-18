import streamlit as st
import pandas as pd
import plotly.express as px

@st.cache_data
def load_data():
    df = pd.read_csv("data/raw/global_air_pollution.csv")
    # Clean column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Drop rows with missing country or aqi_value (for stable charts)
    if "country" in df.columns:
        df = df.dropna(subset=["country"])
    if "aqi_value" in df.columns:
        df = df.dropna(subset=["aqi_value"])

    return df

def show_data_preview(df):
    st.subheader("Dataset Preview")
    st.write(f"Total rows: {df.shape[0]}")
    st.dataframe(df.head())

def show_top_polluted(df):
    st.subheader("Top 10 Most Polluted Countries")
    if "country" not in df.columns or "aqi_value" not in df.columns:
        st.warning("Missing required columns for this chart")
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
    )
    st.plotly_chart(fig, use_container_width=True)

def show_country_pollutants(df):
    st.subheader("Pollutant Breakdown by Country")
    if "country" not in df.columns:
        st.warning("Missing country column")
        return

    # Work on a version with no missing countries
    df_clean = df.dropna(subset=["country"]).copy()

    # Build dropdown from cleaned list (avoids NaN vs str TypeError)
    countries = sorted(df_clean["country"].astype(str).unique().tolist())
    selected_country = st.selectbox("Choose a country", countries)

    filtered = df_clean[df_clean["country"] == selected_country]

    # any column that ends with _aqi_value (pm2_5_aqi_value, ozone_aqi_value, etc.)
    pollutant_cols = [col for col in filtered.columns if col.endswith("_aqi_value")]

    if not pollutant_cols:
        st.warning("No pollutant columns found")
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

def main():
    st.title("🌍 Global Air Pollution Dashboard")

    df = load_data()
    show_data_preview(df)
    show_top_polluted(df)
    show_country_pollutants(df)

if __name__ == "__main__":
    main()
