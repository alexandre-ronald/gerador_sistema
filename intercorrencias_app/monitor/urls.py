from django.urls import path
from . import views

app_name = 'monitor'

urlpatterns = [
    
    # Rotas para Equipamento
    path('equipamento/', views.EquipamentoListView.as_view(), name='equipamento_list'),
    path('equipamento/novo/', views.EquipamentoCreateView.as_view(), name='equipamento_create'),
    path('equipamento/<int:pk>/editar/', views.EquipamentoUpdateView.as_view(), name='equipamento_update'),
    path('equipamento/<int:pk>/deletar/', views.EquipamentoDeleteView.as_view(), name='equipamento_delete'),
    
    # Rotas para Tipo_Intercorrencia
    path('tipo_intercorrencia/', views.Tipo_IntercorrenciaListView.as_view(), name='tipo_intercorrencia_list'),
    path('tipo_intercorrencia/novo/', views.Tipo_IntercorrenciaCreateView.as_view(), name='tipo_intercorrencia_create'),
    path('tipo_intercorrencia/<int:pk>/editar/', views.Tipo_IntercorrenciaUpdateView.as_view(), name='tipo_intercorrencia_update'),
    path('tipo_intercorrencia/<int:pk>/deletar/', views.Tipo_IntercorrenciaDeleteView.as_view(), name='tipo_intercorrencia_delete'),
    
    # Rotas para Intercorrencia
    path('intercorrencia/', views.IntercorrenciaListView.as_view(), name='intercorrencia_list'),
    path('intercorrencia/novo/', views.IntercorrenciaCreateView.as_view(), name='intercorrencia_create'),
    path('intercorrencia/<int:pk>/editar/', views.IntercorrenciaUpdateView.as_view(), name='intercorrencia_update'),
    path('intercorrencia/<int:pk>/deletar/', views.IntercorrenciaDeleteView.as_view(), name='intercorrencia_delete'),
    
]