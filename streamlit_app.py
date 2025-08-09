import os
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
from collections import Counter

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="The Unseen Epidemic — Allegheny County Overdoses",
    page_icon="💔",
    layout="wide"
)

# -----------------------------
# Constants
# -----------------------------
WPRDC_URL = (
    "https://data.wprdc.org/api/3/action/datastore_search?"
    "resource_id=1c59b26a-1684-4bfb-92f7-205b947530cf&limit=50000"
)
PA_ZIP_GEOJSON = (
    "https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/master/"
    "pa_pennsylvania_zip_codes_geo.min.json"
)


MAPBOX_STYLE = "open-street-map"  # works without a token

ALLEGHENY_CENTER = {"lat": 40.44, "lon": -79.99}
ALLEGHENY_ZOOM = 9.5  # tighter focus on Allegheny County

# -----------------------------
# Cached loaders
# -----------------------------
@st.cache_data(show_spinner=True)
def load_from_api() -> pd.DataFrame:
    r = requests.get(WPRDC_URL, timeout=60)
    r.raise_for_status()
    return pd.DataFrame(r.json()["result"]["records"])

@st.cache_data(show_spinner=True)
def load_geojson(url: str):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()

# -----------------------------
# Cleaning & shaping
# -----------------------------
def tidy(df: pd.DataFrame):
    # Year
    if "case_year" in df.columns:
        df["year"] = pd.to_numeric(df["case_year"], errors="coerce")
    elif "death_year" in df.columns:
        df["year"] = pd.to_numeric(df["death_year"], errors="coerce")
    else:
        df["year"] = np.nan

    # Sex
    if "sex" in df.columns:
        df["sex"] = df["sex"].fillna("Unknown").replace({"M": "Male", "F": "Female", "U": "Unknown"})
    else:
        df["sex"] = "Unknown"

    # Age
    if "age" in df.columns:
        df["age"] = pd.to_numeric(df["age"], errors="coerce")

    # ZIP — extract first 5 consecutive digits; pad
    zip_col = None
    for c in ["incident_zip", "zip", "zipcode", "incident_zipcode", "zcta"]:
        if c in df.columns:
            zip_col = c
            break
    if zip_col is None:
        df["zip_norm"] = pd.NA
    else:
        df["zip_norm"] = (
            df[zip_col]
            .astype(str)
            .str.extract(r"(\d{5})")[0]
            .astype(str)
            .str.zfill(5)
        )

    # Substances — long form from combined_od1..10
    od_cols = [c for c in df.columns if c.lower().startswith("combined_od")]

    def classify(cell):
        if not isinstance(cell, str):
            return None
        s = cell.upper()
        if "FENTANYL" in s:
            return "Fentanyl"
        if "HEROIN" in s:
            return "Heroin"
        if "COCAINE" in s:
            return "Cocaine"
        if "ALCOHOL" in s:
            return "Alcohol"
        if any(k in s for k in ["MORPHINE", "OXYCODONE", "HYDROCODONE", "OPIOID", "OPIATE"]):
            return "Other Opioids"
        return "Other/Unknown"

    if od_cols:
        melted = df.melt(
            id_vars=["year", "sex", "age", "zip_norm"],
            value_vars=od_cols,
            var_name="od_col",
            value_name="raw_substance",
        )
        melted["substance"] = melted["raw_substance"].apply(classify)
        melted = melted.dropna(subset=["substance"]).copy()
    else:
        melted = pd.DataFrame(columns=["year", "sex", "age", "zip_norm", "substance"])

    # Year bounds
    if df["year"].notna().any():
        year_min = int(np.nanmax([df["year"].min(), 2008]))
        year_max = int(df["year"].max())
    else:
        year_min, year_max = 2008, 2025

    df = df[df["year"].between(year_min, year_max, inclusive="both")]
    melted = melted[melted["year"].between(year_min, year_max, inclusive="both")]

    meta = {
        "year_min": year_min,
        "year_max": year_max,
        "has_substances": len(od_cols) > 0,
        "has_zip": df["zip_norm"].notna().any(),
        "source": "WPRDC — Allegheny County Fatal Accidental Overdoses",
        "api_url": WPRDC_URL,
    }
    return df.reset_index(drop=True), melted.reset_index(drop=True), meta

# -----------------------------
# Load data
# -----------------------------
try:
    df_raw = load_from_api()
except Exception as e:
    st.error(f"Could not fetch data from API: {e}")
    st.stop()

df, melted, meta = tidy(df_raw)

# -----------------------------
# Title & Narrative
# -----------------------------
st.title("The Unseen Epidemic")
st.subheader("Fatal Accidental Overdoses in Allegheny County")
st.caption(f"Data: {meta['source']} • Live API: {meta['api_url']}")

# -----------------------------
# Filters (top of page)
# -----------------------------
st.markdown("### Filters")
fc1, fc2, fc3 = st.columns([2, 2, 3])

with fc1:
    min_y, max_y = int(meta["year_min"]), int(meta["year_max"])
    year_range = st.slider(
        "Year range", min_value=min_y, max_value=max_y,
        value=(max(min_y, max_y - 7), max_y)
    )
with fc2:
    sexes_all = sorted(df["sex"].dropna().unique().tolist()) if "sex" in df.columns else ["Male", "Female", "Unknown"]
    sex_filter = st.multiselect("Sex", options=sexes_all, default=sexes_all)
with fc3:
    # Use only ZIPs available from the dataset (unique df zip_norm); add "ALL ZIPs" option
    zip_options = sorted(df["zip_norm"].dropna().unique().tolist()) if meta["has_zip"] else []
    zip_select = st.selectbox(
        "ZIP (choose one)",
        options=(["ALL ZIPs"] + zip_options) if zip_options else ["ALL ZIPs"],
        index=0
    )

# Apply filters
mask = (df["year"].between(*year_range) & df["sex"].isin(sex_filter))
if zip_select and zip_select != "ALL ZIPs":
    mask &= df["zip_norm"].astype(str) == str(zip_select)
dff = df[mask].copy()

melt_mask = (melted["year"].between(*year_range) & melted["sex"].isin(sex_filter))
if zip_select and zip_select != "ALL ZIPs":
    melt_mask &= melted["zip_norm"].astype(str) == str(zip_select)
meltedf = melted[melt_mask].copy()

with st.expander("Narrative (≈500 words)", expanded=True):
    st.markdown(
        """
**Introduction & Context.** This interactive data story examines fatal accidental overdoses in Allegheny County over time. We align multiple perspectives—yearly fatalities, substances involved, and geography—to support balanced interpretation and practical action.

**Data, Tools & Construction.** Data come from the Western Pennsylvania Regional Data Center (WPRDC). The app uses Streamlit, Plotly, and Pandas. After ingestion, fields are standardized (year, sex, ZIP) and up to ten substance fields per case are reshaped to a tidy long format. Substances are grouped into interpretable categories (*Fentanyl, Heroin, Cocaine, Alcohol, Other Opioids, Other/Unknown*). Each visualization includes explicit labels and tooltips for transparency.

**Visual roadmap.** (1) *Yearly Fatalities* charts the long-run trajectory with options to view totals and by sex. (2 & 4) *Substance Dynamics* pair a stacked area chart with a treemap of drug combinations to show both composition and co-occurrence. (3) *Geographic Patterning* maps cases by ZIP to support place-based responses.

**Conclusion.** The visuals point to a fentanyl-era epidemic with polysubstance involvement and geographic heterogeneity. Priorities include low-barrier MOUD access, naloxone saturation, and timely public reporting.
        """
    )

# -----------------------------
# KPIs
# -----------------------------
st.markdown("### Key Figures")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Records (filtered)", f"{len(dff):,}")
with k2:
    yrs = dff["year"].dropna()
    st.metric("Year span", f"{int(yrs.min()) if not yrs.empty else '-'}–{int(yrs.max()) if not yrs.empty else '-'}")
with k3:
    # Show current sex selection summary
    st.metric("Sex", "All" if set(sex_filter) == set(sexes_all) else ", ".join(sex_filter))
with k4:
    st.metric("ZIP", "All" if (zip_select == "ALL ZIPs") else zip_select)

st.markdown("---")

# -----------------------------
# Viz 1 — Yearly fatalities (Total + Male + Female) with selector
# -----------------------------
st.header("1) Fatal Overdoses Over Time")

# Build series: total, male, female (only for those present in masked data)
series_frames = []

# Total
if not dff.empty:
    total_df = dff.groupby("year").size().reset_index(name="count")
    total_df["series"] = "Total"
    series_frames.append(total_df)

# Male, Female (only if present in filtered data)
for sx in ["Male", "Female"]:
    if sx in dff["sex"].unique():
        sdf = dff[dff["sex"] == sx].groupby("year").size().reset_index(name="count")
        sdf["series"] = sx
        series_frames.append(sdf)

if series_frames:
    lines_df = pd.concat(series_frames, ignore_index=True)

    # Determine which series exist and set default selection to all available
    available_series = lines_df["series"].unique().tolist()
    # Limit options to those present in the **masked** dataframe
    selected_series = st.multiselect(
        "Show series",
        options=available_series,
        default=available_series,
        help="Toggle lines to display; options are limited to series present in the filtered data."
    )

    if selected_series:
        plot_df = lines_df[lines_df["series"].isin(selected_series)].copy()
        # Color mapping
        color_map = {"Male": "#1f77b4", "Female": "#e63946", "Total": "#555555"}
        fig1 = px.line(
            plot_df,
            x="year", y="count", color="series",
            color_discrete_map={k: v for k, v in color_map.items() if k in available_series},
            labels={"year": "Year", "count": "Fatal overdoses", "series": "Series"},
            title="Yearly Trend of Fatal Overdoses in Allegheny County (Total & By Sex)",
            markers=True,
        )
        fig1.update_layout(hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown(
            """
**Narrative:** The time series shows sustained elevation in recent years. Comparing **Total**, **Male** (blue), and **Female** (red) helps assess differential burden and whether trends move in parallel or diverge across groups.
            """
        )
    else:
        st.info("Select at least one series to display.")
else:
    st.info("No data available for the selected filters.")

st.markdown("---")

# -----------------------------
# Viz 2 & 4 — Substances (Stacked Area) + Drug-Combination Treemap
# -----------------------------
st.header("2 & 4) Substance Dynamics — Composition & Co-occurrence")
left, right = st.columns([3, 2])

with left:
    st.subheader("Substances Involved Over Time (Stacked Area)")
    if not meltedf.empty:
        subs_year = meltedf.groupby(["year", "substance"]).size().reset_index(name="mentions")
        fig2 = px.area(
            subs_year, x="year", y="mentions", color="substance",
            labels={"year": "Year", "mentions": "Mentions across cases", "substance": "Substance"},
            title="Fentanyl Supplants Heroin as the Dominant Driver",
        )
        fig2.update_layout(hovermode="x unified", legend_title_text="Substance")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Substance fields are unavailable in the filtered data.")

with right:
    st.subheader("Drug Combinations (Treemap)")
    od_cols = [c for c in dff.columns if c.lower().startswith("combined_od")]

    def clean_substance(s):
        if not isinstance(s, str):
            return None
        s = s.strip().upper()
        if "FENTANYL" in s:
            return "Fentanyl"
        elif "HEROIN" in s:
            return "Heroin"
        elif "COCAINE" in s:
            return "Cocaine"
        elif "ALCOHOL" in s:
            return "Alcohol"
        elif any(op in s for op in ["MORPHINE", "OXYCODONE", "HYDROCODONE", "OPIOID", "OPIATE"]):
            return "Other Opioids"
        else:
            return s.title()

    combo_counts = Counter()
    if od_cols:
        for _, row in dff[od_cols].iterrows():
            subs = sorted(set(filter(None, (clean_substance(row[c]) for c in od_cols))))
            if subs:
                combo = " + ".join(subs)
                combo_counts[combo] += 1

    if combo_counts:
        combo_df = pd.DataFrame(combo_counts.items(), columns=["Combination", "Count"]).sort_values("Count", ascending=False)
        fig4 = px.treemap(
            combo_df,
            path=["Combination"],
            values="Count",
            color="Count",
            color_continuous_scale="Reds",
            title="Most Common Drug Combinations in Fatal Overdoses"
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No drug-combination data available after filtering.")

st.markdown(
    """
**Narrative (Substances):** The stacked area shows **composition over time** (fentanyl’s rise). The treemap complements it by surfacing **co-occurrence** patterns (e.g., *Fentanyl + Cocaine*), clarifying that many fatal cases involve multiple drugs.
    """
)

st.markdown("---")

# -----------------------------
# Viz 3 — Geography: Mapbox Choropleth (standalone) — zoomed to Allegheny County
# -----------------------------
st.header("3) Geography — ZIP-Code Choropleth")
st.subheader("Fatal Accidental Overdoses by ZIP Code")
if meta["has_zip"]:
    try:
        geojson = load_geojson(PA_ZIP_GEOJSON)
        valid_zips = {str(f["properties"].get("ZCTA5CE10")).zfill(5) for f in geojson.get("features", [])}
        zip_counts = (
            dff.dropna(subset=["zip_norm"])
               .assign(zip_norm=lambda x: x["zip_norm"].astype(str).str.zfill(5))
               .groupby("zip_norm").size().reset_index(name="count")
               .sort_values("count", ascending=False)
        )
        # Restrict to ZIPs that exist in PA ZCTA file
        zip_counts = zip_counts[zip_counts["zip_norm"].isin(valid_zips)]
        if zip_counts.empty:
            st.info("No ZIPs in the filtered data match the PA ZIP boundary file. Try widening filters.")
        else:
            fig3 = px.choropleth_mapbox(
                zip_counts,
                geojson=geojson,
                locations="zip_norm",
                featureidkey="properties.ZCTA5CE10",
                color="count",
                color_continuous_scale="Blues",
                labels={"count": "Fatal overdoses (count)", "zip_norm": "ZIP"},
                mapbox_style=MAPBOX_STYLE,
                zoom=ALLEGHENY_ZOOM,                  # zoom into Allegheny County
                center=ALLEGHENY_CENTER,              # center on Allegheny County
                opacity=0.6,
            )
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown(
                """
**Narrative (Geography):** The choropleth highlights **ZIP-level clustering** of cases, useful for targeting naloxone distribution, outreach, and clinic placement. Interpret descriptively: counts reflect population and recording practices.
                """
            )
    except Exception as e:
        st.warning(f"Choropleth could not be rendered: {e}")
else:
    st.info("ZIP information not available in this dataset.")

st.markdown("---")

# -----------------------------
# Main Takeaway (red background)
# -----------------------------
st.header("Main Takeaway")
st.error(
    """
**Fentanyl-era risk remains high and geographically uneven.** Prioritize sustained treatment access (MOUD), naloxone saturation, drug-checking, and post-overdose outreach, proportionate to local need.
    """
)

# -----------------------------
# References (APA)
# -----------------------------
with st.expander("References (APA)", expanded=False):
    st.markdown(
        """
Western Pennsylvania Regional Data Center. (n.d.). *Allegheny County fatal accidental overdoses* [Data set]. https://data.wprdc.org/

Centers for Disease Control and Prevention. (2024). *Provisional drug overdose death counts*. https://www.cdc.gov/nchs/nvss/vsrr/drug-overdose-data.htm

Hedegaard, H., Miniño, A. M., & Warner, M. (2023). *Drug overdose deaths in the United States, 2002–2022* (NCHS Data Brief No. 457). National Center for Health Statistics. https://www.cdc.gov/nchs/products/databriefs/db457.htm
        """
    )

# -----------------------------
# About & Reproducibility
# -----------------------------
with st.expander("About this App & How to Reproduce"):
    st.markdown(
        f"""
- **Data source:** {meta['source']}  
  Live API endpoint: `{meta['api_url']}`
- **Tools:** Streamlit (UI), Plotly Express (charts), Pandas (wrangling).
- **Construction notes:** Years normalized; sex standardized; substances long-formed from `combined_od1..10`; ZIPs extracted as five-digit strings and validated against PA ZCTA GeoJSON.
- **Map tiles:** Using `choropleth_mapbox` with `"{MAPBOX_STYLE}"` style. Set a Mapbox token via `st.secrets["MAPBOX_TOKEN"]` or env var `MAPBOX_TOKEN` to enable Mapbox-powered styles.
- **Ethical note:** Visuals emphasize clarity and non-stigmatizing interpretation; maps and treemap are intended to guide proportionate resource allocation.
        """
    )

st.caption("© Vasanth Madhavan Srinivasa Raghavan — Graduate Coursework - The Art of Data Visualization - Data Story. Educational use only; not a substitute for official public health reporting.")
