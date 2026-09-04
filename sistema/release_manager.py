import uuid

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import VersaoGeracao
from .observability import emit_event
from .observability_models import ObservabilityEvent
from .validation_center import validate_system


class ReleaseManagerService:
    def __init__(self, sistema):
        self.sistema = sistema

    def versions(self):
        return self.sistema.versoes.filter(numero__gt=0).order_by("-numero")

    def validate_version(self, version):
        self._assert_owned(version)
        if version.numero == 0:
            raise ValidationError("O draft v0 não pode ser promovido.")
        if version.status == VersaoGeracao.STATUS_RELEASED:
            raise ValidationError("Uma release publicada não pode retornar ao fluxo de validação.")

        correlation_id = uuid.uuid4()
        emit_event(
            sistema=self.sistema,
            event_name="release.validation.started",
            message=f"Validação da versão v{version.numero} iniciada.",
            category=ObservabilityEvent.CATEGORY_RELEASE,
            source="release_manager",
            correlation_id=correlation_id,
            object_type="VersaoGeracao",
            object_id=str(version.pk),
            context={"version": version.numero, "status_before": version.status},
        )

        version.status = VersaoGeracao.STATUS_VALIDATING
        version.save(update_fields=["status"])
        report = validate_system(self.sistema, version=version)

        if not report["release_ready"]:
            version.status = VersaoGeracao.STATUS_DRAFT
            version.validado_em = None
            version.save(update_fields=["status", "validado_em"])
            emit_event(
                sistema=self.sistema,
                event_name="release.validation.failed",
                message=f"Versão v{version.numero} não está pronta para publicação.",
                level=ObservabilityEvent.LEVEL_WARNING,
                category=ObservabilityEvent.CATEGORY_RELEASE,
                source="release_manager",
                correlation_id=correlation_id,
                object_type="VersaoGeracao",
                object_id=str(version.pk),
                context={
                    "version": version.numero,
                    "overall_status": report.get("overall_status"),
                    "errors": report.get("errors", 0),
                    "warnings": report.get("warnings", 0),
                    "pending": report.get("pending", 0),
                },
            )
            return report

        version.status = VersaoGeracao.STATUS_VALIDATED
        version.validado_em = timezone.now()
        version.save(update_fields=["status", "validado_em"])
        emit_event(
            sistema=self.sistema,
            event_name="release.validation.succeeded",
            message=f"Versão v{version.numero} validada para publicação.",
            category=ObservabilityEvent.CATEGORY_RELEASE,
            source="release_manager",
            correlation_id=correlation_id,
            object_type="VersaoGeracao",
            object_id=str(version.pk),
            context={"version": version.numero, "release_ready": True},
        )
        return report

    def release(self, version, changelog=""):
        self._assert_owned(version)
        if version.numero == 0:
            raise ValidationError("O draft v0 não pode ser publicado.")
        if version.status != VersaoGeracao.STATUS_VALIDATED:
            raise ValidationError("Somente versões validadas podem ser publicadas.")
        version.status = VersaoGeracao.STATUS_RELEASED
        version.changelog = (changelog or version.changelog or "").strip()
        version.publicado_em = timezone.now()
        version.save(update_fields=["status", "changelog", "publicado_em"])
        emit_event(
            sistema=self.sistema,
            event_name="release.published",
            message=f"Release v{version.numero} publicada.",
            category=ObservabilityEvent.CATEGORY_RELEASE,
            source="release_manager",
            object_type="VersaoGeracao",
            object_id=str(version.pk),
            context={"version": version.numero, "has_changelog": bool(version.changelog)},
        )
        return version

    def _assert_owned(self, version):
        if version.sistema_id != self.sistema.pk:
            raise ValidationError("A versão não pertence a este sistema.")
