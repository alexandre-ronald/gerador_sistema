from django.contrib import admin
from .models import Centro De Custos, Custo


@admin.register(Centro De Custos)
class Centro De CustosAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', ]

@admin.register(Custo)
class CustoAdmin(admin.ModelAdmin):
    list_display = ['centro_custo', 'data', 'descricao', 'valor', ]
