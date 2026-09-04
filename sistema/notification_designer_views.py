import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Entidade, Sistema, VersaoGeracao


EVENTS = {"created", "updated", "deleted"}
AUDIENCES = {"users_with_view_permission"}


def _draft_notifications(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        notifications = versao.estrutura_json.get("notifications")
        return notifications if isinstance(notifications, dict) else {}
    return {}


def _normalize_rule(entity_name, raw, index=1, strict=False):
    raw = raw if isinstance(raw, dict) else {}
    rule_id = str(raw.get("id") or f"notificacao_{index}").strip().lower().replace(" ", "_")
    event = str(raw.get("event") or "created")
    audience = str(raw.get("audience") or "users_with_view_permission")
    if strict and event not in EVENTS:
        raise ValueError(f"Evento de notificação inválido em {entity_name}: {event}")
    if strict and audience not in AUDIENCES:
        raise ValueError(f"Público da notificação inválido em {entity_name}: {audience}")
    if event not in EVENTS:
        event = "created"
    if audience not in AUDIENCES:
        audience = "users_with_view_permission"
    return {
        "id": rule_id,
        "enabled": bool(raw.get("enabled", True)),
        "event": event,
        "title": str(raw.get("title") or f"Atualização em {entity_name}"),
        "message": str(raw.get("message") or f"Houve uma atualização em {entity_name}."),
        "audience": audience,
    }


def _normalize_entity_rules(entity_name, raw, strict=False):
    items = raw if isinstance(raw, list) else []
    result = []
    ids = set()
    for index, item in enumerate(items, start=1):
        rule = _normalize_rule(entity_name, item, index=index, strict=strict)
        if rule["id"] in ids:
            if strict:
                raise ValueError(f"Identificador de notificação duplicado em {entity_name}: {rule['id']}")
            continue
        ids.add(rule["id"])
        result.append(rule)
    return result


@login_required
def notification_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    entities = list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .prefetch_related("campos")
        .order_by("nome")
    )
    stored = _draft_notifications(sistema)
    notifications = {
        entity.nome: _normalize_entity_rules(entity.nome, stored.get(entity.nome), strict=False)
        for entity in entities
    }
    metadata = {
        entity.nome: {
            "name": entity.nome,
            "label": entity.nome,
            "fields": [
                {"name": field.nome, "label": field.verbose_name or field.nome.replace("_", " ").title()}
                for field in entity.campos.all()
            ],
        }
        for entity in entities
    }
    return render(request, "sistema/notification_designer.html", {
        "sistema": sistema,
        "notifications_json": json.dumps(notifications, ensure_ascii=False),
        "entity_metadata_json": json.dumps(metadata, ensure_ascii=False),
    })


@login_required
@require_POST
def salvar_notifications(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_notifications = payload.get("notifications") if isinstance(payload, dict) else None
        if not isinstance(raw_notifications, dict):
            return JsonResponse({"status": "erro", "mensagem": "Configuração de notificações inválida."}, status=400)

        entity_names = set(Entidade.objects.filter(modulo__sistema=sistema).values_list("nome", flat=True))
        unknown = set(raw_notifications) - entity_names
        if unknown:
            return JsonResponse({"status": "erro", "mensagem": f"Informação não disponível: {sorted(unknown)[0]}"}, status=400)

        normalized = {
            name: _normalize_entity_rules(name, rules, strict=True)
            for name, rules in raw_notifications.items()
        }
        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do Notification Designer", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["notifications"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Notification Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "notifications": normalized})
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": str(exc)}, status=400)
