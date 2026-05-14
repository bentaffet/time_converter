import json
import re
import os
import csv
from bisect import bisect_left

# -----------------------------
# CONFIG
# -----------------------------

EVENT_MAP = { ... }  # KEEP YOUR EXACT DICT

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

    if not cfg.get("wa"):
        return None

    race_key = cfg["wa_key"]
    parsed = []

    for pts, t_str in table[race_key].items():
        t_sec = parse_time(t_str)
        if t_sec is not None:
            parsed.append((pts, t_sec))

    parsed.sort(key=lambda x: x[1])

    best_pts = min(parsed, key=lambda x: abs(x[1] - time_sec))[0]

    return best_pts


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
        if c.get("season") != cfg.get("season"):
            continue
        if c.get("new_key") not in cdf:
            continue

        eq = inverse_lookup(cdf[c["new_key"]], p)
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