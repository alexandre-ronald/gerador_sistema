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
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return number


def _overlaps(a, b):
    return not (
        a["x"] + a["w"] <= b["x"]
        or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"]
        or b["y"] + b["h"] <= a["y"]
    )


def _can_place(widget, x, y, placed):
    if x < 0 or y < 0 or x + widget["w"] > GRID_COLUMNS:
        return False

    candidate = {
        "x": x,
        "y": y,
        "w": widget["w"],
        "h": widget["h"],
    }
    return not any(_overlaps(candidate, other) for other in placed)


def _pack_widgets(widgets):
    """Normalize and pack widgets into a collision-free 12-column grid."""
    placed = []

    for widget in widgets:
        widget["x"] = max(0, min(GRID_COLUMNS - 1, _integer(widget.get("x"), 0)))
        widget["y"] = max(0, _integer(widget.get("y"), 0))
        widget["w"] = max(1, min(GRID_COLUMNS, _integer(widget.get("w"), DEFAULT_WIDGET_WIDTH)))
        widget["h"] = max(1, _integer(widget.get("h"), DEFAULT_WIDGET_HEIGHT))

        if widget["x"] + widget["w"] > GRID_COLUMNS:
            widget["x"] = GRID_COLUMNS - widget["w"]

        if not _can_place(widget, widget["x"], widget["y"], placed):
            found = False
            max_y = sum(item["h"] for item in widgets) + len(widgets) + widget["h"]
            for y in range(max(1, max_y)):
                for x in range(GRID_COLUMNS - widget["w"] + 1):
                    if _can_place(widget, x, y, placed):
                        widget["x"] = x
                        widget["y"] = y
                        found = True
                        break
                if found:
                    break

            if not found:
                raise ValueError("Não foi possível posicionar o widget no grid de 12 colunas")

        placed.append({
            "x": widget["x"],
            "y": widget["y"],
            "w": widget["w"],
            "h": widget["h"],
        })


def normalize_dashboard_config(value=None):
    """Return the canonical, persisted Dashboard Builder configuration."""
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

        widget["config"] = widget.get("config") if isinstance(widget.get("config"), dict) else {}
        normalized_widgets.append(widget)

    _pack_widgets(normalized_widgets)

    refresh = _integer(source.get("refresh_seconds"), 0)
    if refresh not in REFRESH_INTERVALS:
        refresh = 0

    return {
        "title": source.get("title") or "Dashboard",
        "refresh_seconds": refresh,
        "layout": source.get("layout") or "12-column",
        "widgets": normalized_widgets,
    }
