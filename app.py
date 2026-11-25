"""DealPilot tender finder: a small Streamlit proof of concept.

Run with:  streamlit run app.py
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st

from config import PRODUCTS
from matching import match
from sources import SOURCES
from sources.common import SourceError

st.set_page_config(page_title="DealPilot tender finder", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_source(source_name: str, date_from: datetime, date_to: datetime,
                 stages: tuple[str, ...], max_pages: int) -> list[dict]:
    """Download notices from one source. Results are kept for an hour so
    pressing Fetch again with the same settings is instant."""
    progress = st.empty()

    def show(message: str) -> None:
        progress.caption(f"{source_name}: {message}")

    rows = SOURCES[source_name].fetch(date_from, date_to, list(stages), max_pages, show)
    progress.empty()
    return rows


# ---------------------------------------------------------------- sidebar
st.sidebar.title("DealPilot")

today = date.today()
date_range = st.sidebar.date_input(
    "Notices published or updated between",
    value=(today - timedelta(days=7), today),
    max_value=today,
)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    d_from, d_to = date_range
else:
    d_from = d_to = date_range[0] if isinstance(date_range, (list, tuple)) else date_range

source_names = st.sidebar.multiselect("Sources", list(SOURCES), default=list(SOURCES))

stage_choice = st.sidebar.multiselect(
    "Notice stage",
    ["tender", "planning", "award"],
    default=["tender", "planning"],
    help="'tender' = open invitations to bid. 'planning' = early notices "
    "of upcoming buys. 'award' = contract already given (useful for "
    "learning who buys what, not for bidding).",
)
open_only = st.sidebar.checkbox("Only show notices still open for bids", value=False)
max_pages = st.sidebar.slider(
    "Max pages per source (100 notices each)", 1, 100, 60,
    help="Caps download time. Find a Tender has about 500 notices a day "
    "(5 pages); each page takes 1 to 5 seconds.",
)

st.sidebar.subheader("Products and keywords")
st.sidebar.caption("One keyword or phrase per line. Changes apply on the next Fetch.")
products: dict[str, list[str]] = {}
for name, info in PRODUCTS.items():
    with st.sidebar.expander(name, expanded=False):
        st.caption(info["description"])
        enabled = st.checkbox("Include", value=True, key=f"on_{name}")
        text = st.text_area("Keywords", "\n".join(info["keywords"]), key=f"kw_{name}", height=160)
        if enabled:
            products[name] = [k.strip() for k in text.splitlines() if k.strip()]

fetch_clicked = st.sidebar.button("Fetch", type="primary", width="stretch")
if st.sidebar.button("Clear cached downloads", width="stretch"):
    fetch_source.clear()
    st.session_state.pop("rows", None)

# ---------------------------------------------------------------- main
st.title("Tender finder")
st.caption(
    "Searches UK public tenders (Find a Tender and Contracts Finder) and "
    "flags notices that mention your product keywords."
)

if fetch_clicked:
    if not source_names:
        st.warning("Pick at least one source.")
    else:
        date_from = datetime.combine(d_from, time.min)
        date_to = min(datetime.combine(d_to, time.max).replace(microsecond=0), datetime.now())
        all_rows, problems = [], []
        with st.spinner("Downloading notices..."):
            for name in source_names:
                try:
                    all_rows += fetch_source(name, date_from, date_to,
                                             tuple(stage_choice), max_pages)
                except SourceError as exc:
                    problems.append(f"{name}: {exc}")
        st.session_state["rows"] = all_rows
        st.session_state["problems"] = problems

rows = st.session_state.get("rows")
for p in st.session_state.get("problems", []):
    st.error(f"Could not read {p}")

if rows is None:
    st.info("Choose your settings on the left and press **Fetch**.")
    st.stop()

df = match(rows, products, open_only=open_only)

c1, c2, c3 = st.columns(3)
c1.metric("Notices downloaded", len(rows))
c2.metric("Matching notices", len(df))
c3.metric("Still open", int(df["open"].sum()) if not df.empty else 0)

if df.empty:
    st.warning("No notices matched your keywords. Try a wider date range or more keywords.")
    st.stop()

product_filter = st.multiselect("Show products", sorted(df["matched_product"].unique()),
                                default=sorted(df["matched_product"].unique()))
view = df[df["matched_product"].isin(product_filter)]

st.dataframe(
    view,
    width="stretch",
    hide_index=True,
    column_order=["score", "title", "buyer", "value", "closing_date", "open",
                  "matched_product", "matched_keywords", "other_products",
                  "source", "stage", "link"],
    column_config={
        "score": st.column_config.NumberColumn("Score", help="3 points per keyword in the title, 1 per keyword only in the description, plus 2 if still open"),
        "title": st.column_config.TextColumn("Title", width="large"),
        "buyer": "Buyer",
        "value": st.column_config.NumberColumn("Value (£)", format="%,.0f"),
        "closing_date": st.column_config.DatetimeColumn("Closing date", format="YYYY-MM-DD"),
        "open": st.column_config.CheckboxColumn("Open"),
        "matched_product": "Product",
        "matched_keywords": st.column_config.TextColumn("Matched keywords", width="medium"),
        "other_products": "Also matches",
        "source": "Source",
        "stage": "Stage",
        "link": st.column_config.LinkColumn("Link", display_text="Open notice"),
    },
)

csv = view.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, file_name=f"dealpilot_matches_{today}.csv",
                   mime="text/csv")
