"""Application Blueprint — projeções somente-leitura dos contratos do DjangoForge."""

from .models import Campo, Entidade, Modulo, VersaoGeracao


RELATIONAL_FIELD_TYPES = {"ForeignKey", "ManyToManyField", "OneToOneField"}


def _draft_structure(sistema):
    draft = (
        VersaoGeracao.objects.filter(sistema=sistema, numero=0)
        .only("estrutura_json")
        .first()
    )
    return draft.estrutura_json if draft and isinstance(draft.estrutura_json, dict) else {}


def build_application_inventory(sistema):
    """Retorna inventário determinístico sem persistir estado de Blueprint."""
    modules = list(
        Modulo.objects.filter(sistema=sistema)
        .prefetch_related("entidades__campos")
        .order_by("nome", "id")
    )
    entities = [entity for module in modules for entity in module.entidades.all()]
    fields = [field for entity in entities for field in entity.campos.all()]
    structure = _draft_structure(sistema)

    workflows = structure.get("workflows") or {}
    rbac = structure.get("rbac") or {}
    roles = rbac.get("roles") or [] if isinstance(rbac, dict) else []
    reports = structure.get("reports") or []
    notifications = structure.get("notifications") or []
    integrations = structure.get("integrations") or []

    workflow_count = sum(
        1 for entity_name, config in workflows.items()
        if config and entity_name
    ) if isinstance(workflows, dict) else 0

    relation_count = sum(
        1 for field in fields if field.tipo in RELATIONAL_FIELD_TYPES
    )

    return {
        "application": {
            "id": sistema.pk,
            "name": sistema.nome,
            "description": sistema.descricao or "",
            "type": sistema.get_tipo_sistema_display(),
        },
        "inventory": {
            "modules": len(modules),
            "entities": len(entities),
            "fields": len(fields),
            "relationships": relation_count,
            "workflows": workflow_count,
            "roles": len(roles) if isinstance(roles, list) else 0,
            "reports": len(reports) if isinstance(reports, list) else 0,
            "notifications": len(notifications) if isinstance(notifications, list) else 0,
            "integrations": len(integrations) if isinstance(integrations, list) else 0,
        },
        "modules": [
            {
                "id": module.pk,
                "name": module.nome,
                "description": module.descricao or "",
                "entities": len(module.entidades.all()),
                "fields": sum(len(entity.campos.all()) for entity in module.entidades.all()),
            }
            for module in modules
        ],
        "sources": {
            "structure": "database",
            "draft": bool(structure),
        },
    }
