"""Application Preview Studio — projeções visuais somente-leitura."""

from django.db.models import Prefetch

from .models import Entidade, Modulo


def build_preview_shell(sistema):
    """Projeta o shell visual da aplicação sem persistir configuração própria."""
    entity_queryset = Entidade.objects.order_by("nome", "id")
    modules = list(
        Modulo.objects.filter(sistema=sistema)
        .prefetch_related(Prefetch("entidades", queryset=entity_queryset))
        .order_by("nome", "id")
    )

    navigation = []
    for module in modules:
        items = [
            {
                "id": entity.pk,
                "name": entity.nome,
                "label": entity.nome_plural or entity.nome,
                "icon": "bi-table",
            }
            for entity in module.entidades.all()
            if entity.gerar_crud_views
        ]
        if items:
            navigation.append(
                {
                    "id": module.pk,
                    "name": module.nome,
                    "label": module.nome,
                    "items": items,
                }
            )

    return {
        "application": {
            "id": sistema.pk,
            "name": sistema.interface_nome or sistema.nome,
            "source_name": sistema.nome,
        },
        "interface": {
            "menu": sistema.tipo_menu,
            "mode": sistema.interface_modo,
            "density": sistema.interface_densidade,
            "primary": sistema.interface_cor_primaria,
            "accent": sistema.interface_cor_destaque,
            "breadcrumb": bool(sistema.interface_breadcrumb),
            "search": bool(sistema.interface_busca),
            "user_menu": bool(sistema.interface_menu_usuario),
        },
        "navigation": {
            "home": {"label": "Início", "icon": "bi-house-door"},
            "dashboard": {"label": "Dashboard", "icon": "bi-bar-chart-line"},
            "modules": navigation,
        },
        "content": {
            "title": "Visão geral",
            "subtitle": "Prévia do shell da aplicação gerada.",
        },
    }
