from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Ambiente, PromocaoAmbiente, VersaoGeracao


class EnvironmentManagerService:
    DEFAULTS = [
        (Ambiente.TIPO_DEVELOPMENT, "Development"),
        (Ambiente.TIPO_TEST, "Test"),
        (Ambiente.TIPO_STAGING, "Staging"),
        (Ambiente.TIPO_PRODUCTION, "Production"),
    ]

    def __init__(self, sistema):
        self.sistema = sistema

    def ensure_defaults(self):
        ambientes = []
        for tipo, nome in self.DEFAULTS:
            ambiente, _ = Ambiente.objects.get_or_create(
                sistema=self.sistema,
                tipo=tipo,
                defaults={"nome": nome},
            )
            ambientes.append(ambiente)
        return ambientes

    def environments(self):
        self.ensure_defaults()
        return self.sistema.ambientes.select_related("release_atual").order_by("tipo")

    def released_versions(self):
        return self.sistema.versoes.filter(
            numero__gt=0,
            status=VersaoGeracao.STATUS_RELEASED,
        ).order_by("-numero")

    @transaction.atomic
    def promote(self, ambiente, versao, observacao=""):
        self._assert_environment(ambiente)
        self._assert_version(versao)
        ambiente.release_atual = versao
        ambiente.save(update_fields=["release_atual", "atualizado_em"])
        return PromocaoAmbiente.objects.create(
            ambiente=ambiente,
            versao=versao,
            observacao=(observacao or "").strip(),
        )

    def update_environment(self, ambiente, *, nome=None, url_base=None, ativo=None):
        self._assert_environment(ambiente)
        fields = []
        if nome is not None:
            ambiente.nome = (nome or ambiente.get_tipo_display()).strip()
            fields.append("nome")
        if url_base is not None:
            ambiente.url_base = (url_base or "").strip()
            fields.append("url_base")
        if ativo is not None:
            ambiente.ativo = bool(ativo)
            fields.append("ativo")
        if fields:
            fields.append("atualizado_em")
            ambiente.save(update_fields=fields)
        return ambiente

    def history(self, limit=20):
        return PromocaoAmbiente.objects.filter(
            ambiente__sistema=self.sistema
        ).select_related("ambiente", "versao")[:limit]

    def _assert_environment(self, ambiente):
        if ambiente.sistema_id != self.sistema.pk:
            raise ValidationError("O ambiente não pertence a este sistema.")

    def _assert_version(self, versao):
        if versao.sistema_id != self.sistema.pk:
            raise ValidationError("A versão não pertence a este sistema.")
        if versao.numero == 0:
            raise ValidationError("O draft v0 não pode ser promovido para um ambiente.")
        if versao.status != VersaoGeracao.STATUS_RELEASED:
            raise ValidationError("Somente releases publicadas podem ser promovidas para ambientes.")
