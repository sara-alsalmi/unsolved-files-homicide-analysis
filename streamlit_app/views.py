"""The six dashboard pages. Every number is calculated from the filtered data."""
import gzip

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import charts as ch
from data_utils import (AGE_ORDER, MIN_CELL, MIN_N, SPECIFIC_CIRCUMSTANCES,
                        compare_within, fmt_int, fmt_pct, has_both_outcomes, missing_by_outcome,
                        missing_flags, pct_pivot, profile_table, split_by_size, state_table,
                        unsolved_pct, unsolved_table, year_table)

PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


# ---------- small display helpers ----------

def show(fig):
    st.plotly_chart(fig, theme=None, config=PLOT_CONFIG)


def kpi_cards(cards):
    html = '<div class="kpi-row">'
    for label, value, note in cards:
        html += (f'<div class="kpi"><div class="kpi-label">{label}</div>'
                 f'<div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>')
    st.markdown(html + "</div>", unsafe_allow_html=True)


def insight_panel(title, items):
    """items: list of (tag, text). Tags keep counts and percentages apart."""
    if not items:
        return
    html = f'<div class="insights"><div class="insights-title">{title}</div>'
    for tag, text in items:
        html += f'<div class="insight"><span class="tag tag-{tag.lower().replace(" ", "-")}">{tag}</span>{text}</div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)


def section(title, text=None):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if text:
        st.markdown(f'<div class="section-text">{text}</div>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def excluded_note(small, min_n):
    if small.empty:
        return
    names = ", ".join(f"{i} ({fmt_int(r)})" for i, r in small["records"].items())
    note(f"Not ranked (fewer than {min_n:,} records): {names}.")


def one_outcome_note():
    st.info("Only one reported outcome is selected, so solved/unsolved comparisons and "
            "reported-unsolved percentages are not shown. Select both outcomes to compare them.")


def compact_table(table, column_config=None, rows=10, label="rows"):
    """Show the top rows only; the full table is one click away."""
    st.dataframe(table.head(rows), hide_index=True, column_config=column_config)
    if len(table) > rows:
        with st.expander(f"Show all {len(table)} {label}"):
            st.dataframe(table, hide_index=True, column_config=column_config, height=360)


def pct_table_display(table, label):
    out = table[["records", "unsolved", "unsolved %", "share of all unsolved %"]].copy()
    out.index.name = label
    return out.reset_index()


PCT_COLUMNS = {
    "records": st.column_config.NumberColumn("Victim records", format="localized"),
    "unsolved": st.column_config.NumberColumn("Reported-unsolved", format="localized"),
    "unsolved %": st.column_config.NumberColumn("Unsolved % within group", format="%.1f%%"),
    "share of all unsolved %": st.column_config.NumberColumn("Share of all unsolved", format="%.1f%%"),
    "years_with_data": st.column_config.NumberColumn("Years with data"),
    "agencies": st.column_config.NumberColumn("Agencies", format="localized"),
    "map_source_pct": st.column_config.NumberColumn("FOIA (MAP) records", format="%.1f%%"),
}


# ---------- 1. Overview ----------

@st.fragment  # widgets inside this page only redraw this page
def overview_page(data, both):
    # The KPI band at the top of every page shows the summary numbers
    total = len(data)
    unsolved = int(data["unsolved"].sum())
    pct = unsolved_pct(data)

    years = year_table(data)
    col1, col2 = st.columns([1, 2])
    with col1, st.container(border=True):
        counts = data["outcome"].value_counts().reindex(["Solved", "Unsolved"]).dropna()
        fig = go.Figure(go.Pie(labels=counts.index, values=counts.values, hole=0.62, sort=False,
                               marker=dict(colors=[ch.OUTCOME_COLORS[o] for o in counts.index],
                                           line=dict(color=ch.SURFACE, width=2)),
                               textinfo="label+percent", textfont=dict(color=ch.TEXT),
                               hovertemplate="<b>%{label}</b><br>%{value:,} records<br>%{percent}<extra></extra>"))
        ch.style(fig, "Reported outcome", height=340, legend=False)
        show(fig)
    with col2, st.container(border=True):
        long = data.groupby(["year", "outcome"], observed=True).size().reset_index(name="records")
        show(ch.outcome_stack(long, "year", "Victim records per year (count)", height=340))

    col1, col2 = st.columns(2)
    with col1, st.container(border=True):
        if both:
            show(ch.line(years.index, years["unsolved %"], "Reported-unsolved % per year",
                         ch.UNSOLVED, "Unsolved % within year", hover_records=years["records"]))
        else:
            one_outcome_note()
    with col2, st.container(border=True):
        months = data.groupby("month", observed=True)["unsolved"].agg(records="size", unsolved="sum")
        months["unsolved %"] = months["unsolved"] / months["records"] * 100
        short = [str(m)[:3] for m in months.index]  # Jan, Feb, ... so the labels are not cut off
        view = st.segmented_control("Monthly view", ["Records (count)", "Unsolved %"],
                                    default="Records (count)", key="month_view", label_visibility="collapsed")
        if view == "Unsolved %" and both:
            show(ch.line(short, months["unsolved %"], "Reported-unsolved % by month",
                         ch.UNSOLVED, "Unsolved % within month", hover_records=months["records"], height=300))
        elif view == "Unsolved %":
            one_outcome_note()
        else:
            show(ch.bar_v(short, months["records"], "Victim records by month (count)", ch.TOTAL,
                          y_title="Victim records", height=300,
                          hover_text=[f"<b>{m}</b><br>{r:,} records" for m, r in months["records"].items()]))
        note("Month can be when the body was found. Months have different lengths.")

    col1, col2 = st.columns(2)
    weapons = data["weapon_group"].value_counts().head(8)
    circs = data["circumstance_group"].value_counts().head(8)
    with col1, st.container(border=True):
        table = pd.DataFrame({"records": weapons, "share %": weapons / total * 100})
        show(ch.bar_h(table, "records", "Most common weapon groups (count)", ch.TOTAL,
                      x_title="Victim records", hover_cols=["share %"]))
    with col2, st.container(border=True):
        table = pd.DataFrame({"records": circs, "share %": circs / total * 100})
        show(ch.bar_h(table, "records", "Most common circumstance groups (count)", ch.TOTAL,
                      x_title="Victim records", hover_cols=["share %"]))

    # Calculated insights
    items = []
    if both:
        items.append(("Percent", f"{fmt_int(unsolved)} of {fmt_int(total)} victim records "
                                 f"({fmt_pct(pct)}) were reported unsolved."))
    if len(years):
        peak = years["records"].idxmax()
        items.append(("Count", f"The most records in one year were in {peak} "
                               f"({fmt_int(years.loc[peak, 'records'])} records)."))
    big_years = years[years["records"] >= MIN_CELL]
    if both and len(big_years) > 1:
        hi, lo = big_years["unsolved %"].idxmax(), big_years["unsolved %"].idxmin()
        items.append(("Percent", f"Among years with at least {MIN_CELL} records, the reported-unsolved % "
                                 f"was highest in {hi} ({fmt_pct(big_years.loc[hi, 'unsolved %'])}) "
                                 f"and lowest in {lo} ({fmt_pct(big_years.loc[lo, 'unsolved %'])})."))
    if len(weapons):
        items.append(("Count", f"The most common weapon group is {weapons.index[0]} "
                               f"({fmt_int(weapons.iloc[0])} records, {fmt_pct(weapons.iloc[0] / total * 100)} of the selection)."))
    undetermined = (data["circumstance_group"] == "Undetermined").mean() * 100
    items.append(("Missing info", f"The circumstance is undetermined in {fmt_pct(undetermined)} of the selected records."))
    insight_panel("Calculated insights for this selection", items)


# ---------- 2. Geographic Analysis ----------

@st.fragment  # widgets inside this page only redraw this page
def geography_page(data, both):
    states = state_table(data)
    options = {"Total victim records": "records", "Reported-unsolved records": "unsolved",
               "Reported-unsolved %": "unsolved %"}
    choice = st.segmented_control("Map metric", list(options), default="Total victim records",
                                  key="map_metric")
    choice = choice or "Total victim records"
    metric = options[choice]
    if metric == "unsolved %" and not both:
        one_outcome_note()
        metric, choice = "records", "Total victim records"

    with st.container(border=True):
        section(f"{choice} by state of the reporting agency")
        show(ch.state_map(states, metric, MIN_N))
        legend = "Dark gray = no records in this selection. D.C. is shown with a small marker."
        if metric == "unsolved %":
            legend += f" Light gray = fewer than {MIN_N:,} records."
        note(legend)

    col1, col2 = st.columns([1, 1.3])
    ranked = states.sort_values(metric, ascending=False)
    small = pd.DataFrame()
    if metric == "unsolved %":
        ranked, small = split_by_size(ranked, MIN_N)
    with col1, st.container(border=True):
        top = ranked.head(15)
        fmt = "{:.1f}%" if metric == "unsolved %" else "{:,.0f}"
        show(ch.bar_h(top, metric, f"Top 15 states: {choice.lower()}",
                      ch.TOTAL if metric == "records" else ch.UNSOLVED, value_fmt=fmt,
                      hover_cols=["records", "unsolved"]))
        excluded_note(small, MIN_N)
    with col2, st.container(border=True):
        section("State table")
        table = states.sort_values(metric, ascending=False)[
            ["records", "unsolved", "unsolved %", "years_with_data", "agencies"]].reset_index().rename(columns={"state": "State"})
        if not both:
            table = table.drop(columns=["unsolved %"])
        compact_table(table, PCT_COLUMNS, rows=10, label="states")

    with st.container(border=True):
        section("Metropolitan areas (MSA labels)",
                f"Areas with at least {MIN_N:,} records are ranked. Some labels group rural areas "
                "(for example \"Rural Arkansas\").")
        msa = unsolved_table(data, "msa")
        msa_ranked, msa_small = split_by_size(msa, MIN_N)
        msa_ranked = msa_ranked.sort_values(metric, ascending=False)
        if msa_ranked.empty:
            note(f"No metro area has at least {MIN_N:,} records in this selection.")
        else:
            out = pct_table_display(msa_ranked, "Metro area")
            if not both:
                out = out.drop(columns=["unsolved %"])
            compact_table(out, PCT_COLUMNS, rows=10, label="metro areas")
        note(f"{len(msa_small)} metro-area labels have fewer than {MIN_N:,} records and are not ranked.")


# ---------- 3. Victim Analysis ----------

@st.fragment  # widgets inside this page only redraw this page
def victims_page(data, both):
    col1, col2 = st.columns([1.6, 1])
    with col1, st.container(border=True):
        ages = data.dropna(subset=["victim_age"]).groupby(["victim_age", "outcome"], observed=True).size()
        ages = ages.reset_index(name="records")
        ages["victim_age"] = ages["victim_age"].astype(int)
        fig = ch.outcome_stack(ages, "victim_age", "Victim age distribution (count, known ages)", height=360)
        fig.update_layout(bargap=0.05, barcornerradius=1)
        fig.update_xaxes(title="Victim age (0 = under 1 year, 99 = 99 or older)", dtick=10)
        show(fig)
        unknown_age = int((data["age_group"] == "Unknown").sum())
        note(f"{fmt_int(unknown_age)} records with unknown age (code 999) are not in this chart "
             "but stay in the \"Unknown\" age group below.")
    with col2, st.container(border=True):
        sex = data.groupby(["victim_sex", "outcome"], observed=True).size().reset_index(name="records")
        show(ch.outcome_stack(sex, "victim_sex", "Victim records by sex (count)", height=360))

    ages = unsolved_table(data, "age_group").reindex([a for a in AGE_ORDER if a in data["age_group"].unique()])
    col1, col2 = st.columns(2)
    with col1, st.container(border=True):
        long = data.groupby(["age_group", "outcome"], observed=True).size().reset_index(name="records")
        show(ch.outcome_stack(long, "age_group", "Victim records by age group (count)", height=340))
    with col2, st.container(border=True):
        if both:
            big = ages[ages["records"] >= MIN_CELL]
            show(ch.bar_v(big.index, big["unsolved %"], "Reported-unsolved % by age group", ch.UNSOLVED,
                          y_title="Unsolved % within group", value_fmt="{:.1f}%", height=340,
                          hover_text=[f"<b>{a}</b><br>{p:.1f}% unsolved<br>{r:,} records"
                                      for a, p, r in zip(big.index, big["unsolved %"], big["records"])]))
            excluded_note(ages[ages["records"] < MIN_CELL], MIN_CELL)
        else:
            one_outcome_note()

    col1, col2 = st.columns(2)
    sexes = unsolved_table(data, "victim_sex")
    races = unsolved_table(data, "victim_race").sort_values("unsolved %", ascending=False)
    with col1, st.container(border=True):
        if both:
            big = sexes[sexes["records"] >= MIN_CELL]
            show(ch.bar_h(big, "unsolved %", "Reported-unsolved % by victim sex", ch.UNSOLVED,
                          value_fmt="{:.1f}%", hover_cols=["records", "unsolved"]))
            excluded_note(sexes[sexes["records"] < MIN_CELL], MIN_CELL)
        else:
            one_outcome_note()
    with col2, st.container(border=True):
        if both:
            big = races[races["records"] >= MIN_CELL]
            show(ch.bar_h(big, "unsolved %", "Reported-unsolved % by victim race", ch.UNSOLVED,
                          value_fmt="{:.1f}%", hover_cols=["records", "unsolved"]))
            excluded_note(races[races["records"] < MIN_CELL], MIN_CELL)
            note("Descriptive only: this does not show an effect of race.")
        else:
            one_outcome_note()

    with st.container(border=True):
        if both:
            pct, size = pct_pivot(data, "victim_sex", "age_group")
            show(ch.heatmap(pct, size, f"Age group × sex: reported-unsolved % (blank = fewer than {MIN_CELL} records)",
                            height=300))
        else:
            one_outcome_note()

    if both:
        items = []
        known = ages.drop(index="Unknown", errors="ignore")
        known = known[known["records"] >= MIN_CELL]
        if len(known) > 1:
            items.append(("Percent", f"Among known age groups, {known['unsolved %'].idxmax()} has the highest "
                                     f"reported-unsolved % ({fmt_pct(known['unsolved %'].max())}) and "
                                     f"{known['unsolved %'].idxmin()} the lowest ({fmt_pct(known['unsolved %'].min())})."))
        if {"Male", "Female"} <= set(sexes.index):
            items.append(("Percent", f"Male victim records: {fmt_pct(sexes.loc['Male', 'unsolved %'])} unsolved; "
                                     f"female: {fmt_pct(sexes.loc['Female', 'unsolved %'])}."))
            items.append(("Count", f"Male victims make up {fmt_pct(sexes.loc['Male', 'share of all unsolved %'])} "
                                   "of all reported-unsolved records in this selection."))
        if "Unknown" in ages.index and ages.loc["Unknown", "records"] >= MIN_CELL:
            items.append(("Missing info", f"Records with unknown age are {fmt_pct(ages.loc['Unknown', 'unsolved %'])} "
                                          "unsolved; these victims were often unidentified."))
        insight_panel("Calculated insights for this selection", items)


# ---------- 4. Weapons & Circumstances ----------

@st.fragment  # widgets inside this page only redraw this page
def weapons_page(data, both):
    tab_w, tab_c, tab_h = st.tabs(["Weapons", "Circumstances", "Combined heatmaps"])

    with tab_w:
        weapons = unsolved_table(data, "weapon_group")
        col1, col2 = st.columns(2)
        with col1, st.container(border=True):
            show(ch.bar_h(weapons.sort_values("records", ascending=False), "records",
                          "Victim records by weapon group (count)", ch.TOTAL, x_title="Victim records"))
        with col2, st.container(border=True):
            if both:
                big, small = split_by_size(weapons, MIN_CELL)
                show(ch.bar_h(big.sort_values("unsolved %", ascending=False), "unsolved %",
                              "Reported-unsolved % within each weapon group", ch.UNSOLVED,
                              value_fmt="{:.1f}%", hover_cols=["records", "unsolved"]))
                excluded_note(small, MIN_CELL)
            else:
                one_outcome_note()
        with st.container(border=True):
            if both:
                show(ch.share_compare(weapons.sort_values("share of all unsolved %", ascending=False),
                                      "Solved vs unsolved: share of records by weapon group"))
            else:
                one_outcome_note()
        with st.container(border=True):
            section("Detailed weapons", f"Original weapon labels with at least {MIN_N:,} records.")
            detail, small = split_by_size(unsolved_table(data, "weapon"), MIN_N)
            out = pct_table_display(detail.sort_values("records", ascending=False), "Weapon")
            if not both:
                out = out.drop(columns=["unsolved %"])
            compact_table(out, PCT_COLUMNS, rows=8, label="weapons")
            excluded_note(small, MIN_N)

    with tab_c:
        note('"Undetermined" means the circumstance was not known when the report was made.')
        circs = unsolved_table(data, "circumstance_group")
        col1, col2 = st.columns(2)
        with col1, st.container(border=True):
            show(ch.bar_h(circs.sort_values("records", ascending=False), "records",
                          "Victim records by circumstance group (count)", ch.TOTAL, x_title="Victim records"))
        with col2, st.container(border=True):
            if both:
                big, small = split_by_size(circs, MIN_CELL)
                show(ch.bar_h(big.sort_values("unsolved %", ascending=False), "unsolved %",
                              "Reported-unsolved % within each circumstance group", ch.UNSOLVED,
                              value_fmt="{:.1f}%", hover_cols=["records", "unsolved"]))
                excluded_note(small, MIN_CELL)
            else:
                one_outcome_note()
        with st.container(border=True):
            if both:
                subset = st.toggle("Only recorded specific circumstances (gang, drugs, robbery, other felony, "
                                   "argument/brawl)", value=False, key="circ_subset")
                part = data[data["circumstance_group"].isin(SPECIFIC_CIRCUMSTANCES)] if subset else data
                table = unsolved_table(part, "circumstance_group")
                show(ch.share_compare(table.sort_values("share of all unsolved %", ascending=False),
                                      "Solved vs unsolved: share of records by circumstance group"))
                if subset:
                    note("Only the five specific circumstance groups, so the shares add up to 100%.")
            else:
                one_outcome_note()
        with st.container(border=True):
            section("Detailed circumstances", f"Original circumstance labels with at least {MIN_N:,} records.")
            detail, small = split_by_size(unsolved_table(data, "circumstance"), MIN_N)
            out = pct_table_display(detail.sort_values("records", ascending=False), "Circumstance")
            if not both:
                out = out.drop(columns=["unsolved %"])
            compact_table(out, PCT_COLUMNS, rows=8, label="circumstances")
            excluded_note(small, MIN_N)

    with tab_h:
        if not both:
            one_outcome_note()
            return
        view = st.segmented_control("Heatmap", ["Circumstance × age group", "Circumstance × weapon group"],
                                    default="Circumstance × age group", key="heat_view")
        specific = data[data["circumstance_group"].isin(SPECIFIC_CIRCUMSTANCES)]
        with st.container(border=True):
            if specific.empty:
                note("No records with a specific circumstance in this selection.")
            elif view == "Circumstance × weapon group":
                pct, size = pct_pivot(specific, "circumstance_group", "weapon_group")
                show(ch.heatmap(pct, size, f"Reported-unsolved % (blank = fewer than {MIN_CELL} records)",
                                height=380))
            else:
                pct, size = pct_pivot(specific, "circumstance_group", "age_group")
                show(ch.heatmap(pct, size, f"Reported-unsolved % (blank = fewer than {MIN_CELL} records)",
                                height=380))
            note("Only the five specific circumstance groups. Hover a cell to see its number of records.")


# ---------- 5. Unsolved Patterns ----------

DIMENSIONS = {"Circumstance group": "circumstance_group", "Weapon group": "weapon_group",
              "Victim age group": "age_group", "Victim sex": "victim_sex",
              "Relationship group": "relationship_group", "Period": "period", "Victim race": "victim_race"}


@st.fragment  # widgets inside this page only redraw this page
def unsolved_page(data, both):
    unsolved = data[data["unsolved"] == 1]
    if unsolved.empty:
        st.warning("There are no reported-unsolved records in this selection.")
        return

    # Unsolved totals are in the top band, so these cards add new information
    flags = missing_flags(unsolved).mean() * 100
    known = unsolved[unsolved["circumstance_group"].isin(SPECIFIC_CIRCUMSTANCES)]["circumstance_group"]
    top_known = known.value_counts().index[0] if len(known) else "—"
    kpi_cards([
        ("Distinct incident IDs", fmt_int(unsolved["incident_id"].nunique()), "among unsolved victim records"),
        ("Most unsolved records (count)", str(top_known), "recorded circumstance"),
        ("Circumstance undetermined", fmt_pct(flags["Circumstance undetermined"]), "of unsolved records"),
        ("Relationship not determined", fmt_pct(flags["Relationship not determined"]), "of unsolved records"),
        ("Firearm type not stated", fmt_pct(flags["Firearm type not stated"]), "of unsolved records"),
    ])

    # A. How unsolved records differ
    with st.container(border=True):
        section("What do unsolved records look like?",
                "Compare how each group's share of unsolved records differs from its share of solved records.")
        label = st.selectbox("Characteristic", list(DIMENSIONS), key="dim_select")
        column = DIMENSIONS[label]
        table = unsolved_table(data, column)
        if both:
            show(ch.share_compare(table.sort_values("share of all unsolved %", ascending=False),
                                  f"Share of solved vs unsolved records by {label.lower()}"))
        else:
            share = table.sort_values("share of all unsolved %", ascending=False)
            show(ch.bar_h(share, "share of all unsolved %", f"Unsolved records by {label.lower()} (share)",
                          ch.UNSOLVED, value_fmt="{:.1f}%", hover_cols=["unsolved"]))
        if column == "relationship_group":
            note("Relationship is usually known only after an offender is identified, so it is \"Not determined\" "
                 "in most unsolved records.")

    # B. Profiles
    with st.container(border=True):
        section("Common profiles vs high-percentage profiles",
                "Profile = circumstance · weapon · victim sex · age group. The most common unsolved profile "
                "is not always the one with the highest unsolved %.")
        scope = st.segmented_control("Circumstances", ["Specific circumstances only", "All circumstance groups"],
                                     default="Specific circumstances only", key="profile_scope")
        profiles = profile_table(data, include_undetermined=(scope == "All circumstance groups"))
        cols = {"profile": st.column_config.TextColumn("Profile", width="medium"), **PCT_COLUMNS}
        show_cols = ["profile", "records", "unsolved", "unsolved %", "share of all unsolved %"]
        if not both:
            show_cols.remove("unsolved %")
        tab_common, tab_high = st.tabs(["Most unsolved records (count)",
                                        f"Highest reported-unsolved % ({MIN_N:,}+ records)"])
        with tab_common:
            common = profiles[profiles["unsolved"] > 0].sort_values("unsolved", ascending=False).head(8)
            st.dataframe(common[show_cols], hide_index=True, column_config=cols)
        with tab_high:
            if both:
                high = profiles[profiles["records"] >= MIN_N].sort_values("unsolved %", ascending=False).head(8)
                if high.empty:
                    note(f"No profile has at least {MIN_N:,} records in this selection.")
                else:
                    st.dataframe(high[show_cols], hide_index=True, column_config=cols)
            else:
                one_outcome_note()
        if both:
            bubbles = profiles[profiles["records"] >= MIN_CELL]
            if len(bubbles):
                show(ch.bubble(bubbles, f"Profiles with {MIN_CELL}+ records: size vs unsolved % "
                                        "(bubble size = unsolved records)"))

    # C. Consistency check
    with st.container(border=True):
        section("Do the patterns hold inside the same state and period?",
                f"Each pair is compared within every state and period where both groups have at least "
                f"{MIN_CELL} records.")
        if both:
            rows = [compare_within(data, "circumstance_group", g, "Argument/Brawl") for g in ["Gang", "Drugs", "Robbery"]]
            rows += [compare_within(data, "weapon_group", "Handgun", "Rifle/Shotgun"),
                     compare_within(data, "victim_sex", "Male", "Female"),
                     compare_within(data, "age_group", "18-24", "0-12")]
            out = pd.DataFrame([{"Comparison": r["comparison"], "State-periods compared": r["state-periods compared"],
                                 "First group higher": list(r.values())[2],
                                 "Median difference (points)": r["median difference (points)"]} for r in rows])
            st.dataframe(out, hide_index=True)
        else:
            one_outcome_note()

    # D. Missing information
    col1, col2 = st.columns(2)
    with col1, st.container(border=True):
        missing = missing_by_outcome(data)
        fig = go.Figure()
        for outcome in [o for o in ["Solved", "Unsolved"] if o in missing.columns]:
            fig.add_bar(y=missing.index, x=missing[outcome], name=outcome, orientation="h",
                        marker_color=ch.OUTCOME_COLORS[outcome],
                        hovertemplate=f"<b>%{{y}}</b><br>{outcome}: %{{x:.1f}}%<extra></extra>")
        fig.update_layout(barmode="group")
        fig.update_yaxes(autorange="reversed")
        ch.style(fig, "Missing or unspecified details by outcome", height=420,
                 x_title="% of records within each outcome")
        show(fig)
    with col2, st.container(border=True):
        per_year = missing_flags(data).groupby(data["year"]).mean() * 100
        measure = st.selectbox("Detail over time", ["Circumstance undetermined", "Firearm type not stated",
                                                    "Relationship not determined"], key="missing_year")
        counts = data.groupby("year").size()
        show(ch.line(per_year.index, per_year[measure], f"{measure}: % of records per year", ch.TOTAL,
                     "% of records", hover_records=counts, height=340))

    # E. Patterns for further review
    items = []
    if both:
        specific = unsolved_table(data[data["circumstance_group"].isin(SPECIFIC_CIRCUMSTANCES)], "circumstance_group")
        specific = specific[specific["records"] >= MIN_N]
        if len(specific) > 1:
            hi, lo = specific["unsolved %"].idxmax(), specific["unsolved %"].idxmin()
            items.append(("Percent", f"Among recorded specific circumstances, {hi} has the highest reported-unsolved % "
                                     f"({fmt_pct(specific.loc[hi, 'unsolved %'])}, {fmt_int(specific.loc[hi, 'records'])} records) "
                                     f"and {lo} the lowest ({fmt_pct(specific.loc[lo, 'unsolved %'])})."))
        profiles_all = profile_table(data, include_undetermined=False)
        if len(profiles_all) and profiles_all["unsolved"].max() > 0:
            top = profiles_all.sort_values("unsolved", ascending=False).iloc[0]
            items.append(("Count", f"The most common unsolved profile with a recorded circumstance is {top['profile']} "
                                   f"({fmt_int(top['unsolved'])} unsolved of {fmt_int(top['records'])} records)."))
        states = state_table(data)
        states = states[states["records"] >= MIN_N]
        if len(states):
            s = states["unsolved %"].idxmax()
            items.append(("Percent", f"Among states with {MIN_N:,}+ records, {s} has the highest reported-unsolved % "
                                     f"({fmt_pct(states.loc[s, 'unsolved %'])}, {fmt_int(states.loc[s, 'records'])} records)."))
        miss = missing_by_outcome(data)
        if "Firearm type not stated" in miss.index:
            items.append(("Missing info", f"Firearm type is not stated in {fmt_pct(miss.loc['Firearm type not stated', 'Unsolved'])} "
                                          f"of unsolved records vs {fmt_pct(miss.loc['Firearm type not stated', 'Solved'])} of solved records."))
    items.append(("Missing info", f"{fmt_pct(flags['Circumstance undetermined'])} of unsolved records have an undetermined "
                                  "circumstance, so circumstance patterns describe only part of the unsolved records."))
    insight_panel("Patterns for further review", items)


# ---------- 6. Data & Definitions ----------

CLEANING_STEPS = pd.DataFrame({
    "Step": ["Original MAP file (SHR76_25a.csv)", "Removed manslaughter by negligence",
             "Removed 2025 (year not complete)", "Removed reported justifiable homicides "
             "(felon killed by police or private citizen)"],
    "Records removed": [0, 23785, 14040, 34229],
    "Records kept": [929433, 905648, 891608, 857379],
})

COLUMN_DEFINITIONS = pd.DataFrame([
    ("incident_id", "MAP identifier built from year, month, incident number and agency code. Victims in the same incident share it."),
    ("state / county / msa", "State, county and metro area of the reporting agency (not the exact crime location)."),
    ("agency_code / agency_type", "Reporting agency code and type (municipal police, sheriff, ...)."),
    ("source", "FBI report, or a record MAP obtained through Freedom of Information Act requests (MAP)."),
    ("year / month / period", "Year and month of the homicide or when the body was recovered; period groups the years."),
    ("outcome / unsolved", "Solved = offender identified when the report was made. unsolved = 1 when no offender was identified."),
    ("victim_age / age_group", "Victim age in years (0 = under one year, 99 = 99 or older). Unknown age (999) is empty / \"Unknown\"."),
    ("victim_sex / victim_race", "Recorded victim sex and race, including Unknown."),
    ("weapon / weapon_group", "Original weapon label and the notebook's weapon group."),
    ("circumstance / circumstance_group", "Reported circumstance or theory (robbery, argument, ...) and the notebook's group."),
    ("relationship / relationship_group", "Victim-offender relationship, if recorded, and the notebook's group."),
    ("additional_victims", "Number of additional victims in the incident (0 = one victim in total)."),
], columns=["Column", "Meaning"])


FACTS = [
    (":material/database:", "The data", "Murder Accountability Project homicide reports (FBI + FOIA), 1976–2024."),
    (":material/person:", "One row", "One victim record. Victims of the same incident share an incident ID."),
    (":material/task_alt:", "Solved", "An offender was identified when the report was made. Not a court result."),
    (":material/percent:", "Unsolved %", "Unsolved records in a group ÷ all records in that group. Not a clearance rate."),
]


@st.fragment  # widgets inside this page only redraw this page
def definitions_page(df, data):
    cards = '<div class="fact-row">' + "".join(
        f'<div class="fact"><div class="fact-title">{title}</div><div class="fact-text">{text}</div></div>'
        for _, title, text in FACTS) + "</div>"
    st.markdown(cards, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1, st.container(border=True):
        section("Good to know")
        st.markdown(
            "- Age **0** = under one year · **99** = 99 or older · **999** = unknown\n"
            "- \"Undetermined\" circumstance = not known when the report was made\n"
            "- Places are the **reporting agency**, not the crime scene\n"
            f"- Rankings need **{MIN_N:,}+ records**; small bars and heatmap cells need **{MIN_CELL}+**")
    with col2, st.container(border=True):
        section("Limits")
        st.markdown(
            "- Reporting coverage differs by agency, state and year\n"
            "- A case may have been solved after it was reported\n"
            "- Counts are not population homicide rates\n"
            "- Patterns are associations, not causes")

    with st.container(border=True):
        section("Downloads", "Downloads use the current filters.")
        summaries = {"Summary by year": ("by_year", year_table(data)),
                     "Summary by state": ("by_state", state_table(data)),
                     "Summary by circumstance": ("by_circumstance_group", unsolved_table(data, "circumstance_group"))}
        cols = st.columns(len(summaries) + 1)
        for col, (label, (name, table)) in zip(cols, summaries.items()):
            with col:
                st.download_button(label, table.round(2).to_csv().encode("utf-8"), file_name=f"summary_{name}.csv",
                                   mime="text/csv", key=f"dl_{name}", on_click="ignore", width="stretch", icon=":material/download:")
        with cols[-1]:
            st.download_button("Filtered data (.csv.gz)",
                               lambda: gzip.compress(data.to_csv(index=False).encode("utf-8"), compresslevel=1),
                               file_name="filtered_homicide_records.csv.gz", mime="application/gzip",
                               key="dl_filtered", type="primary", on_click="ignore", width="stretch", icon=":material/download:")

    with st.expander("How the data was cleaned"):
        st.dataframe(CLEANING_STEPS, hide_index=True,
                     column_config={"Step": st.column_config.TextColumn(width="medium"),
                                    "Records removed": st.column_config.NumberColumn(format="localized", width="small"),
                                    "Records kept": st.column_config.NumberColumn(format="localized", width="small")})
        note("Repeated rows and Unknown values were kept.")
    with st.expander("Column definitions"):
        st.dataframe(COLUMN_DEFINITIONS, hide_index=True,
                     column_config={"Meaning": st.column_config.TextColumn(width="large")})
    with st.expander("Data preview (first 100 filtered records)"):
        preview_cols = ["year", "month", "state", "victim_age", "victim_sex", "weapon_group",
                        "circumstance_group", "relationship_group", "outcome"]
        st.dataframe(data[preview_cols].head(100), hide_index=True, height=320)
    note("Source: Murder Accountability Project, https://www.murderdata.org/p/data-docs.html")
