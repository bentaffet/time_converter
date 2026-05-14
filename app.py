import streamlit as st
import json
import os
import csv

LEGACY_CACHE = "legacy_cdf_cache.json"
NEW_CACHE = "new_percentile_cache.json"
WA_CSV_PATH = "world_athletics_scoring_table.csv"

# -----------------------------
# CACHE FILE LOADER
# -----------------------------

@st.cache_data
def load_cache_file(path):
    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        raw = json.load(f)

    return {
        k: [(float(t), float(p)) for t, p in v]
        for k, v in raw.items()
    }


# -----------------------------
# LOAD CDFS
# -----------------------------

@st.cache_data
def load_cdfs():
    legacy = load_cache_file(LEGACY_CACHE)
    new = load_cache_file(NEW_CACHE)

    if legacy is None or new is None:
        st.error("Missing cache files. Run build_caches.py first.")
        st.stop()

    return legacy, new


legacy_cdf, new_cdf = load_cdfs()


# -----------------------------
# WA TABLE
# -----------------------------

@st.cache_data
def load_points_table(csv_path):

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    headers = [h.strip() for h in rows[0]]

    table = {h: {} for h in headers[1:]}

    for row in rows[1:]:
        if not row:
            continue

        try:
            pts = int(row[0])
        except:
            continue

        for i in range(1, len(headers)):
            if i >= len(row):
                continue

            val = row[i].strip()

            if val:
                table[headers[i]][pts] = val

    return table