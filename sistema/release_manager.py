from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import VersaoGeracao
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

        version.status = VersaoGeracao.STATUS_VALIDATING
        version.save(update_fields=["status"])
        report = validate_system(self.sistema, version=version)

        if not report["release_ready"]:
            version.status = VersaoGeracao.STATUS_DRAFT
            version.validado_em = None
            version.save(update_fields=["status", "validado_em"])
            return report

        version.status = VersaoGeracao.STATUS_VALIDATED
        version.validado_em = timezone.now()
        version.save(update_fields=["status", "validado_em"])
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
        return version

    def _assert_owned(self, version):
        if version.sistema_id != self.sistema.pk:
            raise ValidationError("A versão não pertence a este sistema.")
