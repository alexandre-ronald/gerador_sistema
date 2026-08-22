from django.contrib import admin
from .models import FuncionRio, Organograma


@admin.register(FuncionRio)
class FuncionRioAdmin(admin.ModelAdmin):
    list_display = ['cpf', 'data_de_admissao', 'nome_completo']

@admin.register(Organograma)
class OrganogramaAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'sigla']

