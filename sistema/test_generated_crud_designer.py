import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from sistema.models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from sistema.services import GeradorService


class GeneratedCrudDesignerTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="crud-generator", password="test")
        self.sistema = Sistema.objects.create(usuario=user, nome="Operacao Comercial", caminho_geracao="/tmp/djangoforge-crud-test")
        self.modulo = Modulo.objects.create(sistema=self.sistema, nome="vendas")
        self.entidade = Entidade.objects.create(modulo=self.modulo, nome="Pedido", nome_plural="Pedidos")
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=30, verbose_name="Número")
        Campo.objects.create(entidade=self.entidade, nome="descricao", tipo="TextField", verbose_name="Descrição")
        Campo.objects.create(entidade=self.entidade, nome="ativo", tipo="BooleanField", verbose_name="Ativo")
        Campo.objects.create(entidade=self.entidade, nome="data", tipo="DateField", verbose_name="Data")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "cruds": {
                    "Pedido": {
                        "title": "Gestão de Pedidos",
                        "page_size": 50,
                        "default_order": "-numero",
                        "columns": [
                            {"field": "numero", "label": "Nº Pedido", "order": 0, "visible": True, "sortable": True},
                            {"field": "ativo", "label": "Situação", "order": 1, "visible": True, "sortable": False},
                            {"field": "descricao", "label": "Descrição interna", "order": 2, "visible": False, "sortable": True},
                        ],
                        "search": {"enabled": True, "fields": ["numero"], "placeholder": "Pesquisar número"},
                        "filters": [
                            {"field": "ativo", "label": "Ativo", "type": "boolean", "order": 0},
                            {"field": "numero", "label": "Número contém", "type": "text", "order": 1},
                        ],
                        "actions": {"create": False, "view": True, "edit": True, "delete": False},
                    }
                }
            },
        )

    def _context(self):
        return GeradorService(self.sistema.id)._prepare_context()

    def test_context_materializes_crud_contract_with_safe_generated_names(self):
        ctx = self._context()
        entidade = ctx["modulos"][0].entidades_geracao[0]
        self.assertTrue(entidade.crud_designer_ready)
        self.assertEqual(entidade.crud_title, "Gestão de Pedidos")
        self.assertEqual(entidade.crud_page_size, 50)
        self.assertEqual(entidade.crud_default_order, "-numero")
        self.assertEqual([item.codigo_nome for item in entidade.crud_visible_columns], ["numero", "ativo"])
        self.assertEqual(entidade.crud_search_fields, ["numero"])
        self.assertEqual([item.param for item in entidade.crud_filters], ["filter_ativo", "filter_numero"])
        self.assertFalse(entidade.crud_actions.create)
        self.assertTrue(entidade.crud_actions.view)
        self.assertFalse(entidade.crud_actions.delete)

    def test_generated_views_use_allowlists_filters_ordering_and_pagination(self):
        ctx = self._context()
        modulo = ctx["modulos"][0]
        content = render_to_string(
            "gerador/snippets/views.txt",
            {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud},
        )
        self.assertIn("paginate_by = 50", content)
        self.assertIn("Q(numero__icontains=query)", content)
        self.assertNotIn("Q(descricao__icontains=query)", content)
        self.assertIn("filter_ativo", content)
        self.assertIn("queryset.filter(ativo=True)", content)
        self.assertIn("numero__icontains=value_numero", content)
        self.assertIn("allowed_ordering = ['numero', '-numero', 'descricao', '-descricao']", content)
        self.assertIn("queryset.order_by('-numero')", content)
        self.assertNotIn("class PedidoCreateView", content)
        self.assertIn("class PedidoDetailView", content)
        self.assertIn("class PedidoUpdateView", content)
        self.assertNotIn("class PedidoDeleteView", content)

    def test_generated_urls_and_list_respect_actions_and_columns(self):
        ctx = self._context()
        modulo = ctx["modulos"][0]
        local = {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud}
        urls = render_to_string("gerador/snippets/urls_app_v2.txt", local)
        entidade = modulo.entidades_geracao[0]
        html = render_to_string("gerador/snippets/html_list.txt", {**local, "entidade": entidade})

        self.assertIn("pedido_detail", urls)
        self.assertIn("pedido_update", urls)
        self.assertNotIn("pedido_create", urls)
        self.assertNotIn("pedido_delete", urls)
        self.assertIn("Gestão de Pedidos", html)
        self.assertIn("Nº Pedido", html)
        self.assertIn("Situação", html)
        self.assertNotIn("Descrição interna</th>", html)
        self.assertIn('name="filter_ativo"', html)
        self.assertIn('name="filter_numero"', html)
        self.assertIn("pedido_detail", html)
        self.assertIn("pedido_update", html)
        self.assertNotIn("pedido_delete", html)
        self.assertNotIn("pedido_create", html)

    def test_without_saved_crud_config_keeps_legacy_runtime(self):
        VersaoGeracao.objects.filter(sistema=self.sistema, numero=0).update(estrutura_json={})
        ctx = self._context()
        modulo = ctx["modulos"][0]
        entidade = modulo.entidades_geracao[0]
        self.assertFalse(entidade.crud_designer_ready)

        local = {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud}
        views = render_to_string("gerador/snippets/views.txt", local)
        urls = render_to_string("gerador/snippets/urls_app_v2.txt", local)
        html = render_to_string("gerador/snippets/html_list.txt", {**local, "entidade": entidade})

        self.assertIn("paginate_by = 10", views)
        self.assertIn("Q(numero__icontains=query)", views)
        self.assertIn("Q(descricao__icontains=query)", views)
        self.assertIn("class PedidoCreateView", views)
        self.assertIn("class PedidoUpdateView", views)
        self.assertIn("class PedidoDeleteView", views)
        self.assertNotIn("class PedidoDetailView", views)
        self.assertIn("pedido_create", urls)
        self.assertIn("pedido_update", urls)
        self.assertIn("pedido_delete", urls)
        self.assertNotIn("pedido_detail", urls)
        self.assertIn("Pesquisar registros...", html)

    def test_real_generation_materializes_crud_designer_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.sistema.caminho_geracao = temp_dir
            self.sistema.save(update_fields=["caminho_geracao"])

            service = GeradorService(self.sistema.id)
            service.gerar_projeto_completo()

            views_path = Path(temp_dir) / "vendas" / "views.py"
            urls_path = Path(temp_dir) / "vendas" / "urls.py"
            list_path = Path(temp_dir) / "vendas" / "templates" / "vendas" / "pedido_list.html"
            detail_path = Path(temp_dir) / "vendas" / "templates" / "vendas" / "pedido_detail.html"

            self.assertTrue(views_path.exists())
            self.assertTrue(urls_path.exists())
            self.assertTrue(list_path.exists())
            self.assertTrue(detail_path.exists())

            views = views_path.read_text(encoding="utf-8")
            urls = urls_path.read_text(encoding="utf-8")
            html = list_path.read_text(encoding="utf-8")
            detail = detail_path.read_text(encoding="utf-8")

            self.assertIn("paginate_by = 50", views)
            self.assertIn("allowed_ordering", views)
            self.assertIn("filter_ativo", views)
            self.assertIn("class PedidoDetailView", views)
            self.assertNotIn("class PedidoCreateView", views)
            self.assertNotIn("class PedidoDeleteView", views)
            self.assertIn("pedido_detail", urls)
            self.assertNotIn("pedido_create", urls)
            self.assertIn("Gestão de Pedidos", html)
            self.assertIn("Nº Pedido", html)
            self.assertIn("Detalhes do registro", detail)
            self.assertTrue(any("Validação concluída" in log for log in service.logs))
            self.assertIsNotNone(service.versao_gerada)
            self.assertGreater(service.versao_gerada.numero, 0)
