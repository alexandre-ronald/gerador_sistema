from copy import deepcopy

from django.core.exceptions import ValidationError
from django.db import transaction

from .deployment_center import DeploymentCenterError, normalize_deployment_config, validate_transition
from .models import DeploymentPlan, VersaoGeracao


class DeploymentService:
    def __init__(self, sistema):
        self.sistema = sistema

    def draft(self):
        return self.sistema.versoes.filter(numero=0).first()

    def config(self, *, tolerant=True):
        draft = self.draft()
        raw = (draft.estrutura_json or {}).get("deployment") if draft else None
        return normalize_deployment_config(raw, tolerant=tolerant)

    @transaction.atomic
    def save_config(self, raw):
        config = normalize_deployment_config(raw, tolerant=False)
        draft = self.draft()
        if draft is None:
            raise ValidationError("O sistema não possui draft v0 para armazenar a configuração de deployment.")
        estrutura = deepcopy(draft.estrutura_json or {})
        estrutura["deployment"] = config
        draft.estrutura_json = estrutura
        draft.save(update_fields=["estrutura_json"])
        return config

    def plans(self, limit=50):
        return self.sistema.deployment_plans.select_related("ambiente", "versao", "criado_por")[:limit]

    @transaction.atomic
    def create_plan(self, *, ambiente, versao, user):
        self._assert_environment(ambiente)
        self._assert_version(versao)
        if not ambiente.ativo:
            raise ValidationError("O ambiente está inativo.")
        if ambiente.release_atual_id != versao.pk:
            raise ValidationError("A release do plano deve ser a release atualmente promovida para o ambiente.")

        config = self.config(tolerant=False)
        if not config["enabled"]:
            raise ValidationError("Deployment Center está desativado para este sistema.")
        env_config = config["environments"].get(ambiente.tipo)
        if env_config is None:
            raise ValidationError("O ambiente não possui configuração de deployment válida.")

        return DeploymentPlan.objects.create(
            sistema=self.sistema,
            ambiente=ambiente,
            versao=versao,
            criado_por=user,
            executor=env_config["executor"],
            strategy=env_config["strategy"],
            config_snapshot=deepcopy(env_config),
        )

    @transaction.atomic
    def validate_plan(self, plan):
        self._assert_plan(plan)
        validate_transition(plan.status, DeploymentPlan.STATUS_VALIDATING)
        plan.status = DeploymentPlan.STATUS_VALIDATING
        plan.erro = ""
        plan.save(update_fields=["status", "erro"])
        try:
            if plan.versao.status != VersaoGeracao.STATUS_RELEASED:
                raise ValidationError("A release do plano não está publicada.")
            if plan.ambiente.release_atual_id != plan.versao_id:
                raise ValidationError("A release promovida do ambiente mudou desde a criação do plano.")
            normalize_deployment_config({"enabled": True, "environments": {plan.ambiente.tipo: plan.config_snapshot}})
        except (ValidationError, DeploymentCenterError) as exc:
            plan.status = DeploymentPlan.STATUS_FAILED
            plan.erro = self._safe_error(exc)
            plan.save(update_fields=["status", "erro"])
            return plan
        validate_transition(plan.status, DeploymentPlan.STATUS_READY)
        plan.status = DeploymentPlan.STATUS_READY
        plan.save(update_fields=["status"])
        return plan

    @transaction.atomic
    def cancel_plan(self, plan):
        self._assert_plan(plan)
        validate_transition(plan.status, DeploymentPlan.STATUS_CANCELLED)
        plan.status = DeploymentPlan.STATUS_CANCELLED
        plan.save(update_fields=["status"])
        return plan

    def _assert_environment(self, ambiente):
        if ambiente.sistema_id != self.sistema.pk:
            raise ValidationError("O ambiente não pertence a este sistema.")

    def _assert_version(self, versao):
        if versao.sistema_id != self.sistema.pk:
            raise ValidationError("A release não pertence a este sistema.")
        if versao.numero == 0 or versao.status != VersaoGeracao.STATUS_RELEASED:
            raise ValidationError("Somente releases publicadas podem originar um plano de deployment.")

    def _assert_plan(self, plan):
        if plan.sistema_id != self.sistema.pk:
            raise ValidationError("O plano não pertence a este sistema.")

    @staticmethod
    def _safe_error(exc):
        if isinstance(exc, DeploymentCenterError):
            return exc.message[:500]
        if isinstance(exc, ValidationError):
            return (exc.messages[0] if exc.messages else "Falha de validação.")[:500]
        return "Falha de validação."
