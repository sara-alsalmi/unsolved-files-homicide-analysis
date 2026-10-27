"""Unsolved Files: Homicide Analysis & Investigation Insights (Streamlit dashboard).

Run from the project folder:  streamlit run streamlit_app/app.py
"""
import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import game
import views
from data_utils import (AGE_ORDER, CIRCUMSTANCE_ORDER, SEX_ORDER, WEAPON_ORDER, filter_data,
                        find_data_file, fmt_int, fmt_pct, has_both_outcomes, load_data, unsolved_pct)

LOGO_FILE = Path(__file__).parent / "assets" / "logo.png"
st.set_page_config(page_title="Unsolved Files", page_icon=str(LOGO_FILE), layout="wide",
                   initial_sidebar_state="expanded")

CSS_FILE = Path(__file__).parent / "assets" / "style.css"
st.markdown(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# name: (rail label, icon, page function)
PAGES = {
    "Overview": ("Overview", ":material/dashboard:", views.overview_page),
    "Geographic Analysis": ("Geography", ":material/public:", views.geography_page),
    "Victim Analysis": ("Victims", ":material/groups:", views.victims_page),
    "Weapons & Circumstances": ("Weapons", ":material/target:", views.weapons_page),
    "Unsolved Patterns": ("Unsolved", ":material/manage_search:", views.unsolved_page),
    "Cold Case Game": ("Game", ":material/person_search:", None),
    "Data & Definitions": ("Data", ":material/description:", None),
}

# Original logo: an evidence folder with a magnifying glass (no official seal)
LOGO = """<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
<circle cx="60" cy="60" r="56" fill="#141114" stroke="#6d6266" stroke-width="3"/>
<circle cx="60" cy="60" r="47" fill="none" stroke="#3a3236" stroke-width="2"/>
<path d="M35 33h17l5 6h28v30H35z" fill="#2a2326" stroke="#b9adb0" stroke-width="2.5" stroke-linejoin="round"/>
<path d="M35 44h50" stroke="#b9adb0" stroke-width="2"/>
<circle cx="67" cy="57" r="8.5" fill="#2a2326" stroke="#e05561" stroke-width="3.2"/>
<path d="M73 63l7 7" stroke="#e05561" stroke-width="3.6" stroke-linecap="round"/>
<text x="60" y="88" text-anchor="middle" font-family="Barlow Condensed, sans-serif" font-size="8.5"
 letter-spacing="1.5" fill="#b9adb0">UNSOLVED FILES</text></svg>"""

# ---------- data ----------
data_path = find_data_file()
if data_path is None:
    st.error("No clean data found. Put clean_data_shr.parquet or clean_data_shr.csv in this folder, or run "
             "analysis_shr.ipynb to create clean_data_shr.csv in the project folder.")
    st.stop()
df = load_data(str(data_path), data_path.stat().st_mtime)

YEAR_MIN, YEAR_MAX = int(df["year"].min()), int(df["year"].max())


@st.cache_resource(show_spinner=False)
def filter_options(path, modified):
    """The choices in each filter. Made once (reading 857k rows every click was slow)."""
    def options(column, order):
        present = set(df[column].astype(str).unique())
        return [value for value in order if value in present]
    return {
        "state": sorted(df["state"].astype(str).unique()),
        "circumstance_group": options("circumstance_group", CIRCUMSTANCE_ORDER),
        "weapon_group": options("weapon_group", WEAPON_ORDER),
        "age_group": options("age_group", AGE_ORDER),
        "victim_sex": options("victim_sex", SEX_ORDER),
    }


FILTER_OPTIONS = filter_options(str(data_path), data_path.stat().st_mtime)
FILTER_LABELS = {"state": "State", "circumstance_group": "Circumstance", "weapon_group": "Weapon",
                 "age_group": "Victim Age", "victim_sex": "Victim Sex"}
DROPDOWNS = ["circumstance_group", "weapon_group", "age_group", "victim_sex"]  # one choice each


def reset_filters():
    st.session_state["f_years"] = (YEAR_MIN, YEAR_MAX)
    st.session_state["f_outcome_choice"] = "All"
    st.session_state["f_state"] = []
    for column in DROPDOWNS:
        st.session_state[f"f_{column}"] = "All"


def clear_filter(key, value):
    st.session_state[key] = value


def go_to(page):
    st.session_state["page"] = page


FILTER_KEYS = ["f_years", "f_state", "f_outcome_choice"] + [f"f_{column}" for column in DROPDOWNS]

# The game page has no filters, and Streamlit forgets widgets that are not drawn,
# so keep a copy of the filter values and put it back when the user returns.
for key, value in st.session_state.get("saved_filters", {}).items():
    if key not in st.session_state:
        st.session_state[key] = value
if "f_years" not in st.session_state:
    reset_filters()
if "page" not in st.session_state:
    st.session_state["page"] = "Overview"
page = st.session_state["page"]

# Open each new page at the top. The page name makes the script new each time so it runs again,
# and it repeats for about a second while the new page is drawn.
# It is drawn on every run (same place, hidden by CSS) so the page layout never jumps;
# the script only runs again when the page name inside it changes.
components.html(f"""<script>
  // page: {page}
  let tries = 0;
  const isGame = box => {{
    const frame = box.querySelector('iframe');
    try {{ return !!(frame && frame.contentDocument && frame.contentDocument.querySelector('.wrap #startBtn')); }}
    catch (e) {{ return false; }}
  }};
  const toTop = () => {{
    const doc = window.parent.document;
    const main = doc.querySelector('[data-testid="stMain"]');
    if (main) main.scrollTo(0, 0);
    // remove any height the game left on a box that now shows something else (no empty gaps)
    doc.querySelectorAll('[data-testid="stElementContainer"]').forEach(box => {{
      if (box.style.height && !isGame(box)) {{ box.style.height = ''; box.style.minHeight = ''; }}
    }});
    if (++tries < 12) setTimeout(toTop, 100);
  }};
  toTop();

</script>""", height=0)

# ---------- filtering (done first, so pages without the filter bar still use the filters) ----------
outcome_choice = st.session_state["f_outcome_choice"]
filters = {"years": tuple(st.session_state["f_years"]), "state": tuple(st.session_state["f_state"]),
           "outcome": () if outcome_choice == "All" else (outcome_choice,)}
for column in DROPDOWNS:
    choice = st.session_state[f"f_{column}"]
    filters[column] = () if choice == "All" else (choice,)
st.session_state["saved_filters"] = {key: st.session_state[key] for key in FILTER_KEYS}
data = filter_data(df, tuple(sorted(filters.items())))
both = has_both_outcomes(data)

chips = []
if filters["years"] != (YEAR_MIN, YEAR_MAX):
    chips.append((f"Years {filters['years'][0]}–{filters['years'][1]}", "f_years", (YEAR_MIN, YEAR_MAX)))
if filters["state"]:
    states = ", ".join(filters["state"][:2]) + (f" +{len(filters['state']) - 2}" if len(filters["state"]) > 2 else "")
    chips.append((f"State: {states}", "f_state", []))
for column in DROPDOWNS:
    if filters[column]:
        chips.append((f"{FILTER_LABELS[column]}: {filters[column][0]}", f"f_{column}", "All"))
if outcome_choice != "All":
    chips.append((f"Outcome: {outcome_choice}", "f_outcome_choice", "All"))

# ---------- icon rail ----------
with st.sidebar:
    logo = base64.b64encode(LOGO_FILE.read_bytes()).decode()
    st.markdown(f'<div class="rail-mark"><img src="data:image/png;base64,{logo}" alt="Unsolved Files logo"></div>',
                unsafe_allow_html=True)
    for name, (label, icon, _) in PAGES.items():
        st.button(label, icon=icon, key=f"nav_{name}", on_click=go_to, args=(name,),
                  type="primary" if name == page else "secondary", width="stretch")
    st.markdown('<div class="rail-foot">MAP homicide<br>reports<br>1976–2024</div>', unsafe_allow_html=True)

# ---------- game page: a small title and the game, no filters ----------
if page == "Cold Case Game":
    st.markdown(f'<div class="game-header"><div class="brand-logo">{LOGO}</div>'
                f'<div><div class="brand-title">Unsolved Files · Homicide Analysis</div>'
                f'<div class="brand-page">Cold Case Game</div></div></div>', unsafe_allow_html=True)
    with st.container():
        game.game_page(df)
    st.stop()

# ---------- header: title block + filters ----------
left, right = st.columns([1.15, 2.25], gap="large")
with left:
    st.markdown(f'<div class="brand-block"><div class="brand-logo">{LOGO}</div><div>'
                f'<div class="brand-title">Unsolved Files<br>Homicide Analysis</div>'
                f'<div class="brand-rule"></div><div class="brand-page">{page}</div></div></div>',
                unsafe_allow_html=True)
    year_col, reset_col = st.columns([3, 1], vertical_alignment="bottom")
    with year_col:
        st.slider("Year", YEAR_MIN, YEAR_MAX, key="f_years")
    with reset_col:
        st.button("Reset", on_click=reset_filters, width="stretch", icon=":material/restart_alt:")

with right:
    filter_cols = st.columns([1.4, 1, 1, 1, 1, 1])
    with filter_cols[0]:
        st.multiselect("State", FILTER_OPTIONS["state"], key="f_state", placeholder="All states",
                       help="Type to search. You can pick more than one state.")
    for col, column in zip(filter_cols[1:5], DROPDOWNS):
        with col:
            st.selectbox(FILTER_LABELS[column], ["All"] + FILTER_OPTIONS[column], key=f"f_{column}")
    with filter_cols[5]:
        st.selectbox("Outcome", ["All", "Solved", "Unsolved"], key="f_outcome_choice",
                     help="Choosing one outcome turns off solved/unsolved comparisons.")

# ---------- KPI band ----------
with right:
    unsolved = int(data["unsolved"].sum())
    pct_value = fmt_pct(unsolved_pct(data)) if both else "—"
    pct_note = "unsolved / all records" if both else "outcome filter is active"
    kpis = [("Victim Records", fmt_int(len(data)), f"of {fmt_int(len(df))} in {YEAR_MIN}–{YEAR_MAX}"),
            ("Reported Solved", fmt_int(len(data) - unsolved), "offender identified at report"),
            ("Reported Unsolved", fmt_int(unsolved), "no offender identified at report"),
            ("Reported-Unsolved %", pct_value, pct_note)]
    band = '<div class="kpi-band">' + "".join(
        f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>'
        f'<div class="kpi-note">{note}</div></div>' for label, value, note in kpis) + "</div>"
    st.markdown(band, unsafe_allow_html=True)

# ---------- active filters: one chip per filter, click to remove ----------
# The chip row is always drawn (empty when there are no filters) so the page below keeps its
# place; otherwise Streamlit would redraw the whole page when the first filter is chosen.
chip_row = st.container(horizontal=True, vertical_alignment="center", gap="small", key="chip_row")
if chips:
    with chip_row:
        st.markdown(f'<div class="chip-label">{len(chips)} active filter{"s" if len(chips) > 1 else ""} · '
                    f'{fmt_int(len(data))} records</div>', unsafe_allow_html=True)
        for i, (label, key, value) in enumerate(chips):
            st.button(label, key=f"chip_{i}", icon=":material/close:", on_click=clear_filter, args=(key, value),
                      type="tertiary")
st.markdown('<div class="page-rule"></div>', unsafe_allow_html=True)

# ---------- page ----------
render = PAGES[page][2]
with st.container():
    if data.empty:
        st.warning("No records match these filters. Remove a filter or press **Reset**.")
    else:
        if not both and outcome_choice == "All":
            st.info("This selection contains only one reported outcome, so solved/unsolved comparisons are not shown.")
        if page == "Data & Definitions":
            views.definitions_page(df, data)
        else:
            render(data, both)

