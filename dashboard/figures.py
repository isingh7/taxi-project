"""Pure figure builders for the Dash dashboard: API payload in, Plotly figure out.

Design rules (from the team's chart guidelines):
    * One y-axis per chart. Revenue ($) and drawdown (%) are separate charts.
    * Categorical colours are assigned in a fixed order and follow the entity.
    * Magnitude (the heatmap) uses one hue, light to dark.
    * Bars are ranked; part-to-whole uses ranked bars, not pies.
    * Anomalies use the reserved "critical" status colour plus a text label,
      so colour is never the only cue.
    * Titles live in the HTML card header (see ``CHARTS``), not inside the plot.

``CHARTS`` is the single list of charts, shared by the Dash app and by
``manage.py export_static_api`` (which pre-renders them for the static demo).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import plotly.graph_objects as go

# Validated palette (light mode). Slots 1-3 pass all-pairs CVD checks.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
CRITICAL = "#d03b3b"
INK, INK_2, MUTED = "#14171f", "#5b6170", "#898781"
GRID, BASELINE, SURFACE = "#eceae4", "#c3c2b7", "#ffffff"
FONT = "Inter, -apple-system, Segoe UI, Roboto, sans-serif"
# Sequential blue ramp (steps 100 -> 700); the lightest step means "few trips".
SEQUENTIAL = ["#eef4fc", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def _layout(fig: go.Figure, y_title: str = "", x_title: str = "", top: int = 12) -> go.Figure:
    # No fixed height: each graph container has a fixed CSS height and the figure autosizes
    # into it. Letting the figure size its own container made graphs grow on every resize.
    fig.update_layout(
        autosize=True,
        margin={"l": 60, "r": 20, "t": top, "b": 44},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT, "color": INK_2, "size": 12},
        hoverlabel={"bgcolor": "white", "bordercolor": BASELINE, "font": {"color": INK, "family": FONT}},
        showlegend=False,
        bargap=0.25,
    )
    fig.update_xaxes(title=x_title, showgrid=False, linecolor=BASELINE, tickfont={"color": MUTED},
                     title_font={"size": 12})
    fig.update_yaxes(title=y_title, gridcolor=GRID, zeroline=False, showline=False,
                     tickfont={"color": MUTED}, title_font={"size": 12})
    return fig


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font={"color": INK_2, "size": 14})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig)


def daily_revenue_figure(daily: list[dict]) -> go.Figure:
    if not daily:
        return empty_figure("No daily data")
    dates = [d["date"] for d in daily]
    fig = go.Figure()
    fig.add_scatter(
        x=dates, y=[d["revenue"] for d in daily], name="Daily revenue", mode="lines",
        line={"color": SERIES[0], "width": 2},
        hovertemplate="Revenue $%{y:,.0f}<extra></extra>",
    )
    fig.add_scatter(
        x=dates, y=[d["rolling_mean"] for d in daily], name="7-day average", mode="lines",
        line={"color": SERIES[1], "width": 2},
        hovertemplate="7-day avg $%{y:,.0f}<extra></extra>",
    )
    anomalies = [d for d in daily if d["is_anomaly"]]
    if anomalies:
        fig.add_scatter(
            x=[d["date"] for d in anomalies], y=[d["revenue"] for d in anomalies],
            name="Anomaly (>3σ)", mode="markers+text", text=["▲ anomaly"] * len(anomalies),
            textposition=["bottom center" if (d.get("pct_change") or 0) < 0 else "top center"
                          for d in anomalies],
            textfont={"color": INK_2, "size": 11},
            marker={"color": CRITICAL, "size": 10, "line": {"color": SURFACE, "width": 2}},
            hovertemplate="Anomaly: outside 3σ of the prior week<extra></extra>",
        )
    fig.update_xaxes(hoverformat="%a %d %b %Y")
    top = max(d["revenue"] for d in daily)
    fig.update_yaxes(tickprefix="$", tickformat=",.0f", range=[0, top * 1.15])  # headroom for labels
    fig = _layout(fig, y_title="Revenue (USD)", top=36)
    # After _layout, which hides legends by default: this chart has three series, so it needs one.
    fig.update_layout(
        hovermode="x unified", showlegend=True,
        legend={"orientation": "h", "y": 1.0, "yanchor": "bottom", "x": 1, "xanchor": "right",
                "font": {"size": 12}},
    )
    return fig


def drawdown_figure(daily: list[dict]) -> go.Figure:
    if not daily:
        return empty_figure("No daily data")
    fig = go.Figure()
    fig.add_scatter(
        x=[d["date"] for d in daily], y=[d["drawdown_pct"] for d in daily], mode="lines",
        fill="tozeroy", line={"color": SERIES[0], "width": 2}, fillcolor="rgba(42,120,214,0.15)",
        name="Drawdown", hovertemplate="%{x|%a %d %b}<br>%{y:.1f}% below peak<extra></extra>",
    )
    fig.update_yaxes(ticksuffix="%")
    return _layout(fig, y_title="% below peak")


def heatmap_figure(grid: dict | None) -> go.Figure:
    if not grid or not any(map(sum, grid.get("trips", []))):
        return empty_figure("No trips to chart")
    days = [d[:3] for d in grid["weekdays"]]
    hours = [f"{h:02d}:00" for h in grid["hours"]]
    steps = len(SEQUENTIAL) - 1
    fig = go.Figure(
        go.Heatmap(
            z=grid["trips"], x=hours, y=days,
            colorscale=[[i / steps, c] for i, c in enumerate(SEQUENTIAL)],
            xgap=2, ygap=2,  # surface-coloured gaps between cells
            colorbar={"title": {"text": "Trips", "font": {"size": 12}}, "thickness": 10, "len": 0.9,
                      "outlinewidth": 0, "tickfont": {"color": MUTED}},
            hovertemplate="%{y} %{x}<br>%{z:,} trips<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", gridcolor=SURFACE)  # Monday on top
    fig.update_xaxes(tickvals=hours[::3])
    return _layout(fig)


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
                     ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)])
    return _layout(fig, y_title="Trips", x_title="Hour of day", top=24)


def ranked_bar_figure(rows: list[dict], label_key: str, value_key: str,
                      prefix: str = "", suffix: str = "") -> go.Figure:
    if not rows:
        return empty_figure("No data")
    rows = sorted(rows, key=lambda r: float(r[value_key] or 0))  # ascending -> largest at top
    values = [float(r[value_key] or 0) for r in rows]
    fig = go.Figure()
    fig.add_bar(
        y=[r[label_key] for r in rows], x=values, orientation="h", marker_color=SERIES[0],
        text=[f"{prefix}{v:,.0f}{suffix}" for v in values], textposition="outside",
        textfont={"color": INK_2}, cliponaxis=False,
        hovertemplate=f"%{{y}}<br>{prefix}%{{x:,.2f}}{suffix}<extra></extra>",
    )
    fig.update_xaxes(showticklabels=False, showgrid=False, showline=False, range=[0, max(values) * 1.2])
    fig = _layout(fig)
    fig.update_yaxes(showgrid=False, tickfont={"color": INK_2}, ticksuffix="   ")  # gap before the bar
    fig.update_layout(margin={"l": 104})
    return fig


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
        hovertemplate="$%{customdata[0]:.2f}–$%{customdata[1]:.2f}<br>%{y:,} trips<extra></extra>",
    )
    fig.update_xaxes(tickprefix="$")
    return _layout(fig, y_title="Trips", x_title="Fare (USD)")


@dataclass(frozen=True)
class Chart:
    id: str
    title: str
    subtitle: str | Callable[[dict], str]
    height: int  # fixed container height in px
    full_width: bool
    build: Callable[[dict], go.Figure]

    def subtitle_for(self, payload: dict) -> str:
        return self.subtitle(payload) if callable(self.subtitle) else self.subtitle


def _fare_subtitle(payload: dict) -> str:
    clipped = (payload.get("fare_distribution") or {}).get("clipped_above")
    return f"Unflagged trips. The top 1%, above ${clipped:,.0f}, is not shown." if clipped else "Unflagged trips"


CHARTS: list[Chart] = [
    Chart("daily", "Daily revenue",
          "Total revenue per day with its trailing 7-day average. Red markers are days more than "
          "3 standard deviations from the previous week.",
          360, True, lambda p: daily_revenue_figure(p["daily"])),
    Chart("drawdown", "Drawdown",
          "How far the 7-day average sits below its highest point so far, as a trading desk tracks a P&L.",
          240, True, lambda p: drawdown_figure(p["daily"])),
    Chart("heatmap", "Demand by weekday and hour",
          "Trips by pickup time. Darker cells are busier.",
          300, True, lambda p: heatmap_figure(p.get("weekday_hour"))),
    Chart("hourly", "Trips by pickup hour", "All days combined.",
          320, False, lambda p: hourly_figure(p["hourly"])),
    Chart("fares", "Fare distribution", _fare_subtitle,
          320, False, lambda p: fare_histogram_figure(p["fare_distribution"])),
    Chart("boroughs", "Revenue by pickup borough", "Ranked by total revenue.",
          300, False, lambda p: ranked_bar_figure(p["boroughs"], "borough", "revenue", prefix="$")),
    Chart("payments", "Trips by payment type", "Ranked by number of trips.",
          300, False, lambda p: ranked_bar_figure(p["payment_mix"], "payment_type", "trips")),
]
