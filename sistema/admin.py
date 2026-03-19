from django.contrib import admin
from .models import Sistema, Modulo, Entidade, Campo

class CampoInline(admin.TabularInline):           # ← aqui
    model = Campo
    extra = 1
    show_change_link = True
    fk_name = 'entidade'                          # ← adicione esta linha


class EntidadeInline(admin.TabularInline):
    model = Entidade
    extra = 1
    show_change_link = True

class ModuloInline(admin.TabularInline):
    model = Modulo
    extra = 1
    show_change_link = True


@admin.register(Sistema)
class SistemaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'descricao']
    inlines = [ModuloInline]
    search_fields = ['nome']


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ['nome', 'sistema']
    inlines = [EntidadeInline]
    list_filter = ['sistema']


@admin.register(Entidade)
class EntidadeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'modulo']
    inlines = [CampoInline]
    list_filter = ['modulo__sistema']


@admin.register(Campo)
class CampoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'entidade']
    list_filter = ['tipo', 'entidade__modulo__sistema']