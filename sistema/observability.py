import logging
import re
import uuid
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal

from .observability_models import ObservabilityEvent

logger = logging.getLogger(__name__)

REDACTED = "[REDACTED]"
MAX_STRING_LENGTH = 4000
MAX_COLLECTION_ITEMS = 100
MAX_DEPTH = 8

_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "accesstoken",
    "refreshtoken",
    "authorization",
    "cookie",
    "apikey",
    "privatekey",
}


def _normalized_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _is_sensitive_key(key):
    normalized = _normalized_key(key)
    return normalized in _SENSITIVE_KEYS or normalized.endswith("password") or normalized.endswith("token") or normalized.endswith("secret")


def _sanitize_database_url(value):
    text = str(value)
    if "://" in text and "@" in text:
        scheme, remainder = text.split("://", 1)
        credentials, host = remainder.split("@", 1)
        if ":" in credentials:
            username = credentials.split(":", 1)[0]
            return f"{scheme}://{username}:{REDACTED}@{host}"
    return text


def sanitize_context(value, *, _key="", _depth=0):
    """Return a JSON-safe copy with known secrets redacted and payload bounded."""
    if _is_sensitive_key(_key):
        return REDACTED
    if _normalized_key(_key) == "databaseurl":
        return _sanitize_database_url(value)
    if _depth >= MAX_DEPTH:
        return "[MAX_DEPTH]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Mapping):
        result = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_COLLECTION_ITEMS:
                result["__truncated__"] = True
                break
            text_key = str(key)[:200]
            result[text_key] = sanitize_context(item, _key=text_key, _depth=_depth + 1)
        return result
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        result = [sanitize_context(item, _depth=_depth + 1) for item in items[:MAX_COLLECTION_ITEMS]]
        if len(items) > MAX_COLLECTION_ITEMS:
            result.append("[TRUNCATED]")
        return result
    text = str(value)
    return text if len(text) <= MAX_STRING_LENGTH else text[:MAX_STRING_LENGTH] + "…"


def emit_event(
    *,
    sistema,
    event_name,
    message,
    level=ObservabilityEvent.LEVEL_INFO,
    category=ObservabilityEvent.CATEGORY_SYSTEM,
    ambiente=None,
    usuario=None,
    correlation_id=None,
    source="",
    object_type="",
    object_id="",
    context=None,
):
    """Persist an observability event without allowing telemetry failure to break the caller."""
    valid_levels = {value for value, _ in ObservabilityEvent.LEVEL_CHOICES}
    valid_categories = {value for value, _ in ObservabilityEvent.CATEGORY_CHOICES}
    if level not in valid_levels:
        raise ValueError(f"Nível de observabilidade inválido: {level}")
    if category not in valid_categories:
        raise ValueError(f"Categoria de observabilidade inválida: {category}")
    if not event_name or not str(event_name).strip():
        raise ValueError("event_name é obrigatório")
    if sistema is None:
        raise ValueError("sistema é obrigatório")

    correlation_id = correlation_id or uuid.uuid4()
    safe_context = sanitize_context(context or {})

    try:
        return ObservabilityEvent.objects.create(
            sistema=sistema,
            ambiente=ambiente,
            usuario=usuario,
            level=level,
            category=category,
            source=str(source or "")[:100],
            event_name=str(event_name).strip()[:120],
            message=str(message or ""),
            correlation_id=correlation_id,
            object_type=str(object_type or "")[:100],
            object_id=str(object_id or "")[:100],
            context=safe_context,
        )
    except Exception:
        logger.exception("Falha ao persistir evento de observabilidade %s", event_name)
        return None
