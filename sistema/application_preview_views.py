from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .application_preview import build_preview_shell
from .models import Entidade, Sistema


def _ensure_workflow_navigation(sistema, preview):
    """Garante que workflows persistidos como ativos apareçam na navegação do Preview."""
    navigation = preview.setdefault("navigation", {})
    projected = navigation.get("workflows")
    workflows = list(projected) if isinstance(projected, list) else []
    known_entities = {str(item.get("entity") or "") for item in workflows if isinstance(item, dict)}

    versao = sistema.versoes.filter(numero=0).first()
    estrutura = versao.estrutura_json if versao and isinstance(versao.estrutura_json, dict) else {}
    stored = estrutura.get("workflows") if isinstance(estrutura.get("workflows"), dict) else {}
    if not stored:
        navigation["workflows"] = workflows
        return

    entities = {
        entity.nome: entity
        for entity in Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .order_by("nome", "id")
    }
    selected_entity_id = None
    workflow_page = preview.get("workflow_page")
    if isinstance(workflow_page, dict):
        selected_entity_id = workflow_page.get("entity_id")

    for entity_name, config in stored.items():
        if entity_name in known_entities:
            continue
        if not isinstance(config, dict) or config.get("enabled") is not True:
            continue
        entity = entities.get(entity_name)
        if entity is None:
            continue
        workflows.append({
            "entity_id": entity.pk,
            "entity": entity.nome,
            "label": entity.nome_plural or entity.nome,
            "icon": "bi-diagram-3",
            "active": selected_entity_id == entity.pk,
        })

    workflows.sort(key=lambda item: (str(item.get("label") or "").casefold(), item.get("entity_id") or 0))
    navigation["workflows"] = workflows


@login_required
def application_preview(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    preview = build_preview_shell(
        sistema,
        selected_entity_id=request.GET.get("entidade"),
        page_kind=request.GET.get("pagina", "list"),
        selected_report_id=request.GET.get("relatorio"),
        selected_workflow_state=request.GET.get("estado"),
        selected_role_id=request.GET.get("papel"),
    )
    _ensure_workflow_navigation(sistema, preview)
    template_name = (
        "sistema/application_preview_workflow.html"
        if preview.get("page_kind") == "workflow"
        else "sistema/application_preview.html"
    )
    return render(
        request,
        template_name,
        {"sistema": sistema, "preview": preview},
    )
