from django.urls import path
from . import views

app_name = 'cadastro'

urlpatterns = [
    
    # Rotas para Organograma
    path('organograma/', views.OrganogramaListView.as_view(), name='organograma_list'),
    path('organograma/novo/', views.OrganogramaCreateView.as_view(), name='organograma_create'),
    path('organograma/<int:pk>/editar/', views.OrganogramaUpdateView.as_view(), name='organograma_update'),
    path('organograma/<int:pk>/deletar/', views.OrganogramaDeleteView.as_view(), name='organograma_delete'),
    
]