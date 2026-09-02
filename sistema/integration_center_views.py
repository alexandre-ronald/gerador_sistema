import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .integration_center import IntegrationCenterError, normalize_integrations_config
from .models import Sistema, VersaoGeracao


def _draft_structure(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        return versao.estrutura_json
    return {}


@login_required
def integration_center(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    estrutura = _draft_structure(sistema)
    raw = estrutura.get("integrations") if isinstance(estrutura.get("integrations"), dict) else {}
    integrations = normalize_integrations_config(raw, strict=False)
    return render(request, "sistema/integration_center.html", {
        "sistema": sistema,
        "integrations_json": json.dumps(integrations, ensure_ascii=False),
    })


@login_required
@require_http_methods(["POST"])
def salvar_integration_center(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw = payload.get("integrations") if isinstance(payload, dict) else None
        if not isinstance(raw, dict):
            raise IntegrationCenterError("invalid_integrations_config", "Contrato de integrações inválido.")
        normalized = normalize_integrations_config(raw, strict=True)
        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do Integration Center", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["integrations"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Integration Center"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "integrations": normalized})
    except IntegrationCenterError as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
