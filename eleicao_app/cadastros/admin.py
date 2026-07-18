from django.contrib import admin
from .models import Organograma, Cargos


@admin.register(Organograma)
class OrganogramaAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'sigla', ]

@admin.register(Cargos)
class CargosAdmin(admin.ModelAdmin):
    list_display = ['cargo', ]
