import streamlit as st
import csv
from core import *

LEGACY_CACHE = "legacy_cdf_cache.json"
NEW_CACHE = "new_percentile_cache.json"
WA_CSV_PATH = "world_athletics_scoring_table.csv"


# -----------------------------
# LOAD DATA
# -----------------------------

@st.cache_data
def load_cache_file(path):
    import json, os

    if not os.path.exists(path):
        return None

    with open(path) as f:
        raw = json.load(f)

    return {
        k: [(float(t), float(p)) for t, p in v]
        for k, v in raw.items()
    }


@st.cache_data
def load_points_table(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    headers = [h.strip() for h in rows[0]]
    table = {h: {} for h in headers[1:]}

    for row in rows[1:]:
        try:
            pts = int(row[0])
        except:
            continue

        for i in range(1, len(headers)):
            if i < len(row) and row[i].strip():
                table[headers[i]][pts] = row[i].strip()

    return table


legacy_cdf = load_cache_file(LEGACY_CACHE)
new_cdf = load_cache_file(NEW_CACHE)
wa_table = load_points_table(WA_CSV_PATH)


# -----------------------------
# UI
# -----------------------------

st.title("🏃 Athletics Performance Tool")

event_key = st.selectbox("Event", list(EVENT_MAP.keys()))
time_input = st.text_input("Time (e.g. 4:07.22)")

if st.button("Run"):

    t_sec = parse_time(time_input)

    if t_sec is None:
        st.error("Invalid time")
        st.stop()

    # ---------------- WA ----------------
    st.subheader("World Athletics Score")
    wa = get_score(event_key, t_sec, wa_table)

    if wa:
        st.metric("Points", wa)

    # ---------------- NEW ----------------
    st.subheader("Recent Percentile")

    p, results = run_new_percentile(new_cdf, event_key, t_sec)

    if p is not None:
        st.metric("Percentile", f"{100 - p:.2f}")

        for k, v in results:
            st.write(k, fmt_time(v))

    # ---------------- LEGACY ----------------
    st.subheader("Historical Percentile")

    p2, results2 = run_legacy_percentile(legacy_cdf, event_key, t_sec)

    if p2 is not None:
        st.metric("Percentile", f"{100 - p2:.2f}")

        for k, v in results2:
            st.write(k, fmt_time(v))