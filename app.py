from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
DATA_DIR = ROOT / "data"


st.set_page_config(
    page_title="Bake-Off | Legal Clause Lab",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = pd.read_csv(RESULTS_DIR / "summary.csv")
    results = pd.read_csv(RESULTS_DIR / "per_item.csv", dtype={"id": str})
    with (DATA_DIR / "items.jsonl").open(encoding="utf-8") as handle:
        items = pd.DataFrame(json.loads(line) for line in handle if line.strip())
    return summary, results.merge(items[["id", "description", "clause"]], on="id", how="left")


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


@st.cache_data
def cached_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_data()


summary, results = cached_data()
model = summary.iloc[0]
errors = results[results["correct"] == False].copy()  # noqa: E712
categories = sorted(results["category"].unique())


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
        :root { --ink: #14231f; --muted: #53645e; --teal: #087f73; --mint: #dff4ed; --cream: #f6f3eb; --panel: #fffdf8; --line: #c9ddd4; --coral: #d96d4f; }
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
        [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] * { color: var(--ink); }
        [data-testid="stAppViewContainer"] { background: var(--cream); }
        [data-testid="stHeader"] { background: var(--cream); }
        [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] label, [data-testid="stCaptionContainer"] {
            color: var(--ink) !important;
        }
        [data-testid="stCaptionContainer"], .section-note { color: var(--muted) !important; }
        [data-testid="stTextInput"] label, [data-testid="stSelectbox"] label,
        [data-testid="stRadio"] label { color: var(--ink) !important; }
        [data-baseweb="select"] > div, [data-baseweb="input"] > div,
        [data-testid="stTextInput"] input, [data-baseweb="popover"] {
            background: var(--panel) !important;
            color: var(--ink) !important;
            border-color: var(--line) !important;
        }
        [data-baseweb="select"] *, [data-baseweb="input"] *,
        [data-testid="stTextInput"] input::placeholder { color: var(--ink) !important; }
        [role="listbox"], [role="option"] { background: var(--panel) !important; color: var(--ink) !important; }
        [role="option"]:hover, [aria-selected="true"] { background: var(--mint) !important; color: var(--ink) !important; }
        [data-testid="stDataFrame"] { color: var(--ink) !important; background: var(--panel); }
        [data-testid="stDataFrame"] [role="columnheader"], [data-testid="stDataFrame"] [role="gridcell"] { color: var(--ink) !important; }
        [data-testid="stMetric"] { color: var(--ink) !important; background: var(--panel); border-color: var(--line); }
        [data-testid="stMetricLabel"] { color: var(--muted) !important; }
        [data-testid="stMetricValue"] { color: var(--teal) !important; }
        h1, h2, h3, h4, h5, h6 { color: var(--ink) !important; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: 0 !important; }
    [data-testid="stSidebar"] { background: #173c35; }
    [data-testid="stSidebar"] * { color: #eef8f3 !important; }
    [data-testid="stMetric"] { border: 1px solid var(--line); padding: 16px 18px; border-radius: 8px; }
    [data-testid="stMetricValue"] { font-family: 'Space Grotesk', sans-serif; }
    .hero { background: #173c35; color: #f7fbf5; padding: 30px 34px 28px; border-radius: 10px; margin-bottom: 22px; }
    .hero-kicker { color: #91d8c4; text-transform: uppercase; font-size: .76rem; font-weight: 700; letter-spacing: .12em; }
    .hero h1 { color: #f7fbf5; margin: 8px 0 6px; font-size: 2.4rem; }
    .hero p { color: #c6dfd5; max-width: 760px; margin: 0; font-size: 1.02rem; }
    .status { display: inline-block; background: #f7d6a0; color: #694211; border-radius: 999px; padding: 5px 10px; font-size: .78rem; font-weight: 700; }
    .section-note { color: var(--muted); margin-top: -10px; }
    .callout { border-left: 4px solid var(--coral); background: #fff8ef; padding: 13px 16px; border-radius: 0 8px 8px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown("## ⚖️ Legal Clause Lab")
    st.caption("Project 0 · Bake-Off")
    st.divider()
    view = st.radio(
        "Explore",
        ["Overview", "Item explorer", "Error analysis", "Method & limits"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Run snapshot**")
    st.caption(f"{model['model']}")
    st.caption(f"{model['run_date_utc'][:10]} · {int(model['items'])} items")
    st.caption("Local Ollama baseline")


st.markdown(
    f"""
    <div class="hero">
      <div class="hero-kicker">Project 0 / evaluation workspace</div>
      <h1>Legal clause bake-off</h1>
    <p>A clear view of the binary classification benchmark: the model decides whether a clause contains a given legal category.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


if view == "Overview":
    st.markdown("## Main signal")
    st.markdown('<p class="section-note">Results recorded in <b>results/summary.csv</b> and <b>results/per_item.csv</b>.</p>', unsafe_allow_html=True)
    metric_cols = st.columns(5)
    metric_cols[0].metric("Accuracy", f"{model['accuracy']:.0%}", f"{int(model['correct'])}/{int(model['items'])}")
    metric_cols[1].metric("P50 latency", f"{model['p50_latency_ms']:,.0f} ms")
    metric_cols[2].metric("P95 latency", f"{model['p95_latency_ms']:,.0f} ms")
    metric_cols[3].metric("Cost / 1k", format_currency(model['self_hosted_cost_per_1000_requests_assumption_usd']))
    metric_cols[4].metric("Output speed", f"{model['output_tokens_per_second']:.2f} tok/s")

    st.markdown("## What was actually tested")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("### One model, one controlled run")
        st.write(
            f"`{model['model']}` ran locally through Ollama on {int(model['items'])} synthetic, balanced clauses. "
            "The same prompt, parser, temperature (0), and sequential order were used for every item."
        )
        st.markdown('<div class="callout"><b>Coverage status</b><br>Only the open-weights baseline is present. The top API and cheap API comparisons still need credentials and real runs.</div>', unsafe_allow_html=True)
    with right:
        st.markdown("### Accuracy by category")
        by_category = results.groupby("category", sort=False)["correct"].mean().sort_values()
        st.bar_chart(by_category, horizontal=True, height=330, color="#087f73")

    st.markdown("## Economics at a glance")
    cost_cols = st.columns(3)
    cost_cols[0].metric("Current run", format_currency(model["self_hosted_cost_at_100x_traffic_usd"] / 100))
    cost_cols[1].metric("100× traffic", format_currency(model["self_hosted_cost_at_100x_traffic_usd"]))
    cost_cols[2].metric("Break-even", "Pending API data")
    st.caption("The self-hosted estimate assumes $0.30/hour and 120 requests/hour. Hardware power and API token prices are not yet measured.")

elif view == "Item explorer":
    st.markdown("## Item explorer")
    st.markdown('<p class="section-note">Inspect the exact clause, expected label, parsed answer, and timing captured by the runner.</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.25, 1, 1])
    with c1:
        selected_category = st.selectbox("Category", ["All categories", *categories])
    with c2:
        outcome = st.selectbox("Outcome", ["All", "Correct", "Wrong"])
    with c3:
        search = st.text_input("Search clause", placeholder="e.g. audit, insurance")

    filtered = results.copy()
    if selected_category != "All categories":
        filtered = filtered[filtered["category"] == selected_category]
    if outcome == "Correct":
        filtered = filtered[filtered["correct"] == True]  # noqa: E712
    elif outcome == "Wrong":
        filtered = filtered[filtered["correct"] == False]  # noqa: E712
    if search:
        filtered = filtered[filtered["clause"].str.contains(search, case=False, na=False)]

    st.caption(f"{len(filtered)} item(s)")
    st.dataframe(
        filtered[["id", "category", "expected", "parsed", "correct", "status", "latency_ms", "clause"]],
        width="stretch",
        hide_index=True,
        column_config={
            "correct": st.column_config.CheckboxColumn("Correct"),
            "latency_ms": st.column_config.NumberColumn("Latency (ms)", format="%.0f"),
            "clause": st.column_config.TextColumn("Contract clause", width="large"),
        },
    )

elif view == "Error analysis":
    st.markdown("## Error analysis")
    st.markdown('<p class="section-note">Every error is an incorrect answer, not only a parsing or availability issue.</p>', unsafe_allow_html=True)
    error_cols = st.columns(3)
    error_cols[0].metric("Total errors", len(errors))
    error_cols[1].metric("False negatives", int(((errors["expected"] == "Yes") & (errors["parsed"] == "No")).sum()))
    error_cols[2].metric("Parse / timeout", f"{int(model['parse_errors'])} / {int(model['timeouts'])}")
    st.markdown("### All wrong answers")
    st.dataframe(
        errors[["id", "category", "expected", "parsed", "output", "clause"]],
        width="stretch",
        hide_index=True,
        column_config={"clause": st.column_config.TextColumn("Clause", width="large")},
    )
    st.info("The eight observed errors are false negatives: the model answers No for clauses expected to be Yes. There were no parse errors or timeouts in this run.")

else:
    st.markdown("## Method & limits")
    st.markdown('<p class="section-note">The dashboard makes the benchmark assumptions visible so the score is not overinterpreted.</p>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown("### Protocole")
        st.markdown("""
        - 50 synthetic clauses, balanced between `Yes` and `No`
        - One sequential request per item
        - Temperature `0`
        - Strict parser: first `Yes` or `No`
        - Latency measured until the complete response
        - Hardware: AMD Ryzen 7 7700, local Ollama
        """)
    with right:
        st.markdown("### Limitations to address")
        st.markdown("""
        - The clauses do not yet come from a real corpus
        - Labels have not yet been checked by two annotators
        - The two API models and their costs are missing
        - Power, RAM/VRAM, and hourly cost are assumptions
        - API/self-hosted break-even is therefore undetermined
        """)
    st.markdown("### Evaluated prompt")
    st.code("""You classify one legal contract clause.\nAnswer whether the clause contains the named category.\nReturn exactly one word: Yes or No.""", language="text")
