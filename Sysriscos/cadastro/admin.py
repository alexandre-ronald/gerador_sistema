from django.contrib import admin
from .models import Organograma


@admin.register(Organograma)
class OrganogramaAdmin(admin.ModelAdmin):
    list_display = ['descrição', 'sigla', ]
