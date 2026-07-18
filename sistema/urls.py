from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
''
app_name = 'sistema'  # namespace

urlpatterns = [
    path('', views.lista_sistemas, name='lista'),
    path('novo/', views.criar_sistema, name='criar'),
    path('excluir/<int:sistema_id>/', views.excluir_sistema, name='excluir_sistema'),
    path('api/salvar-modelo/', views.salvar_modelo, name='salvar_modelo'),
    path("sistemas/<int:sistema_id>/editar/", views.editar_sistema, name="editar_sistema"),
    path("api/sistemas/<int:sistema_id>/", views.atualizar_sistema, name="atualizar_sistema"),

    # ROTA 1: A página com o Monitor de Log (HTML)
    path('gerar/<int:pk>/', views.gerar_sistema_view, name='gerar_sistema'),
    path('sistema/gerar/<int:sistema_id>/', views.gerar_e_zipar_sistema, name='gerar_sistema1'),


    # ROTA 2: A API que o JavaScript chama para processar (JSON)
    path('gerar/<int:pk>/processar/', views.processar_geracao_ajax, name='processar_geracao_ajax'),

    # ROTA 3: A página de sucesso final com as instruções
    path('gerar/<int:pk>/sucesso/', views.gerar_sucesso_view, name='gerar_sucesso'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)