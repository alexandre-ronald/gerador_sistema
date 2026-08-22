from django.urls import path
from . import views

app_name = 'gestao_de_pessoas'

urlpatterns = [

    path('funcionario/', views.FuncionRioListView.as_view(), name='funcionario_list'),
    path('funcionario/novo/', views.FuncionRioCreateView.as_view(), name='funcionario_create'),
    path('funcionario/<int:pk>/editar/', views.FuncionRioUpdateView.as_view(), name='funcionario_update'),
    path('funcionario/<int:pk>/deletar/', views.FuncionRioDeleteView.as_view(), name='funcionario_delete'),

    path('organograma/', views.OrganogramaListView.as_view(), name='organograma_list'),
    path('organograma/novo/', views.OrganogramaCreateView.as_view(), name='organograma_create'),
    path('organograma/<int:pk>/editar/', views.OrganogramaUpdateView.as_view(), name='organograma_update'),
    path('organograma/<int:pk>/deletar/', views.OrganogramaDeleteView.as_view(), name='organograma_delete'),

]
