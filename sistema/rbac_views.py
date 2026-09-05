import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Entidade, Sistema, VersaoGeracao
from .rbac import CRUD_ACTIONS, RBACError, normalize_rbac_config


def _draft_structure(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        return versao.estrutura_json
    return {}


def _entities_metadata(sistema):
    entities = list(Entidade.objects.filter(modulo__sistema=sistema).select_related("modulo").order_by("modulo__nome", "nome"))
    metadata = [{"name": entity.nome, "label": entity.nome, "module": entity.modulo.nome} for entity in entities]
    return entities, metadata


def _workflow_metadata(estrutura):
    workflows = estrutura.get("workflows")
    return workflows if isinstance(workflows, dict) else {}


def _report_metadata(estrutura):
    reports = estrutura.get("reports")
    return reports if isinstance(reports, dict) else {}


def _report_ui_metadata(reports):
    result = {}
    for entity_name, collection in reports.items():
        if not isinstance(collection, list):
            continue
        result[entity_name] = [
            {
                "id": str(item.get("id") or ""),
                "label": str((item.get("navigation") or {}).get("label") or item.get("title") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("id") or ""),
            }
            for item in collection
            if isinstance(item, dict) and item.get("id") and item.get("enabled") is True
        ]
    return result


@login_required
def permission_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    _, metadata = _entities_metadata(sistema)
    estrutura = _draft_structure(sistema)
    workflows = _workflow_metadata(estrutura)
    reports = _report_metadata(estrutura)
    raw_rbac = estrutura.get("rbac") if isinstance(estrutura.get("rbac"), dict) else {}
    rbac = normalize_rbac_config(metadata, workflows, raw_rbac, strict=False, reports=reports)

    workflow_ui = {}
    for entity_name, workflow in workflows.items():
        if not isinstance(workflow, dict): continue
        workflow_ui[entity_name] = [{"id": str(item.get("id") or ""), "label": str(item.get("label") or item.get("id") or "")} for item in (workflow.get("transitions") or []) if isinstance(item, dict) and item.get("id")]

    return render(request, "sistema/permission_designer.html", {
        "sistema": sistema,
        "crud_actions_json": json.dumps(list(CRUD_ACTIONS), ensure_ascii=False),
        "entities_json": json.dumps(metadata, ensure_ascii=False),
        "workflows_json": json.dumps(workflow_ui, ensure_ascii=False),
        "reports_json": json.dumps(_report_ui_metadata(reports), ensure_ascii=False),
        "rbac_json": json.dumps(rbac, ensure_ascii=False),
    })


@login_required
@require_http_methods(["POST"])
def salvar_rbac(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_rbac = payload.get("rbac") if isinstance(payload, dict) else None
        if not isinstance(raw_rbac, dict): raise RBACError("invalid_rbac_config", "Contrato RBAC inválido.")
        _, metadata = _entities_metadata(sistema)
        estrutura = _draft_structure(sistema)
        workflows = _workflow_metadata(estrutura)
        reports = _report_metadata(estrutura)
        normalized = normalize_rbac_config(metadata, workflows, raw_rbac, strict=True, reports=reports)

        versao, _ = VersaoGeracao.objects.get_or_create(sistema=sistema, numero=0, defaults={"descricao": "Rascunho do Permission Designer", "estrutura_json": {}})
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["rbac"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Permission Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "rbac": normalized})
    except RBACError as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
