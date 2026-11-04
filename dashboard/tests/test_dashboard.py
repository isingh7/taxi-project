from unittest import mock

import pytest

from dashboard import app as dash_app
from dashboard import figures as f

DAILY = [
    {"date": "2015-01-01", "revenue": 100.0, "rolling_mean": 100.0, "drawdown_pct": 0.0, "is_anomaly": False, "pct_change": None},
    {"date": "2015-01-02", "revenue": 500.0, "rolling_mean": 300.0, "drawdown_pct": 0.0, "is_anomaly": True, "pct_change": 400.0},
]
HOURLY = [{"hour": h, "trips": 10 + h, "share_pct": 4.0, "avg_fare": 12.0} for h in range(24)]


def test_daily_revenue_has_single_axis_and_labelled_anomaly():
    fig = f.daily_revenue_figure(DAILY)
    names = [t.name for t in fig.data]
    assert names == ["Daily revenue", "7-day average", "Anomaly (>3σ)"]
    assert fig.data[2].marker.color == f.CRITICAL
    assert "anomaly" in fig.data[2].text[0]          # never colour alone
    assert "yaxis2" not in fig.layout.to_plotly_json()  # no dual axis


def test_hourly_marks_peak():
    fig = f.hourly_figure(HOURLY)
    assert fig.layout.annotations[0].text == "Peak 23:00"


def test_ranked_bars_sorted_largest_on_top():
    rows = [{"b": "A", "v": 5}, {"b": "B", "v": 50}, {"b": "C", "v": 20}]
    fig = f.ranked_bar_figure(rows, "b", "v", "t", prefix="$")
    assert list(fig.data[0].y) == ["A", "C", "B"]
    assert fig.data[0].text[-1] == "$50"


def test_histogram_title_states_clipping():
    fig = f.fare_histogram_figure({"edges": [0, 10, 20], "counts": [3, 4], "clipped_above": 90.0})
    assert "$90" in fig.layout.title.text and len(fig.data[0].x) == 2


@pytest.mark.parametrize("builder", [f.daily_revenue_figure, f.drawdown_figure, f.hourly_figure])
def test_empty_inputs_render_message(builder):
    assert builder([]).layout.annotations[0].text.startswith("No")


def test_kpis_handle_missing_quality_report():
    tiles = dash_app.build_kpis({"trips": 10, "gross_revenue": 99.5, "median_fare": 9.0}, None)
    assert len(tiles) == 5
    assert tiles[0].children[1].children == "$99.50"


def test_create_app_and_callback_with_api_down():
    with mock.patch.object(dash_app, "fetch", return_value=None):
        app = dash_app.create_app()
        layout = dash_app.serve_layout()
        assert layout is not None
        callback = next(v["callback"] for k, v in app.callback_map.items() if "kpis.children" in k)
        outputs = callback.__wrapped__(None)
        assert outputs[0] == []


def test_layout_lists_only_loaded_tables():
    tables = [{"table": "a", "trips": 10, "loaded": True}, {"table": "b", "trips": 0, "loaded": False}]
    with mock.patch.object(dash_app, "fetch", return_value=tables):
        assert [o["value"] for o in dash_app.table_options()] == ["a"]


@pytest.mark.parametrize(
    "search, expected",
    [
        ("?table=tlc_yellow_trips_2015&embed=1", ("tlc_yellow_trips_2015", True)),
        ("?table=tlc_green_trips_2014", ("tlc_green_trips_2014", False)),
        ("", (None, False)),
        (None, (None, False)),
    ],
)
def test_parse_query(search, expected):
    assert dash_app.parse_query(search) == expected


def test_every_graph_has_a_fixed_container_height():
    # Regression: graphs without a fixed height grew taller on every resize/scroll.
    for graph_id in dash_app.GRAPH_HEIGHTS:
        g = dash_app.graph(graph_id).children
        assert g.style["height"].endswith("px") and g.responsive is True


def test_figures_do_not_set_their_own_height():
    fig = f.hourly_figure(HOURLY)
    assert fig.layout.height is None and fig.layout.autosize is True
