from django.contrib import admin
from .models import Eleitor, Candidato


@admin.register(Eleitor)
class EleitorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'unidade', ]

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ['cargo', 'nome', ]
