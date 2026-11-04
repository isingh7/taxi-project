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


def money(v, digits: int = 2):
    return "–" if v is None else f"${v:,.{digits}f}"


def kpi_tile(label: str, value: str, note: str = "") -> html.Div:
    return html.Div(
        [html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"),
         html.Div(note, className="kpi-note")],
        className="kpi",
    )


def build_kpis(kpis: dict, dq: dict | None) -> list:
    pass_rate = dq["quality_report"]["pass_rate_pct"] if dq else None
    return [
        kpi_tile("Gross revenue", money(kpis.get("gross_revenue"), 0),
                 f"{money(kpis.get('gross_revenue_ex_outliers'), 0)} excluding flagged trips"),
        kpi_tile("Trips", f"{kpis.get('trips', 0):,}",
                 f"Median trip {kpis.get('median_duration_min') or 0:.1f} min"),
        kpi_tile("Median fare", money(kpis.get("median_fare")), f"95th percentile {money(kpis.get('p95_fare'))}"),
        kpi_tile("Card tip rate", f"{kpis.get('avg_card_tip_pct') or 0:.1f}%",
                 f"{kpis.get('card_share_pct') or 0:.0f}% of trips paid by card"),
        kpi_tile("Data quality", "–" if pass_rate is None else f"{pass_rate:.1f}%",
                 "of raw rows passed every check"),
    ]


TONE_LABELS = {"warning": "Check", "insight": "Insight"}


def build_findings(findings: list[dict]):
    """Plain-English findings. The tone is shown as a word, never only as a colour."""
    if not findings:
        return html.P("No findings for this dataset.", className="muted")
    return html.Ul(
        [
            html.Li(
                [
                    html.Span(TONE_LABELS.get(item["tone"], "Insight"), className=f"tone tone-{item['tone']}"),
                    html.Div([html.Div(item["title"], className="finding-title"),
                              html.P(item["detail"], className="finding-detail")]),
                ],
                className="finding",
            )
            for item in findings
        ],
        className="findings",
    )


def humanise_rule(rule: str) -> str:
    return rule.replace("_", " ").capitalize().replace("nyc", "NYC")


def quality_table(dq: dict | None):
    if not dq:
        return html.P("No ingestion run recorded for this table.", className="muted")
    rows = [{**r, "rule": humanise_rule(r["rule"]), "action": r["action"].capitalize()}
            for r in dq["quality_report"]["rules"]]
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
        style_header={"fontWeight": 600, "backgroundColor": "#f6f7f9", "color": f.INK_2,
                      "textTransform": "uppercase", "fontSize": 11, "letterSpacing": "0.04em"},
        style_cell={"fontFamily": f.FONT, "fontSize": 13, "padding": "10px 12px", "textAlign": "left",
                    "backgroundColor": "#ffffff", "color": f.INK, "whiteSpace": "normal",
                    "borderBottom": "1px solid #eef0f3"},
        style_data_conditional=[
            {"if": {"filter_query": "{rows_affected} = 0"}, "color": "#9aa0ab"},
            {"if": {"filter_query": "{action} = Reject && {rows_affected} > 0", "column_id": "action"},
             "color": "#c62f2f", "fontWeight": 600},
        ],
    )


def chart_card(chart: f.Chart) -> html.Div:
    """Card with an HTML title and subtitle above a fixed-height graph.

    The fixed container height means a resize can never feed back into a taller container.
    """
    return html.Div(
        [
            html.Div([html.H3(chart.title), html.P(id=f"{chart.id}-subtitle")], className="card-head"),
            dcc.Graph(
                id=chart.id,
                responsive=True,
                style={"height": f"{chart.height}px"},
                config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
            ),
        ],
        className="card",
    )


def chart_rows() -> list:
    """Full-width charts get their own row; half-width charts are paired."""
    rows, pending = [], []
    for chart in f.CHARTS:
        if chart.full_width:
            rows.append(chart_card(chart))
            continue
        pending.append(chart_card(chart))
        if len(pending) == 2:
            rows.append(html.Div(pending, className="grid-2"))
            pending = []
    if pending:
        rows.append(html.Div(pending, className="grid-2"))
    return rows


def parse_query(search: str | None) -> tuple[str | None, bool]:
    """Read ?table=...&embed=1 (set when the React app embeds this dashboard)."""
    params = parse_qs((search or "").lstrip("?"))
    return params.get("table", [None])[0], params.get("embed", ["0"])[0] == "1"


def table_label(table: str | None) -> str:
    parts = (table or "").split("_")
    if len(parts) == 4 and parts[0] == "tlc":
        return f"{parts[1].capitalize()} cab · {parts[3]}"
    return table or "–"


def create_app() -> Dash:
    app = Dash(
        __name__,
        title="NYC Taxi Revenue Dashboard",
        assets_folder=os.path.join(os.path.dirname(__file__), "assets"),
        external_stylesheets=["https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"],
    )
    # A function layout is re-evaluated on each page load, so the table list stays
    # current and the dashboard can start before the API is up.
    app.layout = serve_layout
    _register_callbacks(app)
    return app


def table_options() -> list[dict]:
    tables = fetch("tables/") or []
    return [{"label": f"{table_label(t['table'])}  ({t['trips']:,} trips)", "value": t["table"]}
            for t in tables if t["loaded"]]


def serve_layout() -> html.Div:
    options = table_options()
    default = options[0]["value"] if options else None
    return html.Div(
        id="root",
        children=[
            dcc.Location(id="url", refresh=False),
            html.Div(
                id="topbar",
                className="topbar",
                children=[
                    html.Div([html.Span("NYC", className="brand-mark"),
                              html.Div([html.Strong("NYC Taxi"), html.Span("Revenue analytics · Plotly Dash")])],
                             className="brand"),
                    html.Div([html.Label("Dataset", htmlFor="table"),
                              dcc.Dropdown(id="table", options=options, value=default, clearable=False,
                                           placeholder="No tables loaded - run manage.py ingest_trips")],
                             className="filters"),
                ],
            ),
            html.Main(
                className="page",
                children=[
                    html.Header([html.H1("Revenue & operations"), html.P(id="page-subtitle")],
                                className="page-head"),
                    dcc.Loading(
                        type="dot",
                        color=f.SERIES[0],
                        children=html.Div([
                            html.Div(id="kpis", className="kpi-row"),
                            html.Section(
                                [html.Div([html.H3("Key findings"),
                                           html.P("Written from the data for this dataset.")],
                                          className="card-head"),
                                 html.Div(id="findings")],
                                className="card findings-card",
                            ),
                            *chart_rows(),
                            html.Section(
                                [html.Div([html.H3("Data quality report"),
                                           html.P("What each rule found in the latest load. Faded rules "
                                                  "found no problems.")], className="card-head"),
                                 html.Div(id="dq", className="table-wrap")],
                                className="card",
                            ),
                        ]),
                    ),
                ],
            ),
        ],
    )


def _register_callbacks(app: Dash) -> None:
    @app.callback(
        Output("table", "value"), Output("topbar", "style"), Output("root", "className"),
        Input("url", "search"),
        prevent_initial_call=False,
    )
    def apply_query(search):
        table, embed = parse_query(search)
        value = table if table else dash.no_update
        return value, {"display": "none"} if embed else {}, "embed" if embed else ""

    chart_outputs = []
    for chart in f.CHARTS:
        chart_outputs += [Output(chart.id, "figure"), Output(f"{chart.id}-subtitle", "children")]

    @app.callback(
        Output("kpis", "children"), Output("findings", "children"), Output("page-subtitle", "children"),
        Output("dq", "children"), *chart_outputs,
        Input("table", "value"),
    )
    def refresh(table):
        data = fetch(f"analytics/{table}/") if table else None
        if not data:
            empty = f.empty_figure("API unavailable or table not loaded")
            charts = [x for c in f.CHARTS for x in (empty, c.subtitle_for({}))]
            return ([], html.P("No data.", className="muted"), "No dataset loaded.",
                    html.P("No data.", className="muted"), *charts)
        dq = fetch(f"data-quality/{table}/")
        charts = [x for c in f.CHARTS for x in (c.build(data), c.subtitle_for(data))]
        subtitle = (f"{table_label(table)} · {data['kpis'].get('trips', 0):,} validated trips. "
                    "Revenue, demand and data quality at a glance.")
        return (build_kpis(data["kpis"], dq), build_findings(data.get("findings", [])), subtitle,
                quality_table(dq), *charts)


app = create_app()
server = app.server  # gunicorn entrypoint: dashboard.app:server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)), debug=False)
