"""Dashboard Data Engine.

GEN-048.1 compila a configuração normalizada do Dashboard Designer para um
plano de consulta seguro. A execução ORM será adicionada em bloco posterior.
"""
from dataclasses import dataclass

from .models import Entidade


ALLOWED_OPERATIONS = ("count", "sum", "avg", "min", "max")
NUMERIC_FIELD_TYPES = {"IntegerField", "FloatField", "DecimalField"}
DEFAULT_LIMIT = 100
MAX_LIMIT = 500


class DashboardDataError(ValueError):
    """Erro de domínio estável do Dashboard Data Engine."""

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)

    def as_dict(self):
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class DashboardQueryPlan:
    entity: str
    operation: str
    value_field: str
    group_by: str
    group_by_related: str
    related_label: str
    table_fields: tuple
    ordering: str
    limit: int


class DashboardDataEngine:
    """Compila widgets em planos validados contra o metamodelo do sistema."""

    @classmethod
    def compile(cls, sistema, widget):
        widget = widget if isinstance(widget, dict) else {}
        config = widget.get("config") if isinstance(widget.get("config"), dict) else {}
        entity_name = str(widget.get("entity") or "").strip()
        entity = cls._entity(sistema, entity_name)
        fields = {field.nome: field for field in entity.campos.select_related("entidade_relacionada").all()}

        operation = str(config.get("operation") or "count").lower().strip()
        if operation not in ALLOWED_OPERATIONS:
            raise DashboardDataError("invalid_operation", f"Operação não suportada: {operation}")

        value_field = str(config.get("field") or "id").strip()
        if value_field != "id":
            field = cls._field(fields, value_field)
            if operation in {"sum", "avg"} and field.tipo not in NUMERIC_FIELD_TYPES:
                raise DashboardDataError(
                    "numeric_field_required",
                    f"A operação {operation} exige um campo numérico: {value_field}",
                )
        elif operation in {"sum", "avg", "min", "max"}:
            raise DashboardDataError(
                "field_not_found",
                f"A operação {operation} exige um campo configurado da entidade.",
            )

        group_by = str(config.get("group_by") or "").strip()
        if group_by:
            cls._safe_name(group_by, "invalid_grouping")
            cls._field(fields, group_by, code="invalid_grouping")

        group_by_related = str(config.get("group_by_related") or "").strip()
        related_label = str(config.get("related_label") or "__str__").strip() or "__str__"
        if group_by_related:
            cls._safe_name(group_by_related, "invalid_related_grouping")
            relation = cls._field(fields, group_by_related, code="invalid_related_grouping")
            if not relation.eh_relacional or not relation.entidade_relacionada:
                raise DashboardDataError(
                    "invalid_related_grouping",
                    f"Campo não é um relacionamento válido: {group_by_related}",
                )
            if related_label != "__str__":
                cls._safe_name(related_label, "invalid_related_grouping")
                related_fields = {
                    field.nome for field in relation.entidade_relacionada.campos.all()
                }
                if related_label not in related_fields:
                    raise DashboardDataError(
                        "invalid_related_grouping",
                        f"Rótulo relacionado desconhecido: {related_label}",
                    )

        raw_table_fields = config.get("fields") or []
        if not isinstance(raw_table_fields, (list, tuple)):
            raise DashboardDataError("invalid_table_fields", "Campos da tabela devem ser uma lista.")
        table_fields = []
        for name in raw_table_fields:
            name = str(name).strip()
            cls._safe_name(name, "invalid_table_fields")
            cls._field(fields, name, code="invalid_table_fields")
            if name not in table_fields:
                table_fields.append(name)

        ordering = str(config.get("ordering") or "").strip()
        if ordering:
            plain_ordering = ordering[1:] if ordering.startswith("-") else ordering
            cls._safe_name(plain_ordering, "invalid_ordering")
            cls._field(fields, plain_ordering, code="invalid_ordering")

        limit = cls._limit(config.get("limit", DEFAULT_LIMIT))

        return DashboardQueryPlan(
            entity=entity.nome,
            operation=operation,
            value_field=value_field,
            group_by=group_by,
            group_by_related=group_by_related,
            related_label=related_label,
            table_fields=tuple(table_fields),
            ordering=ordering,
            limit=limit,
        )

    @staticmethod
    def _entity(sistema, name):
        if not name:
            raise DashboardDataError("entity_not_found", "O widget não possui uma entidade configurada.")
        entity = (
            Entidade.objects.filter(modulo__sistema=sistema, nome=name)
            .prefetch_related("campos", "campos__entidade_relacionada__campos")
            .first()
        )
        if not entity:
            raise DashboardDataError("entity_not_found", f"Entidade não disponível: {name}")
        return entity

    @staticmethod
    def _field(fields, name, code="field_not_found"):
        field = fields.get(name)
        if not field:
            raise DashboardDataError(code, f"Campo não disponível: {name}")
        return field

    @staticmethod
    def _safe_name(name, code):
        if not name or "__" in name or not name.replace("_", "a").isalnum():
            raise DashboardDataError(code, f"Campo ou lookup inválido: {name}")

    @staticmethod
    def _limit(value):
        try:
            limit = int(value)
        except (TypeError, ValueError):
            raise DashboardDataError("invalid_limit", "Limite deve ser um número inteiro.")
        if not 1 <= limit <= MAX_LIMIT:
            raise DashboardDataError("invalid_limit", f"Limite deve estar entre 1 e {MAX_LIMIT}.")
        return limit
