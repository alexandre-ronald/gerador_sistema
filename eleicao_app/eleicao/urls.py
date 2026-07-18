from django.urls import path
from . import views

app_name = 'eleicao'

urlpatterns = [
    
    # Rotas para Eleitor
    path('eleitor/', views.EleitorListView.as_view(), name='eleitor_list'),
    path('eleitor/novo/', views.EleitorCreateView.as_view(), name='eleitor_create'),
    path('eleitor/<int:pk>/editar/', views.EleitorUpdateView.as_view(), name='eleitor_update'),
    path('eleitor/<int:pk>/deletar/', views.EleitorDeleteView.as_view(), name='eleitor_delete'),
    
    # Rotas para Candidato
    path('candidato/', views.CandidatoListView.as_view(), name='candidato_list'),
    path('candidato/novo/', views.CandidatoCreateView.as_view(), name='candidato_create'),
    path('candidato/<int:pk>/editar/', views.CandidatoUpdateView.as_view(), name='candidato_update'),
    path('candidato/<int:pk>/deletar/', views.CandidatoDeleteView.as_view(), name='candidato_delete'),
    
]