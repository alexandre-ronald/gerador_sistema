import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class GeneratedBusinessRulesTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="rules_generator", password="x")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sistema = Sistema.objects.create(usuario=user, nome="Rules Runtime", slug="rules-runtime", caminho_geracao=self.tmp.name)
        modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Pedido", gerar_crud_views=True)
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30)
        Campo.objects.create(entidade=self.entidade, nome="valor_total", tipo="DecimalField", max_digits=10, decimal_places=2)
        Campo.objects.create(entidade=self.entidade, nome="status_copia", tipo="CharField", max_length=30, blank=True)
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={"business_rules": {"Pedido": {"rules": [
            {"id":"default_status","name":"Status padrão","enabled":True,"event":"before_create","priority":1,"condition_mode":"all","conditions":[{"field":"status","operator":"is_empty","value_source":"literal","value":None}],"actions":[{"type":"set_value","field":"status","value":"PENDENTE"}]},
            {"id":"copy_status","name":"Copiar status","enabled":True,"event":"before_update","priority":2,"condition_mode":"all","conditions":[],"actions":[{"type":"copy_value","field":"status_copia","source_field":"status"}]},
            {"id":"reject_zero","name":"Rejeitar zero","enabled":True,"event":"before_save","priority":3,"condition_mode":"all","conditions":[{"field":"valor_total","operator":"lte","value_source":"literal","value":"0"}],"actions":[{"type":"reject","message":"Valor deve ser maior que zero."}]}
        ]}}})

    def test_generation_context_materializes_rules_with_generated_field_names(self):
        ctx = GeradorService(self.sistema.id)._prepare_context()
        entidade = ctx["modulos"][0].entidades_geracao[0]
        self.assertTrue(entidade.business_rules_ready)
        self.assertEqual([r["id"] for r in entidade.business_rules], ["default_status", "copy_status", "reject_zero"])
        self.assertEqual(entidade.business_rules[0]["actions"][0]["field"], "status")
        self.assertEqual(entidade.business_rules[1]["actions"][0]["source_field"], "status")

    def test_generated_runtime_is_closed_and_views_call_expected_events(self):
        service = GeradorService(self.sistema.id); ctx = service._prepare_context(); modulo = ctx["modulos"][0]
        from django.template.loader import render_to_string
        runtime = render_to_string("gerador/snippets/business_rules_runtime.txt", {**ctx,"app_name":modulo.app_name,"entidades":modulo.entidades_geracao,"entidades_crud":modulo.entidades_crud})
        views = render_to_string("gerador/snippets/views.txt", {**ctx,"app_name":modulo.app_name,"entidades":modulo.entidades_geracao,"entidades_crud":modulo.entidades_crud})
        self.assertIn("def run_business_rules(instance, event):", runtime)
        self.assertNotIn("eval(", runtime); self.assertNotIn("exec(", runtime)
        self.assertIn("run_business_rules(form.instance, 'before_create')", views)
        self.assertIn("run_business_rules(form.instance, 'before_update')", views)
        self.assertIn("run_business_rules(self.object, 'before_delete')", views)
        self.assertIn("form.add_error(None, exc)", views)

    def test_real_generation_creates_runtime_and_passes_runtime_validation(self):
        logs = GeradorService(self.sistema.id).gerar_projeto_completo()
        runtime_path = os.path.join(self.tmp.name, "core", "business_rules.py")
        views_path = os.path.join(self.tmp.name, "core", "views.py")
        self.assertTrue(os.path.isfile(runtime_path)); self.assertTrue(os.path.isfile(views_path))
        with open(runtime_path, encoding="utf-8") as f: runtime = f.read()
        self.assertIn("reject_zero", runtime); self.assertIn("Valor deve ser maior que zero.", runtime)
        self.assertTrue(any("Validação concluída" in item for item in logs))

    def test_no_rules_keeps_crud_without_rule_calls(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0); draft.estrutura_json = {}; draft.save(update_fields=["estrutura_json"])
        service = GeradorService(self.sistema.id); ctx = service._prepare_context(); modulo = ctx["modulos"][0]; entidade = modulo.entidades_geracao[0]
        self.assertFalse(entidade.business_rules_ready)
        from django.template.loader import render_to_string
        views = render_to_string("gerador/snippets/views.txt", {**ctx,"app_name":modulo.app_name,"entidades":modulo.entidades_geracao,"entidades_crud":modulo.entidades_crud})
        self.assertNotIn("run_business_rules(form.instance, 'before_create')", views)
        self.assertNotIn("run_business_rules(form.instance, 'before_update')", views)
