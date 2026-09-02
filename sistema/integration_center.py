from copy import deepcopy
import re
from urllib.parse import urlparse


HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
HTTP_METHOD_SET = set(HTTP_METHODS)
AUTHENTICATION_TYPES = {"none", "basic", "bearer", "api_key"}
API_KEY_LOCATIONS = {"header", "query"}
TIMEOUT_MIN = 1
TIMEOUT_MAX = 120
SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SAFE_PARAM_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SAFE_ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
PATH_PARAM_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
FORBIDDEN_STATIC_HEADERS = {"authorization", "proxy-authorization"}


class IntegrationCenterError(ValueError):
    def __init__(self, code, message, *, integration=None, operation=None, field=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.integration = integration
        self.operation = operation
        self.field = field

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.integration:
            data["integration"] = self.integration
        if self.operation:
            data["operation"] = self.operation
        if self.field:
            data["field"] = self.field
        return data


def _bool(value, *, code, integration=None):
    if isinstance(value, bool):
        return value
    raise IntegrationCenterError(code, "Valor booleano inválido.", integration=integration)


def _safe_id(value, *, code, label, integration=None, operation=None):
    value = str(value or "").strip()
    if not SAFE_ID_RE.fullmatch(value):
        raise IntegrationCenterError(code, f"{label} inválido.", integration=integration, operation=operation)
    return value


def _safe_param(value, *, code, integration, operation):
    value = str(value or "").strip()
    if not SAFE_PARAM_RE.fullmatch(value):
        raise IntegrationCenterError(code, "Nome de parâmetro inválido.", integration=integration, operation=operation, field=value or None)
    return value


def _safe_env(value, *, code, integration):
    value = str(value or "").strip()
    if not SAFE_ENV_RE.fullmatch(value):
        raise IntegrationCenterError(code, "Nome de variável de ambiente inválido.", integration=integration, field=value or None)
    return value


def _normalize_unique_params(raw, *, code, integration, operation):
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise IntegrationCenterError(code, "Lista de parâmetros inválida.", integration=integration, operation=operation)
    result = []
    seen = set()
    for value in raw:
        param = _safe_param(value, code=code, integration=integration, operation=operation)
        if param not in seen:
            result.append(param)
            seen.add(param)
    return result


def _normalize_headers(raw, integration):
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise IntegrationCenterError("invalid_integration_headers", "Headers devem ser um objeto.", integration=integration)
    result = {}
    for key, value in raw.items():
        name = str(key or "").strip()
        if not name or any(ch in name for ch in "\r\n:"):
            raise IntegrationCenterError("invalid_integration_header_name", "Nome de header inválido.", integration=integration, field=name or None)
        if name.lower() in FORBIDDEN_STATIC_HEADERS:
            raise IntegrationCenterError("forbidden_secret_header", "Header de autenticação não pode armazenar segredo estático.", integration=integration, field=name)
        if isinstance(value, (dict, list, tuple, set)):
            raise IntegrationCenterError("invalid_integration_header_value", "Valor de header deve ser escalar.", integration=integration, field=name)
        result[name] = str(value)
    return {key: result[key] for key in sorted(result, key=str.lower)}


def _normalize_auth(raw, integration):
    if raw is None:
        raw = {"type": "none"}
    if not isinstance(raw, dict):
        raise IntegrationCenterError("invalid_integration_authentication", "Autenticação deve ser um objeto.", integration=integration)
    auth_type = str(raw.get("type", "none") or "").strip()
    if auth_type not in AUTHENTICATION_TYPES:
        raise IntegrationCenterError("unknown_integration_authentication", "Tipo de autenticação desconhecido.", integration=integration)

    if auth_type == "none":
        return {"type": "none"}
    if auth_type == "basic":
        return {
            "type": "basic",
            "username_env_var": _safe_env(raw.get("username_env_var"), code="invalid_basic_username_env", integration=integration),
            "password_env_var": _safe_env(raw.get("password_env_var"), code="invalid_basic_password_env", integration=integration),
        }
    if auth_type == "bearer":
        return {
            "type": "bearer",
            "env_var": _safe_env(raw.get("env_var"), code="invalid_bearer_env", integration=integration),
        }

    location = str(raw.get("location") or "").strip()
    if location not in API_KEY_LOCATIONS:
        raise IntegrationCenterError("invalid_api_key_location", "API key deve usar header ou query.", integration=integration)
    name = str(raw.get("name") or "").strip()
    if not name or any(ch in name for ch in "\r\n"):
        raise IntegrationCenterError("invalid_api_key_name", "Nome da API key inválido.", integration=integration, field=name or None)
    return {
        "type": "api_key",
        "env_var": _safe_env(raw.get("env_var"), code="invalid_api_key_env", integration=integration),
        "location": location,
        "name": name,
    }


def _normalize_base_url(raw, integration):
    value = str(raw or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise IntegrationCenterError("invalid_integration_base_url", "Base URL deve ser absoluta HTTP/HTTPS e não pode conter credenciais.", integration=integration)
    if parsed.query or parsed.fragment:
        raise IntegrationCenterError("invalid_integration_base_url", "Base URL não pode conter query string ou fragmento.", integration=integration)
    return value


def _normalize_operation(raw, integration):
    if not isinstance(raw, dict):
        raise IntegrationCenterError("invalid_integration_operation", "Operação deve ser um objeto.", integration=integration)
    operation = _safe_id(raw.get("id"), code="invalid_integration_operation_id", label="ID da operação", integration=integration)
    label = str(raw.get("label") or "").strip()
    if not label:
        raise IntegrationCenterError("invalid_integration_operation_label", "Nome da operação é obrigatório.", integration=integration, operation=operation)
    method = str(raw.get("method") or "").upper().strip()
    if method not in HTTP_METHOD_SET:
        raise IntegrationCenterError("unknown_integration_http_method", "Método HTTP desconhecido.", integration=integration, operation=operation)
    path = str(raw.get("path") or "").strip()
    parsed = urlparse(path)
    if not path.startswith("/") or path.startswith("//") or parsed.scheme or parsed.netloc or ".." in path or "?" in path or "#" in path:
        raise IntegrationCenterError("invalid_integration_operation_path", "Path deve ser relativo, iniciar por / e não conter URL absoluta, query ou fragmento.", integration=integration, operation=operation)

    path_params = _normalize_unique_params(raw.get("path_params", []), code="invalid_integration_path_params", integration=integration, operation=operation)
    query_params = _normalize_unique_params(raw.get("query_params", []), code="invalid_integration_query_params", integration=integration, operation=operation)
    body_fields = _normalize_unique_params(raw.get("body_fields", []), code="invalid_integration_body_fields", integration=integration, operation=operation)

    placeholders = PATH_PARAM_RE.findall(path)
    if len(placeholders) != len(set(placeholders)):
        raise IntegrationCenterError("duplicate_path_placeholder", "Placeholder duplicado no path.", integration=integration, operation=operation)
    if set(placeholders) != set(path_params):
        raise IntegrationCenterError("path_params_mismatch", "Placeholders do path e path_params devem corresponder exatamente.", integration=integration, operation=operation)
    if set(path_params) & set(query_params) or set(path_params) & set(body_fields) or set(query_params) & set(body_fields):
        raise IntegrationCenterError("duplicate_operation_parameter", "O mesmo parâmetro não pode ocupar mais de uma origem.", integration=integration, operation=operation)
    if method in {"GET", "DELETE"} and body_fields:
        raise IntegrationCenterError("body_not_allowed_for_method", "GET e DELETE não aceitam body_fields nesta versão.", integration=integration, operation=operation)

    return {
        "id": operation,
        "label": label,
        "method": method,
        "path": path,
        "path_params": path_params,
        "query_params": query_params,
        "body_fields": body_fields,
    }


def _normalize_integration(raw):
    if not isinstance(raw, dict):
        raise IntegrationCenterError("invalid_integration_item", "Integração deve ser um objeto.")
    integration = _safe_id(raw.get("id"), code="invalid_integration_id", label="ID da integração")
    label = str(raw.get("label") or "").strip()
    if not label:
        raise IntegrationCenterError("invalid_integration_label", "Nome da integração é obrigatório.", integration=integration)
    base_url = _normalize_base_url(raw.get("base_url"), integration)
    authentication = _normalize_auth(raw.get("authentication"), integration)
    timeout = raw.get("timeout_seconds", 15)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not TIMEOUT_MIN <= timeout <= TIMEOUT_MAX:
        raise IntegrationCenterError("invalid_integration_timeout", f"Timeout deve estar entre {TIMEOUT_MIN} e {TIMEOUT_MAX} segundos.", integration=integration)
    headers = _normalize_headers(raw.get("headers", {}), integration)
    operations_raw = raw.get("operations", [])
    if not isinstance(operations_raw, list):
        raise IntegrationCenterError("invalid_integration_operations", "Operações devem ser uma lista.", integration=integration)
    operations = []
    operation_ids = set()
    for item in operations_raw:
        operation = _normalize_operation(item, integration)
        if operation["id"] in operation_ids:
            raise IntegrationCenterError("duplicate_integration_operation", "ID de operação duplicado.", integration=integration, operation=operation["id"])
        operation_ids.add(operation["id"])
        operations.append(operation)
    operations.sort(key=lambda item: item["id"])
    return {
        "id": integration,
        "label": label,
        "base_url": base_url,
        "authentication": authentication,
        "timeout_seconds": timeout,
        "headers": headers,
        "operations": operations,
    }


def normalize_integrations_config(raw_config, *, strict=True):
    if raw_config is None:
        raw_config = {}
    if not isinstance(raw_config, dict):
        if strict:
            raise IntegrationCenterError("invalid_integrations_config", "Configuração de integrações deve ser um objeto.")
        return {"enabled": False, "items": []}
    try:
        enabled = _bool(raw_config.get("enabled", False), code="invalid_integrations_enabled")
        raw_items = raw_config.get("items", [])
        if not isinstance(raw_items, list):
            raise IntegrationCenterError("invalid_integrations_items", "Lista de integrações inválida.")
    except IntegrationCenterError:
        if strict:
            raise
        return {"enabled": False, "items": []}

    result = []
    ids = set()
    for raw in raw_items:
        try:
            integration = _normalize_integration(raw)
            if integration["id"] in ids:
                raise IntegrationCenterError("duplicate_integration_id", "ID de integração duplicado.", integration=integration["id"])
            ids.add(integration["id"])
            result.append(integration)
        except IntegrationCenterError:
            if strict:
                raise
            continue
    result.sort(key=lambda item: item["id"])
    return {"enabled": enabled, "items": result}


def integration_config(config, integration_id):
    for item in (config or {}).get("items", []):
        if item.get("id") == integration_id:
            return deepcopy(item)
    return None
