from urllib.parse import parse_qs, urlparse

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .advanced_page_metric_preview import enrich_related_metrics_preview
from .advanced_page_preview import build_advanced_page_preview
from .advanced_pages import normalize_advanced_pages_config
from .application_preview import build_preview_shell, _report_navigation_rows
from .models import Entidade, Sistema
from .workspace_navigation_context import resolve_workspace_navigation_context
from .workspace_preview import project_workspace_preview


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
    return {"selected": selected,"requested": requested,"invalid": requested not in PREVIEW_DEVICES,"options": [dict(item) for item in PREVIEW_DEVICES.values()],**PREVIEW_DEVICES[selected]}


def _advanced_page_from_designer_referer(request, sistema):
    referer = str(request.META.get("HTTP_REFERER") or "").strip()
    if not referer: return ""
    parsed = urlparse(referer); designer_path = reverse("sistema:page_designer", args=[sistema.pk])
    if parsed.path != designer_path: return ""
    contextual_page = str((parse_qs(parsed.query).get("pagina") or [""])[0]).strip()
    if contextual_page: return contextual_page
    structure = _draft_structure(sistema); config = normalize_advanced_pages_config(structure.get("advanced_pages"), strict=False); first_enabled = next((page for page in config.get("pages", []) if page.get("enabled")), None)
    return str((first_enabled or {}).get("id") or "").strip()


def _advanced_record_entity_id(sistema, selected_page_id):
    selected_page_id = str(selected_page_id or "").strip()
    if not selected_page_id: return None
    structure = _draft_structure(sistema); config = normalize_advanced_pages_config(structure.get("advanced_pages"), strict=False); page = next((item for item in config.get("pages", []) if item.get("id") == selected_page_id and item.get("enabled")), None); context = (page or {}).get("context") or {}
    if context.get("kind") != "record" or not context.get("entity"): return None
    return Entidade.objects.filter(modulo__sistema=sistema, nome=context.get("entity")).values_list("pk", flat=True).first()


def _designer_links(sistema, preview):
    sistema_id = sistema.pk; entity_id = None
    for projection in ("form_page", "list_page", "workflow_page", "report_page"):
        page = preview.get(projection)
        if isinstance(page, dict) and page.get("entity_id"): entity_id = page.get("entity_id"); break
    def link(key, label, route, icon, *, entity_context=False, query=""):
        url = reverse(f"sistema:{route}", args=[sistema_id])
        if entity_context and entity_id: query = f"entidade={entity_id}" if not query else f"{query}&entidade={entity_id}"
        if query: url = f"{url}?{query}"
        return {"id": key, "label": label, "url": url, "icon": icon}
    page_kind = preview.get("page_kind") or "list"; contextual = []
    if page_kind == "advanced" and preview.get("advanced_page"): contextual.append(link("advanced", "Editar página", "page_designer", "bi-window-stack", query=f"pagina={preview['advanced_page']['id']}"))
    elif page_kind == "form": contextual.append(link("form", "Editar formulário", "form_designer", "bi-ui-checks-grid", entity_context=True))
    elif page_kind == "dashboard": contextual.append(link("dashboard", "Editar dashboard", "dashboard_builder", "bi-grid-1x2", entity_context=True))
    elif page_kind == "workflow": contextual.append(link("workflow", "Editar fluxo", "workflow_designer", "bi-diagram-3", entity_context=True))
    elif page_kind == "report": contextual.append(link("report", "Editar relatório", "report_designer", "bi-file-earmark-bar-graph", entity_context=True))
    else: contextual.append(link("crud", "Editar listagem", "crud_designer", "bi-table", entity_context=True))
    contextual.append(link("permissions", "Permissões", "permission_designer", "bi-shield-lock")); return contextual


def _ensure_workflow_navigation(sistema, preview):
    navigation = preview.setdefault("navigation", {}); projected = navigation.get("workflows"); workflows = list(projected) if isinstance(projected, list) else []; known_entities = {str(item.get("entity") or "") for item in workflows if isinstance(item, dict)}; estrutura = _draft_structure(sistema); stored = estrutura.get("workflows") if isinstance(estrutura.get("workflows"), dict) else {}
    if not stored: navigation["workflows"] = workflows; return
    entities = {entity.nome: entity for entity in Entidade.objects.filter(modulo__sistema=sistema).select_related("modulo").order_by("nome", "id")}; selected_entity_id = None; workflow_page = preview.get("workflow_page")
    if isinstance(workflow_page, dict): selected_entity_id = workflow_page.get("entity_id")
    for entity_name, config in stored.items():
        if entity_name in known_entities or not isinstance(config, dict) or config.get("enabled") is not True: continue
        entity = entities.get(entity_name)
        if entity is None: continue
        workflows.append({"entity_id": entity.pk,"entity": entity.nome,"label": entity.nome_plural or entity.nome,"icon": "bi-diagram-3","active": selected_entity_id == entity.pk})
    workflows.sort(key=lambda item: (str(item.get("label") or "").casefold(), item.get("entity_id") or 0)); navigation["workflows"] = workflows


def _apply_report_permissions(sistema, preview):
    simulation = preview.get("role_simulation") or {}; invalid_role = bool(simulation.get("invalid_role")); active_role = bool(simulation.get("active"))
    if not invalid_role and not active_role: return
    estrutura = _draft_structure(sistema); raw_rbac = estrutura.get("rbac") if isinstance(estrutura.get("rbac"), dict) else {}; report_policies = raw_rbac.get("reports")
    if not invalid_role and not isinstance(report_policies, dict): return
    role_id = simulation.get("selected_role_id") or ""
    def allowed(report):
        if invalid_role: return False
        entity_policies = report_policies.get(report.get("entity")) if isinstance(report_policies, dict) else None
        if not isinstance(entity_policies, dict): return False
        authorized_roles = entity_policies.get(report.get("id")); return isinstance(authorized_roles, list) and role_id in authorized_roles
    original_report_page = preview.get("report_page"); visible_reports = [report for report in (preview.get("reports") or []) if allowed(report)]; preview["reports"] = visible_reports; preview["entity_reports"] = [report for report in (preview.get("entity_reports") or []) if allowed(report)]; report_page = original_report_page if isinstance(original_report_page, dict) and allowed(original_report_page) else None; preview["report_page"] = report_page; preview.setdefault("navigation", {})["reports"] = _report_navigation_rows(visible_reports, report_page)
    if preview.get("page_kind") == "report" and original_report_page and report_page is None:
        preview["report_access_denied"] = {"entity": original_report_page.get("entity"),"id": original_report_page.get("id"),"title": original_report_page.get("title")}; preview["list_page"] = None; preview["form_page"] = None; preview["dashboard_page"] = None; preview["workflow_page"] = None; preview["content"] = {"title": "Relatório não disponível para este papel", "subtitle": "O Permission Designer não autorizou o papel simulado a acessar este relatório."}


def _apply_workspace_navigation(preview):
    """Substitui a navegação legada pela composição de todos os Workspaces visíveis."""
    workspace_preview = preview.get("workspace_preview") or {}
    if not workspace_preview.get("configured"): return
    navigation = preview.setdefault("navigation", {}); navigation["workspace_active"] = True; navigation["workspace_label"] = "Workspaces"; navigation["workspace_groups"] = []; navigation["workspace_sections"] = []
    active_context = preview.get("workspace_navigation_context") or {}; active_workspace_id = str(active_context.get("workspace_id") or ""); active_item_id = str(active_context.get("item_id") or "")
    for workspace in workspace_preview.get("navigation_groups") or []:
        sections = []
        for section in workspace.get("sections") or []:
            items = []
            for item in section.get("items") or []:
                projected = dict(item); projected["active"] = str(workspace.get("id") or "") == active_workspace_id and str(item.get("id") or "") == active_item_id; items.append(projected)
            if items:
                section_projection = {"id": section.get("id") or "","label": section.get("label") or "","icon": section.get("icon") or "","items": items}; sections.append(section_projection)
                navigation["workspace_sections"].append({**section_projection, "id": f"{workspace.get('id')}:{section.get('id')}", "label": f"{workspace.get('label') or 'Workspace'} · {section.get('label') or 'Seção'}"})
        if sections: navigation["workspace_groups"].append({"id": workspace.get("id") or "","label": workspace.get("label") or "Workspace","icon": workspace.get("icon") or "","sections": sections})


@login_required
def application_preview(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user); explicit_page_kind = request.GET.get("pagina"); referer_advanced_page = _advanced_page_from_designer_referer(request, sistema) if not explicit_page_kind else ""; requested_page_kind = explicit_page_kind or ("advanced" if referer_advanced_page else "list"); selected_advanced_page = request.GET.get("pagina_avancada") or referer_advanced_page; selected_entity_id = request.GET.get("entidade")
    if not selected_entity_id and requested_page_kind == "advanced": selected_entity_id = _advanced_record_entity_id(sistema, selected_advanced_page)
    preview = build_preview_shell(sistema,selected_entity_id=selected_entity_id,page_kind="list" if requested_page_kind == "advanced" else requested_page_kind,selected_report_id=request.GET.get("relatorio"),selected_workflow_state=request.GET.get("estado"),selected_role_id=request.GET.get("papel")); preview["device_preview"] = _device_preview(request.GET.get("dispositivo")); _apply_report_permissions(sistema, preview); _ensure_workflow_navigation(sistema, preview)
    if requested_page_kind == "advanced": build_advanced_page_preview(sistema, preview, selected_advanced_page); enrich_related_metrics_preview(preview)
    structure = _draft_structure(sistema); entities = list(Entidade.objects.filter(modulo__sistema=sistema).order_by("nome", "id")); preview["workspace_preview"] = project_workspace_preview(structure,role_simulation=preview.get("role_simulation") or {},entities=entities,selected_workspace_id=request.GET.get("workspace")); preview["workspace_navigation_context"] = resolve_workspace_navigation_context({"default_workspace": preview["workspace_preview"].get("selected_id"),"workspaces": preview["workspace_preview"].get("workspaces") or []},workspace_id=request.GET.get("workspace"),item_id=request.GET.get("workspace_item")); _apply_workspace_navigation(preview); preview["designer_links"] = _designer_links(sistema, preview)
    if preview.get("page_kind") == "workflow": template_name = "sistema/application_preview_workflow.html"
    elif preview.get("page_kind") == "advanced": template_name = "sistema/application_preview_advanced.html"
    else: template_name = "sistema/application_preview_roles.html"
    return render(request, template_name, {"sistema": sistema, "preview": preview})