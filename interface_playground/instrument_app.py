from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

OUTDIR = Path("../measurement_locked/runs/outputs")

def list_dated_outputs():
    return sorted(OUTDIR.glob("*_edacec_output.jsonl"))

def load_jsonl(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows

def rows_to_df(rows):
    flat = []
    for r in rows:
        meta = r.get("meta", {})
        scores = r["hesm"]["scores"]
        flat.append({
            "source": meta.get("source", ""),
            "timestamp": meta.get("timestamp", ""),
            "headline": r["headline"],
            "vi": r["vi"],
            "k": r["hesm"]["k_total"],
            "S": scores["structural"],
            "E": scores["emotional"],
            "I": scores["irreversibility"],
            "A": scores["agenda"],
            "S_matches": ", ".join(r["hesm"]["matches"]["structural"]),
            "E_matches": ", ".join(r["hesm"]["matches"]["emotional"]),
            "I_matches": ", ".join(r["hesm"]["matches"]["irreversibility"]),
            "A_matches": ", ".join(r["hesm"]["matches"]["agenda"]),
        })
    df = pd.DataFrame(flat)
    if not df.empty:
        df = df.sort_values(["k", "vi"], ascending=[False, False])
    return df

def parse_date_from_filename(path: Path) -> str:
    return path.name.split("_")[0]

def build_trend_df(files):
    rows = []
    for f in files:
        date = parse_date_from_filename(f)
        data = load_jsonl(f)
        df = rows_to_df(data)
        if df.empty:
            continue
        rows.append({
            "date": date,
            "n": len(df),
            "avg_vi": float(df["vi"].mean()),
            "avg_k": float(df["k"].mean()),
            "avg_S": float(df["S"].mean()),
            "avg_E": float(df["E"].mean()),
            "avg_I": float(df["I"].mean()),
            "avg_A": float(df["A"].mean()),
            "max_vi": float(df["vi"].max()),
        })
    tdf = pd.DataFrame(rows)
    if not tdf.empty:
        tdf = tdf.sort_values("date")
    return tdf

st.set_page_config(page_title="EDACEC Instrument", layout="wide")
st.title("EDACEC Instrument (Interface-Only)")
st.caption("Reads locked EDACEC measurement outputs. Does not modify measurement.")

files = list_dated_outputs()
if not files:
    st.error("No dated outputs found in measurement_locked/runs/outputs/")
    st.write("Run measurement with a dated output filename.")
    st.stop()

choice = st.selectbox(
    "Select a dated run",
    options=list(range(len(files))),
    index=len(files) - 1,
    format_func=lambda i: files[i].name,
)
selected = files[choice]

rows = load_jsonl(selected)
df = rows_to_df(rows)

st.subheader(f"Run: {selected.name}")
c1, c2, c3 = st.columns(3)
c1.metric("Avg VI", f"{df['vi'].mean():.3f}")
c2.metric("Max VI", f"{df['vi'].max():.3f}")
c3.metric("Avg k", f"{df['k'].mean():.2f}")

st.dataframe(
    df[["source", "timestamp", "headline", "vi", "k", "S", "E", "I", "A", "S_matches", "E_matches", "I_matches", "A_matches"]],
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download CSV for this run",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"{parse_date_from_filename(selected)}_edacec.csv",
    mime="text/csv",
)

st.subheader("Run charts")

left, right = st.columns(2)
with left:
    fig = plt.figure()
    plt.hist(df["vi"])
    st.pyplot(fig)

with right:
    fig = plt.figure()
    plt.bar(["S", "E", "I", "A"], [df["S"].mean(), df["E"].mean(), df["I"].mean(), df["A"].mean()])
    st.pyplot(fig)

st.subheader("Trend over time")
tdf = build_trend_df(files)

if len(tdf) < 2:
    st.info("Trend requires 2+ dated outputs.")
else:
    st.dataframe(tdf, use_container_width=True, hide_index=True)
    fig = plt.figure()
    plt.plot(tdf["date"], tdf["avg_vi"])
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)
