"""Plotly chart helpers with one shared dark style."""
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# Colors for the red-black theme. Solved is a neutral blue-gray and unsolved is the red
# highlight; the pair passes the colorblind and normal-vision separation checks.
SURFACE = "#1a0d10"
TEXT = "#f2eeee"
TEXT_MUTED = "#b3a4a6"
GRID = "#3a2125"
SOLVED = "#7d8aa6"
UNSOLVED = "#ef5a5f"
TOTAL = "#b9a9ac"      # neutral color for all-record counts
NO_DATA = "#2b2224"    # states with no records in the selection
TOO_SMALL = "#4d4245"  # states below the minimum group size
OUTCOME_COLORS = {"Solved": SOLVED, "Unsolved": UNSOLVED}
TITLE_FONT = "'Barlow Condensed', 'Arial Narrow', sans-serif"
BODY_FONT = "Barlow, 'Segoe UI', sans-serif"

# Sequential scales: dark (low) to bright (high) on the dark surface
RED_SCALE = [[0.0, "#4f1f27"], [0.25, "#7a2433"], [0.5, "#ad2f40"], [0.75, "#e2525a"], [1.0, "#ffc1b8"]]
BLUE_SCALE = RED_SCALE  # one red family for every map metric, like the reference
MAP_BORDER = "#8a6d72"

GEOJSON_PATH = Path(__file__).parent / "assets" / "us-states.json"
DC_CENTER = {"lon": -77.016, "lat": 38.905}


def style(fig, title=None, height=380, legend=True, x_title=None, y_title=None):
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=title, font=dict(family=TITLE_FONT, size=19, color="#ddd2d3"), x=0.5,
                   xanchor="center") if title else None,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=BODY_FONT, color=TEXT, size=13),
        margin=dict(l=10, r=20, t=64 if title else 20, b=10),
        hoverlabel=dict(bgcolor="#140a0c", bordercolor="#d63a47", font=dict(family=BODY_FONT, color=TEXT, size=13)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5, title=None,
                    font=dict(color=TEXT_MUTED)),
        barcornerradius=3,
        bargap=0.3,
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, title=x_title,
                     tickfont=dict(color=TEXT_MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, title=y_title,
                     tickfont=dict(color=TEXT_MUTED))
    return fig


def bar_h(table, value_col, title, color, value_fmt="{:,.0f}", x_title=None, height=None,
          hover_cols=None):
    """Horizontal bar chart from a table indexed by category (first row on top)."""
    labels = [str(i) for i in table.index]
    values = table[value_col]
    hover_cols = hover_cols or []
    customdata = table[hover_cols].values if hover_cols else None
    hover = f"<b>%{{y}}</b><br>{value_col}: %{{x:,.1f}}"
    for i, col in enumerate(hover_cols):
        hover += f"<br>{col}: %{{customdata[{i}]:,.0f}}" if "%" not in col else f"<br>{col}: %{{customdata[{i}]:.1f}}%"
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=color,
        text=[value_fmt.format(v) for v in values], textposition="outside",
        textfont=dict(color=TEXT_MUTED, size=12), cliponaxis=False,
        customdata=customdata, hovertemplate=hover + "<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    height = height or max(260, 34 * len(labels) + 80)
    style(fig, title, height=height, legend=False, x_title=x_title)
    fig.update_xaxes(range=[0, values.max() * 1.18 if len(values) else 1])
    return fig


def bar_v(x, y, title, color, y_title=None, value_fmt=None, hover_text=None, height=360):
    fig = go.Figure(go.Bar(
        x=[str(v) for v in x], y=y, marker_color=color,
        text=[value_fmt.format(v) for v in y] if value_fmt else None,
        textposition="outside", textfont=dict(color=TEXT_MUTED, size=12), cliponaxis=False,
        hovertext=hover_text, hovertemplate="%{hovertext}<extra></extra>" if hover_text is not None else None))
    style(fig, title, height=height, legend=False, y_title=y_title)
    if len(y):
        fig.update_yaxes(range=[0, max(y) * 1.15])
    return fig


def outcome_stack(counts, x_col, title, y_title="Victim records", height=360, horizontal=False):
    """Stacked solved/unsolved bars from a long table with x_col, outcome and records."""
    fig = go.Figure()
    for outcome in ["Solved", "Unsolved"]:
        part = counts[counts["outcome"] == outcome]
        if part.empty:
            continue
        if horizontal:
            fig.add_bar(y=part[x_col].astype(str), x=part["records"], name=outcome, orientation="h",
                        marker=dict(color=OUTCOME_COLORS[outcome], line=dict(color=SURFACE, width=1)),
                        hovertemplate=f"<b>%{{y}}</b><br>{outcome}: %{{x:,}}<extra></extra>")
        else:
            fig.add_bar(x=part[x_col].astype(str), y=part["records"], name=outcome,
                        marker=dict(color=OUTCOME_COLORS[outcome], line=dict(color=SURFACE, width=1)),
                        hovertemplate=f"<b>%{{x}}</b><br>{outcome}: %{{y:,}}<extra></extra>")
    fig.update_layout(barmode="stack")
    style(fig, title, height=height, x_title=None if not horizontal else y_title,
          y_title=y_title if not horizontal else None)
    if horizontal:
        fig.update_yaxes(autorange="reversed")
    return fig


def line(x, y, title, color, y_title, hover_records=None, height=340, y_range=None):
    customdata = hover_records if hover_records is not None else None
    hover = "<b>%{x}</b><br>" + y_title + ": %{y:.1f}%"
    if customdata is not None:
        hover += "<br>Victim records: %{customdata:,}"
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines+markers", line=dict(color=color, width=2),
                               marker=dict(size=6, color=color), customdata=customdata,
                               hovertemplate=hover + "<extra></extra>"))
    style(fig, title, height=height, legend=False, y_title=y_title)
    fig.update_layout(hovermode="x")
    if y_range:
        fig.update_yaxes(range=y_range)
    return fig


def share_compare(table, title, height=None):
    """Grouped bars: share of all solved vs share of all unsolved records for each group."""
    labels = [str(i) for i in table.index]
    fig = go.Figure()
    fig.add_bar(y=labels, x=table["share of all solved %"], name="Share of solved records",
                orientation="h", marker_color=SOLVED,
                customdata=table[["solved"]].values,
                hovertemplate="<b>%{y}</b><br>Share of solved: %{x:.1f}%<br>Solved records: %{customdata[0]:,}<extra></extra>")
    fig.add_bar(y=labels, x=table["share of all unsolved %"], name="Share of unsolved records",
                orientation="h", marker_color=UNSOLVED,
                customdata=table[["unsolved"]].values,
                hovertemplate="<b>%{y}</b><br>Share of unsolved: %{x:.1f}%<br>Unsolved records: %{customdata[0]:,}<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig.update_yaxes(autorange="reversed")
    style(fig, title, height=height or max(300, 52 * len(labels) + 90), x_title="% of records within each outcome")
    return fig


def heatmap(pct, size, title, x_title=None, y_title=None, height=420):
    text = pct.map(lambda v: "" if pd.isna(v) else f"{v:.1f}")
    fig = go.Figure(go.Heatmap(
        z=pct.values, x=[str(c) for c in pct.columns], y=[str(i) for i in pct.index],
        text=text.values, texttemplate="%{text}", textfont=dict(size=12),
        customdata=size.values, colorscale=RED_SCALE, zmin=0, zmax=100,
        xgap=2, ygap=2, hoverongaps=False,
        colorbar=dict(title=dict(text="Unsolved %", font=dict(color=TEXT_MUTED)), tickfont=dict(color=TEXT_MUTED)),
        hovertemplate="<b>%{y} · %{x}</b><br>Reported-unsolved: %{z:.1f}%<br>Victim records: %{customdata:,}<extra></extra>"))
    style(fig, title, height=height, legend=False, x_title=x_title, y_title=y_title)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


@lru_cache(maxsize=1)
def load_geojson():
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def state_map(states, metric, min_n, height=520):
    """US choropleth by state name. states: table indexed by state with records, unsolved, unsolved %."""
    geojson = load_geojson()
    all_states = [f["properties"]["name"] for f in geojson["features"]]
    labels = {"records": "Total victim records", "unsolved": "Reported-unsolved records",
              "unsolved %": "Reported-unsolved %"}
    scale = BLUE_SCALE if metric == "records" else RED_SCALE

    shown = states.copy()
    too_small = pd.DataFrame()
    if metric == "unsolved %":
        too_small = shown[shown["records"] < min_n]
        shown = shown[shown["records"] >= min_n]
    no_data = [s for s in all_states if s not in states.index]

    fig = go.Figure()
    # Gray layers so missing data is not confused with zero
    if no_data:
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.name", locations=no_data, z=[0] * len(no_data),
            colorscale=[[0, NO_DATA], [1, NO_DATA]], showscale=False, marker_line_color=MAP_BORDER,
            marker_line_width=0.8, name="No records",
            hovertemplate="<b>%{location}</b><br>No records in this selection<extra></extra>"))
    if not too_small.empty:
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.name", locations=list(too_small.index),
            z=[0] * len(too_small), colorscale=[[0, TOO_SMALL], [1, TOO_SMALL]], showscale=False,
            marker_line_color=MAP_BORDER, marker_line_width=0.8,
            customdata=too_small[["records", "unsolved"]].values,
            hovertemplate=("<b>%{location}</b><br>Victim records: %{customdata[0]:,}"
                           "<br>Reported-unsolved: %{customdata[1]:,}"
                           f"<br>Fewer than {min_n:,} records: % not shown<extra></extra>")))
    if not shown.empty:
        custom = shown[["records", "unsolved", "unsolved %"]].values
        hover = ("<b>%{location}</b><br>Victim records: %{customdata[0]:,}"
                 "<br>Reported-unsolved: %{customdata[1]:,}"
                 "<br>Reported-unsolved %: %{customdata[2]:.1f}%<extra></extra>")
        zmin, zmax = float(shown[metric].min()), float(shown[metric].max())
        if zmin == zmax:
            zmin = 0
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.name", locations=list(shown.index),
            z=shown[metric], zmin=zmin, zmax=zmax, colorscale=scale,
            marker_line_color=MAP_BORDER, marker_line_width=0.8, customdata=custom, hovertemplate=hover,
            colorbar=dict(title=dict(text=labels[metric], font=dict(color=TEXT_MUTED, size=12)),
                          tickfont=dict(color=TEXT_MUTED), thickness=12, len=0.7)))
        # D.C. is too small to see on the map, so add a marker at its center
        if "District of Columbia" in shown.index:
            dc = shown.loc["District of Columbia"]
            fig.add_trace(go.Scattergeo(
                lon=[DC_CENTER["lon"]], lat=[DC_CENTER["lat"]], mode="markers",
                marker=dict(size=11, color=[dc[metric]], colorscale=scale, cmin=zmin, cmax=zmax,
                            line=dict(color=TEXT, width=1.2)),
                customdata=[[dc["records"], dc["unsolved"], dc["unsolved %"]]],
                hovertemplate=hover.replace("%{location}", "District of Columbia"), showlegend=False))
    fig.update_geos(projection_type="albers usa", visible=False, bgcolor="rgba(0,0,0,0)",
                    showlakes=False, showland=False)
    style(fig, None, height=height, legend=False)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), dragmode=False)
    return fig


def bubble(profiles, title, height=440):
    fig = go.Figure(go.Scatter(
        x=profiles["records"], y=profiles["unsolved %"], mode="markers",
        marker=dict(size=profiles["unsolved"], sizemode="area",
                    sizeref=2.0 * profiles["unsolved"].max() / (38 ** 2) if len(profiles) else 1,
                    sizemin=4, color=UNSOLVED, opacity=0.75, line=dict(color=SURFACE, width=1.5)),
        customdata=profiles[["profile", "unsolved", "share of all unsolved %"]].values,
        hovertemplate=("<b>%{customdata[0]}</b><br>Victim records: %{x:,}<br>Unsolved records: %{customdata[1]:,}"
                       "<br>Reported-unsolved: %{y:.1f}%<br>Share of all unsolved: %{customdata[2]:.1f}%<extra></extra>")))
    style(fig, title, height=height, legend=False, x_title="Victim records in profile (log scale)",
          y_title="Reported-unsolved % within profile")
    fig.update_xaxes(type="log")
    fig.update_yaxes(range=[0, 100])
    return fig
