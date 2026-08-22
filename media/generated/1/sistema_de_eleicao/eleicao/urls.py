from django.urls import path
from . import views

app_name = 'eleicao'

urlpatterns = [

    path('candidato/', views.CandidatoListView.as_view(), name='candidato_list'),
    path('candidato/novo/', views.CandidatoCreateView.as_view(), name='candidato_create'),
    path('candidato/<int:pk>/editar/', views.CandidatoUpdateView.as_view(), name='candidato_update'),
    path('candidato/<int:pk>/deletar/', views.CandidatoDeleteView.as_view(), name='candidato_delete'),

    path('cargo/', views.CargoListView.as_view(), name='cargo_list'),
    path('cargo/novo/', views.CargoCreateView.as_view(), name='cargo_create'),
    path('cargo/<int:pk>/editar/', views.CargoUpdateView.as_view(), name='cargo_update'),
    path('cargo/<int:pk>/deletar/', views.CargoDeleteView.as_view(), name='cargo_delete'),

]
