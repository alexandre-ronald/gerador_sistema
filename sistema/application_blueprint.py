"""Application Blueprint — projeções somente-leitura dos contratos do DjangoForge."""

from .builder_contracts import normalize_dashboard_config
from .crud_designer import normalize_crud_config
from .form_designer import normalize_form_config
from .models import Modulo, VersaoGeracao

RELATIONAL_FIELD_TYPES = {"ForeignKey", "ManyToManyField", "OneToOneField"}
RELATION_LABELS = {"ForeignKey": "pertence a", "ManyToManyField": "relaciona-se com vários", "OneToOneField": "possui relação exclusiva com"}
FIELD_TYPE_LABELS = {"CharField": "Texto curto", "TextField": "Texto longo", "EmailField": "E-mail", "URLField": "Endereço web", "IntegerField": "Número inteiro", "FloatField": "Número", "DecimalField": "Número decimal", "BooleanField": "Sim ou não", "DateField": "Data", "DateTimeField": "Data e hora", "TimeField": "Hora", "FileField": "Arquivo", "ImageField": "Imagem"}
WIDGET_LABELS = {"metric": "Indicador", "table": "Tabela", "bar": "Gráfico de barras", "line": "Gráfico de linha", "area": "Gráfico de área", "pie": "Gráfico de pizza", "donut": "Gráfico de rosca"}
ACTION_LABELS = {"create": "Cadastrar", "view": "Consultar", "edit": "Editar", "delete": "Excluir"}


def _draft_structure(sistema):
    draft = VersaoGeracao.objects.filter(sistema=sistema, numero=0).only("estrutura_json").first()
    return draft.estrutura_json if draft and isinstance(draft.estrutura_json, dict) else {}


def _field_label(field):
    return field.verbose_name or field.nome.replace("_", " ").strip().capitalize()


def _entity_metadata(entity):
    return {"name": entity.nome, "label": entity.nome, "plural_label": entity.nome_plural or entity.nome, "fields": [{"name": field.nome, "label": _field_label(field), "type": field.tipo, "help_text": field.help_text or "", "editable": True} for field in entity.campos.all()]}


def _information_projection(modules):
    information, relationships = [], []
    for module in modules:
        for entity in module.entidades.all():
            attributes, entity_relationships = [], []
            for field in entity.campos.all():
                if field.tipo in RELATIONAL_FIELD_TYPES and field.entidade_relacionada:
                    target = field.entidade_relacionada
                    relation = {"field": field.nome, "label": _field_label(field), "kind": RELATION_LABELS[field.tipo], "source": entity.nome, "source_area": module.nome, "target": target.nome, "target_area": target.modulo.nome, "multiple": field.tipo == "ManyToManyField"}
                    entity_relationships.append(relation); relationships.append(relation); continue
                attributes.append({"name": field.nome, "label": _field_label(field), "type": FIELD_TYPE_LABELS.get(field.tipo, "Informação"), "required": not field.null and not field.blank, "unique": field.unique})
            information.append({"id": entity.pk, "name": entity.nome, "plural": entity.nome_plural or entity.nome, "description": entity.descricao or "", "area": module.nome, "attributes": attributes, "relationships": entity_relationships})
    return information, relationships


def _report_count(reports):
    if not isinstance(reports, dict): return 0
    return sum(len(items) if isinstance(items, list) else 1 for items in reports.values() if isinstance(items, (list, dict)))


def _experience_projection(entities, structure):
    forms = structure.get("forms") if isinstance(structure.get("forms"), dict) else {}
    cruds = structure.get("cruds") if isinstance(structure.get("cruds"), dict) else {}
    reports = structure.get("reports") if isinstance(structure.get("reports"), dict) else {}
    experiences = []
    for entity in entities:
        metadata = _entity_metadata(entity)
        form = normalize_form_config(entity.nome, metadata, forms.get(entity.nome))
        crud = normalize_crud_config(entity.nome, metadata, cruds.get(entity.nome))
        visible_fields = [field for field in form["fields"] if field["visible"]]
        visible_columns = [column for column in crud["columns"] if column["visible"]]
        actions = [ACTION_LABELS[name] for name, enabled in crud["actions"].items() if enabled]
        entity_reports = reports.get(entity.nome) or []
        if isinstance(entity_reports, dict): entity_reports = [entity_reports]
        report_items = [{"id": item.get("id", ""), "title": item.get("title") or f"Relatório de {entity.nome}", "enabled": bool(item.get("enabled", False))} for item in entity_reports if isinstance(item, dict)]
        experiences.append({"entity": entity.nome, "area": entity.modulo.nome, "form": {"title": form["title"], "fields": len(visible_fields), "sections": len(form["sections"])}, "listing": {"title": crud["title"], "columns": len(visible_columns), "search": bool(crud["search"]["enabled"]), "filters": len(crud["filters"]), "actions": actions}, "reports": report_items})
    dashboard = normalize_dashboard_config(structure.get("dashboard"))
    dashboard_projection = {"enabled": bool(dashboard["enabled"]), "title": dashboard["title"], "widgets": [{"id": widget["id"], "title": widget["title"], "type": WIDGET_LABELS.get(widget["type"], "Visualização"), "information": widget["entity"]} for widget in dashboard["widgets"]]}
    return experiences, dashboard_projection


def build_application_inventory(sistema):
    """Retorna Blueprint determinístico sem persistir estado próprio."""
    modules = list(Modulo.objects.filter(sistema=sistema).prefetch_related("entidades__campos__entidade_relacionada__modulo").order_by("nome", "id"))
    entities = [entity for module in modules for entity in module.entidades.all()]
    fields = [field for entity in entities for field in entity.campos.all()]
    information, relationships = _information_projection(modules)
    structure = _draft_structure(sistema)
    experiences, dashboard = _experience_projection(entities, structure)
    workflows = structure.get("workflows") or {}; rbac = structure.get("rbac") or {}; roles = rbac.get("roles") or [] if isinstance(rbac, dict) else []
    reports = structure.get("reports") or {}; notifications = structure.get("notifications") or []; integrations = structure.get("integrations") or []
    workflow_count = sum(1 for entity_name, config in workflows.items() if config and entity_name) if isinstance(workflows, dict) else 0
    return {
        "application": {"id": sistema.pk, "name": sistema.nome, "description": sistema.descricao or "", "type": sistema.get_tipo_sistema_display()},
        "inventory": {"modules": len(modules), "entities": len(entities), "fields": len(fields), "relationships": len(relationships), "workflows": workflow_count, "roles": len(roles) if isinstance(roles, list) else 0, "reports": _report_count(reports), "notifications": len(notifications) if isinstance(notifications, list) else 0, "integrations": len(integrations) if isinstance(integrations, list) else 0},
        "modules": [{"id": module.pk, "name": module.nome, "description": module.descricao or "", "entities": len(module.entidades.all()), "fields": sum(len(entity.campos.all()) for entity in module.entidades.all())} for module in modules],
        "information": information, "relationships": relationships, "experiences": experiences, "dashboard": dashboard,
        "sources": {"structure": "database", "draft": bool(structure)},
    }
