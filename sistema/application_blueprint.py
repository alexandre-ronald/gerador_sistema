"""Application Blueprint — projeções somente-leitura dos contratos do DjangoForge."""

from .models import Modulo, VersaoGeracao


RELATIONAL_FIELD_TYPES = {"ForeignKey", "ManyToManyField", "OneToOneField"}
RELATION_LABELS = {
    "ForeignKey": "pertence a",
    "ManyToManyField": "relaciona-se com vários",
    "OneToOneField": "possui relação exclusiva com",
}
FIELD_TYPE_LABELS = {
    "CharField": "Texto curto",
    "TextField": "Texto longo",
    "EmailField": "E-mail",
    "URLField": "Endereço web",
    "IntegerField": "Número inteiro",
    "FloatField": "Número",
    "DecimalField": "Número decimal",
    "BooleanField": "Sim ou não",
    "DateField": "Data",
    "DateTimeField": "Data e hora",
    "TimeField": "Hora",
    "FileField": "Arquivo",
    "ImageField": "Imagem",
}


def _draft_structure(sistema):
    draft = VersaoGeracao.objects.filter(sistema=sistema, numero=0).only("estrutura_json").first()
    return draft.estrutura_json if draft and isinstance(draft.estrutura_json, dict) else {}


def _field_label(field):
    return field.verbose_name or field.nome.replace("_", " ").strip().capitalize()


def _information_projection(modules):
    information = []
    relationships = []
    for module in modules:
        for entity in module.entidades.all():
            attributes = []
            entity_relationships = []
            for field in entity.campos.all():
                if field.tipo in RELATIONAL_FIELD_TYPES and field.entidade_relacionada:
                    target = field.entidade_relacionada
                    relation = {
                        "field": field.nome,
                        "label": _field_label(field),
                        "kind": RELATION_LABELS[field.tipo],
                        "source": entity.nome,
                        "source_area": module.nome,
                        "target": target.nome,
                        "target_area": target.modulo.nome,
                        "multiple": field.tipo == "ManyToManyField",
                    }
                    entity_relationships.append(relation)
                    relationships.append(relation)
                    continue
                attributes.append({
                    "name": field.nome,
                    "label": _field_label(field),
                    "type": FIELD_TYPE_LABELS.get(field.tipo, "Informação"),
                    "required": not field.null and not field.blank,
                    "unique": field.unique,
                })
            information.append({
                "id": entity.pk,
                "name": entity.nome,
                "plural": entity.nome_plural or entity.nome,
                "description": entity.descricao or "",
                "area": module.nome,
                "attributes": attributes,
                "relationships": entity_relationships,
            })
    return information, relationships


def build_application_inventory(sistema):
    """Retorna inventário determinístico sem persistir estado de Blueprint."""
    modules = list(
        Modulo.objects.filter(sistema=sistema)
        .prefetch_related("entidades__campos__entidade_relacionada__modulo")
        .order_by("nome", "id")
    )
    entities = [entity for module in modules for entity in module.entidades.all()]
    fields = [field for entity in entities for field in entity.campos.all()]
    information, relationships = _information_projection(modules)
    structure = _draft_structure(sistema)
    workflows = structure.get("workflows") or {}
    rbac = structure.get("rbac") or {}
    roles = rbac.get("roles") or [] if isinstance(rbac, dict) else []
    reports = structure.get("reports") or []
    notifications = structure.get("notifications") or []
    integrations = structure.get("integrations") or []
    workflow_count = sum(1 for entity_name, config in workflows.items() if config and entity_name) if isinstance(workflows, dict) else 0

    return {
        "application": {"id": sistema.pk, "name": sistema.nome, "description": sistema.descricao or "", "type": sistema.get_tipo_sistema_display()},
        "inventory": {
            "modules": len(modules), "entities": len(entities), "fields": len(fields),
            "relationships": len(relationships), "workflows": workflow_count,
            "roles": len(roles) if isinstance(roles, list) else 0,
            "reports": len(reports) if isinstance(reports, list) else 0,
            "notifications": len(notifications) if isinstance(notifications, list) else 0,
            "integrations": len(integrations) if isinstance(integrations, list) else 0,
        },
        "modules": [{
            "id": module.pk, "name": module.nome, "description": module.descricao or "",
            "entities": len(module.entidades.all()),
            "fields": sum(len(entity.campos.all()) for entity in module.entidades.all()),
        } for module in modules],
        "information": information,
        "relationships": relationships,
        "sources": {"structure": "database", "draft": bool(structure)},
    }
