from django.contrib import admin
from .models import Unidade


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'sigla', ]
