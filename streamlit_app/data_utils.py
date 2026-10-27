"""Loading, filtering and summary tables for the dashboard.

The calculations follow analysis_shr.ipynb:
reported-unsolved % = unsolved records in a group / all records in that group.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
DATA_FILE = "clean_data_shr.csv"
CSV_CANDIDATES = [APP_DIR / DATA_FILE, APP_DIR.parent / DATA_FILE]
# Fast copy of the clean data (about 10 MB). It is made automatically from the CSV the first time.
PARQUET_FILE = APP_DIR / "clean_data_shr.parquet"

# Minimum group sizes from the notebook (size rules, not statistical tests)
MIN_N = 1000      # rankings of states, areas, detailed categories and profiles
MIN_CELL = 200    # small category bars and combined cells (heatmaps)

# Orders used in the notebook
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
AGE_ORDER = ["0-12", "13-17", "18-24", "25-34", "35-49", "50-64", "65+", "Unknown"]
OUTCOME_ORDER = ["Solved", "Unsolved"]
SEX_ORDER = ["Male", "Female", "Unknown"]
PERIOD_ORDER = ["1976-79", "1980s", "1990s", "2000s", "2010s", "2020-24"]
CIRCUMSTANCE_ORDER = ["Argument/Brawl", "Robbery", "Gang", "Drugs", "Other felony",
                      "Other", "Suspected felony", "Undetermined"]
SPECIFIC_CIRCUMSTANCES = ["Gang", "Drugs", "Robbery", "Other felony", "Argument/Brawl"]
WEAPON_ORDER = ["Handgun", "Rifle/Shotgun", "Other gun", "Firearm type not stated", "Knife",
                "Blunt object", "Personal weapons", "Other specified weapon",
                "Other/type unknown", "Not reported"]
RELATIONSHIP_ORDER = ["Partner/ex-partner", "Family", "Other known person", "Stranger",
                      "Not determined"]

PROFILE_COLS = ["circumstance_group", "weapon_group", "victim_sex", "age_group"]

USE_COLS = ["incident_id", "agency_code", "agency_name", "agency_type", "source", "state",
            "county", "msa", "year", "month", "period", "victim_age", "victim_age_raw",
            "victim_sex", "victim_race", "age_group", "weapon", "weapon_group",
            "circumstance", "circumstance_group", "relationship", "relationship_group",
            "offender_sex", "outcome", "unsolved", "additional_victims"]
NUMBER_COLS = ["year", "victim_age", "victim_age_raw", "unsolved", "additional_victims"]

ORDERS = {"month": MONTH_ORDER, "age_group": AGE_ORDER, "outcome": OUTCOME_ORDER,
          "victim_sex": SEX_ORDER, "period": PERIOD_ORDER,
          "circumstance_group": CIRCUMSTANCE_ORDER, "weapon_group": WEAPON_ORDER,
          "relationship_group": RELATIONSHIP_ORDER}


def find_data_file():
    """Use the Parquet copy if it is up to date, otherwise the CSV made by the notebook."""
    csv = next((path for path in CSV_CANDIDATES if path.exists()), None)
    if PARQUET_FILE.exists() and (csv is None or PARQUET_FILE.stat().st_mtime >= csv.stat().st_mtime):
        return PARQUET_FILE
    return csv


def ordered_category(series, order):
    # Keep any unexpected value instead of turning it into NaN
    extra = sorted(set(series.dropna().unique()) - set(order))
    return pd.Categorical(series, categories=order + extra, ordered=True)


# cache_resource keeps one copy in memory (cache_data would copy 857k rows on every click)
@st.cache_resource(show_spinner="Loading 857,379 victim records...")
def load_data(path, modified):
    if str(path).endswith(".parquet"):
        df = pd.read_parquet(path, columns=USE_COLS)
    else:
        dtypes = {col: "category" for col in USE_COLS if col not in NUMBER_COLS}
        df = pd.read_csv(path, usecols=USE_COLS, dtype=dtypes)

    # The CSV loses category order, so restore it
    for col, order in ORDERS.items():
        df[col] = ordered_category(df[col].astype(str), order)
    df["unsolved"] = df["unsolved"].astype(int)

    if not str(path).endswith(".parquet"):
        try:
            df.to_parquet(PARQUET_FILE, index=False, compression="zstd")
        except Exception:
            pass  # the app still works from the CSV
    return df


@st.cache_resource(max_entries=8, show_spinner=False)
def filter_data(_df, key):
    """Filtered rows for one filter selection. Results are kept, so going back is instant."""
    data = apply_filters(_df, dict(key))
    known = _known_frames()
    if len(known) >= 12:  # keep memory small: forget old selections
        known.clear()
        _memo_store().clear()
    known[id(data)] = data
    return data


@st.cache_resource(show_spinner=False)
def _known_frames():
    # the filtered tables made by filter_data; only these get their summaries remembered
    return {}


@st.cache_resource(show_spinner=False)
def _memo_store():
    return {}


def remember(fn):
    """Keep the result of a summary for the same filtered data, so opening a page again is fast.
    The filtered data object is reused between clicks (see filter_data), so it can be the key.
    A copy is returned, so pages can never change the stored result."""
    def wrapper(data, *args, **kwargs):
        if _known_frames().get(id(data)) is not data:
            return fn(data, *args, **kwargs)  # a temporary subset: just calculate it
        store = _memo_store()
        key = (fn.__name__, id(data), args, tuple(sorted(kwargs.items())))
        hit = store.get(key)
        if hit is None or hit[0] is not data:
            if len(store) > 200:
                store.clear()
            hit = (data, fn(data, *args, **kwargs))
            store[key] = hit
        result = hit[1]
        if isinstance(result, tuple):
            return tuple(r.copy() if hasattr(r, "copy") else r for r in result)
        return result.copy() if hasattr(result, "copy") else result
    wrapper.__name__ = fn.__name__
    return wrapper


def apply_filters(df, filters):
    mask = df["year"].between(*filters["years"])
    for col in ["state", "outcome", "age_group", "victim_sex", "weapon_group", "circumstance_group"]:
        if filters[col]:
            mask &= df[col].isin(filters[col])
    return df[mask]


def has_both_outcomes(data):
    return data["unsolved"].nunique() == 2


def unsolved_pct(data):
    if len(data) == 0:
        return None
    return data["unsolved"].mean() * 100


@remember
def unsolved_table(data, column):
    """Records, unsolved, unsolved % and shares for each group of a column."""
    table = data.groupby(column, observed=True)["unsolved"].agg(records="size", unsolved="sum")
    table["solved"] = table["records"] - table["unsolved"]
    table["unsolved %"] = table["unsolved"] / table["records"] * 100
    total_unsolved = table["unsolved"].sum()
    total_solved = table["solved"].sum()
    table["share of all unsolved %"] = table["unsolved"] / total_unsolved * 100 if total_unsolved else 0.0
    table["share of all solved %"] = table["solved"] / total_solved * 100 if total_solved else 0.0
    return table


def split_by_size(table, min_n):
    """Groups big enough to rank, and the small groups left out."""
    return table[table["records"] >= min_n], table[table["records"] < min_n]


@remember
def year_table(data):
    table = data.groupby("year")["unsolved"].agg(records="size", unsolved="sum")
    table["unsolved %"] = table["unsolved"] / table["records"] * 100
    return table


@remember
def state_table(data):
    table = unsolved_table(data, "state")
    extra = data.groupby("state", observed=True).agg(
        years_with_data=("year", "nunique"),
        agencies=("agency_code", "nunique"),
        map_source_pct=("source", lambda s: (s == "MAP").mean() * 100))
    return table.join(extra)


@remember
def pct_pivot(data, rows, cols, min_cell=MIN_CELL):
    """Unsolved % and record counts for two columns. Small cells become NaN."""
    pct = data.pivot_table(index=rows, columns=cols, values="unsolved", aggfunc="mean", observed=True) * 100
    size = data.pivot_table(index=rows, columns=cols, values="unsolved", aggfunc="size", observed=True)
    size = size.reindex(index=pct.index, columns=pct.columns).fillna(0).astype(int)
    return pct.where(size >= min_cell), size


@remember
def profile_table(data, include_undetermined=True):
    # Share is always out of ALL unsolved records in the selection, even for the subset
    all_unsolved = data["unsolved"].sum()
    if not include_undetermined:
        data = data[data["circumstance_group"].isin(SPECIFIC_CIRCUMSTANCES)]
    table = data.groupby(PROFILE_COLS, observed=True)["unsolved"].agg(records="size", unsolved="sum")
    table["unsolved %"] = table["unsolved"] / table["records"] * 100
    table["share of all unsolved %"] = table["unsolved"] / all_unsolved * 100 if all_unsolved else 0.0
    table = table.reset_index()
    table["profile"] = (table["circumstance_group"].astype(str) + " · " + table["weapon_group"].astype(str)
                        + " · " + table["victim_sex"].astype(str) + " · " + table["age_group"].astype(str))
    return table


@remember
def compare_within(data, column, group_a, group_b, min_cell=MIN_CELL):
    """Compare two groups inside each state and period, like the notebook."""
    sub = data[data[column].isin([group_a, group_b])]
    if sub.empty:
        return {"comparison": f"{group_a} vs {group_b}", "state-periods compared": 0,
                f"{group_a} higher": 0, "median difference (points)": None}
    pct = sub.pivot_table(index=["state", "period"], columns=column, values="unsolved",
                          aggfunc="mean", observed=True) * 100
    size = sub.pivot_table(index=["state", "period"], columns=column, values="unsolved",
                           aggfunc="size", observed=True)
    for group in [group_a, group_b]:
        if group not in size.columns:
            size[group] = 0
            pct[group] = None
    keep = (size[group_a].fillna(0) >= min_cell) & (size[group_b].fillna(0) >= min_cell)
    diff = (pct[group_a] - pct[group_b])[keep]
    return {"comparison": f"{group_a} vs {group_b}", "state-periods compared": int(len(diff)),
            f"{group_a} higher": int((diff > 0).sum()),
            "median difference (points)": round(diff.median(), 1) if len(diff) else None}


@remember
def missing_flags(data):
    return pd.DataFrame({
        "Circumstance undetermined": data["circumstance_group"] == "Undetermined",
        "Relationship not determined": data["relationship_group"] == "Not determined",
        "Firearm type not stated": data["weapon_group"] == "Firearm type not stated",
        "Weapon other/type unknown": data["weapon_group"] == "Other/type unknown",
        "Weapon not reported": data["weapon_group"] == "Not reported",
        "Victim age unknown": data["age_group"] == "Unknown",
        "Victim race unknown": data["victim_race"] == "Unknown",
        "Victim sex unknown": data["victim_sex"] == "Unknown",
    })


@remember
def missing_by_outcome(data):
    flags = missing_flags(data)
    return (flags.groupby(data["outcome"], observed=True).mean().T * 100)


def fmt_int(value):
    return f"{int(value):,}"


def fmt_pct(value, digits=1):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{digits}f}%"
