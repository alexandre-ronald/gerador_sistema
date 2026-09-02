from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation


ALLOWED_EVENTS = ("before_create", "before_update", "before_save", "before_delete")
ALLOWED_CONDITION_MODES = ("all", "any")
ALLOWED_VALUE_SOURCES = ("literal", "field")
ALLOWED_ACTIONS = ("reject", "set_value", "copy_value")

TEXT_TYPES = {"CharField", "TextField", "EmailField", "SlugField", "URLField", "UUIDField"}
NUMBER_TYPES = {
    "IntegerField",
    "BigIntegerField",
    "SmallIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "FloatField",
    "DecimalField",
}
DATE_TYPES = {"DateField", "DateTimeField", "TimeField"}
BOOLEAN_TYPES = {"BooleanField", "NullBooleanField"}
RELATION_TYPES = {"ForeignKey", "OneToOneField"}
UNSUPPORTED_TYPES = {"ManyToManyField", "FileField", "ImageField"}

COMMON_OPERATORS = {"eq", "neq", "is_empty", "is_not_empty"}
ORDER_OPERATORS = {"gt", "gte", "lt", "lte"}
TEXT_OPERATORS = {"contains", "starts_with", "ends_with"}
BOOLEAN_OPERATORS = {"is_true", "is_false"}

PRIORITY_MIN = -10000
PRIORITY_MAX = 10000


class BusinessRuleError(ValueError):
    def __init__(self, code, message, *, field=None, rule_id=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.rule_id = rule_id

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.field:
            data["field"] = self.field
        if self.rule_id:
            data["rule_id"] = self.rule_id
        return data


def _safe_name(value, *, code="unsafe_name", rule_id=None):
    value = str(value or "").strip()
    if not value or "__" in value or "." in value or "/" in value or "\\" in value:
        raise BusinessRuleError(code, "Nome inválido ou inseguro.", rule_id=rule_id)
    return value


def _metadata_map(entity_metadata):
    result = {}
    for item in entity_metadata.get("fields") or []:
        name = _safe_name(item.get("name"), code="invalid_metadata_field")
        result[name] = deepcopy(item)
    return result


def _field_type(metadata):
    return str(metadata.get("type") or "CharField")


def compatible_operators(metadata):
    field_type = _field_type(metadata)
    if field_type in UNSUPPORTED_TYPES:
        return ()
    operators = set(COMMON_OPERATORS)
    if field_type in TEXT_TYPES:
        operators |= TEXT_OPERATORS
    if field_type in NUMBER_TYPES or field_type in DATE_TYPES:
        operators |= ORDER_OPERATORS
    if field_type in BOOLEAN_TYPES:
        operators |= BOOLEAN_OPERATORS
    return tuple(sorted(operators))


def is_assignable(metadata):
    field_type = _field_type(metadata)
    if field_type in UNSUPPORTED_TYPES:
        return False
    if metadata.get("auto_created") or metadata.get("editable") is False:
        return False
    return True


def _coerce_boolean(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "sim", "yes"}:
            return True
        if normalized in {"false", "0", "nao", "não", "no"}:
            return False
    raise ValueError


def coerce_literal(value, metadata):
    field_type = _field_type(metadata)
    if value is None:
        return None

    try:
        if field_type in TEXT_TYPES:
            return str(value)
        if field_type in {"IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField", "PositiveSmallIntegerField"}:
            if isinstance(value, bool):
                raise ValueError
            return int(value)
        if field_type == "FloatField":
            if isinstance(value, bool):
                raise ValueError
            return float(value)
        if field_type == "DecimalField":
            if isinstance(value, bool):
                raise ValueError
            return str(Decimal(str(value)))
        if field_type in BOOLEAN_TYPES:
            return _coerce_boolean(value)
        if field_type == "DateField":
            if isinstance(value, datetime):
                return value.date().isoformat()
            if isinstance(value, date):
                return value.isoformat()
            return date.fromisoformat(str(value)).isoformat()
        if field_type == "DateTimeField":
            if isinstance(value, datetime):
                return value.isoformat()
            return datetime.fromisoformat(str(value)).isoformat()
        if field_type == "TimeField":
            if isinstance(value, time):
                return value.isoformat()
            return time.fromisoformat(str(value)).isoformat()
        if field_type in RELATION_TYPES:
            if isinstance(value, bool):
                raise ValueError
            return int(value)
    except (ValueError, TypeError, InvalidOperation):
        raise BusinessRuleError("invalid_literal", "Valor literal incompatível com o tipo do campo.")

    raise BusinessRuleError("unsupported_literal_type", "Tipo de campo não suporta valor literal em regras.")


def _normalize_condition(item, metadata, *, strict, rule_id):
    field = _safe_name(item.get("field"), code="invalid_condition_field", rule_id=rule_id)
    if field not in metadata:
        if strict:
            raise BusinessRuleError("unknown_condition_field", "Campo da condição não existe.", field=field, rule_id=rule_id)
        return None

    operator = str(item.get("operator") or "").strip()
    if operator not in compatible_operators(metadata[field]):
        raise BusinessRuleError("incompatible_operator", "Operador incompatível com o tipo do campo.", field=field, rule_id=rule_id)

    value_source = str(item.get("value_source") or "literal").strip()
    if value_source not in ALLOWED_VALUE_SOURCES:
        raise BusinessRuleError("invalid_value_source", "Fonte de valor inválida.", field=field, rule_id=rule_id)

    normalized = {"field": field, "operator": operator, "value_source": value_source}

    if operator in {"is_empty", "is_not_empty", "is_true", "is_false"}:
        normalized["value_source"] = "literal"
        normalized["value"] = None
        return normalized

    if value_source == "field":
        compare_field = _safe_name(item.get("value"), code="invalid_comparison_field", rule_id=rule_id)
        if compare_field not in metadata:
            if strict:
                raise BusinessRuleError("unknown_comparison_field", "Campo de comparação não existe.", field=compare_field, rule_id=rule_id)
            return None
        if _field_type(metadata[compare_field]) in UNSUPPORTED_TYPES:
            raise BusinessRuleError("incompatible_comparison_field", "Campo de comparação não é suportado.", field=compare_field, rule_id=rule_id)
        normalized["value"] = compare_field
    else:
        normalized["value"] = coerce_literal(item.get("value"), metadata[field])

    return normalized


def _normalize_action(item, metadata, *, strict, rule_id):
    action_type = str(item.get("type") or "").strip()
    if action_type not in ALLOWED_ACTIONS:
        raise BusinessRuleError("invalid_action_type", "Tipo de ação inválido.", rule_id=rule_id)

    if action_type == "reject":
        message = str(item.get("message") or "").strip()
        if not message:
            raise BusinessRuleError("empty_reject_message", "Ação reject exige uma mensagem.", rule_id=rule_id)
        return {"type": "reject", "message": message}

    target = _safe_name(item.get("field"), code="invalid_action_field", rule_id=rule_id)
    if target not in metadata:
        if strict:
            raise BusinessRuleError("unknown_action_field", "Campo alvo da ação não existe.", field=target, rule_id=rule_id)
        return None
    if not is_assignable(metadata[target]):
        raise BusinessRuleError("non_assignable_field", "Campo alvo não pode ser alterado por regra.", field=target, rule_id=rule_id)

    if action_type == "set_value":
        return {
            "type": "set_value",
            "field": target,
            "value": coerce_literal(item.get("value"), metadata[target]),
        }

    source = _safe_name(item.get("source_field"), code="invalid_source_field", rule_id=rule_id)
    if source not in metadata:
        if strict:
            raise BusinessRuleError("unknown_source_field", "Campo de origem não existe.", field=source, rule_id=rule_id)
        return None
    if _field_type(metadata[source]) in UNSUPPORTED_TYPES:
        raise BusinessRuleError("incompatible_source_field", "Campo de origem não é suportado.", field=source, rule_id=rule_id)
    return {"type": "copy_value", "field": target, "source_field": source}


def _normalize_rule(item, metadata, *, strict):
    rule_id = _safe_name(item.get("id"), code="invalid_rule_id")
    name = str(item.get("name") or "").strip()
    if not name:
        raise BusinessRuleError("empty_rule_name", "Regra exige um nome.", rule_id=rule_id)

    enabled = item.get("enabled", True)
    if not isinstance(enabled, bool):
        raise BusinessRuleError("invalid_rule_enabled", "enabled deve ser booleano.", rule_id=rule_id)

    event = str(item.get("event") or "").strip()
    if event not in ALLOWED_EVENTS:
        raise BusinessRuleError("invalid_event", "Evento da regra é inválido.", rule_id=rule_id)

    try:
        priority = int(item.get("priority", 0))
    except (TypeError, ValueError):
        raise BusinessRuleError("invalid_priority", "Prioridade da regra deve ser inteira.", rule_id=rule_id)
    if priority < PRIORITY_MIN or priority > PRIORITY_MAX:
        raise BusinessRuleError("invalid_priority", "Prioridade fora da faixa permitida.", rule_id=rule_id)

    condition_mode = str(item.get("condition_mode") or "all").strip()
    if condition_mode not in ALLOWED_CONDITION_MODES:
        raise BusinessRuleError("invalid_condition_mode", "Modo das condições deve ser all ou any.", rule_id=rule_id)

    conditions = []
    for condition in item.get("conditions") or []:
        normalized = _normalize_condition(condition, metadata, strict=strict, rule_id=rule_id)
        if normalized is not None:
            conditions.append(normalized)

    actions = []
    for action in item.get("actions") or []:
        normalized = _normalize_action(action, metadata, strict=strict, rule_id=rule_id)
        if normalized is not None:
            actions.append(normalized)
    if not actions:
        if strict:
            raise BusinessRuleError("empty_actions", "Regra deve possuir pelo menos uma ação válida.", rule_id=rule_id)
        return None

    return {
        "id": rule_id,
        "name": name,
        "enabled": enabled,
        "event": event,
        "priority": priority,
        "condition_mode": condition_mode,
        "conditions": conditions,
        "actions": actions,
    }


def default_business_rules_config(entity_name, entity_metadata):
    _safe_name(entity_name, code="invalid_entity")
    metadata_name = str(entity_metadata.get("name") or entity_name)
    if metadata_name != entity_name:
        raise BusinessRuleError("unknown_entity", "Entidade não corresponde ao metadata informado.")
    _metadata_map(entity_metadata)
    return {"rules": []}


def normalize_business_rules_config(entity_name, entity_metadata, config=None, *, strict=False):
    entity_name = _safe_name(entity_name, code="invalid_entity")
    metadata_name = str(entity_metadata.get("name") or entity_name)
    if metadata_name != entity_name:
        raise BusinessRuleError("unknown_entity", "Entidade não corresponde ao metadata informado.")

    metadata = _metadata_map(entity_metadata)
    config = deepcopy(config or {})
    rules = []
    seen = set()

    for item in config.get("rules") or []:
        rule_id = _safe_name(item.get("id"), code="invalid_rule_id")
        if rule_id in seen:
            raise BusinessRuleError("duplicate_rule_id", "ID da regra não pode se repetir.", rule_id=rule_id)
        seen.add(rule_id)
        normalized = _normalize_rule(item, metadata, strict=strict)
        if normalized is not None:
            rules.append(normalized)

    rules.sort(key=lambda rule: (rule["priority"], rule["id"]))
    return {"rules": rules}
