from django.template.loader import render_to_string
from django.test import SimpleTestCase


class DashboardHomeTemplateTests(SimpleTestCase):
    def test_dashboard_uses_djangoforge_control_center(self):
        source = render_to_string(
            "sistema/dashboard.html",
            {
                "sistemas": [],
                "total_modulos": 0,
                "total_entidades": 0,
                "total_zips": 0,
            },
        )
        self.assertIn("DjangoForge Control Center", source)
        self.assertIn("Visão geral da plataforma", source)
        self.assertIn("Design → Build → Run", source)
        self.assertIn("Acesso rápido", source)
        self.assertIn("Sistemas recentes", source)
        self.assertNotIn("Painel de Controle", source)
        self.assertNotIn("Sistemas Mapeados", source)

    def test_dashboard_empty_state_is_operational(self):
        source = render_to_string(
            "sistema/dashboard.html",
            {
                "sistemas": [],
                "total_modulos": 0,
                "total_entidades": 0,
                "total_zips": 0,
            },
        )
        self.assertIn("Nenhum sistema cadastrado", source)
        self.assertIn("Criar primeiro sistema", source)
