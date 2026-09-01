"""Dashboard Data Engine.

Compila a configuração normalizada do Dashboard Designer para um plano seguro
e executa esse plano sobre um model Django real fornecido por um resolver.
"""
from dataclasses import dataclass

from django.db.models import Avg, Count, Max, Min, Sum

from .models import Entidade

ALLOWED_OPERATIONS = ("count", "sum", "avg", "min", "max")
NUMERIC_FIELD_TYPES = {"IntegerField", "FloatField", "DecimalField"}
DEFAULT_LIMIT = 100
MAX_LIMIT = 500
AGGREGATES = {"count": Count, "sum": Sum, "avg": Avg, "min": Min, "max": Max}


class DashboardDataError(ValueError):
    def __init__(self, code, message):
        self.code, self.message = code, message
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
    @classmethod
    def compile(cls, sistema, widget):
        widget = widget if isinstance(widget, dict) else {}
        config = widget.get("config") if isinstance(widget.get("config"), dict) else {}
        entity = cls._entity(sistema, str(widget.get("entity") or "").strip())
        fields = {f.nome: f for f in entity.campos.select_related("entidade_relacionada").all()}
        operation = str(config.get("operation") or "count").lower().strip()
        if operation not in ALLOWED_OPERATIONS:
            raise DashboardDataError("invalid_operation", f"Operação não suportada: {operation}")
        value_field = str(config.get("field") or "id").strip()
        if value_field != "id":
            field = cls._field(fields, value_field)
            if operation in {"sum", "avg"} and field.tipo not in NUMERIC_FIELD_TYPES:
                raise DashboardDataError("numeric_field_required", f"A operação {operation} exige um campo numérico: {value_field}")
        elif operation in {"sum", "avg", "min", "max"}:
            raise DashboardDataError("field_not_found", f"A operação {operation} exige um campo configurado da entidade.")
        group_by = str(config.get("group_by") or "").strip()
        if group_by:
            cls._safe_name(group_by, "invalid_grouping"); cls._field(fields, group_by, "invalid_grouping")
        group_by_related = str(config.get("group_by_related") or "").strip()
        related_label = str(config.get("related_label") or "__str__").strip() or "__str__"
        if group_by_related:
            cls._safe_name(group_by_related, "invalid_related_grouping")
            relation = cls._field(fields, group_by_related, "invalid_related_grouping")
            if not relation.eh_relacional or not relation.entidade_relacionada:
                raise DashboardDataError("invalid_related_grouping", f"Campo não é um relacionamento válido: {group_by_related}")
            if related_label != "__str__":
                cls._safe_name(related_label, "invalid_related_grouping")
                if related_label not in {f.nome for f in relation.entidade_relacionada.campos.all()}:
                    raise DashboardDataError("invalid_related_grouping", f"Rótulo relacionado desconhecido: {related_label}")
        raw_fields = config.get("fields") or []
        if not isinstance(raw_fields, (list, tuple)):
            raise DashboardDataError("invalid_table_fields", "Campos da tabela devem ser uma lista.")
        table_fields = []
        for name in raw_fields:
            name = str(name).strip(); cls._safe_name(name, "invalid_table_fields"); cls._field(fields, name, "invalid_table_fields")
            if name not in table_fields: table_fields.append(name)
        ordering = str(config.get("ordering") or "").strip()
        if ordering:
            plain = ordering[1:] if ordering.startswith("-") else ordering
            cls._safe_name(plain, "invalid_ordering"); cls._field(fields, plain, "invalid_ordering")
        return DashboardQueryPlan(entity.nome, operation, value_field, group_by, group_by_related, related_label, tuple(table_fields), ordering, cls._limit(config.get("limit", DEFAULT_LIMIT)))

    @classmethod
    def execute(cls, plan, model_resolver):
        """Executa um plano sobre o model real resolvido pelo host/runtime."""
        try:
            model = model_resolver(plan.entity)
        except Exception as exc:
            raise DashboardDataError("model_resolution_failed", f"Não foi possível resolver o model {plan.entity}.") from exc
        if model is None or not hasattr(model, "objects"):
            raise DashboardDataError("model_resolution_failed", f"Model não disponível: {plan.entity}")
        queryset = model.objects.all()
        try:
            if plan.table_fields:
                qs = queryset.order_by(plan.ordering) if plan.ordering else queryset
                return {"kind": "table", "columns": list(plan.table_fields), "rows": list(qs.values(*plan.table_fields)[:plan.limit])}
            grouping = cls._runtime_grouping(plan)
            aggregate = AGGREGATES[plan.operation](plan.value_field)
            if grouping:
                qs = queryset.values(grouping).annotate(value=aggregate)
                if plan.ordering:
                    qs = qs.order_by(plan.ordering)
                return {"kind": "series", "group_field": grouping, "items": list(qs[:plan.limit])}
            value = queryset.aggregate(value=aggregate)["value"]
            return {"kind": "scalar", "value": value}
        except DashboardDataError:
            raise
        except Exception as exc:
            raise DashboardDataError("query_execution_failed", "Falha ao executar consulta do widget.") from exc

    @staticmethod
    def _runtime_grouping(plan):
        if plan.group_by_related:
            if plan.related_label == "__str__":
                return plan.group_by_related
            return f"{plan.group_by_related}__{plan.related_label}"
        return plan.group_by

    @staticmethod
    def _entity(sistema, name):
        if not name: raise DashboardDataError("entity_not_found", "O widget não possui uma entidade configurada.")
        entity = Entidade.objects.filter(modulo__sistema=sistema, nome=name).prefetch_related("campos", "campos__entidade_relacionada__campos").first()
        if not entity: raise DashboardDataError("entity_not_found", f"Entidade não disponível: {name}")
        return entity

    @staticmethod
    def _field(fields, name, code="field_not_found"):
        field = fields.get(name)
        if not field: raise DashboardDataError(code, f"Campo não disponível: {name}")
        return field

    @staticmethod
    def _safe_name(name, code):
        if not name or "__" in name or not name.replace("_", "a").isalnum(): raise DashboardDataError(code, f"Campo ou lookup inválido: {name}")

    @staticmethod
    def _limit(value):
        try: limit = int(value)
        except (TypeError, ValueError): raise DashboardDataError("invalid_limit", "Limite deve ser um número inteiro.")
        if not 1 <= limit <= MAX_LIMIT: raise DashboardDataError("invalid_limit", f"Limite deve estar entre 1 e {MAX_LIMIT}.")
        return limit
