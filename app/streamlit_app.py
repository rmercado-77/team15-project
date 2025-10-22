# app/streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import pydeck as pdk
from pathlib import Path

# ---------- Page setup ----------
st.set_page_config(
    page_title="Climate Action – Justice Lens",
    layout="wide",
    page_icon="🌍"
)
st.title("Global Climate Action Social Media Trends (Justice Lens)")
st.caption("Prototype by **Mubarak Alazemi** — Streamlit app & visuals")

# ---------- Data loaders ----------
@st.cache_data
def load_demo():
    """Generate small synthetic data so the app runs anywhere."""
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    df_time = pd.DataFrame({
        "date": dates,
        "sentiment": np.clip(
            np.sin(np.linspace(0, 10, len(dates))) + np.random.normal(0, 0.2, len(dates)),
            -1, 1
        ),
        "posts": np.random.randint(50, 400, len(dates))
    })

    df_tags = pd.DataFrame({
        "hashtag": ["#ClimateJustice", "#LossAndDamage", "#NetZero", "#JustTransition", "#AirQuality"],
        "count": np.random.randint(200, 2000, 5)
    })

    df_geo = pd.DataFrame({
        "lat": [40.71, 34.05, 51.50, 28.61, -33.87],
        "lon": [-74.00, -118.24, -0.12, 77.21, 151.21],
        "region": ["NA-US-NY", "NA-US-CA", "EU-UK-LON", "AS-IN-DEL", "OC-AU-SYD"],
        "engagement": np.random.randint(100, 3000, 5)
    })

    return df_time, df_tags, df_geo


@st.cache_data
def load_csv(path: str):
    """Load a real CSV if you add one under /data (must have at least date, posts, sentiment)."""
    df = pd.read_csv(path)
    # Try to parse common columns; adjust to your real schema later.
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# ---------- Sidebar controls ----------
st.sidebar.header("Data source")
use_demo = st.sidebar.radio("Choose data", ["Demo (built-in)", "CSV from /data"], index=0)

time_df, tag_df, geo_df = load_demo()

if use_demo == "CSV from /data":
    data_dir = Path(__file__).resolve().parents[1] / "data"
    candidates = sorted([p for p in data_dir.glob("*.csv")]) if data_dir.exists() else []
    choice = st.sidebar.selectbox("Pick a CSV in /data", ["(none)"] + [p.name for p in candidates])
    if choice != "(none)":
        df_real = load_csv(str(data_dir / choice))
        # Heuristic mapping to expected columns if present
        if {"date", "posts", "sentiment"}.issubset(df_real.columns):
            time_df = df_real[["date", "posts", "sentiment"]].dropna().copy()
        if {"hashtag", "count"}.issubset(df_real.columns):
            tag_df = df_real[["hashtag", "count"]].groupby("hashtag", as_index=False).sum().copy()
        if {"lat", "lon", "region", "engagement"}.issubset(df_real.columns):
            geo_df = df_real[["lat", "lon", "region", "engagement"]].dropna().copy()

# Optional quick filters (work for demo and real data)
st.sidebar.header("Filters")
date_min = pd.to_datetime(time_df["date"]).min()
date_max = pd.to_datetime(time_df["date"]).max()
start, end = st.sidebar.slider(
    "Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max
)
time_df = time_df[(time_df["date"] >= start) & (time_df["date"] <= end)]

# ---------- KPIs ----------
c1, c2, c3 = st.columns(3)
c1.metric("Total Posts", f"{int(time_df['posts'].sum()):,}")
c2.metric("Average Sentiment", f"{time_df['sentiment'].mean():.2f}")
if not tag_df.empty:
    c3.metric("Top Hashtag", tag_df.sort_values("count", ascending=False).iloc[0]["hashtag"])
else:
    c3.metric("Top Hashtag", "n/a")

st.divider()

# ---------- Sentiment over time ----------
st.subheader("Sentiment over time")
sent_line = (
    alt.Chart(time_df)
    .mark_line(point=False)
    .encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("sentiment:Q", title="Sentiment (−1 to +1)", scale=alt.Scale(domain=(-1, 1))),
        tooltip=["date:T", alt.Tooltip("sentiment:Q", format=".2f")]
    )
    .properties(height=280)
)
st.altair_chart(sent_line, use_container_width=True)

# ---------- Posts over time ----------
st.subheader("Posts over time")
posts_bar = (
    alt.Chart(time_df)
    .mark_bar()
    .encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("posts:Q", title="Number of posts"),
        tooltip=["date:T", "posts:Q"]
    )
    .properties(height=280)
)
st.altair_chart(posts_bar, use_container_width=True)

# ---------- Hashtag frequencies ----------
st.subheader("Top hashtags")
if not tag_df.empty:
    tag_chart = (
        alt.Chart(tag_df.sort_values("count", ascending=False))
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("hashtag:N", sort="-x", title="Hashtag"),
            tooltip=["hashtag:N", "count:Q"]
        )
        .properties(height=260)
    )
    st.altair_chart(tag_chart, use_container_width=True)
else:
    st.info("No hashtag data available for this source.")

# ---------- Geo engagement map ----------
st.subheader("Engagement by region (demo)")
if not geo_df.empty:
    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",  # Streamlit usually provides a default token
            initial_view_state=pdk.ViewState(latitude=20, longitude=0, zoom=1.2),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=geo_df,
                    get_position="[lon, lat]",
                    get_radius="engagement",
                    radius_scale=50,
                    pickable=True,
                )
            ],
            tooltip={"text": "{region}\nEngagement: {engagement}"},
        )
    )
else:
    st.info("No geo data available for this source.")

# ---------- Footer ----------
st.divider()
st.markdown(
    "ℹ️ **How to use**: This app ships with demo data so it runs anywhere. "
    "To use the real dataset later, place a CSV in `/data`, choose it in the sidebar, "
    "and map/rename columns to `date`, `posts`, `sentiment`, `hashtag`, `count`, "
    "`lat`, `lon`, `region`, `engagement` as needed."
)
