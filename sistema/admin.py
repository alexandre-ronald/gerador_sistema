from django.contrib import admin

from .models import Campo, Entidade, Modulo, ObservabilityEvent, Sistema


class CampoInline(admin.TabularInline):
    model = Campo
    extra = 1
    show_change_link = True
    fk_name = "entidade"


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
    list_display = ["nome", "descricao"]
    inlines = [ModuloInline]
    search_fields = ["nome"]


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ["nome", "sistema"]
    inlines = [EntidadeInline]
    list_filter = ["sistema"]


@admin.register(Entidade)
class EntidadeAdmin(admin.ModelAdmin):
    list_display = ["nome", "modulo"]
    inlines = [CampoInline]
    list_filter = ["modulo__sistema"]


@admin.register(Campo)
class CampoAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "entidade"]
    list_filter = ["tipo", "entidade__modulo__sistema"]


@admin.register(ObservabilityEvent)
class ObservabilityEventAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "level",
        "category",
        "sistema",
        "ambiente",
        "event_name",
        "source",
    ]
    list_filter = ["level", "category", "sistema", "ambiente", "created_at"]
    search_fields = [
        "event_name",
        "message",
        "source",
        "correlation_id",
        "object_type",
        "object_id",
    ]
    readonly_fields = [
        "sistema",
        "ambiente",
        "usuario",
        "level",
        "category",
        "source",
        "event_name",
        "message",
        "correlation_id",
        "object_type",
        "object_id",
        "context",
        "created_at",
    ]
    ordering = ["-created_at", "-id"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
