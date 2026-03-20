from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth do Django (Login/Logout)
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Home do Sistema (Protegida)
    path('', login_required(TemplateView.as_view(template_name='index.html')), name='index'),

    # Inclusão automática dos Apps Gerados
    
    path('cadastros/', include('cadastros.urls')),
    
    path('eleicao/', include('eleicao.urls')),
    
]