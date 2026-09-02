import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Ambiente, DeploymentPlan, Sistema, VersaoGeracao


User = get_user_model()


class DeploymentCenterUITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner_deploy", password="x")
        self.other = User.objects.create_user(username="other_deploy", password="x")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="DeployApp", slug="deployapp")
        self.draft = VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={})
        self.release = VersaoGeracao.objects.create(sistema=self.sistema, numero=1, status=VersaoGeracao.STATUS_RELEASED, estrutura_json={})
        self.ambiente = Ambiente.objects.create(sistema=self.sistema, tipo=Ambiente.TIPO_DEVELOPMENT, nome="Development", release_atual=self.release)
        self.client = Client()
        self.client.force_login(self.user)

    def config_payload(self):
        return {"enabled": True, "environments": {"DEVELOPMENT": {"executor": "local", "strategy": "docker_compose", "working_directory": "C:/apps/deployapp", "compose_file": "docker-compose.yml"}}}

    def test_page_is_owner_only(self):
        url = reverse("sistema:deployment_center", args=[self.sistema.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        other = Client(); other.force_login(self.other)
        self.assertEqual(other.get(url).status_code, 404)

    def test_page_sets_csrf_cookie(self):
        response = self.client.get(reverse("sistema:deployment_center", args=[self.sistema.pk]))
        self.assertIn("csrftoken", response.cookies)

    def test_save_config_persists_only_deployment_key(self):
        self.draft.estrutura_json = {"api": {"enabled": True}, "integrations": {"enabled": False, "items": []}}
        self.draft.save(update_fields=["estrutura_json"])
        response = self.client.post(reverse("sistema:save_deployment_config", args=[self.sistema.pk]), data=json.dumps(self.config_payload()), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertTrue(self.draft.estrutura_json["deployment"]["enabled"])
        self.assertEqual(self.draft.estrutura_json["api"], {"enabled": True})
        self.assertIn("integrations", self.draft.estrutura_json)

    def test_invalid_config_returns_structured_400(self):
        payload = self.config_payload(); payload["environments"]["PRODUCTION"] = payload["environments"].pop("DEVELOPMENT")
        response = self.client.post(reverse("sistema:save_deployment_config", args=[self.sistema.pk]), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "local_executor_forbidden")

    def test_create_plan_requires_promoted_released_version_and_snapshots_config(self):
        self.draft.estrutura_json = {"deployment": self.config_payload()}; self.draft.save(update_fields=["estrutura_json"])
        response = self.client.post(reverse("sistema:create_deployment_plan", args=[self.sistema.pk, self.ambiente.pk]), {"version_id": self.release.pk})
        self.assertEqual(response.status_code, 302)
        plan = DeploymentPlan.objects.get()
        self.assertEqual(plan.status, DeploymentPlan.STATUS_PLANNED)
        self.assertEqual(plan.executor, "local")
        self.assertEqual(plan.config_snapshot["working_directory"], "C:/apps/deployapp")

    def test_validate_plan_moves_to_ready_without_execution(self):
        self.draft.estrutura_json = {"deployment": self.config_payload()}; self.draft.save(update_fields=["estrutura_json"])
        plan = DeploymentPlan.objects.create(sistema=self.sistema, ambiente=self.ambiente, versao=self.release, criado_por=self.user, executor="local", strategy="docker_compose", config_snapshot=self.config_payload()["environments"]["DEVELOPMENT"])
        response = self.client.post(reverse("sistema:validate_deployment_plan", args=[self.sistema.pk, plan.pk]))
        self.assertEqual(response.status_code, 302)
        plan.refresh_from_db()
        self.assertEqual(plan.status, DeploymentPlan.STATUS_READY)

    def test_validate_plan_fails_if_promoted_release_changed(self):
        self.draft.estrutura_json = {"deployment": self.config_payload()}; self.draft.save(update_fields=["estrutura_json"])
        plan = DeploymentPlan.objects.create(sistema=self.sistema, ambiente=self.ambiente, versao=self.release, criado_por=self.user, executor="local", strategy="docker_compose", config_snapshot=self.config_payload()["environments"]["DEVELOPMENT"])
        self.ambiente.release_atual = None; self.ambiente.save(update_fields=["release_atual"])
        self.client.post(reverse("sistema:validate_deployment_plan", args=[self.sistema.pk, plan.pk]))
        plan.refresh_from_db()
        self.assertEqual(plan.status, DeploymentPlan.STATUS_FAILED)

    def test_cancel_plan(self):
        plan = DeploymentPlan.objects.create(sistema=self.sistema, ambiente=self.ambiente, versao=self.release, criado_por=self.user, executor="local", strategy="docker_compose", config_snapshot=self.config_payload()["environments"]["DEVELOPMENT"])
        self.client.post(reverse("sistema:cancel_deployment_plan", args=[self.sistema.pk, plan.pk]))
        plan.refresh_from_db(); self.assertEqual(plan.status, DeploymentPlan.STATUS_CANCELLED)
