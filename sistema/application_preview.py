"""Application Preview Studio — projeções visuais somente-leitura."""

from django.db.models import Prefetch

from .builder_contracts import normalize_dashboard_config
from .crud_designer import normalize_crud_config
from .form_designer import normalize_form_config
from .models import Entidade, Modulo
from .report_designer_views import _normalize_report_collection


FIELD_KIND_LABELS = {
    "text": "Texto",
    "select": "Seleção",
    "boolean": "Sim/Não",
    "date": "Data",
    "relation": "Relacionamento",
}

FORM_WIDGET_LABELS = {
    "text": "Texto",
    "textarea": "Texto longo",
    "number": "Número",
    "date": "Data",
    "datetime": "Data e hora",
    "checkbox": "Sim/Não",
    "select": "Seleção",
}

DASHBOARD_WIDGET_LABELS = {
    "metric": "Indicador",
    "table": "Tabela",
    "bar": "Barras",
    "line": "Linha",
    "area": "Área",
    "pie": "Pizza",
    "donut": "Rosca",
}

DASHBOARD_WIDGET_ICONS = {
    "metric": "bi-123",
    "table": "bi-table",
    "bar": "bi-bar-chart",
    "line": "bi-graph-up",
    "area": "bi-graph-up-arrow",
    "pie": "bi-pie-chart",
    "donut": "bi-circle-half",
}

REPORT_FILTER_LABELS = {
    "contains": "Contém",
    "exact": "Igual a",
    "startswith": "Começa com",
    "gte": "A partir de",
    "lte": "Até",
    "range": "Intervalo",
}


def _field_metadata(field):
    return {
        "name": field.nome,
        "label": field.verbose_name or field.nome.replace("_", " ").title(),
        "type": field.tipo,
        "help_text": field.help_text or "",
        "editable": True,
        "required": not bool(field.blank),
    }


def _entity_metadata(entity):
    return {
        "name": entity.nome,
        "label": entity.nome,
        "fields": [_field_metadata(field) for field in entity.campos.all()],
    }


def _draft_contracts(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if not versao or not isinstance(versao.estrutura_json, dict):
        return {}, {}, normalize_dashboard_config(), {}
    estrutura = versao.estrutura_json
    cruds = estrutura.get("cruds")
    forms = estrutura.get("forms")
    reports = estrutura.get("reports")
    return (
        cruds if isinstance(cruds, dict) else {},
        forms if isinstance(forms, dict) else {},
        normalize_dashboard_config(estrutura.get("dashboard")),
        reports if isinstance(reports, dict) else {},
    )


def _demo_value(metadata, row_number):
    """Gera conteúdo demonstrativo determinístico; nunca consulta dados da aplicação final."""
    field_type = str(metadata.get("type") or "CharField")
    label = str(metadata.get("label") or metadata.get("name") or "Valor")

    if field_type == "BooleanField":
        return "Sim" if row_number % 2 else "Não"
    if field_type == "DateField":
        return f"{row_number:02d}/09/2026"
    if field_type == "DateTimeField":
        return f"{row_number:02d}/09/2026 09:{row_number * 7:02d}"
    if field_type == "TimeField":
        return f"09:{row_number * 7:02d}"
    if field_type in {"IntegerField", "FloatField", "DecimalField"}:
        return str(row_number * 100)
    if field_type == "EmailField":
        return f"exemplo{row_number}@demo.local"
    if field_type == "URLField":
        return f"https://exemplo{row_number}.local"
    if field_type in {"ForeignKey", "OneToOneField"}:
        return f"Referência {row_number:02d}"
    return f"{label} {row_number:02d}"


def _list_projection(entity, stored_cruds):
    metadata = _entity_metadata(entity)
    config = normalize_crud_config(entity.nome, metadata, stored_cruds.get(entity.nome))
    metadata_by_name = {item["name"]: item for item in metadata["fields"]}
    columns = [item for item in config["columns"] if item["visible"]]

    rows = []
    for row_number in range(1, 5):
        values = []
        for column in columns:
            field_metadata = metadata_by_name.get(
                column["field"],
                {"name": column["field"], "label": column["label"], "type": "CharField"},
            )
            values.append({"field": column["field"], "value": _demo_value(field_metadata, row_number)})
        rows.append({"number": row_number, "values": values})

    filters = [
        {**item, "kind_label": FIELD_KIND_LABELS.get(item["type"], "Filtro")}
        for item in config["filters"]
    ]

    return {
        "entity_id": entity.pk,
        "entity": entity.nome,
        "area": entity.modulo.nome,
        "title": config["title"],
        "page_size": config["page_size"],
        "default_order": config["default_order"],
        "columns": columns,
        "search": config["search"],
        "filters": filters,
        "actions": config["actions"],
        "rows": rows,
        "demo_count": len(rows),
    }


def _form_projection(entity, stored_forms):
    metadata = _entity_metadata(entity)
    config = normalize_form_config(entity.nome, metadata, stored_forms.get(entity.nome))
    metadata_by_name = {item["name"]: item for item in metadata["fields"]}
    visible_fields = []
    for field in config["fields"]:
        if not field["visible"]:
            continue
        field_metadata = metadata_by_name.get(field["name"], {})
        visible_fields.append(
            {
                **field,
                "required": bool(field_metadata.get("required")),
                "widget_label": FORM_WIDGET_LABELS.get(field["widget"], "Campo"),
            }
        )

    sections = []
    section_map = {}
    for section in config["sections"]:
        projected = {**section, "fields": []}
        sections.append(projected)
        section_map[section["id"]] = projected

    general_fields = []
    for field in visible_fields:
        if field["section"] and field["section"] in section_map:
            section_map[field["section"]]["fields"].append(field)
        else:
            general_fields.append(field)

    blocks = []
    if general_fields:
        blocks.append({"id": "__general__", "title": "Informações gerais", "description": "", "fields": general_fields})
    blocks.extend(section for section in sections if section["fields"])

    return {
        "entity_id": entity.pk,
        "entity": entity.nome,
        "area": entity.modulo.nome,
        "title": config["title"],
        "sections": blocks,
        "visible_fields": visible_fields,
        "visible_count": len(visible_fields),
    }


def _dashboard_projection(config):
    widgets = []
    for index, widget in enumerate(config["widgets"]):
        demo_values = [28 + index * 7, 42 + index * 6, 35 + index * 5, 58 + index * 4, 49 + index * 3]
        widgets.append(
            {
                **widget,
                "kind_label": DASHBOARD_WIDGET_LABELS.get(widget["type"], "Widget"),
                "icon": DASHBOARD_WIDGET_ICONS.get(widget["type"], "bi-grid"),
                "demo_metric": str(120 + index * 37),
                "demo_values": demo_values,
                "appearance": widget["config"].get("appearance", {}),
            }
        )
    return {
        "enabled": bool(config["enabled"]),
        "title": config["title"],
        "layout": config["layout"],
        "refresh_seconds": config["refresh_seconds"],
        "widgets": widgets,
        "widget_count": len(widgets),
    }


def _reports_projection(entity, stored_reports):
    metadata = _entity_metadata(entity)
    field_map = {field["name"]: field for field in metadata["fields"]}
    normalized = _normalize_report_collection(
        entity.nome,
        metadata,
        stored_reports.get(entity.nome),
        strict=False,
    )
    reports = []
    for report in normalized:
        if not report["enabled"]:
            continue
        fields = [
            {"name": name, "label": field_map.get(name, {}).get("label", name)}
            for name in report["fields"]
        ]
        filters = [
            {
                **item,
                "label": field_map.get(item["field"], {}).get("label", item["field"]),
                "type_label": REPORT_FILTER_LABELS.get(item["type"], item["type"]),
            }
            for item in report["filters"]
        ]
        rows = []
        for row_number in range(1, 5):
            rows.append(
                {
                    "number": row_number,
                    "values": [
                        _demo_value(field_map.get(field["name"], field), row_number)
                        for field in fields
                    ],
                }
            )
        reports.append(
            {
                **report,
                "entity_id": entity.pk,
                "entity": entity.nome,
                "area": entity.modulo.nome,
                "fields_meta": fields,
                "filters_meta": filters,
                "rows": rows,
            }
        )
    reports.sort(key=lambda item: (item["title"].lower(), item["id"]))
    return reports


def build_preview_shell(sistema, selected_entity_id=None, page_kind="list", selected_report_id=None):
    """Projeta shell e página selecionada sem persistir configuração própria."""
    entity_queryset = Entidade.objects.prefetch_related("campos").order_by("nome", "id")
    modules = list(
        Modulo.objects.filter(sistema=sistema)
        .prefetch_related(Prefetch("entidades", queryset=entity_queryset))
        .order_by("nome", "id")
    )

    available_entities = []
    navigation = []
    for module in modules:
        items = []
        for entity in module.entidades.all():
            if not entity.gerar_crud_views:
                continue
            available_entities.append(entity)
            items.append(
                {
                    "id": entity.pk,
                    "name": entity.nome,
                    "label": entity.nome_plural or entity.nome,
                    "icon": "bi-table",
                    "active": False,
                }
            )
        if items:
            navigation.append({"id": module.pk, "name": module.nome, "label": module.nome, "items": items})

    selected_entity = None
    if selected_entity_id is not None:
        try:
            selected_id = int(selected_entity_id)
        except (TypeError, ValueError):
            selected_id = None
        selected_entity = next((entity for entity in available_entities if entity.pk == selected_id), None)
    if selected_entity is None and available_entities:
        selected_entity = available_entities[0]

    valid_page_kinds = {"list", "form", "dashboard", "report"}
    page_kind = page_kind if page_kind in valid_page_kinds else "list"

    if selected_entity is not None and page_kind not in {"dashboard"}:
        for module in navigation:
            for item in module["items"]:
                item["active"] = item["id"] == selected_entity.pk

    stored_cruds, stored_forms, stored_dashboard, stored_reports = _draft_contracts(sistema)
    dashboard_page = _dashboard_projection(stored_dashboard)
    list_page = _list_projection(selected_entity, stored_cruds) if selected_entity else None
    form_page = _form_projection(selected_entity, stored_forms) if selected_entity and page_kind == "form" else None
    reports = _reports_projection(selected_entity, stored_reports) if selected_entity else []
    report_page = None
    if page_kind == "report" and reports:
        report_page = next((item for item in reports if item["id"] == selected_report_id), reports[0])

    if page_kind == "dashboard":
        content_title = dashboard_page["title"]
        content_subtitle = "Painel projetado pelo Dashboard Designer com dados demonstrativos."
    elif report_page:
        content_title = report_page["title"]
        content_subtitle = f"Relatório de {report_page['entity']} projetado pelo Report Designer."
    elif form_page:
        content_title = form_page["title"]
        content_subtitle = f"Formulário de {form_page['entity']} projetado pelo Form Designer."
    elif list_page:
        content_title = list_page["title"]
        content_subtitle = f"Consulta de {list_page['entity']} projetada pelo CRUD Designer."
    else:
        content_title = "Visão geral"
        content_subtitle = "Prévia do shell da aplicação gerada."

    return {
        "application": {
            "id": sistema.pk,
            "name": sistema.interface_nome or sistema.nome,
            "source_name": sistema.nome,
        },
        "interface": {
            "menu": sistema.tipo_menu,
            "mode": sistema.interface_modo,
            "density": sistema.interface_densidade,
            "primary": sistema.interface_cor_primaria,
            "accent": sistema.interface_cor_destaque,
            "breadcrumb": bool(sistema.interface_breadcrumb),
            "search": bool(sistema.interface_busca),
            "user_menu": bool(sistema.interface_menu_usuario),
        },
        "navigation": {
            "home": {"label": "Início", "icon": "bi-house-door"},
            "dashboard": {
                "label": "Dashboard",
                "icon": "bi-bar-chart-line",
                "active": page_kind == "dashboard",
            },
            "modules": navigation,
        },
        "content": {"title": content_title, "subtitle": content_subtitle},
        "page_kind": page_kind,
        "list_page": list_page,
        "form_page": form_page,
        "dashboard_page": dashboard_page if page_kind == "dashboard" else None,
        "reports": reports,
        "report_page": report_page,
    }
