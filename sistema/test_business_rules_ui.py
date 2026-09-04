import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class BusinessRulesDesignerUITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="owner_rules", password="test123")
        self.other = user_model.objects.create_user(username="other_rules", password="test123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Rules App", slug="rules-app")
        self.modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=self.modulo, nome="Pedido")
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30)
        Campo.objects.create(entidade=self.entidade, nome="valor_total", tipo="DecimalField", max_digits=10, decimal_places=2)
        Campo.objects.create(entidade=self.entidade, nome="ativo", tipo="BooleanField")
        self.url = reverse("sistema:business_rules_designer", args=[self.sistema.id])
        self.save_url = reverse("sistema:salvar_business_rules", args=[self.sistema.id])
        self.client.force_login(self.user)

    def payload(self):
        return {
            "business_rules": {
                "Pedido": {
                    "rules": [{
                        "id": "validar_valor",
                        "name": "Validar valor aprovado",
                        "enabled": True,
                        "event": "before_save",
                        "priority": 10,
                        "condition_mode": "all",
                        "conditions": [{
                            "field": "status",
                            "operator": "eq",
                            "value_source": "literal",
                            "value": "APROVADO",
                        }],
                        "actions": [{
                            "type": "reject",
                            "message": "Valor inválido.",
                        }],
                    }]
                }
            }
        }

    def test_designer_renders_friendly_business_language(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Regras de negócio")
        self.assertContains(response, "Design · GEN-063")
        self.assertContains(response, "Nova regra")
        self.assertContains(response, "Aplicar esta regra quando")
        self.assertContains(response, "O que deve acontecer?")
        self.assertContains(response, "Resumo da regra")
        self.assertContains(response, "Ao salvar um registro")
        self.assertContains(response, "Impedir o salvamento")
        self.assertContains(response, "Definir um valor")
        self.assertContains(response, "Copiar valor de outro campo")
        self.assertContains(response, "Todas precisam ser verdadeiras")
        self.assertContains(response, "Basta uma ser verdadeira")
        self.assertNotContains(response, "alert(")

    def test_visual_condition_editor_explains_logic_without_technical_terms(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Monte as condições como uma frase")
        self.assertContains(response, "Quando há mais de uma condição")
        self.assertContains(response, "Esta regra vale sempre")
        self.assertContains(response, "Condição ${i+1}")
        self.assertContains(response, "condition-join")
        self.assertContains(response, "conditionsHtml")
        self.assertContains(response, "Informe o valor esperado")
        self.assertContains(response, "Esta condição é completa e não precisa de outro valor")

    def test_keeps_internal_contract_values_behind_friendly_labels(self):
        response = self.client.get(self.url)
        self.assertContains(response, "before_save")
        self.assertContains(response, "set_value")
        self.assertContains(response, "copy_value")
        self.assertContains(response, "for igual a")
        self.assertContains(response, "for menor ou igual a")
        self.assertContains(response, "Um valor")
        self.assertContains(response, "Outro campo")

    def test_workspace_lists_business_rules_link(self):
        response = self.client.get(reverse("sistema:workspace", args=[self.sistema.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Business Rules")
        self.assertContains(response, self.url)

    def test_save_persists_normalized_rules_and_preserves_other_draft_keys(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"forms": {"Pedido": {"sections": []}}, "cruds": {"Pedido": {"title": "Pedidos"}}},
        )
        response = self.client.post(
            self.save_url,
            data=json.dumps(self.payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "sucesso")
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertIn("forms", draft.estrutura_json)
        self.assertIn("cruds", draft.estrutura_json)
        self.assertEqual(
            draft.estrutura_json["business_rules"]["Pedido"]["rules"][0]["id"],
            "validar_valor",
        )

    def test_save_rejects_unknown_entity(self):
        payload = self.payload()
        payload["business_rules"]["Fantasma"] = payload["business_rules"].pop("Pedido")
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "unknown_entity")

    def test_save_rejects_unsafe_lookup(self):
        payload = self.payload()
        payload["business_rules"]["Pedido"]["rules"][0]["conditions"][0]["field"] = "status__icontains"
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "invalid_condition_field")

    def test_save_rejects_invalid_action(self):
        payload = self.payload()
        payload["business_rules"]["Pedido"]["rules"][0]["actions"] = [{"type": "python", "value": "exec('x')"}]
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "invalid_action_type")

    def test_other_user_cannot_open_or_save(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(
            self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json").status_code,
            404,
        )

    def test_saved_rules_are_loaded_back_into_designer(self):
        response = self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.url)
        self.assertContains(response, "validar_valor")
        self.assertContains(response, "Validar valor aprovado")

    def test_save_requires_business_rules_object(self):
        response = self.client.post(self.save_url, data=json.dumps({"business_rules": []}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "invalid_business_rules")
