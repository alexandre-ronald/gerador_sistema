from dataclasses import replace

from django.test import TestCase

from .compiler import SpecificationCompiler
from .specification import EntitySpec, FieldSpec, ModuleSpec, SystemSpec


def build_spec():
    entity = EntitySpec(
        name="Pessoa",
        class_name="Pessoa",
        technical_name="pessoa",
        plural_name="Pessoas",
        description="Cadastro de pessoas",
        generate_admin=True,
        generate_crud=True,
        generate_api=False,
        fields=(
            FieldSpec("Nome", "nome", "CharField", max_length=120),
            FieldSpec("Email", "email", "EmailField", max_length=255),
            FieldSpec("Idade", "idade", "IntegerField"),
        ),
    )
    module = ModuleSpec("Cadastro", "cadastro", "Módulo de cadastro", (entity,))
    return SystemSpec(
        version="2.1",
        name="Sistema Teste",
        technical_name="sistema_teste",
        slug="sistema-teste",
        description="Teste",
        database="sqlite3",
        menu="lateral",
        custom_user=False,
        rest_api=False,
        docker=False,
        audit=False,
        modules=(module,),
    )


class Gen0013PaginationFilteringTests(TestCase):
    def test_generated_list_view_has_search_and_pagination_contract(self):
        compiled = SpecificationCompiler(build_spec()).compile()
        views = next(i.content for i in compiled if i.path == "cadastro/views.py")
        listing = next(i.content for i in compiled if i.path.endswith("pessoa_list.html"))

        self.assertIn('request.GET.get("q"', views)
        self.assertIn('icontains=query', views)
        self.assertIn("paginate_by = 20", views)
        self.assertIn('request.GET.get("page_size"', views)
        self.assertIn('name="q"', listing)
        self.assertIn('name="page_size"', listing)
        self.assertIn("is_paginated", listing)

    def test_generated_list_preserves_search_and_page_size_in_navigation(self):
        compiled = SpecificationCompiler(build_spec()).compile()
        listing = next(i.content for i in compiled if i.path.endswith("pessoa_list.html"))
        self.assertIn("termo_busca|urlencode", listing)
        self.assertIn("page_obj.next_page_number", listing)
        self.assertIn("page_obj.previous_page_number", listing)


class Gen0014NavigationTests(TestCase):
    def test_generated_base_has_module_navigation_and_active_state(self):
        compiled = SpecificationCompiler(build_spec()).compile()
        base = next(i.content for i in compiled if i.path == "templates/base.html")
        self.assertIn("Módulos", base)
        self.assertIn("cadastro:pessoa_list", base)
        self.assertIn("request.resolver_match.url_name", base)
        self.assertIn("request.resolver_match.app_name", base)

    def test_both_menu_modes_remain_supported_by_specification(self):
        lateral = build_spec()
        self.assertEqual(lateral.menu, "lateral")
        superior = replace(lateral, menu="superior")
        compiled = SpecificationCompiler(superior).compile()
        base = next(i.content for i in compiled if i.path == "templates/base.html")
        self.assertIn("navbar-brand", base)
        self.assertIn("dropdown-menu", base)
