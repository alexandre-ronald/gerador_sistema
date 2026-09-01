import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError

from .models import RuntimeSnapshot


class RuntimeAgentService:
    CONTRACT = "1.0"
    STATUS_PATH = "/__djangoforge__/status/"

    def __init__(self, sistema):
        self.sistema = sistema

    def check_environment(self, ambiente, timeout=3):
        if ambiente.sistema_id != self.sistema.pk:
            raise ValidationError("O ambiente não pertence a este sistema.")
        url = self._status_url(ambiente.url_base)
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "DjangoForge/GEN-045"})
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self._validate_payload(payload)
            database = payload.get("database") or {}
            migrations = payload.get("migrations") or {}
            snapshot, _ = RuntimeSnapshot.objects.update_or_create(
                ambiente=ambiente,
                defaults={
                    "online": True,
                    "contract": str(payload.get("contract", "")),
                    "status": str(payload.get("status", "")),
                    "release_observada": str(payload.get("release", "")),
                    "ambiente_observado": str(payload.get("environment", "")),
                    "database_vendor": str(database.get("vendor", "")),
                    "migrations_pending": max(0, int(migrations.get("pending", 0) or 0)),
                    "uptime_seconds": max(0, int(payload.get("uptime_seconds", 0) or 0)),
                    "payload": payload,
                    "erro": "",
                },
            )
            return snapshot
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            snapshot, _ = RuntimeSnapshot.objects.update_or_create(
                ambiente=ambiente,
                defaults={
                    "online": False,
                    "status": "offline",
                    "payload": {},
                    "erro": str(exc),
                },
            )
            return snapshot

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
