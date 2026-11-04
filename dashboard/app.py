"""Plotly Dash dashboard for operations and finance users.

Reads the Django REST API, so it holds no database credentials and can scale
as its own ECS service.

    python -m dashboard.app        # http://localhost:8050
"""

from __future__ import annotations

import os
from urllib.parse import parse_qs

import dash
import requests
from dash import Dash, Input, Output, dash_table, dcc, html

from dashboard import figures as f

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api").rstrip("/")
TIMEOUT = 30


def fetch(path: str) -> dict | list | None:
    try:
        resp = requests.get(f"{API_BASE_URL}/{path}", timeout=TIMEOUT)
        return resp.json() if resp.ok else None
    except requests.RequestException:
        return None


def money(v):
    return "–" if v is None else f"${v:,.2f}"


def kpi_tile(label: str, value: str, note: str = "") -> html.Div:
    return html.Div(
        [html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"),
         html.Div(note, className="kpi-note")],
        className="kpi",
    )


def build_kpis(kpis: dict, dq: dict | None) -> list:
    pass_rate = dq["quality_report"]["pass_rate_pct"] if dq else None
    return [
        kpi_tile("Gross revenue", money(kpis.get("gross_revenue")),
                 f"{money(kpis.get('gross_revenue_ex_outliers'))} excl. flagged · {kpis.get('trips', 0):,} trips"),
        kpi_tile("Median fare", money(kpis.get("median_fare")),
                 f"p95 {money(kpis.get('p95_fare'))}"),
        kpi_tile("Median trip", f"{kpis.get('median_duration_min', 0):.1f} min",
                 f"p95 {kpis.get('p95_duration_min', 0):.0f} min"),
        kpi_tile("Card tip rate", f"{kpis.get('avg_card_tip_pct') or 0:.1f}%",
                 f"{kpis.get('card_share_pct') or 0:.0f}% of trips paid by card"),
        kpi_tile("Data quality pass rate", "–" if pass_rate is None else f"{pass_rate:.1f}%",
                 f"{kpis.get('outlier_rate_pct') or 0:.2f}% flagged as outliers"),
    ]


def quality_table(dq: dict | None):
    if not dq:
        return html.P("No ingestion run recorded for this table.")
    rows = [
        {**r, "action": r["action"].upper()}
        for r in dq["quality_report"]["rules"]
    ]
    return dash_table.DataTable(
        data=rows,
        columns=[
            {"name": "Rule", "id": "rule"}, {"name": "Action", "id": "action"},
            {"name": "Rows", "id": "rows_affected", "type": "numeric", "format": {"specifier": ","}},
            {"name": "% of input", "id": "pct_of_input", "type": "numeric"},
            {"name": "Description", "id": "description"},
        ],
        sort_action="native",
        style_as_list_view=True,
        style_header={"fontWeight": 600, "backgroundColor": f.SURFACE, "color": f.INK},
        style_cell={"fontFamily": f.FONT, "fontSize": 13, "padding": "8px", "textAlign": "left",
                    "backgroundColor": f.SURFACE, "color": f.INK_2, "whiteSpace": "normal"},
        style_data_conditional=[
            {"if": {"filter_query": "{action} = REJECT"}, "fontWeight": 600, "color": f.INK},
        ],
    )


# Fixed pixel height per graph. The container sets the size and the figure fills it,
# so a resize can never feed back into a taller container.
GRAPH_HEIGHTS = {"daily": 340, "drawdown": 240, "hourly": 320, "fares": 320, "boroughs": 300, "payments": 300}


def graph(graph_id: str) -> html.Div:
    return html.Div(
        dcc.Graph(
            id=graph_id,
            responsive=True,
            style={"height": f"{GRAPH_HEIGHTS[graph_id]}px"},
            config={"displaylogo": False},
        ),
        className="card",
    )


def parse_query(search: str | None) -> tuple[str | None, bool]:
    """Read ?table=...&embed=1 (set when the React app embeds this dashboard)."""
    params = parse_qs((search or "").lstrip("?"))
    return params.get("table", [None])[0], params.get("embed", ["0"])[0] == "1"


def create_app() -> Dash:
    app = Dash(__name__, title="Taxi Revenue Dashboard",
               assets_folder=os.path.join(os.path.dirname(__file__), "assets"))
    # A function layout is re-evaluated on each page load, so the table list stays
    # current and the dashboard can start before the API is up.
    app.layout = serve_layout
    _register_callbacks(app)
    return app


def table_options() -> list[dict]:
    tables = fetch("tables/") or []
    return [{"label": f"{t['table']}  ({t['trips']:,} trips)", "value": t["table"]}
            for t in tables if t["loaded"]]


def serve_layout() -> html.Div:
    options = table_options()
    default = options[0]["value"] if options else None
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            html.Header(
                [html.H1("NYC Taxi Revenue & Operations"),
                 html.P("Revenue, demand and data quality for the selected TLC dataset.")],
                id="header",
            ),
            html.Div(
                id="filters",
                children=[html.Label("Dataset", htmlFor="table"),
                 dcc.Dropdown(id="table", options=options, value=default, clearable=False,
                              placeholder="No tables loaded - run manage.py ingest_trips")],
                className="filters",
            ),
            dcc.Loading(
                html.Div(
                    [
                        html.Div(id="kpis", className="kpi-row"),
                        graph("daily"),
                        graph("drawdown"),
                        html.Div([graph("hourly"), graph("fares")], className="grid-2"),
                        html.Div([graph("boroughs"), graph("payments")], className="grid-2"),
                        html.H2("Data quality report"),
                        html.Div(id="dq"),
                    ]
                )
            ),
        ],
        className="page",
        id="page",
    )


def _register_callbacks(app: Dash) -> None:
    @app.callback(
        Output("table", "value"), Output("header", "style"), Output("filters", "style"),
        Output("page", "className"),
        Input("url", "search"),
        prevent_initial_call=False,
    )
    def apply_query(search):
        table, embed = parse_query(search)
        hidden = {"display": "none"} if embed else {}
        value = table if table else dash.no_update
        return value, hidden, hidden, "page embed" if embed else "page"

    @app.callback(
        Output("kpis", "children"), Output("daily", "figure"), Output("drawdown", "figure"),
        Output("hourly", "figure"), Output("fares", "figure"), Output("boroughs", "figure"),
        Output("payments", "figure"), Output("dq", "children"),
        Input("table", "value"),
    )
    def refresh(table):
        data = fetch(f"analytics/{table}/") if table else None
        if not data:
            empty = f.empty_figure("API unavailable or table not loaded")
            return [], empty, empty, empty, empty, empty, empty, html.P("No data.")
        dq = fetch(f"data-quality/{table}/")
        return (
            build_kpis(data["kpis"], dq),
            f.daily_revenue_figure(data["daily"]),
            f.drawdown_figure(data["daily"]),
            f.hourly_figure(data["hourly"]),
            f.fare_histogram_figure(data["fare_distribution"]),
            f.ranked_bar_figure(data["boroughs"], "borough", "revenue", "Revenue by pickup borough", "$"),
            f.ranked_bar_figure(data["payment_mix"], "payment_type", "trips", "Trips by payment type"),
            quality_table(dq),
        )


app = create_app()
server = app.server  # gunicorn entrypoint: dashboard.app:server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)), debug=False)
