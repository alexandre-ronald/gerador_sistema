"""GEN-070.8/070.9 e GEN-071.5 — projeção read-only das páginas avançadas no Preview Studio."""
from copy import deepcopy

from .advanced_pages import normalize_advanced_pages_config
from .builder_contracts import normalize_dashboard_config
from .form_designer import normalize_form_config
from .models import Entidade


CRUD_ACTIONS = ("list", "view", "create", "update", "delete")


def _draft_structure(sistema):
    version = sistema.versoes.filter(numero=0).first()
    return version.estrutura_json if version and isinstance(version.estrutura_json, dict) else {}


def _field_metadata(entity):
    return [
        {
            "name": field.nome,
            "label": field.verbose_name or field.nome.replace("_", " ").title(),
            "type": field.tipo,
            "help_text": field.help_text or "",
            "editable": True,
            "required": not bool(field.blank),
        }
        for field in entity.campos.all()
    ]


def _demo_value(field, row=1):
    field_type = str(field.get("type") or "CharField")
    label = str(field.get("label") or field.get("name") or "Valor")
    if field_type == "BooleanField": return "Sim" if row % 2 else "Não"
    if field_type == "DateField": return f"{row:02d}/09/2026"
    if field_type == "DateTimeField": return f"{row:02d}/09/2026 09:{row * 7:02d}"
    if field_type in {"IntegerField", "FloatField", "DecimalField"}: return str(row * 100)
    if field_type == "EmailField": return f"exemplo{row}@demo.local"
    if field_type in {"ForeignKey", "OneToOneField"}: return f"Referência {row:02d}"
    return f"{label} {row:02d}"


def _entity_permissions(role_simulation, entity_name):
    if role_simulation.get("invalid_role"):
        return {action: False for action in CRUD_ACTIONS}
    if not role_simulation.get("active"):
        return {action: True for action in CRUD_ACTIONS}
    role_id = role_simulation.get("selected_role_id")
    policy = (role_simulation.get("entities") or {}).get(entity_name) or {}
    allowed = set(((policy.get("roles") or {}).get(role_id)) or [])
    return {action: action in allowed for action in CRUD_ACTIONS}


def _report_allowed(structure, role_simulation, entity_name, report_id):
    if role_simulation.get("invalid_role"): return False
    if not role_simulation.get("active"): return True
    policies = ((structure.get("rbac") or {}).get("reports") or {}) if isinstance(structure.get("rbac"), dict) else {}
    roles = ((policies.get(entity_name) or {}).get(report_id)) if isinstance(policies, dict) else None
    return isinstance(roles, list) and role_simulation.get("selected_role_id") in roles


def _transition_allowed(role_simulation, entity_name, transition_id):
    if role_simulation.get("invalid_role"): return False
    if not role_simulation.get("active"): return True
    role_id = role_simulation.get("selected_role_id")
    policy = (role_simulation.get("entities") or {}).get(entity_name) or {}
    roles = (policy.get("transitions") or {}).get(transition_id)
    return isinstance(roles, list) and role_id in roles


def _workflow_transition(structure, entity_name, transition_id):
    workflows = structure.get("workflows") if isinstance(structure.get("workflows"), dict) else {}
    workflow = workflows.get(entity_name) if isinstance(workflows.get(entity_name), dict) else {}
    for item in workflow.get("transitions") or []:
        if isinstance(item, dict) and str(item.get("id") or "") == str(transition_id or ""):
            return item
    return None


def _page_context_allowed(role_simulation, page):
    context = (page or {}).get("context") or {}
    kind = context.get("kind")
    if kind == "none":
        return True
    permissions = _entity_permissions(role_simulation, context.get("entity"))
    if kind == "collection":
        return bool(permissions.get("list"))
    if kind == "record":
        return bool(permissions.get("view"))
    return False


def _action_projection(action, page, page_map, entities, structure, role_simulation):
    target = action.get("target") or {}
    kind = action.get("kind")
    allowed = True
    description = ""
    confirm = False
    confirm_message = ""
    if kind == "navigate":
        target_page = page_map.get(target.get("page"))
        allowed = bool(target_page and target_page.get("enabled") and _page_context_allowed(role_simulation, target_page))
        description = f"Abrir {target_page['name']}" if target_page else "Destino indisponível"
    elif kind == "crud":
        operation = target.get("operation")
        allowed = _entity_permissions(role_simulation, target.get("entity")).get(operation, False)
        description = f"{operation} · {target.get('entity')}"
    elif kind == "report":
        allowed = _report_allowed(structure, role_simulation, target.get("entity"), target.get("report"))
        description = f"Relatório {target.get('report')} · {target.get('entity')}"
    elif kind == "workflow":
        allowed = _transition_allowed(role_simulation, target.get("entity"), target.get("transition"))
        transition = _workflow_transition(structure, target.get("entity"), target.get("transition"))
        confirm = bool(transition and transition.get("confirm"))
        if confirm:
            confirm_message = str(transition.get("confirm_message") or "Confirme para continuar.")
        description = f"Transição {target.get('transition')} · {target.get('entity')}"

    projection = {**deepcopy(action), "allowed": bool(allowed), "description": description, "confirm": confirm, "confirm_message": confirm_message}
    transport = action.get("transport") if isinstance(action.get("transport"), dict) else None
    if kind == "crud" and target.get("operation") == "create" and transport:
        context_entity = str((page.get("context") or {}).get("entity") or "").strip()
        target_entity = str(target.get("entity") or "").strip()
        target_field = str(transport.get("target_field") or "").strip()
        projection["transport_projection"] = {
            "active": True,
            "source_entity": context_entity,
            "target_entity": target_entity,
            "target_field": target_field,
            "summary": f"{target_entity}.{target_field} ← {context_entity} atual",
        }
    else:
        projection["transport_projection"] = None
    return projection


def _component_projection(component, page, entities, structure, role_simulation, actions):
    projected = deepcopy(component)
    binding = component.get("binding") or {}
    entity_name = binding.get("ref") or (page.get("context") or {}).get("entity")
    entity = entities.get(entity_name)
    fields = _field_metadata(entity) if entity else []
    field_map = {field["name"]: field for field in fields}
    projected["demo_value"] = None
    projected["demo_rows"] = []
    projected["fields"] = fields
    projected["form_sections"] = []
    projected["special"] = {}
    projected["allowed"] = True
    projected["action_projection"] = actions.get(component.get("action")) if component.get("action") else None
    if projected["action_projection"] is not None:
        projected["allowed"] = projected["action_projection"]["allowed"]

    kind = binding.get("kind")
    if kind in {"entity", "crud"} and entity_name:
        projected["allowed"] = projected["allowed"] and _entity_permissions(role_simulation, entity_name).get("list" if component.get("type") == "table" else "view", False)
    elif kind in {"field", "page_context"} and entity_name:
        projected["allowed"] = projected["allowed"] and _entity_permissions(role_simulation, entity_name).get("view", False)
    elif kind == "form" and entity_name:
        permissions = _entity_permissions(role_simulation, entity_name)
        operation = "update" if (page.get("context") or {}).get("kind") == "record" and (page.get("context") or {}).get("entity") == entity_name else "create"
        projected["allowed"] = projected["allowed"] and permissions.get(operation, False)
        raw_forms = structure.get("forms") if isinstance(structure.get("forms"), dict) else {}
        config = normalize_form_config(entity_name, {"name": entity_name, "label": entity_name, "fields": fields}, raw_forms.get(entity_name)) if entity else None
        if config:
            projected["form_sections"] = [{"title": "Campos", "fields": [field for field in config.get("fields", []) if field.get("visible")]}]
        projected["special"] = {"operation": operation}
    elif kind == "report" and entity_name:
        report_id = str((component.get("config") or {}).get("report_id") or "")
        projected["allowed"] = projected["allowed"] and _report_allowed(structure, role_simulation, entity_name, report_id)
        projected["special"] = {"report_id": report_id}
    elif kind == "dashboard":
        dashboard = normalize_dashboard_config(structure.get("dashboard"))
        projected["special"] = {"enabled": bool(dashboard.get("enabled")), "title": dashboard.get("title"), "widget_count": len(dashboard.get("widgets") or [])}
    elif kind == "workflow" and entity_name:
        projected["allowed"] = projected["allowed"] and _entity_permissions(role_simulation, entity_name).get("view", False)

    if component.get("type") in {"metric", "field_summary"}:
        field = field_map.get(binding.get("field"))
        projected["demo_value"] = _demo_value(field or {"name": binding.get("field"), "label": component.get("title") or binding.get("field")}, 1)
    elif component.get("type") == "record_detail":
        projected["fields"] = [{**field, "demo_value": _demo_value(field, 1)} for field in fields]
    elif component.get("type") == "table":
        projected["demo_rows"] = [
            {"number": row, "values": [{"field": field["name"], "value": _demo_value(field, row)} for field in fields]}
            for row in range(1, 5)
        ]
    return projected


def build_advanced_page_preview(sistema, preview, selected_page_id=None):
    """Acrescenta ao Preview uma projeção read-only do contrato advanced_pages."""
    structure = _draft_structure(sistema)
    config = normalize_advanced_pages_config(structure.get("advanced_pages"), strict=False)
    pages = [page for page in config.get("pages", []) if page.get("enabled")]
    page_map = {page["id"]: page for page in pages}
    requested = str(selected_page_id or "").strip()
    selected = page_map.get(requested) if requested else (pages[0] if pages else None)
    entities = {
        entity.nome: entity
        for entity in Entidade.objects.filter(modulo__sistema=sistema).select_related("modulo").prefetch_related("campos")
    }
    role_simulation = preview.get("role_simulation") or {}

    navigation = []
    for page in pages:
        nav = page.get("navigation") or {}
        if not nav.get("visible") or (page.get("context") or {}).get("kind") == "record":
            continue
        if _page_context_allowed(role_simulation, page):
            navigation.append({"id": page["id"], "label": nav.get("label") or page["name"], "icon": nav.get("icon") or "bi-window", "group": nav.get("group") or "Páginas", "order": nav.get("order", 0), "active": bool(selected and page["id"] == selected["id"])})
    navigation.sort(key=lambda item: (item["group"].casefold(), item["order"], item["label"].casefold()))

    projection = None
    if selected:
        page_allowed = _page_context_allowed(role_simulation, selected)
        actions = {action["id"]: _action_projection(action, selected, page_map, entities, structure, role_simulation) for action in selected.get("actions", [])}
        components = [_component_projection(component, selected, entities, structure, role_simulation, actions) for component in selected.get("components", [])]
        projection = {**deepcopy(selected), "allowed": page_allowed, "actions_projection": actions, "components_projection": components}

    preview["advanced_pages"] = navigation
    preview["advanced_page"] = projection
    if projection:
        preview["page_kind"] = "advanced"
        preview["content"] = {
            "title": projection["name"],
            "subtitle": "Página composta no Advanced Page Designer; dados exibidos são demonstrativos e somente leitura.",
        }
    return preview
