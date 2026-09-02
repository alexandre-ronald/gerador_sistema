import re
from pathlib import PurePosixPath, PureWindowsPath


ENVIRONMENTS = ("DEVELOPMENT", "TEST", "STAGING", "PRODUCTION")
EXECUTORS = {"local", "ssh"}
STRATEGIES = {"docker_compose"}
DEPLOYMENT_STATES = {
    "PLANNED",
    "VALIDATING",
    "READY",
    "RUNNING",
    "VERIFYING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
}
FINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELLED"}
TRANSITIONS = {
    "PLANNED": {"VALIDATING", "CANCELLED"},
    "VALIDATING": {"READY", "FAILED", "CANCELLED"},
    "READY": {"RUNNING", "CANCELLED"},
    "RUNNING": {"VERIFYING", "FAILED"},
    "VERIFYING": {"SUCCEEDED", "FAILED"},
    "SUCCEEDED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}

ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
HOST_RE = re.compile(r"^[A-Za-z0-9.-]+$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class DeploymentCenterError(ValueError):
    def __init__(self, code, message, *, environment=None, field=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.environment = environment
        self.field = field

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.environment is not None:
            data["environment"] = self.environment
        if self.field is not None:
            data["field"] = self.field
        return data


def _fail(code, message, *, environment=None, field=None):
    raise DeploymentCenterError(code, message, environment=environment, field=field)


def _require_string(value, *, environment, field):
    if not isinstance(value, str) or not value.strip():
        _fail("invalid_field", f"{field} deve ser uma string não vazia.", environment=environment, field=field)
    value = value.strip()
    if CONTROL_RE.search(value):
        _fail("invalid_field", f"{field} contém caracteres de controle.", environment=environment, field=field)
    return value


def _validate_env_name(value, *, environment, field):
    value = _require_string(value, environment=environment, field=field)
    if not ENV_RE.fullmatch(value):
        _fail("invalid_env_var", f"{field} deve conter apenas um nome seguro de variável de ambiente.", environment=environment, field=field)
    return value


def _validate_working_directory(value, *, environment):
    value = _require_string(value, environment=environment, field="working_directory")
    is_windows_abs = PureWindowsPath(value).is_absolute()
    is_posix_abs = PurePosixPath(value).is_absolute()
    if not (is_windows_abs or is_posix_abs):
        _fail("invalid_working_directory", "working_directory deve ser um caminho absoluto.", environment=environment, field="working_directory")
    return value


def _validate_compose_file(value, *, environment):
    value = value or "docker-compose.yml"
    value = _require_string(value, environment=environment, field="compose_file")
    p_win = PureWindowsPath(value)
    p_posix = PurePosixPath(value)
    if p_win.is_absolute() or p_posix.is_absolute() or ".." in p_win.parts or ".." in p_posix.parts:
        _fail("invalid_compose_file", "compose_file deve ser um caminho relativo seguro.", environment=environment, field="compose_file")
    return value.replace("\\", "/")


def _normalize_environment(name, config):
    if name not in ENVIRONMENTS:
        _fail("invalid_environment", f"Ambiente desconhecido: {name}.", environment=name)
    if not isinstance(config, dict):
        _fail("invalid_environment_config", "Configuração do ambiente deve ser um objeto.", environment=name)

    executor = str(config.get("executor") or "").strip().lower()
    if executor not in EXECUTORS:
        _fail("invalid_executor", "Executor deve ser local ou ssh.", environment=name, field="executor")

    strategy = str(config.get("strategy") or "").strip().lower()
    if strategy not in STRATEGIES:
        _fail("invalid_strategy", "Estratégia não suportada.", environment=name, field="strategy")

    if name in {"STAGING", "PRODUCTION"} and executor == "local":
        _fail("local_executor_forbidden", f"{name} não aceita executor local.", environment=name, field="executor")

    normalized = {
        "executor": executor,
        "strategy": strategy,
        "working_directory": _validate_working_directory(config.get("working_directory"), environment=name),
        "compose_file": _validate_compose_file(config.get("compose_file"), environment=name),
    }

    forbidden_secret_fields = {"password", "token", "private_key", "secret", "username"}
    if any(field in config for field in forbidden_secret_fields):
        _fail("plaintext_secret_forbidden", "Secrets/credenciais em texto puro não são permitidos.", environment=name)

    if executor == "ssh":
        host = _require_string(config.get("host"), environment=name, field="host")
        if not HOST_RE.fullmatch(host):
            _fail("invalid_host", "host contém caracteres inválidos.", environment=name, field="host")
        port = config.get("port", 22)
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            _fail("invalid_port", "port deve estar entre 1 e 65535.", environment=name, field="port")
        normalized.update({
            "host": host,
            "port": port,
            "username_env_var": _validate_env_name(config.get("username_env_var"), environment=name, field="username_env_var"),
            "private_key_env_var": _validate_env_name(config.get("private_key_env_var"), environment=name, field="private_key_env_var"),
        })
        if config.get("known_hosts_env_var"):
            normalized["known_hosts_env_var"] = _validate_env_name(
                config.get("known_hosts_env_var"), environment=name, field="known_hosts_env_var"
            )

    return normalized


def normalize_deployment_config(raw, *, tolerant=False):
    if raw is None:
        return {"enabled": False, "environments": {}}
    if not isinstance(raw, dict):
        if tolerant:
            return {"enabled": False, "environments": {}}
        _fail("invalid_config", "deployment deve ser um objeto.")

    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        if tolerant:
            return {"enabled": False, "environments": {}}
        _fail("invalid_enabled", "enabled deve ser booleano.", field="enabled")

    environments = raw.get("environments", {})
    if not isinstance(environments, dict):
        if tolerant:
            return {"enabled": False, "environments": {}}
        _fail("invalid_environments", "environments deve ser um objeto.", field="environments")

    unknown_environments = [name for name in environments if name not in ENVIRONMENTS]
    if unknown_environments and not tolerant:
        name = unknown_environments[0]
        _fail("invalid_environment", f"Ambiente desconhecido: {name}.", environment=name)

    result = {"enabled": enabled, "environments": {}}
    for name in ENVIRONMENTS:
        if name not in environments:
            continue
        try:
            result["environments"][name] = _normalize_environment(name, environments[name])
        except DeploymentCenterError:
            if tolerant:
                continue
            raise
    return result


def validate_transition(current, target):
    if current not in DEPLOYMENT_STATES:
        _fail("invalid_state", f"Estado atual desconhecido: {current}.", field="status")
    if target not in DEPLOYMENT_STATES:
        _fail("invalid_state", f"Estado destino desconhecido: {target}.", field="status")
    if target not in TRANSITIONS[current]:
        _fail("invalid_transition", f"Transição {current} → {target} não é permitida.", field="status")
    return True
