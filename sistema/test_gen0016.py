from dataclasses import replace

from django.test import TestCase

from .compiler import SpecificationCompiler
from .test_gen0013_0014 import build_spec


class Gen0016AuditTests(TestCase):
    def _compiled(self, audit=True):
        return SpecificationCompiler(replace(build_spec(), audit=audit)).compile()

    def test_audit_artifacts_are_generated_only_when_enabled(self):
        enabled = {item.path for item in self._compiled(True)}
        disabled = {item.path for item in self._compiled(False)}

        self.assertIn("auditoria/models.py", enabled)
        self.assertIn("auditoria/services.py", enabled)
        self.assertIn("auditoria/middleware.py", enabled)
        self.assertNotIn("auditoria/models.py", disabled)

    def test_generated_audit_model_has_traceability_fields(self):
        model = next(i.content for i in self._compiled() if i.path == "auditoria/models.py")
        for field in ("usuario", "acao", "metodo", "caminho", "status_code", "ip", "user_agent", "detalhes"):
            self.assertIn(field, model)
        self.assertIn("ordering = (\"-criado_em\",)", model)

    def test_generated_settings_enable_audit_app_and_middleware(self):
        settings = next(i.content for i in self._compiled() if i.path.endswith("/settings.py"))
        self.assertIn('"auditoria"', settings)
        self.assertIn('"auditoria.middleware.AuditoriaMiddleware"', settings)

    def test_generated_audit_middleware_does_not_break_requests(self):
        middleware = next(i.content for i in self._compiled() if i.path == "auditoria/middleware.py")
        self.assertIn("self.get_response(request)", middleware)
        self.assertIn("except Exception:", middleware)
        self.assertIn("return response", middleware)
