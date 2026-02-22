from pathlib import Path
import json
import sys
import feedparser
from dateutil import parser as dtparser
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import os, certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

# Resolve paths relative to this file (works no matter where you run from)
BASE_DIR = Path(__file__).resolve().parents[1]
OUTDIR = BASE_DIR / "measurement_locked" / "runs" / "outputs"

# Ensure repo root is importable (so measurement_locked.* imports work)
sys.path.insert(0, str(BASE_DIR))


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
        matches = r["hesm"]["matches"]

        flat.append(
            {
                "source": meta.get("source", ""),
                "timestamp": meta.get("timestamp", ""),
                "headline": r.get("headline", ""),
                "vi": r.get("vi", None),
                "k": r["hesm"].get("k_total", None),
                "S": scores.get("structural", None),
                "E": scores.get("emotional", None),
                "I": scores.get("irreversibility", None),
                "A": scores.get("agenda", None),
                "S_matches": ", ".join(matches.get("structural", [])),
                "E_matches": ", ".join(matches.get("emotional", [])),
                "I_matches": ", ".join(matches.get("irreversibility", [])),
                "A_matches": ", ".join(matches.get("agenda", [])),
            }
        )

    df = pd.DataFrame(flat)
    if not df.empty:
        # Sort most volatile-ish at top (k then vi)
        if "k" in df.columns and "vi" in df.columns:
            df = df.sort_values(["k", "vi"], ascending=[False, False])
    return df


def parse_date_from_filename(path: Path) -> str:
    return path.name.split("_")[0]


def _utc_iso(dt):
    # deterministic ISO timestamp for snapshots
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def build_trend_df(files):
    rows = []
    for f in files:
        date = parse_date_from_filename(f)
        data = load_jsonl(f)
        df = rows_to_df(data)
        if df.empty:
            continue
        rows.append(
            {
                "date": date,
                "n": int(len(df)),
                "avg_vi": float(df["vi"].mean()),
                "avg_k": float(df["k"].mean()),
                "avg_S": float(df["S"].mean()),
                "avg_E": float(df["E"].mean()),
                "avg_I": float(df["I"].mean()),
                "avg_A": float(df["A"].mean()),
                "max_vi": float(df["vi"].max()),
            }
        )
    tdf = pd.DataFrame(rows)
    if not tdf.empty:
        tdf = tdf.sort_values("date")
    return tdf

# --- Deterministic RSS Headline Fetcher ---

FEEDS = [
    ("Reuters", "https://feeds.reuters.com/reuters/topNews"),
    ("AP", "https://feeds.apnews.com/rss/apf-topnews"),
    ("NYT", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
    ("BBC", "http://feeds.bbci.co.uk/news/rss.xml"),
]
def _parse_dt(entry):
    for key in ("published", "updated", "created"):
        if key in entry and entry[key]:
            try:
                dt = dtparser.parse(entry[key])
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)

@st.cache_data(ttl=300)
def fetch_top_headlines(limit=5):
    items = []
    debug = []

    for source, url in FEEDS:
        feed = feedparser.parse(url)

        status = getattr(feed, "status", None)
        bozo = int(getattr(feed, "bozo", 0) or 0)
        bozo_exc = str(getattr(feed, "bozo_exception", "")) if bozo else ""
        n_entries = len(getattr(feed, "entries", []) or [])

        debug.append(
            {
                "source": source,
                "url": url,
                "status": status,
                "bozo": bozo,
                "bozo_exception": bozo_exc,
                "entries": n_entries,
            }
        )

        for e in getattr(feed, "entries", []) or []:
            title = (getattr(e, "title", "") or "").strip()
            link = (getattr(e, "link", "") or "").strip()
            if not title or not link:
                continue
            pub = _parse_dt(e)
            items.append(
                {
                    "source": source,
                    "title": title,
                    "url": link,
                    "published_utc": pub,
                }
            )

    items.sort(key=lambda x: (-x["published_utc"].timestamp(), x["source"], x["title"]))

    seen = set()
    unique = []
    for item in items:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        unique.append(item)
        if len(unique) >= limit:
            break

    return unique, debug


# --- Optional: score a selected headline using locked EDACEC (no core changes) ---
EDACEC_SCORER_AVAILABLE = False
EDACEC_SCORER_ERROR = ""
EDACEC_SPEC = None
score_headline = None

try:
    import measurement_locked.edacec_v1_08 as _ed
    score_headline = _ed.score_headline

    _logic_path = BASE_DIR / "hesm_logic.json"
    _logic = json.loads(_logic_path.read_text(encoding="utf-8"))

    # If the module supports from_dict, prefer it
    if hasattr(_ed.EDACECSpec, "from_dict"):
        EDACEC_SPEC = _ed.EDACECSpec.from_dict(_logic)
    else:
        # Build spec like the verified working terminal test
        d = _logic.get("dictionary") or _logic.get("components") or {}
        comps = {}
        CS = getattr(_ed, "ComponentSpec", None)
        if CS is None:
            raise RuntimeError("ComponentSpec not found in edacec_v1_08")

        for key, obj in d.items():
            if not isinstance(obj, dict):
                continue
            max_score = int(obj.get("max_score", 0))
            keywords = tuple(str(k).lower() for k in obj.get("keywords", []))
            comps[key] = CS(name=key, max_score=max_score, keywords=keywords)

        EDACEC_SPEC = _ed.EDACECSpec(version=str(_logic.get("version", "1.08")), components=comps)

    EDACEC_SCORER_AVAILABLE = True

except Exception as _e:
    EDACEC_SCORER_ERROR = repr(_e)
    EDACEC_SCORER_AVAILABLE = False


st.set_page_config(page_title="EDACEC Interface Sampler v0.1", layout="wide")
st.title("EDACEC Interface Sampler v0.1")
st.caption("Reads locked EDACEC measurement outputs. Does not modify measurement.")
st.caption(f"Outputs dir: {OUTDIR}")
st.divider()
st.divider()
st.subheader("Headlines (Sample)")
st.caption("Fixed-source sample. Headline text shown as published. Not world coverage.")

# Sidebar controls (kept neutral)
with st.sidebar:
    st.markdown("### Headline sampler")
    show_feed_debug = st.checkbox("Show feed diagnostics", value=False)
    st.caption("Deterministic ordering: published desc, source asc, title asc.")

# Fetch headlines (+ diagnostics if your function returns it)
tmp = fetch_top_headlines(limit=5)
if isinstance(tmp, tuple) and len(tmp) == 2:
    headlines, debug = tmp
else:
    headlines, debug = tmp, []

if not headlines:
    st.warning("No headlines returned from feeds.")
    if show_feed_debug and debug:
        with st.expander("Feed diagnostics"):
            st.dataframe(pd.DataFrame(debug), hide_index=True, width="stretch")
else:
    # --- Carousel state ---
    if "headline_idx" not in st.session_state:
        st.session_state.headline_idx = 0

    c_prev, c_mid, c_next = st.columns([1, 6, 1])
    with c_prev:
        if st.button("⬅ Prev", width="stretch"):
            st.session_state.headline_idx = (st.session_state.headline_idx - 1) % len(headlines)
    with c_next:
        if st.button("Next ➡", width="stretch"):
            st.session_state.headline_idx = (st.session_state.headline_idx + 1) % len(headlines)

    h = headlines[int(st.session_state.headline_idx)]
    with c_mid:
        st.markdown(f"**[{st.session_state.headline_idx+1}/{len(headlines)}] {h['source']}** — {h['published_utc'].strftime('%Y-%m-%d %H:%M UTC')}")
        st.link_button(f"Open: {h['title']}", h["url"], width="stretch")

    # Actions row
    a1, a2, a3 = st.columns([2, 2, 3])
    with a1:
        if st.button("Freeze this 5-headline sample", width="stretch"):
            from datetime import datetime, timezone
            snap_dir = BASE_DIR / "interface_playground" / "headline_samples"
            snap_dir.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc)
            payload = {
                "generated_utc": _utc_iso(now),
                "feeds": [{"source": src, "url": url} for (src, url) in FEEDS],
                "headlines": [
                    {
                        "source": x["source"],
                        "published_utc": _utc_iso(x["published_utc"]),
                        "title": x["title"],
                        "url": x["url"],
                    }
                    for x in headlines
                ],
            }
            out = snap_dir / f"headline_sample_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success(f"Snapshot saved: {out.name}")
    with a2:
        score_this = st.button("Score selected headline", width="stretch")
    with a3:
        if show_feed_debug and debug:
            with st.expander("Feed diagnostics"):
                st.dataframe(pd.DataFrame(debug), hide_index=True, width="stretch")

    # Optional scoring panel
    if score_this:
        if not EDACEC_SCORER_AVAILABLE:
            st.info("Scoring import not available in this interface build. Sampler UI is still deterministic.")
            if EDACEC_SCORER_ERROR:
                st.code(EDACEC_SCORER_ERROR)

        else:
            result = score_headline(h["title"], EDACEC_SPEC)
            st.markdown("### EDACEC score (locked rules)")
            st.json(result)

    # Table view (double-clickable links)
    tdf_links = pd.DataFrame(
        [
            {
                "Source": x["source"],
                "Published (UTC)": x["published_utc"].strftime("%Y-%m-%d %H:%M"),
                "Headline (as published)": x["title"],
                "Link": x["url"],
            }
            for x in headlines
        ]
    )
    st.dataframe(
        tdf_links,
        hide_index=True,
        width="stretch",
        column_config={"Link": st.column_config.LinkColumn("Link")},
    )

st.divider()
files = list_dated_outputs()
if not files:
    st.error("No dated outputs found.")
    st.write(f"Expected files like: YYYY-MM-DD_edacec_output.jsonl in: {OUTDIR}")
    st.stop()

choice = st.selectbox(
    "Select a dated run",
    options=list(range(len(files))),
    index=len(files) - 1,
    format_func=lambda i: files[i].name,
)

# Guard against any weird None behavior
if choice is None:
    st.stop()

selected = files[int(choice)]

rows = load_jsonl(selected)
df = rows_to_df(rows)

st.subheader(f"Run: {selected.name}")
c1, c2, c3 = st.columns(3)
c1.metric("Avg VI", f"{df['vi'].mean():.3f}")
c2.metric("Max VI", f"{df['vi'].max():.3f}")
c3.metric("Avg k", f"{df['k'].mean():.2f}")

st.dataframe(
    df[
        [
            "source",
            "timestamp",
            "headline",
            "vi",
            "k",
            "S",
            "E",
            "I",
            "A",
            "S_matches",
            "E_matches",
            "I_matches",
            "A_matches",
        ]
    ],
    width="stretch",
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
    st.dataframe(tdf, width="stretch", hide_index=True)
    fig = plt.figure()
    plt.plot(tdf["date"], tdf["avg_vi"])
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)
