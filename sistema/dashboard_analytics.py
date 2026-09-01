"""Dashboard Analytics Engine.

Compila filtros e janelas temporais seguras sobre o contrato da GEN-048.
Nenhum lookup ORM vindo do cliente é aceito diretamente.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from .models import Entidade

ALLOWED_FILTER_OPERATORS = ("eq", "neq", "gt", "gte", "lt", "lte", "contains", "icontains", "in", "isnull")
ALLOWED_PERIODS = ("all", "today", "current_week", "current_month", "current_year", "last_7_days", "last_30_days", "last_90_days", "custom")
ALLOWED_COMPARISONS = ("none", "previous_period", "previous_year")
TEMPORAL_FIELD_TYPES = {"DateField", "DateTimeField"}
NUMERIC_FIELD_TYPES = {"IntegerField", "FloatField", "DecimalField"}
TEXT_FIELD_TYPES = {"CharField", "TextField", "EmailField", "SlugField"}
ORDERABLE_FIELD_TYPES = NUMERIC_FIELD_TYPES | TEMPORAL_FIELD_TYPES


class DashboardAnalyticsError(ValueError):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)

    def as_dict(self):
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class DashboardFilter:
    field: str
    operator: str
    value: object


@dataclass(frozen=True)
class DateWindow:
    start: date
    end: date


@dataclass(frozen=True)
class DashboardAnalyticsPlan:
    date_field: str
    period: str
    custom_start: date | None
    custom_end: date | None
    compare: str
    filters: tuple
    current_window: DateWindow | None
    comparison_window: DateWindow | None


class DashboardAnalyticsEngine:
    @classmethod
    def compile(cls, sistema, widget, reference_date=None):
        widget = widget if isinstance(widget, dict) else {}
        config = widget.get("config") if isinstance(widget.get("config"), dict) else {}
        raw_analytics = config.get("analytics")
        if raw_analytics is None:
            raw_analytics = {}
        elif not isinstance(raw_analytics, dict):
            raise DashboardAnalyticsError("invalid_analytics", "Configuração analytics deve ser um objeto.")

        entity_name = str(widget.get("entity") or "").strip()
        entity = cls._entity(sistema, entity_name)
        fields = {field.nome: field for field in entity.campos.all()}

        period = str(raw_analytics.get("period") or "all").strip().lower()
        if period not in ALLOWED_PERIODS:
            raise DashboardAnalyticsError("invalid_period", f"Período não suportado: {period}")

        compare = str(raw_analytics.get("compare") or "none").strip().lower()
        if compare not in ALLOWED_COMPARISONS:
            raise DashboardAnalyticsError("invalid_comparison", f"Comparação não suportada: {compare}")
        if period == "all" and compare != "none":
            raise DashboardAnalyticsError("invalid_comparison", "Comparação exige um período temporal.")

        date_field = str(raw_analytics.get("date_field") or "").strip()
        if period != "all" or compare != "none" or date_field:
            cls._safe_name(date_field, "invalid_date_field")
            temporal = fields.get(date_field)
            if temporal is None or temporal.tipo not in TEMPORAL_FIELD_TYPES:
                raise DashboardAnalyticsError("invalid_date_field", f"Campo temporal inválido: {date_field}")

        custom_start = cls._parse_date(raw_analytics.get("custom_start"), "custom_start") if period == "custom" else None
        custom_end = cls._parse_date(raw_analytics.get("custom_end"), "custom_end") if period == "custom" else None
        if period == "custom" and custom_start > custom_end:
            raise DashboardAnalyticsError("invalid_custom_period", "Data inicial deve ser menor ou igual à data final.")

        raw_filters = raw_analytics.get("filters") or []
        if not isinstance(raw_filters, (list, tuple)):
            raise DashboardAnalyticsError("invalid_filter", "Filtros devem ser uma lista.")
        filters = tuple(cls._compile_filter(fields, item) for item in raw_filters)

        reference = reference_date or date.today()
        if not isinstance(reference, date):
            raise DashboardAnalyticsError("invalid_period", "Data de referência inválida.")
        current_window = cls.resolve_window(period, reference, custom_start, custom_end)
        comparison_window = cls.resolve_comparison(compare, current_window)

        return DashboardAnalyticsPlan(
            date_field=date_field,
            period=period,
            custom_start=custom_start,
            custom_end=custom_end,
            compare=compare,
            filters=filters,
            current_window=current_window,
            comparison_window=comparison_window,
        )

    @classmethod
    def _compile_filter(cls, fields, raw):
        if not isinstance(raw, dict):
            raise DashboardAnalyticsError("invalid_filter", "Filtro deve ser um objeto.")
        field_name = str(raw.get("field") or "").strip()
        cls._safe_name(field_name, "invalid_filter_field")
        field = fields.get(field_name)
        if field is None:
            raise DashboardAnalyticsError("invalid_filter_field", f"Campo de filtro não disponível: {field_name}")
        operator = str(raw.get("operator") or "eq").strip().lower()
        if operator not in ALLOWED_FILTER_OPERATORS:
            raise DashboardAnalyticsError("invalid_filter_operator", f"Operador de filtro não suportado: {operator}")
        if operator in {"contains", "icontains"} and field.tipo not in TEXT_FIELD_TYPES:
            raise DashboardAnalyticsError("invalid_filter_operator", f"Operador {operator} exige campo textual: {field_name}")
        if operator in {"gt", "gte", "lt", "lte"} and field.tipo not in ORDERABLE_FIELD_TYPES:
            raise DashboardAnalyticsError("invalid_filter_operator", f"Operador {operator} não é permitido para {field_name}")
        value = raw.get("value")
        if operator == "in" and not isinstance(value, (list, tuple)):
            raise DashboardAnalyticsError("invalid_filter_value", "Operador in exige uma lista de valores.")
        if operator == "isnull" and not isinstance(value, bool):
            raise DashboardAnalyticsError("invalid_filter_value", "Operador isnull exige valor booleano.")
        return DashboardFilter(field=field_name, operator=operator, value=value)

    @staticmethod
    def resolve_window(period, reference, custom_start=None, custom_end=None):
        if period == "all":
            return None
        if period == "today":
            return DateWindow(reference, reference)
        if period == "current_week":
            return DateWindow(reference - timedelta(days=reference.weekday()), reference)
        if period == "current_month":
            return DateWindow(reference.replace(day=1), reference)
        if period == "current_year":
            return DateWindow(reference.replace(month=1, day=1), reference)
        if period == "last_7_days":
            return DateWindow(reference - timedelta(days=6), reference)
        if period == "last_30_days":
            return DateWindow(reference - timedelta(days=29), reference)
        if period == "last_90_days":
            return DateWindow(reference - timedelta(days=89), reference)
        if period == "custom" and custom_start is not None and custom_end is not None:
            return DateWindow(custom_start, custom_end)
        raise DashboardAnalyticsError("invalid_period", f"Período não suportado: {period}")

    @classmethod
    def resolve_comparison(cls, compare, current_window):
        if compare == "none":
            return None
        if current_window is None:
            raise DashboardAnalyticsError("invalid_comparison", "Comparação exige janela temporal.")
        if compare == "previous_period":
            days = (current_window.end - current_window.start).days + 1
            end = current_window.start - timedelta(days=1)
            return DateWindow(end - timedelta(days=days - 1), end)
        if compare == "previous_year":
            return DateWindow(cls._shift_year(current_window.start), cls._shift_year(current_window.end))
        raise DashboardAnalyticsError("invalid_comparison", f"Comparação não suportada: {compare}")

    @staticmethod
    def _shift_year(value):
        try:
            return value.replace(year=value.year - 1)
        except ValueError:
            return value.replace(year=value.year - 1, day=28)

    @staticmethod
    def _parse_date(value, label):
        try:
            return date.fromisoformat(str(value or ""))
        except ValueError as exc:
            raise DashboardAnalyticsError("invalid_custom_period", f"{label} deve usar YYYY-MM-DD.") from exc

    @staticmethod
    def _entity(sistema, name):
        if not name:
            raise DashboardAnalyticsError("invalid_analytics", "Analytics exige entidade configurada no widget.")
        entity = Entidade.objects.filter(modulo__sistema=sistema, nome=name).prefetch_related("campos").first()
        if not entity:
            raise DashboardAnalyticsError("invalid_analytics", f"Entidade não disponível para analytics: {name}")
        return entity

    @staticmethod
    def _safe_name(name, code):
        if not name or "__" in name or not name.replace("_", "a").isalnum():
            raise DashboardAnalyticsError(code, f"Campo inválido: {name}")
