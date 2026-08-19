from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from .compiler import SpecificationCompiler
from .specification import EntitySpec, ModuleSpec, SystemSpec
from .specification_plan import CompilationPlan


class Gen0013ListagemTests(SimpleTestCase):
    def _spec(self, audit=False):
        entity = EntitySpec("Pessoa", "Pessoa", "pessoa", "Pessoas", "", True, True, False, ())
        module = ModuleSpec("Cadastro", "cadastro", "", (entity,))
        return SystemSpec("2.1", "Sistema Teste", "sistema_teste", "sistema-teste", "", "sqlite3", "lateral", False, False, False, audit, (module,))

    def test_list_artifact_uses_pagination_and_search(self):
        compiled = SpecificationCompiler(self._spec()).compile()
        item = next(x for x in compiled if x.path.endswith("pessoa_list.html"))
        self.assertIn("is_paginated", item.content)
        self.assertIn('name="q"', item.content)

    def test_generated_list_view_has_pagination_and_search(self):
        compiled = SpecificationCompiler(self._spec()).compile()
        item = next(x for x in compiled if item_path(item := x) == "cadastro/views.py")
        self.assertIn("paginate_by = 10", item.content)
        self.assertIn('self.request.GET.get("q"', item.content)


def item_path(item):
    return item.path


class Gen0014AuditTests(SimpleTestCase):
    def test_audit_disabled_does_not_generate_audit_app(self):
        paths = CompilationPlan(Gen0013ListagemTests()._spec(False)).paths()
        self.assertFalse(any(path.startswith("auditoria/") for path in paths))

    def test_audit_enabled_generates_complete_audit_app(self):
        spec = Gen0013ListagemTests()._spec(True)
        paths = CompilationPlan(spec).paths()
        for path in (
            "auditoria/apps.py", "auditoria/models.py", "auditoria/admin.py",
            "auditoria/request_context.py", "auditoria/middleware.py",
            "auditoria/signals.py", "auditoria/migrations/__init__.py",
        ):
            self.assertIn(path, paths)
        compiled = SpecificationCompiler(spec).compile()
        settings = next(x for x in compiled if x.path == "sistema_teste/settings.py")
        self.assertIn("auditoria.apps.AuditoriaConfig", settings.content)
        self.assertIn("auditoria.middleware.CurrentUserMiddleware", settings.content)

    def test_audit_artifacts_are_written(self):
        spec = Gen0013ListagemTests()._spec(True)
        with TemporaryDirectory() as tmp:
            SpecificationCompiler(spec).write(Path(tmp))
            self.assertTrue((Path(tmp) / "auditoria" / "models.py").exists())
            self.assertTrue((Path(tmp) / "auditoria" / "signals.py").exists())
