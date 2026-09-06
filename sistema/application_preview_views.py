from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .application_preview import build_preview_shell, _report_navigation_rows
from .models import Entidade, Sistema


PREVIEW_DEVICES = {
    "desktop": {"id": "desktop", "label": "Desktop", "icon": "bi-display", "width": 1280},
    "tablet": {"id": "tablet", "label": "Tablet", "icon": "bi-tablet", "width": 820},
    "mobile": {"id": "mobile", "label": "Mobile", "icon": "bi-phone", "width": 390},
}


def _draft_structure(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    return versao.estrutura_json if versao and isinstance(versao.estrutura_json, dict) else {}


def _device_preview(raw_device):
    """Normaliza o dispositivo do Preview sem persistir estado no contrato."""
    requested = str(raw_device or "desktop").strip().lower()
    selected = requested if requested in PREVIEW_DEVICES else "desktop"
    return {
        "selected": selected,
        "requested": requested,
        "invalid": requested not in PREVIEW_DEVICES,
        "options": [dict(item) for item in PREVIEW_DEVICES.values()],
        **PREVIEW_DEVICES[selected],
    }


def _ensure_workflow_navigation(sistema, preview):
    """Garante que workflows persistidos como ativos apareçam na navegação do Preview."""
    navigation = preview.setdefault("navigation", {})
    projected = navigation.get("workflows")
    workflows = list(projected) if isinstance(projected, list) else []
    known_entities = {str(item.get("entity") or "") for item in workflows if isinstance(item, dict)}

    estrutura = _draft_structure(sistema)
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


def _apply_report_permissions(sistema, preview):
    """Filtra relatórios pelo papel simulado e bloqueia acesso direto não autorizado."""
    simulation = preview.get("role_simulation") or {}
    invalid_role = bool(simulation.get("invalid_role"))
    active_role = bool(simulation.get("active"))
    if not invalid_role and not active_role:
        return

    estrutura = _draft_structure(sistema)
    raw_rbac = estrutura.get("rbac") if isinstance(estrutura.get("rbac"), dict) else {}
    report_policies = raw_rbac.get("reports")

    # Compatibilidade: contratos RBAC antigos, anteriores às permissões de relatório,
    # mantêm a visão legada até serem salvos novamente no Permission Designer.
    if not invalid_role and not isinstance(report_policies, dict):
        return

    role_id = simulation.get("selected_role_id") or ""

    def allowed(report):
        if invalid_role:
            return False
        entity_policies = report_policies.get(report.get("entity")) if isinstance(report_policies, dict) else None
        if not isinstance(entity_policies, dict):
            return False
        authorized_roles = entity_policies.get(report.get("id"))
        return isinstance(authorized_roles, list) and role_id in authorized_roles

    original_report_page = preview.get("report_page")
    visible_reports = [report for report in (preview.get("reports") or []) if allowed(report)]
    preview["reports"] = visible_reports
    preview["entity_reports"] = [
        report
        for report in (preview.get("entity_reports") or [])
        if allowed(report)
    ]

    report_page = original_report_page if isinstance(original_report_page, dict) and allowed(original_report_page) else None
    preview["report_page"] = report_page
    preview.setdefault("navigation", {})["reports"] = _report_navigation_rows(visible_reports, report_page)

    if preview.get("page_kind") == "report" and original_report_page and report_page is None:
        preview["report_access_denied"] = {
            "entity": original_report_page.get("entity"),
            "id": original_report_page.get("id"),
            "title": original_report_page.get("title"),
        }
        preview["list_page"] = None
        preview["form_page"] = None
        preview["dashboard_page"] = None
        preview["workflow_page"] = None
        preview["content"] = {
            "title": "Relatório não disponível para este papel",
            "subtitle": "O Permission Designer não autorizou o papel simulado a acessar este relatório.",
        }


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
    preview["device_preview"] = _device_preview(request.GET.get("dispositivo"))
    _apply_report_permissions(sistema, preview)
    _ensure_workflow_navigation(sistema, preview)
    template_name = (
        "sistema/application_preview_workflow.html"
        if preview.get("page_kind") == "workflow"
        else "sistema/application_preview_roles.html"
    )
    return render(
        request,
        template_name,
        {"sistema": sistema, "preview": preview},
    )
