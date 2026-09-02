import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .business_rules import (
    ALLOWED_ACTIONS,
    ALLOWED_CONDITION_MODES,
    ALLOWED_EVENTS,
    BusinessRuleError,
    compatible_operators,
    is_assignable,
    normalize_business_rules_config,
)
from .models import Entidade, Sistema, VersaoGeracao


def _field_metadata(field):
    metadata = {
        "name": field.nome,
        "label": field.verbose_name or field.nome.replace("_", " ").title(),
        "type": field.tipo,
        "editable": True,
    }
    metadata["operators"] = list(compatible_operators(metadata))
    metadata["assignable"] = is_assignable(metadata)
    return metadata


def _entity_metadata(entity):
    return {
        "name": entity.nome,
        "label": entity.nome,
        "fields": [_field_metadata(field) for field in entity.campos.all()],
    }


def _draft_business_rules(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        rules = versao.estrutura_json.get("business_rules")
        return rules if isinstance(rules, dict) else {}
    return {}


@login_required
def business_rules_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    entities = list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .prefetch_related("campos")
        .order_by("nome")
    )
    metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
    stored = _draft_business_rules(sistema)
    business_rules = {}
    for entity in entities:
        business_rules[entity.nome] = normalize_business_rules_config(
            entity.nome,
            metadata[entity.nome],
            stored.get(entity.nome),
        )
    return render(request, "sistema/business_rules_designer.html", {
        "sistema": sistema,
        "entities": entities,
        "business_rules_json": json.dumps(business_rules, ensure_ascii=False),
        "entity_metadata_json": json.dumps(metadata, ensure_ascii=False),
        "events_json": json.dumps(ALLOWED_EVENTS),
        "condition_modes_json": json.dumps(ALLOWED_CONDITION_MODES),
        "actions_json": json.dumps(ALLOWED_ACTIONS),
    })


@login_required
@require_http_methods(["POST"])
def salvar_business_rules(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_rules = payload.get("business_rules") if isinstance(payload, dict) else None
        if not isinstance(raw_rules, dict):
            raise BusinessRuleError("invalid_business_rules", "Contrato business_rules inválido.")

        entities = list(
            Entidade.objects.filter(modulo__sistema=sistema)
            .prefetch_related("campos")
            .order_by("nome")
        )
        metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
        unknown = set(raw_rules) - set(metadata)
        if unknown:
            raise BusinessRuleError("unknown_entity", f"Entidade não disponível: {sorted(unknown)[0]}")

        normalized = {}
        for entity_name, config in raw_rules.items():
            normalized[entity_name] = normalize_business_rules_config(
                entity_name,
                metadata[entity_name],
                config,
                strict=True,
            )

        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do Business Rules Designer", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["business_rules"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Business Rules Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({
            "status": "sucesso",
            "sistema_id": sistema.id,
            "business_rules": normalized,
        })
    except BusinessRuleError as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
