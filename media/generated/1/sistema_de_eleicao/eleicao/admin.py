from django.contrib import admin
from .models import Candidato, Cargo


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ['cargo', 'nome_do_candidato']

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'sigla']

