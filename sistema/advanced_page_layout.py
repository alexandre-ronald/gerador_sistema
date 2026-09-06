"""Layout Engine da GEN-070.3 para a grade canônica de 12 colunas."""
from copy import deepcopy

GRID_COLUMNS = 12


def collides(a, b):
    return not (
        a["x"] + a["w"] <= b["x"]
        or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"]
        or b["y"] + b["h"] <= a["y"]
    )


def first_available_layout(components, *, w=12, h=1, preferred_x=0, preferred_y=0, ignore_id=None):
    """Encontra a primeira posição livre, varrendo linha/coluna de forma determinística."""
    w = max(1, min(GRID_COLUMNS, int(w)))
    h = max(1, min(100, int(h)))
    preferred_x = max(0, min(GRID_COLUMNS - w, int(preferred_x)))
    preferred_y = max(0, int(preferred_y))
    occupied = [c for c in components if c.get("id") != ignore_id]
    y = preferred_y
    while True:
        starts = list(range(preferred_x, GRID_COLUMNS - w + 1))
        if preferred_x:
            starts += list(range(0, preferred_x))
        for x in starts:
            candidate = {"x": x, "y": y, "w": w, "h": h}
            if not any(collides(candidate, c["layout"]) for c in occupied):
                return candidate
        y += 1


def place_component(components, component, *, preferred_x=None, preferred_y=None):
    """Posiciona/reposiciona um componente sem permitir sobreposição silenciosa."""
    result = deepcopy(component)
    layout = result.get("layout") or {}
    result["layout"] = first_available_layout(
        components,
        w=layout.get("w", 12),
        h=layout.get("h", 1),
        preferred_x=layout.get("x", 0) if preferred_x is None else preferred_x,
        preferred_y=layout.get("y", 0) if preferred_y is None else preferred_y,
        ignore_id=result.get("id"),
    )
    return result


def resize_component(components, component_id, *, w, h=None):
    """Redimensiona e, se necessário, move o componente para a primeira posição válida."""
    current = next(c for c in components if c.get("id") == component_id)
    updated = deepcopy(current)
    updated["layout"]["w"] = max(1, min(GRID_COLUMNS, int(w)))
    if h is not None:
        updated["layout"]["h"] = max(1, min(100, int(h)))
    return place_component(
        components,
        updated,
        preferred_x=updated["layout"]["x"],
        preferred_y=updated["layout"]["y"],
    )
