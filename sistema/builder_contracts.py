from copy import deepcopy


WIDGET_TYPES = {
    "metric",
    "table",
    "bar",
    "line",
    "area",
    "pie",
    "donut",
}

REFRESH_INTERVALS = {0, 15, 30, 60, 300}
GRID_COLUMNS = 12
DEFAULT_WIDGET_WIDTH = 4
DEFAULT_WIDGET_HEIGHT = 3


def _integer(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def normalize_dashboard_config(value=None):
    """Normalize the Dashboard Builder configuration used by GEN-036."""
    source = deepcopy(value) if isinstance(value, dict) else {}
    widgets = source.get("widgets")
    widgets = widgets if isinstance(widgets, list) else []

    normalized_widgets = []
    for raw_widget in widgets:
        widget = deepcopy(raw_widget) if isinstance(raw_widget, dict) else {}

        widget_type = widget.get("type")
        widget["type"] = widget_type if widget_type in WIDGET_TYPES else "metric"

        if not widget.get("title"):
            widget["title"] = "Indicador" if widget["type"] == "metric" else "Novo gráfico"

        entity = widget.get("entity")
        widget["entity"] = entity if isinstance(entity, str) else ""

        widget["x"] = max(0, min(GRID_COLUMNS - 1, _integer(widget.get("x"), 0)))
        widget["y"] = max(0, _integer(widget.get("y"), 0))
        widget["w"] = max(1, min(GRID_COLUMNS, _integer(widget.get("w"), DEFAULT_WIDGET_WIDTH)))
        widget["h"] = max(1, _integer(widget.get("h"), DEFAULT_WIDGET_HEIGHT))

        if widget["x"] + widget["w"] > GRID_COLUMNS:
            widget["x"] = GRID_COLUMNS - widget["w"]

        widget["config"] = widget.get("config") if isinstance(widget.get("config"), dict) else {}
        normalized_widgets.append(widget)

    refresh = _integer(source.get("refresh_seconds"), 0)
    if refresh not in REFRESH_INTERVALS:
        refresh = 0

    return {
        "title": source.get("title") or "Dashboard",
        "refresh_seconds": refresh,
        "layout": source.get("layout") or "12-column",
        "widgets": normalized_widgets,
    }
