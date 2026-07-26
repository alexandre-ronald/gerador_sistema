from django.urls import path
from . import views

app_name = 'custo'

urlpatterns = [
    
    # Rotas para Centro De Custos
    path('centro de custos/', views.Centro De CustosListView.as_view(), name='centro de custos_list'),
    path('centro de custos/novo/', views.Centro De CustosCreateView.as_view(), name='centro de custos_create'),
    path('centro de custos/<int:pk>/editar/', views.Centro De CustosUpdateView.as_view(), name='centro de custos_update'),
    path('centro de custos/<int:pk>/deletar/', views.Centro De CustosDeleteView.as_view(), name='centro de custos_delete'),
    
    # Rotas para Custo
    path('custo/', views.CustoListView.as_view(), name='custo_list'),
    path('custo/novo/', views.CustoCreateView.as_view(), name='custo_create'),
    path('custo/<int:pk>/editar/', views.CustoUpdateView.as_view(), name='custo_update'),
    path('custo/<int:pk>/deletar/', views.CustoDeleteView.as_view(), name='custo_delete'),
    
]