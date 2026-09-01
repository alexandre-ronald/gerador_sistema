import os
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from sistema.models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from sistema.services import GeradorService


class GeneratedFormDesignerTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="form-generator", password="test")
        self.sistema = Sistema.objects.create(usuario=user, nome="Cadastro Operacional", caminho_geracao="/tmp/djangoforge-test")
        self.modulo = Modulo.objects.create(sistema=self.sistema, nome="cadastros")
        self.entidade = Entidade.objects.create(modulo=self.modulo, nome="Pedido")
        Campo.objects.create(entidade=self.entidade, nome="descricao", tipo="TextField", verbose_name="Descrição")
        Campo.objects.create(entidade=self.entidade, nome="quantidade", tipo="IntegerField")
        Campo.objects.create(entidade=self.entidade, nome="ativo", tipo="BooleanField")
        Campo.objects.create(entidade=self.entidade, nome="interno", tipo="CharField", max_length=100)
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "forms": {
                    "Pedido": {
                        "title": "Dados do Pedido",
                        "sections": [
                            {"id": "principal", "title": "Dados principais", "description": "Informações para o cadastro.", "order": 0}
                        ],
                        "fields": [
                            {"name": "descricao", "order": 0, "section": "principal", "visible": True, "readonly": False, "width": 8, "label": "Descrição detalhada", "placeholder": "Informe a descrição", "help_text": "Descreva o pedido.", "widget": "textarea"},
                            {"name": "quantidade", "order": 1, "section": "principal", "visible": True, "readonly": True, "width": 4, "label": "Quantidade", "placeholder": "", "help_text": "", "widget": "number"},
                            {"name": "ativo", "order": 2, "section": "", "visible": True, "readonly": False, "width": 6, "label": "Ativo", "placeholder": "", "help_text": "", "widget": "checkbox"},
                            {"name": "interno", "order": 3, "section": "", "visible": False, "readonly": False, "width": 12, "label": "Interno", "placeholder": "", "help_text": "", "widget": "text"},
                        ],
                    }
                }
            },
        )

    def _context(self):
        return GeradorService(self.sistema.id)._prepare_context()

    def test_context_applies_designer_order_visibility_sections_and_widths(self):
        ctx = self._context()
        entidade = ctx["modulos"][0].entidades_geracao[0]
        self.assertTrue(entidade.form_designer_ready)
        self.assertEqual(entidade.form_title, "Dados do Pedido")
        self.assertEqual([field.codigo_nome for field in entidade.form_fields], ["descricao", "quantidade", "ativo"])
        self.assertNotIn("interno", [field.codigo_nome for field in entidade.form_fields])
        self.assertEqual(entidade.form_fields[0].width, 8)
        self.assertTrue(entidade.form_fields[1].readonly)
        self.assertEqual(entidade.form_sections[0].fields[0].codigo_nome, "ativo")
        self.assertEqual(entidade.form_sections[1].title, "Dados principais")

    def test_generated_modelform_excludes_hidden_and_applies_widget_metadata(self):
        ctx = self._context()
        modulo = ctx["modulos"][0]
        content = render_to_string(
            "gerador/snippets/forms_v2.txt",
            {**ctx, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud},
        )
        self.assertIn('"descricao",', content)
        self.assertIn('"quantidade",', content)
        self.assertIn('"ativo",', content)
        self.assertNotIn('"interno",', content)
        self.assertIn('forms.Textarea(attrs={"rows": 4})', content)
        self.assertIn('widget.attrs["placeholder"] = "Informe a descrição"', content)
        self.assertIn('self.fields["quantidade"].disabled = True', content)
        self.assertIn('self.fields["descricao"].label = "Descrição detalhada"', content)

    def test_generated_html_uses_sections_grid_and_only_visible_fields(self):
        ctx = self._context()
        modulo = ctx["modulos"][0]
        entidade = modulo.entidades_geracao[0]
        content = render_to_string(
            "gerador/snippets/html_form.txt",
            {**ctx, "app_name": modulo.app_name, "entidade": entidade},
        )
        self.assertIn("Dados do Pedido", content)
        self.assertIn("Dados principais", content)
        self.assertIn("Informações para o cadastro.", content)
        self.assertIn("col-12 col-md-8", content)
        self.assertIn("col-12 col-md-4", content)
        self.assertIn("{{ form.descricao }}", content)
        self.assertIn("{{ form.ativo }}", content)
        self.assertNotIn("form.interno", content)

    def test_without_saved_form_config_keeps_legacy_fields_with_default_layout(self):
        VersaoGeracao.objects.filter(sistema=self.sistema, numero=0).update(estrutura_json={})
        ctx = self._context()
        entidade = ctx["modulos"][0].entidades_geracao[0]
        self.assertEqual([field.codigo_nome for field in entidade.form_fields], ["ativo", "descricao", "interno", "quantidade"])
        self.assertTrue(all(field.width == 12 for field in entidade.form_fields))
        self.assertTrue(all(field.visible for field in entidade.form_fields))

    def test_real_generation_materializes_form_designer_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.sistema.caminho_geracao = temp_dir
            self.sistema.save(update_fields=["caminho_geracao"])

            service = GeradorService(self.sistema.id)
            service.gerar_projeto_completo()

            forms_path = Path(temp_dir) / "cadastros" / "forms.py"
            html_path = Path(temp_dir) / "cadastros" / "templates" / "cadastros" / "pedido_form.html"
            self.assertTrue(forms_path.exists())
            self.assertTrue(html_path.exists())

            forms_content = forms_path.read_text(encoding="utf-8")
            html_content = html_path.read_text(encoding="utf-8")

            self.assertIn('fields = [', forms_content)
            self.assertIn('"descricao",', forms_content)
            self.assertIn('"quantidade",', forms_content)
            self.assertIn('"ativo",', forms_content)
            self.assertNotIn('"interno",', forms_content)
            self.assertIn('forms.Textarea(attrs={"rows": 4})', forms_content)
            self.assertIn('self.fields["quantidade"].disabled = True', forms_content)
            self.assertIn('self.fields["descricao"].label = "Descrição detalhada"', forms_content)
            self.assertIn('widget.attrs["placeholder"] = "Informe a descrição"', forms_content)

            self.assertIn("Dados do Pedido", html_content)
            self.assertIn("Dados principais", html_content)
            self.assertIn("Informações para o cadastro.", html_content)
            self.assertIn("col-12 col-md-8", html_content)
            self.assertIn("col-12 col-md-4", html_content)
            self.assertIn("{{ form.descricao }}", html_content)
            self.assertIn("{{ form.quantidade }}", html_content)
            self.assertIn("{{ form.ativo }}", html_content)
            self.assertNotIn("form.interno", html_content)

            self.assertTrue(any("Validação concluída" in log for log in service.logs))
            self.assertIsNotNone(service.versao_gerada)
            self.assertGreater(service.versao_gerada.numero, 0)
