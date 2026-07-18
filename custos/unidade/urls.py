from django.urls import path
from . import views

app_name = 'unidade'

urlpatterns = [
    
    # Rotas para Unidade
    path('unidade/', views.UnidadeListView.as_view(), name='unidade_list'),
    path('unidade/novo/', views.UnidadeCreateView.as_view(), name='unidade_create'),
    path('unidade/<int:pk>/editar/', views.UnidadeUpdateView.as_view(), name='unidade_update'),
    path('unidade/<int:pk>/deletar/', views.UnidadeDeleteView.as_view(), name='unidade_delete'),
    
]