from django.contrib import admin
from .models import Equipamento, Tipo_Intercorrencia, Intercorrencia


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ['area', 'nome', ]

@admin.register(Tipo_Intercorrencia)
class Tipo_IntercorrenciaAdmin(admin.ModelAdmin):
    list_display = ['nome', ]

@admin.register(Intercorrencia)
class IntercorrenciaAdmin(admin.ModelAdmin):
    list_display = ['area', 'criado_em', 'criado_por', 'data_final', 'data_inicio', 'descricao', 'dias_impacto', 'equipamento', 'qtd_exames_impactados', 'tipo', ]
