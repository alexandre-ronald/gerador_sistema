"""Contrato canônico da GEN-070 — Advanced Page Designer.

O módulo é deliberadamente independente de Django: Designer, Preview e gerador/runtime
podem consumir a mesma normalização sem criar uma segunda fonte de verdade.
"""
from copy import deepcopy


CONTRACT_VERSION = 1
UNSAFE_TOKENS = ("__", "\\", "..")
CONTEXT_KINDS = ("none", "record", "collection")
COMPONENT_TYPES = (
    "title",
    "text",
    "separator",
    "alert",
    "metric",
    "table",
    "record_detail",
    "field_summary",
    "report",
    "dashboard",
    "button",
    "link",
    "form",
    "workflow_action",
)
BINDING_KINDS = (
    "none",
    "page_context",
    "entity",
    "field",
    "crud",
    "form",
    "dashboard",
    "report",
    "workflow",
)
ACTION_KINDS = ("navigate", "crud", "workflow", "report")
CRUD_ACTIONS = ("list", "view", "create", "update", "delete")


class AdvancedPageContractError(ValueError):
    def __init__(self, code, message, *, page_id=None, component_id=None, action_id=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.page_id = page_id
        self.component_id = component_id
        self.action_id = action_id

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.page_id:
            data["page_id"] = self.page_id
        if self.component_id:
            data["component_id"] = self.component_id
        if self.action_id:
            data["action_id"] = self.action_id
        return data


def default_advanced_pages_config():
    return {"version": CONTRACT_VERSION, "pages": []}


def _safe_id(value, *, code, page_id=None, component_id=None, action_id=None):
    value = str(value or "").strip()
    if not value or any(token in value for token in UNSAFE_TOKENS) or "/" in value:
        raise AdvancedPageContractError(
            code,
            "Identificador inválido ou inseguro.",
            page_id=page_id,
            component_id=component_id,
            action_id=action_id,
        )
    return value


def _label(value, *, code, page_id=None):
    value = str(value or "").strip()
    if not value:
        raise AdvancedPageContractError(code, "Nome obrigatório.", page_id=page_id)
    return value


def _bool(value, *, code, page_id=None):
    if not isinstance(value, bool):
        raise AdvancedPageContractError(code, "Valor booleano inválido.", page_id=page_id)
    return value


def _int(value, *, code, minimum, maximum=None, page_id=None, component_id=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise AdvancedPageContractError(code, "Valor inteiro inválido.", page_id=page_id, component_id=component_id)
    if value < minimum or (maximum is not None and value > maximum):
        raise AdvancedPageContractError(code, "Valor fora do intervalo permitido.", page_id=page_id, component_id=component_id)
    return value


def _normalize_context(raw, *, page_id):
    raw = raw if isinstance(raw, dict) else {}
    kind = str(raw.get("kind") or "none").strip()
    if kind not in CONTEXT_KINDS:
        raise AdvancedPageContractError("unknown_context_kind", "Tipo de contexto desconhecido.", page_id=page_id)
    entity = str(raw.get("entity") or "").strip()
    if kind in ("record", "collection") and not entity:
        raise AdvancedPageContractError("context_entity_required", "Contexto de registro/coleção exige entidade.", page_id=page_id)
    if kind == "none":
        entity = ""
    return {"kind": kind, "entity": entity}


def _normalize_navigation(raw, *, page_id):
    raw = raw if isinstance(raw, dict) else {}
    return {
        "visible": _bool(raw.get("visible", True), code="invalid_navigation_visible", page_id=page_id),
        "label": str(raw.get("label") or "").strip(),
        "icon": str(raw.get("icon") or "").strip(),
        "group": str(raw.get("group") or "").strip(),
        "order": _int(raw.get("order", 0), code="invalid_navigation_order", minimum=-10000, maximum=10000, page_id=page_id),
    }


def _normalize_binding(raw, *, page_id, component_id):
    raw = raw if isinstance(raw, dict) else {}
    kind = str(raw.get("kind") or "none").strip()
    if kind not in BINDING_KINDS:
        raise AdvancedPageContractError("unknown_binding_kind", "Tipo de binding desconhecido.", page_id=page_id, component_id=component_id)
    ref = str(raw.get("ref") or "").strip()
    field = str(raw.get("field") or "").strip()
    if kind not in ("none", "page_context") and not ref:
        raise AdvancedPageContractError("binding_reference_required", "Binding exige referência explícita.", page_id=page_id, component_id=component_id)
    if kind == "field" and not field:
        raise AdvancedPageContractError("binding_field_required", "Binding de campo exige field.", page_id=page_id, component_id=component_id)
    if kind in ("none", "page_context"):
        ref = ""
    if kind != "field":
        field = ""
    return {"kind": kind, "ref": ref, "field": field}


def _normalize_layout(raw, *, page_id, component_id):
    raw = raw if isinstance(raw, dict) else {}
    x = _int(raw.get("x", 0), code="invalid_layout_x", minimum=0, maximum=11, page_id=page_id, component_id=component_id)
    y = _int(raw.get("y", 0), code="invalid_layout_y", minimum=0, page_id=page_id, component_id=component_id)
    w = _int(raw.get("w", 12), code="invalid_layout_w", minimum=1, maximum=12, page_id=page_id, component_id=component_id)
    h = _int(raw.get("h", 1), code="invalid_layout_h", minimum=1, maximum=100, page_id=page_id, component_id=component_id)
    if x + w > 12:
        raise AdvancedPageContractError("layout_overflow", "Componente ultrapassa a grade de 12 colunas.", page_id=page_id, component_id=component_id)
    return {"x": x, "y": y, "w": w, "h": h}


def _normalize_component(raw, *, page_id):
    if not isinstance(raw, dict):
        raise AdvancedPageContractError("invalid_component", "Componente deve ser um objeto.", page_id=page_id)
    component_id = _safe_id(raw.get("id"), code="invalid_component_id", page_id=page_id)
    kind = str(raw.get("type") or "").strip()
    if kind not in COMPONENT_TYPES:
        raise AdvancedPageContractError("unknown_component_type", "Tipo de componente desconhecido.", page_id=page_id, component_id=component_id)
    config = raw.get("config") if isinstance(raw.get("config"), dict) else {}
    return {
        "id": component_id,
        "type": kind,
        "title": str(raw.get("title") or "").strip(),
        "layout": _normalize_layout(raw.get("layout"), page_id=page_id, component_id=component_id),
        "binding": _normalize_binding(raw.get("binding"), page_id=page_id, component_id=component_id),
        "action": str(raw.get("action") or "").strip(),
        "config": deepcopy(config),
    }


def _normalize_action(raw, *, page_id):
    if not isinstance(raw, dict):
        raise AdvancedPageContractError("invalid_action", "Ação deve ser um objeto.", page_id=page_id)
    action_id = _safe_id(raw.get("id"), code="invalid_action_id", page_id=page_id)
    kind = str(raw.get("kind") or "").strip()
    if kind not in ACTION_KINDS:
        raise AdvancedPageContractError("unknown_action_kind", "Tipo de ação desconhecido.", page_id=page_id, action_id=action_id)
    target = raw.get("target") if isinstance(raw.get("target"), dict) else {}
    normalized_target = {str(key): deepcopy(value) for key, value in target.items() if str(key).strip()}
    if kind == "navigate" and not str(normalized_target.get("page") or "").strip():
        raise AdvancedPageContractError("action_page_required", "Ação de navegação exige target.page.", page_id=page_id, action_id=action_id)
    if kind == "crud":
        entity = str(normalized_target.get("entity") or "").strip()
        operation = str(normalized_target.get("operation") or "").strip()
        if not entity or operation not in CRUD_ACTIONS:
            raise AdvancedPageContractError("invalid_crud_action_target", "Ação CRUD exige entidade e operação válida.", page_id=page_id, action_id=action_id)
        normalized_target = {"entity": entity, "operation": operation}
    if kind == "workflow":
        entity = str(normalized_target.get("entity") or "").strip()
        transition = str(normalized_target.get("transition") or "").strip()
        if not entity or not transition:
            raise AdvancedPageContractError("invalid_workflow_action_target", "Ação de workflow exige entidade e transição.", page_id=page_id, action_id=action_id)
        normalized_target = {"entity": entity, "transition": transition}
    if kind == "report":
        entity = str(normalized_target.get("entity") or "").strip()
        report = str(normalized_target.get("report") or "").strip()
        if not entity or not report:
            raise AdvancedPageContractError("invalid_report_action_target", "Ação de relatório exige entidade e relatório.", page_id=page_id, action_id=action_id)
        normalized_target = {"entity": entity, "report": report}
    return {
        "id": action_id,
        "kind": kind,
        "label": str(raw.get("label") or "").strip(),
        "target": normalized_target,
    }


def _check_layout_collisions(components, *, page_id):
    occupied = set()
    for component in components:
        layout = component["layout"]
        for row in range(layout["y"], layout["y"] + layout["h"]):
            for col in range(layout["x"], layout["x"] + layout["w"]):
                cell = (row, col)
                if cell in occupied:
                    raise AdvancedPageContractError("layout_collision", "Componentes não podem ocupar a mesma célula da grade.", page_id=page_id, component_id=component["id"])
                occupied.add(cell)


def _normalize_page(raw):
    if not isinstance(raw, dict):
        raise AdvancedPageContractError("invalid_page", "Página deve ser um objeto.")
    page_id = _safe_id(raw.get("id"), code="invalid_page_id")
    name = _label(raw.get("name"), code="empty_page_name", page_id=page_id)
    slug = str(raw.get("slug") or "").strip().strip("/")
    if not slug or any(token in slug for token in UNSAFE_TOKENS) or " " in slug:
        raise AdvancedPageContractError("invalid_page_slug", "Slug da página é inválido.", page_id=page_id)

    raw_components = raw.get("components", [])
    raw_actions = raw.get("actions", [])
    if not isinstance(raw_components, list):
        raise AdvancedPageContractError("invalid_components", "Componentes devem ser uma lista.", page_id=page_id)
    if not isinstance(raw_actions, list):
        raise AdvancedPageContractError("invalid_actions", "Ações devem ser uma lista.", page_id=page_id)

    components = []
    component_ids = set()
    for item in raw_components:
        component = _normalize_component(item, page_id=page_id)
        if component["id"] in component_ids:
            raise AdvancedPageContractError("duplicate_component_id", "ID de componente duplicado.", page_id=page_id, component_id=component["id"])
        component_ids.add(component["id"])
        components.append(component)

    actions = []
    action_ids = set()
    for item in raw_actions:
        action = _normalize_action(item, page_id=page_id)
        if action["id"] in action_ids:
            raise AdvancedPageContractError("duplicate_action_id", "ID de ação duplicado.", page_id=page_id, action_id=action["id"])
        action_ids.add(action["id"])
        actions.append(action)

    for component in components:
        if component["action"] and component["action"] not in action_ids:
            raise AdvancedPageContractError("unknown_component_action", "Componente referencia ação inexistente.", page_id=page_id, component_id=component["id"])
    _check_layout_collisions(components, page_id=page_id)

    return {
        "id": page_id,
        "name": name,
        "slug": slug,
        "enabled": _bool(raw.get("enabled", True), code="invalid_page_enabled", page_id=page_id),
        "context": _normalize_context(raw.get("context"), page_id=page_id),
        "navigation": _normalize_navigation(raw.get("navigation"), page_id=page_id),
        "components": components,
        "actions": actions,
    }


def normalize_advanced_pages_config(raw_config=None, *, strict=True):
    """Normaliza o contrato persistido em ``estrutura_json['advanced_pages']``.

    Em modo estrito, qualquer configuração inválida falha fechada. O modo tolerante é
    destinado a telas de Designer/inspeção e descarta páginas inválidas sem promovê-las
    a uma configuração executável.
    """
    if raw_config is None:
        raw_config = default_advanced_pages_config()
    if not isinstance(raw_config, dict):
        if strict:
            raise AdvancedPageContractError("invalid_advanced_pages_config", "Configuração de páginas avançadas deve ser um objeto.")
        return default_advanced_pages_config()

    version = raw_config.get("version", CONTRACT_VERSION)
    if version != CONTRACT_VERSION:
        if strict:
            raise AdvancedPageContractError("unsupported_contract_version", "Versão do contrato de páginas avançadas não suportada.")
        version = CONTRACT_VERSION

    raw_pages = raw_config.get("pages", [])
    if not isinstance(raw_pages, list):
        if strict:
            raise AdvancedPageContractError("invalid_pages", "Pages deve ser uma lista.")
        raw_pages = []

    pages = []
    page_ids = set()
    slugs = set()
    for item in raw_pages:
        try:
            page = _normalize_page(item)
            if page["id"] in page_ids:
                raise AdvancedPageContractError("duplicate_page_id", "ID de página duplicado.", page_id=page["id"])
            if page["slug"] in slugs:
                raise AdvancedPageContractError("duplicate_page_slug", "Slug de página duplicado.", page_id=page["id"])
            page_ids.add(page["id"])
            slugs.add(page["slug"])
            pages.append(page)
        except AdvancedPageContractError:
            if strict:
                raise

    known_pages = {page["id"] for page in pages}
    for page in pages:
        for action in page["actions"]:
            if action["kind"] == "navigate" and str(action["target"].get("page") or "").strip() not in known_pages:
                if strict:
                    raise AdvancedPageContractError("unknown_navigation_page", "Ação referencia página avançada inexistente.", page_id=page["id"], action_id=action["id"])

    return {"version": CONTRACT_VERSION, "pages": pages}


def page_map(config):
    return {page["id"]: deepcopy(page) for page in (config or {}).get("pages", []) if isinstance(page, dict) and page.get("id")}
