from django.urls import path
from . import views
from . import installer_views
from . import dashboard_builder_views
from . import validation_center_views
from . import release_manager_views
from . import environment_manager_views

app_name = 'sistema'

urlpatterns = [
    path('', views.lista_sistemas, name='lista'),
    path('novo/', views.criar_sistema, name='criar'),
    path('excluir/<int:sistema_id>/', views.excluir_sistema, name='excluir_sistema'),
    path('sistemas/<int:sistema_id>/editar/', views.editar_sistema, name='editar_sistema'),
    path('api/salvar-modelo/', views.salvar_modelo, name='salvar_modelo'),
    path('api/sistemas/<int:sistema_id>/', views.atualizar_sistema, name='atualizar_sistema'),
    path('gerar/<int:pk>/', views.gerar_sistema_view, name='gerar_sistema'),
    path('gerar/<int:pk>/processar/', installer_views.processar_geracao_ajax, name='processar_geracao_ajax'),
    path('gerar/<int:pk>/preview/', installer_views.preview_geracao, name='preview_geracao'),
    path('gerar/<int:pk>/sucesso/', views.gerar_sucesso_view, name='gerar_sucesso'),
    path('sistemas/<int:sistema_id>/dashboard-builder/', dashboard_builder_views.dashboard_builder, name='dashboard_builder'),
    path('sistemas/<int:sistema_id>/dashboard-builder/salvar/', dashboard_builder_views.salvar_dashboard, name='salvar_dashboard'),
    path('sistemas/<int:sistema_id>/validation-center/', validation_center_views.validation_center, name='validation_center'),
    path('sistemas/<int:sistema_id>/releases/', release_manager_views.release_manager, name='release_manager'),
    path('sistemas/<int:sistema_id>/releases/<int:version_id>/validar/', release_manager_views.validate_release, name='validate_release'),
    path('sistemas/<int:sistema_id>/releases/<int:version_id>/publicar/', release_manager_views.publish_release, name='publish_release'),
    path('sistemas/<int:sistema_id>/environments/', environment_manager_views.environment_manager, name='environment_manager'),
    path('sistemas/<int:sistema_id>/environments/<int:ambiente_id>/atualizar/', environment_manager_views.update_environment, name='update_environment'),
    path('sistemas/<int:sistema_id>/environments/<int:ambiente_id>/promover/', environment_manager_views.promote_environment, name='promote_environment'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('users/', views.users_view, name='users'),
    path('search/', views.search_view, name='search'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('usuario/novo/', views.registrar_usuario_view, name='registro'),
    path('sistemas/<int:pk>/download/', views.baixar_zip_sistema, name='baixar_zip'),
]
