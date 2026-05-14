import json
import re
import os
import csv
from bisect import bisect_left

# -----------------------------
# CONFIG
# -----------------------------

EVENT_MAP = {

    # =====================================================
    # OUTDOOR TRACK
    # =====================================================

    "800_outdoor": {
        "display": "800 Meters Outdoor",
        "wa": True,
        "wa_key": "800m",
        "season": "outdoor",
        "legacy_event": "800 Meters",
        "new_key": "800m_outdoor"
    },

    "1500_outdoor": {
        "display": "1500 Meters Outdoor",
        "wa": True,
        "wa_key": "1500m",
        "season": "outdoor",
        "legacy_event": "1500 Meters",
        "new_key": "1500m_outdoor"
    },

    "3000_outdoor": {
        "display": "3000 Meters Outdoor",
        "wa": False,
        "season": "outdoor",
        "new_key": "3000m_outdoor"
    },

    "5000_outdoor": {
        "display": "5000 Meters Outdoor",
        "wa": True,
        "wa_key": "5000m",
        "season": "outdoor",
        "legacy_event": "5000 Meters",
        "new_key": "5000m_outdoor"
    },

    "10000_outdoor": {
        "display": "10000 Meters Outdoor",
        "wa": True,
        "wa_key": "10000m",
        "season": "outdoor",
        "legacy_event": "10000 Meters",
        "new_key": "10000m_outdoor"
    },

    "3000S_outdoor": {
        "display": "3000m Steeplechase Outdoor",
        "wa": False,
        "season": "outdoor",
        "new_key": "3000S_outdoor"
    },

    "1Mile_outdoor": {
        "display": "1 Mile Outdoor",
        "wa": False,
        "season": "outdoor",
        "new_key": "1Mile_outdoor"
    },

    # =====================================================
    # INDOOR TRACK
    # =====================================================

    "800_indoor": {
        "display": "800 Meters Indoor",
        "wa": False,
        "season": "indoor",
        "new_key": "800m_indoor"
    },

    "1500_indoor": {
        "display": "1500 Meters Indoor",
        "wa": False,
        "season": "indoor",
        "new_key": "1500m_indoor"
    },

    "3000_indoor": {
        "display": "3000 Meters Indoor",
        "wa": False,
        "season": "indoor",
        "new_key": "3000m_indoor"
    },

    "5000_indoor": {
        "display": "5000 Meters Indoor",
        "wa": False,
        "season": "indoor",
        "new_key": "5000m_indoor"
    },

    "3000S_indoor": {
        "display": "3000m Steeplechase Indoor",
        "wa": False,
        "season": "indoor",
        "new_key": "3000S_indoor"
    },

    "1Mile_indoor": {
        "display": "1 Mile Indoor",
        "wa": False,
        "season": "indoor",
        "new_key": "1Mile_indoor"
    },

    # =====================================================
    # XC
    # =====================================================

    "8000_xc": {
        "display": "8000 Meters XC",
        "wa": False,
        "season": "xc",
        "legacy_event": "8000 Meters"
    }
}


LEGACY_CACHE = "legacy_cdf_cache.json"
NEW_CACHE = "new_percentile_cache.json"


# -----------------------------
# TIME PARSER
# -----------------------------

def parse_time(t):
    if t is None:
        return None

    t = str(t).strip().lower()

    if t in {"", "dnf", "dq", "dns", "-"}:
        return None

    t = re.sub(r"[^0-9:\.]", "", t)

    if not t:
        return None

    parts = t.split(":")

    try:
        if len(parts) == 3:
            h, m, s = parts
            return int(h)*3600 + int(m)*60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m)*60 + float(s)
        else:
            return float(parts[0])
    except:
        return None


def fmt_time(seconds):
    m = int(seconds // 60)
    s = seconds - 60*m
    return f"{m}:{s:05.2f}"


# -----------------------------
# LOOKUP
# -----------------------------

def lookup_percentile(table, value):
    times = [t for t, _ in table]
    i = bisect_left(times, value)

    if i <= 0:
        return table[0][1]
    if i >= len(table):
        return table[-1][1]

    t0, p0 = table[i-1]
    t1, p1 = table[i]

    frac = (value - t0) / (t1 - t0 + 1e-9)
    return p0 + frac*(p1 - p0)


def inverse_lookup(table, p):
    for i in range(len(table)-1):
        t0, p0 = table[i]
        t1, p1 = table[i+1]

        if p0 <= p <= p1:
            frac = (p - p0) / (p1 - p0 + 1e-9)
            return t0 + frac*(t1 - t0)

    return table[-1][0]


# -----------------------------
# WA SCORE (RETURN NOT PRINT)
# -----------------------------

def get_score(event_key, time_sec, table):
    cfg = EVENT_MAP[event_key]

    if not cfg["wa"]:
        return None, []

    race_key = cfg["wa_key"]

    if race_key not in table:
        return None, []

    points_times = [
        (pts, parse_time(t))
        for pts, t in table[race_key].items()
        if parse_time(t) is not None
    ]

    points_times.sort(key=lambda x: x[1])

    best_pts, _ = min(
        points_times,
        key=lambda x: abs(x[1] - time_sec)
    )

    # -----------------------------
    # build equivalent performances
    # -----------------------------
    equivalents = []

    for event_name, col in table.items():
        if best_pts in col:
            t = parse_time(col[best_pts])
            if t is not None:
                equivalents.append((event_name, t))

    return best_pts, equivalents


# -----------------------------
# PERCENTILE FUNCTIONS
# -----------------------------

def run_new_percentile(cdf, event_key, time_sec):
    cfg = EVENT_MAP[event_key]
    dataset = cfg.get("new_key")

    if dataset not in cdf:
        return None, []

    p = lookup_percentile(cdf[dataset], time_sec)

    results = []

    for k, c in EVENT_MAP.items():
        if k == event_key:
            continue

        # must have data
        other_dataset = c.get("new_key")
        if other_dataset not in cdf:
            continue

        # ❌ only exclude XC
        if c.get("season") == "xc" or cfg.get("season") == "xc":
            continue

        # ✅ REMOVE SAME-SEASON FILTER (this was the bug)
        # if c.get("season") != cfg.get("season"):
        #     continue

        eq = inverse_lookup(cdf[other_dataset], p)
        results.append((k, eq))

    return p, results


def run_legacy_percentile(cdf, event_key, time_sec):
    cfg = EVENT_MAP[event_key]
    event = cfg.get("legacy_event")

    if event not in cdf:
        return None, []

    p = lookup_percentile(cdf[event], time_sec)

    results = []

    for k, c in EVENT_MAP.items():
        if k == event_key:
            continue
        if c.get("legacy_event") not in cdf:
            continue

        eq = inverse_lookup(cdf[c["legacy_event"]], p)
        results.append((k, eq))

    return p, results