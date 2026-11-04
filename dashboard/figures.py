"""Pure figure builders for the Dash dashboard: API payload in, Plotly figure out.

Design rules (from the team's chart guidelines):
    * One y-axis per chart. Revenue ($) and drawdown (%) are separate charts.
    * Categorical colours are assigned in a fixed order and follow the entity.
    * Bars are ranked; part-to-whole uses ranked bars, not pies.
    * Anomalies use the reserved "critical" status colour plus a text label,
      so colour is never the only cue.
"""

from __future__ import annotations

import plotly.graph_objects as go

# Validated palette (light mode). Slots 1-3 pass all-pairs CVD checks.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
CRITICAL = "#d03b3b"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
FONT = "Inter, -apple-system, Segoe UI, Roboto, sans-serif"


def _layout(fig: go.Figure, title: str, y_title: str = "", x_title: str = "") -> go.Figure:
    # No fixed height here: each dcc.Graph gets a fixed CSS height (see app.GRAPH_HEIGHTS) and
    # the figure autosizes into it. Letting the figure size its own container caused a
    # resize feedback loop where graphs grew taller on every scroll/resize.
    fig.update_layout(
        autosize=True,
        title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 15, "color": INK}},
        margin={"l": 56, "r": 24, "t": 48, "b": 44},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT, "color": INK_2, "size": 12},
        hoverlabel={"bgcolor": "white", "bordercolor": BASELINE, "font": {"color": INK}},
        legend={"orientation": "h", "y": 1.12, "x": 1, "xanchor": "right"},
        bargap=0.25,
    )
    fig.update_xaxes(title=x_title, showgrid=False, linecolor=BASELINE, tickfont={"color": MUTED})
    fig.update_yaxes(title=y_title, gridcolor=GRID, zeroline=False, linecolor=BASELINE,
                     tickfont={"color": MUTED})
    return fig


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font={"color": INK_2, "size": 14})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig, "")


def daily_revenue_figure(daily: list[dict]) -> go.Figure:
    if not daily:
        return empty_figure("No daily data")
    dates = [d["date"] for d in daily]
    fig = go.Figure()
    fig.add_scatter(
        x=dates, y=[d["revenue"] for d in daily], name="Daily revenue", mode="lines",
        line={"color": SERIES[0], "width": 2},
        hovertemplate="%{x|%a %d %b %Y}<br>Revenue $%{y:,.0f}<extra></extra>",
    )
    fig.add_scatter(
        x=dates, y=[d["rolling_mean"] for d in daily], name="7-day average", mode="lines",
        line={"color": SERIES[1], "width": 2},
        hovertemplate="%{x|%d %b}<br>7-day avg $%{y:,.0f}<extra></extra>",
    )
    anomalies = [d for d in daily if d["is_anomaly"]]
    if anomalies:
        fig.add_scatter(
            x=[d["date"] for d in anomalies], y=[d["revenue"] for d in anomalies],
            name="Anomaly (>3σ)", mode="markers+text", text=["▲ anomaly"] * len(anomalies),
            textposition=["bottom center" if (d["pct_change"] or 0) < 0 else "top center" for d in anomalies],
            textfont={"color": INK_2, "size": 11},
            marker={"color": CRITICAL, "size": 10, "line": {"color": SURFACE, "width": 2}},
            hovertemplate="%{x|%d %b}<br>$%{y:,.0f} - outside 3σ of prior week<extra></extra>",
        )
    fig.update_layout(hovermode="x unified")
    top = max(d["revenue"] for d in daily)
    fig.update_yaxes(tickprefix="$", tickformat=",.0f", range=[0, top * 1.15])  # headroom for labels
    return _layout(fig, "Daily revenue", y_title="Revenue (USD)")


def drawdown_figure(daily: list[dict]) -> go.Figure:
    if not daily:
        return empty_figure("No daily data")
    fig = go.Figure()
    fig.add_scatter(
        x=[d["date"] for d in daily], y=[d["drawdown_pct"] for d in daily], mode="lines",
        fill="tozeroy", line={"color": SERIES[0], "width": 2}, fillcolor="rgba(42,120,214,0.15)",
        name="Drawdown", hovertemplate="%{x|%d %b}<br>%{y:.1f}% below peak<extra></extra>",
    )
    fig.update_yaxes(ticksuffix="%")
    return _layout(fig, "Revenue drawdown from running peak", y_title="% below peak")


def hourly_figure(hourly: list[dict]) -> go.Figure:
    if not hourly:
        return empty_figure("No hourly data")
    peak = max(hourly, key=lambda h: h["trips"])
    fig = go.Figure()
    fig.add_bar(
        x=[h["hour"] for h in hourly], y=[h["trips"] for h in hourly], marker_color=SERIES[0],
        name="Trips", customdata=[[h["share_pct"], h["avg_fare"]] for h in hourly],
        hovertemplate="%{x}:00<br>%{y:,} trips (%{customdata[0]:.1f}%)<br>"
                      "Avg fare $%{customdata[1]:.2f}<extra></extra>",
    )
    fig.add_annotation(x=peak["hour"], y=peak["trips"], text=f"Peak {peak['hour']}:00",
                       showarrow=False, yshift=12, font={"color": INK, "size": 11})
    fig.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 3)),
                     ticktext=[f"{h}:00" for h in range(0, 24, 3)])
    return _layout(fig, "Trips by pickup hour", y_title="Trips", x_title="Hour of day")


def ranked_bar_figure(rows: list[dict], label_key: str, value_key: str, title: str,
                      prefix: str = "", suffix: str = "") -> go.Figure:
    if not rows:
        return empty_figure("No data")
    rows = sorted(rows, key=lambda r: r[value_key] or 0)  # ascending -> largest at top
    values = [float(r[value_key] or 0) for r in rows]
    fig = go.Figure()
    fig.add_bar(
        y=[r[label_key] for r in rows], x=values, orientation="h", marker_color=SERIES[0],
        text=[f"{prefix}{v:,.0f}{suffix}" for v in values], textposition="outside",
        textfont={"color": INK_2}, cliponaxis=False,
        hovertemplate=f"%{{y}}<br>{prefix}%{{x:,.2f}}{suffix}<extra></extra>",
    )
    fig.update_xaxes(showticklabels=False, showgrid=False, range=[0, max(values) * 1.18])
    fig.update_yaxes(showgrid=False)
    return _layout(fig, title)


def fare_histogram_figure(dist: dict) -> go.Figure:
    edges, counts = dist.get("edges", []), dist.get("counts", [])
    if not counts:
        return empty_figure("No fare data")
    mids = [(a + b) / 2 for a, b in zip(edges[:-1], edges[1:], strict=False)]
    fig = go.Figure()
    fig.add_bar(
        x=mids, y=counts, width=[(b - a) * 0.92 for a, b in zip(edges[:-1], edges[1:], strict=False)],
        marker_color=SERIES[0], name="Trips",
        customdata=list(zip(edges[:-1], edges[1:], strict=False)),
        hovertemplate="$%{customdata[0]:.2f}-$%{customdata[1]:.2f}<br>%{y:,} trips<extra></extra>",
    )
    fig.update_xaxes(tickprefix="$")
    return _layout(fig, f"Fare distribution (unflagged trips; top 1% above ${dist['clipped_above']:,.0f} not shown)",
                   y_title="Trips", x_title="Fare (USD)")
