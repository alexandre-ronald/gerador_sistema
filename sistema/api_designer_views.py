import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .api_designer import API_OPERATIONS, APIDesignerError, normalize_api_config
from .models import Entidade, Sistema, VersaoGeracao


def _draft_structure(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        return versao.estrutura_json
    return {}


def _entities_metadata(sistema, estrutura):
    workflows = estrutura.get("workflows") if isinstance(estrutura.get("workflows"), dict) else {}
    entities = list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .prefetch_related("campos")
        .order_by("modulo__nome", "nome")
    )
    metadata = []
    for entity in entities:
        workflow = workflows.get(entity.nome) if isinstance(workflows.get(entity.nome), dict) else {}
        workflow_state_field = str(workflow.get("state_field") or "") if workflow.get("enabled") else ""
        metadata.append({
            "name": entity.nome,
            "label": entity.nome,
            "module": entity.modulo.nome,
            "api_eligible": bool(entity.gerar_endpoints_api),
            "workflow_state_field": workflow_state_field,
            "fields": [
                {
                    "name": field.nome,
                    "label": field.verbose_name or field.nome,
                    "type": field.tipo,
                    "editable": True,
                }
                for field in entity.campos.all().order_by("id")
            ],
        })
    return metadata


@login_required
def api_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    estrutura = _draft_structure(sistema)
    metadata = _entities_metadata(sistema, estrutura)
    raw_api = estrutura.get("api") if isinstance(estrutura.get("api"), dict) else {}
    api = normalize_api_config(sistema.gerar_api_rest, metadata, raw_api, strict=False)
    return render(request, "sistema/api_designer.html", {
        "sistema": sistema,
        "api_json": json.dumps(api, ensure_ascii=False),
        "entities_json": json.dumps(metadata, ensure_ascii=False),
        "api_operations_json": json.dumps(list(API_OPERATIONS), ensure_ascii=False),
    })


@login_required
@require_http_methods(["POST"])
def salvar_api_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_api = payload.get("api") if isinstance(payload, dict) else None
        if not isinstance(raw_api, dict):
            raise APIDesignerError("invalid_api_config", "Contrato da API inválido.")

        estrutura = _draft_structure(sistema)
        metadata = _entities_metadata(sistema, estrutura)
        normalized = normalize_api_config(sistema.gerar_api_rest, metadata, raw_api, strict=True)

        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do API Designer", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["api"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do API Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])

        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "api": normalized})
    except APIDesignerError as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
