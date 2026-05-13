from django.urls import path
from . import views

app_name = 'cadastro'

urlpatterns = [
    
    # Rotas para Area
    path('area/', views.AreaListView.as_view(), name='area_list'),
    path('area/novo/', views.AreaCreateView.as_view(), name='area_create'),
    path('area/<int:pk>/editar/', views.AreaUpdateView.as_view(), name='area_update'),
    path('area/<int:pk>/deletar/', views.AreaDeleteView.as_view(), name='area_delete'),
    
]