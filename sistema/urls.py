from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import generation_export, stabilization, views

app_name = "sistema"

urlpatterns = [
    path("", views.lista_sistemas, name="lista"),
    path("novo/", stabilization.criar_sistema_seguro, name="criar"),
    path(
        "excluir/<int:sistema_id>/",
        stabilization.secured_post(views.excluir_sistema),
        name="excluir_sistema",
    ),
    path("api/salvar-modelo/", stabilization.salvar_modelo_seguro, name="salvar_modelo"),
    path(
        "sistemas/<int:sistema_id>/editar/",
        stabilization.editar_sistema_seguro,
        name="editar_sistema",
    ),
    path(
        "api/sistemas/<int:sistema_id>/",
        stabilization.atualizar_sistema_seguro,
        name="atualizar_sistema",
    ),
    path("gerar/<int:pk>/", stabilization.secured_get(views.gerar_sistema_view), name="gerar_sistema"),
    path(
        "sistema/gerar/<int:sistema_id>/",
        stabilization.secured_get(views.gerar_e_zipar_sistema),
        name="gerar_sistema1",
    ),
    path(
        "gerar/<int:pk>/processar/",
        stabilization.secured(generation_export.processar_geracao_ajax),
        name="processar_geracao_ajax",
    ),
    path(
        "gerar/<int:pk>/sucesso/",
        stabilization.secured_get(views.gerar_sucesso_view),
        name="gerar_sucesso",
    ),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("analytics/", views.analytics_view, name="analytics"),
    path("users/", views.users_view, name="users"),
    path("search/", views.search_view, name="search"),
    path("profile/", views.profile_view, name="profile"),
    path("settings/", views.settings_view, name="settings"),
    path("usuario/novo/", views.registrar_usuario_view, name="registro"),
    path(
        "sistemas/<int:pk>/download/",
        stabilization.secured_get(views.baixar_zip_sistema),
        name="baixar_zip",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
