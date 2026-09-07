from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class GenerationRegressions0718Tests(SimpleTestCase):
    def test_relational_metric_without_binding_field_renders_generated_template(self):
        component = SimpleNamespace(
            id="contratos_ativos",
            type="metric",
            title="Contratos ativos",
            runtime_key="advanced_component_contratos_ativos",
            grid_column_start=1,
            grid_row_start=1,
            layout=SimpleNamespace(w=4, h=1),
            binding_field=None,
            binding_fields=[],
            config={},
            runtime_action=None,
        )
        page = SimpleNamespace(
            name="Central do Fornecedor",
            context=SimpleNamespace(entity="Fornecedor"),
            components=[component],
        )
        source = render_to_string("gerador/snippets/advanced_page_html.txt", {"page": page})
        self.assertIn("Contratos ativos", source)
        self.assertIn("advanced_component_contratos_ativos", source)

    def test_generated_admin_excludes_many_to_many_from_list_display(self):
        entidade = SimpleNamespace(
            gerar_admin=True,
            classe_nome="Fornecedor",
            campos_geracao=[
                SimpleNamespace(codigo_nome="nome", tipo="CharField"),
                SimpleNamespace(codigo_nome="categorias", tipo="ManyToManyField"),
            ],
        )
        source = render_to_string("gerador/snippets/admin_v2.txt", {"entidades": [entidade]})
        compile(source, "admin.py", "exec")
        self.assertIn("list_display = ['nome',]", source)
        self.assertNotIn("list_display = ['nome','categorias'", source)
        self.assertIn("filter_horizontal = ['categorias',]", source)
