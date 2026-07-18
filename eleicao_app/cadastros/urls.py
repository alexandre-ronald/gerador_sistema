from django.urls import path
from . import views

app_name = 'cadastros'

urlpatterns = [
    
    # Rotas para Organograma
    path('organograma/', views.OrganogramaListView.as_view(), name='organograma_list'),
    path('organograma/novo/', views.OrganogramaCreateView.as_view(), name='organograma_create'),
    path('organograma/<int:pk>/editar/', views.OrganogramaUpdateView.as_view(), name='organograma_update'),
    path('organograma/<int:pk>/deletar/', views.OrganogramaDeleteView.as_view(), name='organograma_delete'),
    
    # Rotas para Cargos
    path('cargos/', views.CargosListView.as_view(), name='cargos_list'),
    path('cargos/novo/', views.CargosCreateView.as_view(), name='cargos_create'),
    path('cargos/<int:pk>/editar/', views.CargosUpdateView.as_view(), name='cargos_update'),
    path('cargos/<int:pk>/deletar/', views.CargosDeleteView.as_view(), name='cargos_delete'),
    
]