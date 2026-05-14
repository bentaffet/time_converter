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

st.title("Division III Time Conversion Tool")

event_key = st.selectbox("Event", list(EVENT_MAP.keys()))
time_input = st.text_input("Time (e.g. 4:07.22)")

if st.button("Run"):

    t_sec = parse_time(time_input)

    if t_sec is None:
        st.error("Invalid time")
        st.stop()

    # ---------------- WA ----------------
    st.subheader("World Athletics Score")

    wa_points, wa_equiv = get_score(event_key, t_sec, wa_table)

    st.subheader("Performance Summary Table")

    rows = []

    # ---------------- WA ----------------
    if wa_points is not None:
        wa_pct = None  # WA isn't percentile-based

        rows.append({
            "System": "World Athletics",
            "Percentile": "N/A",
            "Main Output": f"{int(wa_points)} pts",
            "Key Equivalents": ", ".join(
                f"{e}: {fmt_time(t)}"
                for e, t in wa_equiv
                if e in ["3000m", "5000m", "10000m", "800m", "1500m"]
            )
        })

    # ---------------- NEW ----------------
    if p is not None:
        rows.append({
            "System": "2023–2026 PR",
            "Percentile": f"{100 - p:.2f}",
            "Main Output": "DIII recent pool",
            "Key Equivalents": ", ".join(
                f"{k}: {fmt_time(v)}"
                for k, v in results[:3]
            )
        })

    # ---------------- LEGACY ----------------
    if p2 is not None:
        rows.append({
            "System": "2015–2025 All",
            "Percentile": f"{100 - p2:.2f}",
            "Main Output": "DIII full history",
            "Key Equivalents": ", ".join(
                f"{k}: {fmt_time(v)}"
                for k, v in results2[:3]
            )
        })

    st.dataframe(rows, use_container_width=True)
        

st.subheader("Notes")

st.write(
    "World Athletics Score is calculated based on the world athletics chart linked here: "
    "https://worldathletics.org/about-iaaf/documents/technical-information\n"
)

st.write(
    "2015-2025 All Performances Percentile is calculated based on over 130,000 DIII track performances and over 150,000 XC performances."
    "This data was scraped from Athletic.net."
)

st.write(
    "All Percentile data removes 0.5 percent of slow data. This means that the percentiles of times the bottom 50 percent may be higher on this website."
    "For example, if a time is 30th percentile, its true percentile may be 26th to 29th percentile, depending on the specific data."
    "The reason for this is so this website works as a better conversion calculater than a percentile finder."
)

st.write(
    "Conversion limitations: There are certain limitations on conversions, such as not being able to convert an indoor event to a World Athletics time."
)