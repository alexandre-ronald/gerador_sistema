import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .advanced_pages import AdvancedPageContractError, normalize_advanced_pages_config
from .advanced_pages_semantics import validate_advanced_pages_semantics
from .models import Entidade, Sistema, VersaoGeracao


def _draft_structure(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        return versao.estrutura_json
    return {}


def _entity_metadata(sistema):
    entities = list(Entidade.objects.filter(modulo__sistema=sistema).select_related("modulo").prefetch_related("campos").order_by("modulo__nome", "nome"))
    metadata = []
    for entity in entities:
        metadata.append({"name": entity.nome, "label": entity.nome, "module": entity.modulo.nome, "fields": [{"name": field.nome, "label": field.verbose_name or field.nome} for field in entity.campos.all()]})
    return entities, metadata


def _catalogs(estrutura):
    workflows = estrutura.get("workflows") if isinstance(estrutura.get("workflows"), dict) else {}
    reports = estrutura.get("reports") if isinstance(estrutura.get("reports"), dict) else {}
    forms = estrutura.get("forms") if isinstance(estrutura.get("forms"), dict) else None
    dashboard = estrutura.get("dashboard") if isinstance(estrutura.get("dashboard"), dict) else None
    return workflows, reports, forms, dashboard


def _designer_catalog(estrutura):
    workflows, reports, forms, dashboard = _catalogs(estrutura)
    return {
        "forms": sorted(forms.keys()) if forms else [],
        "reports": {entity: [{"id": str(item.get("id") or ""), "name": str(item.get("name") or item.get("title") or item.get("id") or "")} for item in items if isinstance(item, dict) and item.get("id")] for entity, items in reports.items() if isinstance(items, list)},
        "workflows": {entity: [{"id": str(item.get("id") or ""), "name": str(item.get("name") or item.get("label") or item.get("id") or "")} for item in (value.get("transitions") or []) if isinstance(item, dict) and item.get("id")] for entity, value in workflows.items() if isinstance(value, dict)},
        "dashboard": bool(dashboard is not None),
    }


@login_required
def page_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    _, metadata = _entity_metadata(sistema)
    estrutura = _draft_structure(sistema)
    raw_config = estrutura.get("advanced_pages") if isinstance(estrutura.get("advanced_pages"), dict) else None
    config = normalize_advanced_pages_config(raw_config, strict=False)
    return render(request, "sistema/page_designer.html", {"sistema": sistema, "advanced_pages_json": json.dumps(config, ensure_ascii=False), "entities_json": json.dumps(metadata, ensure_ascii=False), "designer_catalog_json": json.dumps(_designer_catalog(estrutura), ensure_ascii=False)})


@login_required
@require_http_methods(["POST"])
def salvar_page_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_config = payload.get("advanced_pages") if isinstance(payload, dict) else None
        if not isinstance(raw_config, dict):
            raise AdvancedPageContractError("invalid_advanced_pages_config", "Contrato advanced_pages inválido.")
        _, metadata = _entity_metadata(sistema)
        estrutura = _draft_structure(sistema)
        workflows, reports, forms, dashboard = _catalogs(estrutura)
        normalized = validate_advanced_pages_semantics(raw_config, entities_metadata=metadata, workflows=workflows, reports=reports, forms=forms, dashboards=dashboard)
        versao, _ = VersaoGeracao.objects.get_or_create(sistema=sistema, numero=0, defaults={"descricao": "Rascunho do Advanced Page Designer", "estrutura_json": {}})
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["advanced_pages"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Advanced Page Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "advanced_pages": normalized})
    except AdvancedPageContractError as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
