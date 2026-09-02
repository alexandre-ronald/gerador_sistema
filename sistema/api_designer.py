from copy import deepcopy
import re


API_OPERATIONS = ("list", "retrieve", "create", "update", "partial_update", "destroy")
API_OPERATION_SET = set(API_OPERATIONS)
AUTHENTICATION_MODES = {"session", "basic", "session_basic"}
TEXT_SEARCH_TYPES = {"CharField", "TextField", "EmailField", "URLField"}
UNSAFE_TOKENS = ("__", "..", "/", "\\", " ")
PAGE_SIZE_MIN = 1
PAGE_SIZE_MAX = 500
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SAFE_VERSION_RE = re.compile(r"^v[1-9][0-9]*$")


class APIDesignerError(ValueError):
    def __init__(self, code, message, *, entity=None, field=None, operation=None, endpoint=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.entity = entity
        self.field = field
        self.operation = operation
        self.endpoint = endpoint

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.entity:
            data["entity"] = self.entity
        if self.field:
            data["field"] = self.field
        if self.operation:
            data["operation"] = self.operation
        if self.endpoint:
            data["endpoint"] = self.endpoint
        return data


def _bool(value, *, code, entity=None):
    if isinstance(value, bool):
        return value
    raise APIDesignerError(code, "Valor booleano inválido.", entity=entity)


def _safe_path(value, *, code, label, entity=None):
    value = str(value or "").strip()
    if not value or not SAFE_PATH_RE.fullmatch(value) or any(token in value for token in UNSAFE_TOKENS):
        raise APIDesignerError(code, f"{label} inválido ou inseguro.", entity=entity, endpoint=value or None)
    return value


def _metadata_map(entities_metadata):
    result = {}
    for item in entities_metadata or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        fields = []
        for field in item.get("fields") or []:
            if not isinstance(field, dict):
                continue
            field_name = str(field.get("name") or "").strip()
            if not field_name:
                continue
            fields.append({
                "name": field_name,
                "label": str(field.get("label") or field_name),
                "type": str(field.get("type") or ""),
                "editable": bool(field.get("editable", True)),
            })
        result[name] = {
            "name": name,
            "label": str(item.get("label") or name),
            "api_eligible": bool(item.get("api_eligible", False)),
            "workflow_state_field": str(item.get("workflow_state_field") or "").strip(),
            "fields": fields,
        }
    return result


def _field_map(metadata):
    fields = {field["name"]: deepcopy(field) for field in metadata.get("fields", [])}
    fields["id"] = {"name": "id", "label": "ID", "type": "AutoField", "editable": False}
    return fields


def _unique_field_list(raw, *, code, known_fields, entity, allowed_types=None):
    if not isinstance(raw, list):
        raise APIDesignerError(code, "Lista de campos inválida.", entity=entity)
    result = []
    seen = set()
    for value in raw:
        field_name = str(value or "").strip()
        if field_name not in known_fields:
            raise APIDesignerError("unknown_api_field", "Campo da API não existe.", entity=entity, field=field_name or None)
        if allowed_types is not None and known_fields[field_name]["type"] not in allowed_types:
            raise APIDesignerError(code, "Tipo de campo não suportado nesta configuração.", entity=entity, field=field_name)
        if field_name not in seen:
            result.append(field_name)
            seen.add(field_name)
    return result


def _normalize_operations(raw, entity):
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise APIDesignerError("invalid_api_operations", "Operações da API devem ser um objeto.", entity=entity)
    unknown = set(raw) - API_OPERATION_SET
    if unknown:
        operation = sorted(unknown)[0]
        raise APIDesignerError("unknown_api_operation", "Operação de API desconhecida.", entity=entity, operation=operation)
    defaults = {
        "list": True,
        "retrieve": True,
        "create": False,
        "update": False,
        "partial_update": False,
        "destroy": False,
    }
    return {operation: _bool(raw.get(operation, defaults[operation]), code="invalid_api_operation_enabled", entity=entity) for operation in API_OPERATIONS}


def _normalize_default_ordering(raw, *, ordering_fields, entity):
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise APIDesignerError("invalid_api_default_ordering", "Ordenação padrão deve ser uma lista.", entity=entity)
    result = []
    seen = set()
    allowed = set(ordering_fields)
    for value in raw:
        value = str(value or "").strip()
        field_name = value[1:] if value.startswith("-") else value
        if not field_name or field_name not in allowed:
            raise APIDesignerError("unknown_api_ordering_field", "Campo de ordenação padrão não autorizado.", entity=entity, field=field_name or None)
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _normalize_entity(entity_name, metadata, raw):
    if not isinstance(raw, dict):
        raise APIDesignerError("invalid_api_entity_config", "Configuração da entidade deve ser um objeto.", entity=entity_name)
    if not metadata.get("api_eligible"):
        raise APIDesignerError("api_entity_not_eligible", "Entidade não está habilitada para endpoints API.", entity=entity_name)

    enabled = _bool(raw.get("enabled", False), code="invalid_api_entity_enabled", entity=entity_name)
    endpoint = _safe_path(raw.get("endpoint") or entity_name.lower(), code="invalid_api_endpoint", label="Endpoint", entity=entity_name)
    operations = _normalize_operations(raw.get("operations"), entity_name)
    known_fields = _field_map(metadata)

    fields = _unique_field_list(raw.get("fields", ["id"]), code="invalid_api_fields", known_fields=known_fields, entity=entity_name)
    if not fields:
        raise APIDesignerError("empty_api_fields", "API ativa exige ao menos um campo exposto.", entity=entity_name)

    read_only = _unique_field_list(raw.get("read_only_fields", []), code="invalid_api_read_only_fields", known_fields=known_fields, entity=entity_name)
    exposed = set(fields)
    for field_name in read_only:
        if field_name not in exposed:
            raise APIDesignerError("read_only_field_not_exposed", "Campo somente leitura precisa estar exposto.", entity=entity_name, field=field_name)
    if "id" in exposed and "id" not in read_only:
        read_only.append("id")

    workflow_state = metadata.get("workflow_state_field")
    if workflow_state and workflow_state in exposed and workflow_state not in read_only:
        read_only.append(workflow_state)

    search_fields = _unique_field_list(
        raw.get("search_fields", []),
        code="invalid_api_search_field",
        known_fields=known_fields,
        entity=entity_name,
        allowed_types=TEXT_SEARCH_TYPES,
    )
    for field_name in search_fields:
        if field_name not in exposed:
            raise APIDesignerError("search_field_not_exposed", "Campo de busca precisa estar exposto.", entity=entity_name, field=field_name)

    ordering_fields = _unique_field_list(raw.get("ordering_fields", []), code="invalid_api_ordering_fields", known_fields=known_fields, entity=entity_name)
    for field_name in ordering_fields:
        if field_name not in exposed:
            raise APIDesignerError("ordering_field_not_exposed", "Campo de ordenação precisa estar exposto.", entity=entity_name, field=field_name)

    default_ordering = _normalize_default_ordering(raw.get("default_ordering", []), ordering_fields=ordering_fields, entity=entity_name)
    page_size = raw.get("page_size", 25)
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not PAGE_SIZE_MIN <= page_size <= PAGE_SIZE_MAX:
        raise APIDesignerError("invalid_api_page_size", f"Page size deve estar entre {PAGE_SIZE_MIN} e {PAGE_SIZE_MAX}.", entity=entity_name)

    return {
        "enabled": enabled,
        "endpoint": endpoint,
        "operations": operations,
        "fields": fields,
        "read_only_fields": read_only,
        "search_fields": search_fields,
        "ordering_fields": ordering_fields,
        "default_ordering": default_ordering,
        "page_size": page_size,
    }


def normalize_api_config(system_api_enabled, entities_metadata, raw_config, *, strict=True):
    if raw_config is None:
        raw_config = {}
    if not isinstance(raw_config, dict):
        if strict:
            raise APIDesignerError("invalid_api_config", "Configuração APIs deve ser um objeto.")
        raw_config = {}

    try:
        enabled = _bool(raw_config.get("enabled", False), code="invalid_api_enabled")
        if enabled and not system_api_enabled:
            raise APIDesignerError("system_api_disabled", "Sistema não está habilitado para gerar API REST.")
        prefix = _safe_path(raw_config.get("prefix", "api"), code="invalid_api_prefix", label="Prefixo")
        version = str(raw_config.get("version", "v1") or "").strip()
        if not SAFE_VERSION_RE.fullmatch(version):
            raise APIDesignerError("invalid_api_version", "Versão da API deve seguir o formato v1, v2, ...")
        authentication = str(raw_config.get("authentication", "session_basic") or "").strip()
        if authentication not in AUTHENTICATION_MODES:
            raise APIDesignerError("invalid_api_authentication", "Modo de autenticação desconhecido.")
    except APIDesignerError:
        if strict:
            raise
        return {"enabled": False, "prefix": "api", "version": "v1", "authentication": "session_basic", "entities": {}}

    raw_entities = raw_config.get("entities", {})
    if not isinstance(raw_entities, dict):
        if strict:
            raise APIDesignerError("invalid_api_entities", "Entidades da API devem ser um objeto.")
        raw_entities = {}

    metadata = _metadata_map(entities_metadata)
    entities = {}
    used_endpoints = {}
    for raw_name, raw_entity in raw_entities.items():
        entity_name = str(raw_name or "").strip()
        if entity_name not in metadata:
            if strict:
                raise APIDesignerError("unknown_api_entity", "Entidade da API não existe.", entity=entity_name or None)
            continue
        try:
            normalized = _normalize_entity(entity_name, metadata[entity_name], raw_entity)
            if normalized["enabled"]:
                endpoint = normalized["endpoint"]
                if endpoint in used_endpoints:
                    raise APIDesignerError("duplicate_api_endpoint", "Endpoint duplicado entre entidades.", entity=entity_name, endpoint=endpoint)
                used_endpoints[endpoint] = entity_name
            entities[entity_name] = normalized
        except APIDesignerError:
            if strict:
                raise
            continue

    return {
        "enabled": enabled,
        "prefix": prefix,
        "version": version,
        "authentication": authentication,
        "entities": {key: entities[key] for key in sorted(entities)},
    }


def api_entity_config(config, entity_name):
    entity = ((config or {}).get("entities") or {}).get(entity_name)
    return deepcopy(entity) if isinstance(entity, dict) else None
