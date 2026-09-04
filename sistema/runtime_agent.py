import json
import uuid
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError

from .models import RuntimeCheck, RuntimeSnapshot
from .observability import emit_event
from .observability_models import ObservabilityEvent


class RuntimeAgentService:
    CONTRACT = "1.0"
    STATUS_PATH = "/__djangoforge__/status/"

    def __init__(self, sistema):
        self.sistema = sistema

    def check_environment(self, ambiente, timeout=3):
        if ambiente.sistema_id != self.sistema.pk:
            raise ValidationError("O ambiente não pertence a este sistema.")
        url = self._status_url(ambiente.url_base)
        correlation_id = uuid.uuid4()
        emit_event(
            sistema=self.sistema,
            ambiente=ambiente,
            event_name="runtime.check.started",
            message="Verificação do Runtime Agent iniciada.",
            category=ObservabilityEvent.CATEGORY_RUNTIME,
            source="runtime_agent",
            correlation_id=correlation_id,
            object_type="Ambiente",
            object_id=str(ambiente.pk),
            context={"environment": ambiente.tipo, "url": url},
        )
        started = perf_counter()
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "DjangoForge/GEN-046"})
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            latency_ms = max(0, int((perf_counter() - started) * 1000))
            self._validate_payload(payload)
            database = payload.get("database") or {}
            migrations = payload.get("migrations") or {}
            migrations_pending = max(0, int(migrations.get("pending", 0) or 0))
            release_observada = str(payload.get("release", ""))
            health = self._health(ambiente, payload, release_observada, migrations_pending)
            snapshot, _ = RuntimeSnapshot.objects.update_or_create(
                ambiente=ambiente,
                defaults={
                    "online": True,
                    "contract": str(payload.get("contract", "")),
                    "status": str(payload.get("status", "")),
                    "release_observada": release_observada,
                    "ambiente_observado": str(payload.get("environment", "")),
                    "database_vendor": str(database.get("vendor", "")),
                    "migrations_pending": migrations_pending,
                    "uptime_seconds": max(0, int(payload.get("uptime_seconds", 0) or 0)),
                    "latency_ms": latency_ms,
                    "payload": payload,
                    "erro": "",
                },
            )
            check = self._record_check(
                ambiente,
                online=True,
                health=health,
                release_observada=release_observada,
                migrations_pending=migrations_pending,
                latency_ms=latency_ms,
                payload=payload,
            )
            degraded = health != "HEALTHY"
            emit_event(
                sistema=self.sistema,
                ambiente=ambiente,
                event_name="runtime.check.degraded" if degraded else "runtime.check.healthy",
                message="Runtime Agent respondeu com degradação." if degraded else "Runtime Agent respondeu saudável.",
                level=ObservabilityEvent.LEVEL_WARNING if degraded else ObservabilityEvent.LEVEL_INFO,
                category=ObservabilityEvent.CATEGORY_RUNTIME,
                source="runtime_agent",
                correlation_id=correlation_id,
                object_type="RuntimeCheck",
                object_id=str(check.pk),
                context={
                    "health": health,
                    "release": release_observada,
                    "migrations_pending": migrations_pending,
                    "latency_ms": latency_ms,
                },
            )
            return snapshot
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            latency_ms = max(0, int((perf_counter() - started) * 1000))
            snapshot, _ = RuntimeSnapshot.objects.update_or_create(
                ambiente=ambiente,
                defaults={
                    "online": False,
                    "status": "offline",
                    "latency_ms": latency_ms,
                    "payload": {},
                    "erro": str(exc),
                },
            )
            check = self._record_check(
                ambiente,
                online=False,
                health="OFFLINE",
                latency_ms=latency_ms,
                erro=str(exc),
            )
            emit_event(
                sistema=self.sistema,
                ambiente=ambiente,
                event_name="runtime.check.offline",
                message="Runtime Agent indisponível.",
                level=ObservabilityEvent.LEVEL_ERROR,
                category=ObservabilityEvent.CATEGORY_RUNTIME,
                source="runtime_agent",
                correlation_id=correlation_id,
                object_type="RuntimeCheck",
                object_id=str(check.pk),
                context={"latency_ms": latency_ms, "error": str(exc)},
            )
            return snapshot

    def _record_check(
        self,
        ambiente,
        *,
        online,
        health,
        release_observada="",
        migrations_pending=0,
        latency_ms=0,
        erro="",
        payload=None,
    ):
        return RuntimeCheck.objects.create(
            ambiente=ambiente,
            online=online,
            health=health,
            release_observada=release_observada,
            migrations_pending=migrations_pending,
            latency_ms=latency_ms,
            erro=erro,
            payload=payload or {},
        )

    def _health(self, ambiente, payload, release_observada, migrations_pending):
        if str(payload.get("status", "")).lower() != "ok":
            return "DEGRADED"
        if migrations_pending > 0:
            return "DEGRADED"
        if ambiente.release_atual_id and str(ambiente.release_atual.numero) != release_observada:
            return "DEGRADED"
        return "HEALTHY"

    def _status_url(self, base_url):
        value = (base_url or "").strip()
        if not value:
            raise ValidationError("Informe a URL base do ambiente antes de consultar o Runtime Agent.")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValidationError("A URL do ambiente deve usar http ou https.")
        return value.rstrip("/") + self.STATUS_PATH

    def _validate_payload(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("O Runtime Agent retornou um payload inválido.")
        if str(payload.get("contract", "")) != self.CONTRACT:
            raise ValueError(f"Contrato do Runtime Agent incompatível: {payload.get('contract') or 'ausente'}")
        if "status" not in payload or "system" not in payload:
            raise ValueError("O Runtime Agent não retornou os campos obrigatórios.")
