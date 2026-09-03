from copy import deepcopy

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .deployment_center import DeploymentCenterError, normalize_deployment_config, validate_transition
from .deployment_executor import DeploymentExecutionError, LocalDockerComposeExecutor
from .models import DeploymentPlan, VersaoGeracao
from .runtime_agent import RuntimeAgentService


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
            if plan.executor != "local":
                raise ValidationError("GEN-057.3 suporta execução efetiva apenas com executor local.")
            if plan.strategy != "docker_compose":
                raise ValidationError("A estratégia do plano não é suportada para execução.")
        except (ValidationError, DeploymentCenterError) as exc:
            plan.status = DeploymentPlan.STATUS_FAILED
            plan.erro = self._safe_error(exc)
            plan.save(update_fields=["status", "erro"])
            return plan
        validate_transition(plan.status, DeploymentPlan.STATUS_READY)
        plan.status = DeploymentPlan.STATUS_READY
        plan.save(update_fields=["status"])
        return plan

    def execute_plan(self, plan, *, executor_factory=LocalDockerComposeExecutor, runtime_service_factory=RuntimeAgentService):
        self._assert_plan(plan)
        validate_transition(plan.status, DeploymentPlan.STATUS_RUNNING)
        if plan.executor != "local":
            raise ValidationError("A execução remota SSH ainda não está habilitada na GEN-057.3.")
        if plan.strategy != "docker_compose":
            raise ValidationError("A estratégia de deployment não é suportada.")
        if plan.ambiente.release_atual_id != plan.versao_id:
            raise ValidationError("A release promovida do ambiente mudou desde a validação do plano.")

        started_at = timezone.now()
        with transaction.atomic():
            claimed = DeploymentPlan.objects.filter(
                pk=plan.pk,
                sistema=self.sistema,
                status=DeploymentPlan.STATUS_READY,
            ).update(
                status=DeploymentPlan.STATUS_RUNNING,
                iniciado_em=started_at,
                finalizado_em=None,
                erro="",
                etapas=[],
            )
        if claimed != 1:
            raise DeploymentCenterError(
                "plan_already_claimed",
                "O plano já foi iniciado, cancelado ou alterado por outra execução.",
                field="status",
            )

        plan.status = DeploymentPlan.STATUS_RUNNING
        plan.iniciado_em = started_at
        plan.finalizado_em = None
        plan.erro = ""
        plan.etapas = []

        try:
            executor = executor_factory(plan.config_snapshot)
            self._step(plan, "prepare", "RUNNING", "Validando host local e Docker Compose.")
            executor.prepare()
            self._step(plan, "prepare", "SUCCEEDED", "Host local e Docker Compose validados.")

            self._step(plan, "deploy", "RUNNING", "Executando Docker Compose.")
            executor.deploy()
            self._step(plan, "deploy", "SUCCEEDED", "Docker Compose concluído.")

            validate_transition(plan.status, DeploymentPlan.STATUS_VERIFYING)
            plan.status = DeploymentPlan.STATUS_VERIFYING
            plan.save(update_fields=["status"])
            self._step(plan, "verify", "RUNNING", "Consultando Runtime Agent.")

            snapshot = runtime_service_factory(self.sistema).check_environment(plan.ambiente)
            plan.release_observada = str(snapshot.release_observada or "")
            if not snapshot.online:
                raise ValidationError("O Runtime Agent não respondeu após o deployment.")
            if str(snapshot.status or "").lower() != "ok":
                raise ValidationError("O Runtime Agent informou status diferente de ok.")
            if int(snapshot.migrations_pending or 0) > 0:
                raise ValidationError("O sistema implantado possui migrações pendentes.")
            if plan.release_observada != str(plan.versao.numero):
                raise ValidationError("A release observada pelo Runtime Agent não corresponde à release do plano.")

            self._step(plan, "verify", "SUCCEEDED", f"Runtime Agent confirmou a release v{plan.versao.numero}.")
            validate_transition(plan.status, DeploymentPlan.STATUS_SUCCEEDED)
            plan.status = DeploymentPlan.STATUS_SUCCEEDED
            plan.finalizado_em = timezone.now()
            plan.save(update_fields=["status", "release_observada", "finalizado_em", "etapas"])
            return plan
        except (DeploymentExecutionError, ValidationError, DeploymentCenterError) as exc:
            self._fail_execution(plan, exc)
            return plan
        except Exception:
            self._fail_execution(plan, ValidationError("Falha inesperada durante o deployment."))
            return plan

    @transaction.atomic
    def cancel_plan(self, plan):
        self._assert_plan(plan)
        validate_transition(plan.status, DeploymentPlan.STATUS_CANCELLED)
        plan.status = DeploymentPlan.STATUS_CANCELLED
        plan.finalizado_em = timezone.now()
        plan.save(update_fields=["status", "finalizado_em"])
        return plan

    def _step(self, plan, name, status, message):
        etapas = list(plan.etapas or [])
        etapas.append({
            "name": str(name)[:50],
            "status": str(status)[:20],
            "message": str(message)[:300],
            "at": timezone.now().isoformat(),
        })
        plan.etapas = etapas[-100:]
        plan.save(update_fields=["etapas"])

    def _fail_execution(self, plan, exc):
        message = self._safe_error(exc)
        self._step(plan, "failure", "FAILED", message)
        if plan.status in {DeploymentPlan.STATUS_RUNNING, DeploymentPlan.STATUS_VERIFYING}:
            validate_transition(plan.status, DeploymentPlan.STATUS_FAILED)
        plan.status = DeploymentPlan.STATUS_FAILED
        plan.erro = message
        plan.finalizado_em = timezone.now()
        plan.save(update_fields=["status", "erro", "finalizado_em", "etapas", "release_observada"])

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
        if isinstance(exc, DeploymentExecutionError):
            return exc.message[:500]
        if isinstance(exc, DeploymentCenterError):
            return exc.message[:500]
        if isinstance(exc, ValidationError):
            return (exc.messages[0] if exc.messages else "Falha de validação.")[:500]
        return "Falha de validação."
