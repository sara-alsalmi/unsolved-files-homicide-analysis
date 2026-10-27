"""Cold Case: The Pinboard - a quick (2-3 minute) detective game inside the dashboard.

The story is fictional, but the case uses the dashboard's own categories, and the verdict
compares the case with real numbers calculated from the cleaned data (all records, 1976-2024).
"""
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from data_utils import unsolved_table

GAME_HTML = Path(__file__).parent / "assets" / "game.html"

# groups shown on the verdict screen: (key used in the game, column, group)
FACT_GROUPS = [
    ("argument", "circumstance_group", "Argument/Brawl"),
    ("other_felony", "circumstance_group", "Other felony"),
    ("robbery", "circumstance_group", "Robbery"),
    ("drugs", "circumstance_group", "Drugs"),
    ("gang", "circumstance_group", "Gang"),
]
# Relationship is left out on purpose: it is mostly recorded only after an offender is
# identified, so unsolved % by relationship would be circular and misleading.


@st.cache_data(show_spinner=False)
def game_facts(_df, key="all-records-v2"):
    facts = {"overall": round(float(_df["unsolved"].mean() * 100), 1), "records": int(len(_df))}
    tables = {}
    for name, column, group in FACT_GROUPS:
        if column not in tables:
            tables[column] = unsolved_table(_df, column)
        row = tables[column].loc[group]
        facts[name] = {"pct": round(float(row["unsolved %"]), 1), "n": int(row["records"])}
    unsolved = _df[_df["unsolved"] == 1]
    facts["undetermined"] = round(float((unsolved["circumstance_group"] == "Undetermined").mean() * 100), 1)
    facts["rel_not_determined"] = round(float((unsolved["relationship_group"] == "Not determined").mean() * 100), 1)
    return facts


def game_page(df):
    html = GAME_HTML.read_text(encoding="utf-8").replace("__FACTS__", json.dumps(game_facts(df)))
    components.html(html, height=590, scrolling=False)
    st.markdown('<div class="note">The story is fictional. The numbers on the final screen come from the real data '
                '(1976–2024).</div>', unsafe_allow_html=True)
