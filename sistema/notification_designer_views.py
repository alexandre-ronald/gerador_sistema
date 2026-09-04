import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Entidade, Sistema, VersaoGeracao


CRUD_EVENTS = {"created", "updated", "deleted"}
WORKFLOW_EVENT = "workflow_transition"
EVENTS = CRUD_EVENTS | {WORKFLOW_EVENT}
AUDIENCES = {"users_with_view_permission"}


def _draft_structure(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        return versao.estrutura_json
    return {}


def _draft_notifications(sistema):
    notifications = _draft_structure(sistema).get("notifications")
    return notifications if isinstance(notifications, dict) else {}


def _draft_workflows(sistema):
    workflows = _draft_structure(sistema).get("workflows")
    return workflows if isinstance(workflows, dict) else {}


def _workflow_event_metadata(raw_workflow):
    if not isinstance(raw_workflow, dict) or raw_workflow.get("enabled") is not True:
        return {"enabled": False, "transitions": []}

    raw_states = raw_workflow.get("states")
    raw_transitions = raw_workflow.get("transitions")
    if not isinstance(raw_states, list) or not isinstance(raw_transitions, list):
        return {"enabled": False, "transitions": []}

    states = {}
    for item in raw_states:
        if not isinstance(item, dict):
            continue
        state_id = str(item.get("id") or "").strip()
        if not state_id:
            continue
        states[state_id] = str(item.get("label") or state_id).strip() or state_id

    transitions = []
    for item in raw_transitions:
        if not isinstance(item, dict) or item.get("enabled") is not True:
            continue
        transition_id = str(item.get("id") or "").strip()
        destination = str(item.get("to") or "").strip()
        origins = item.get("from")
        if not transition_id or destination not in states or not isinstance(origins, list):
            continue
        valid_origins = [str(value).strip() for value in origins if str(value).strip() in states]
        if not valid_origins:
            continue
        transitions.append({
            "id": transition_id,
            "label": str(item.get("label") or transition_id).strip() or transition_id,
            "from": valid_origins,
            "from_labels": [states[state_id] for state_id in valid_origins],
            "to": destination,
            "to_label": states[destination],
            "order": item.get("order", 0) if isinstance(item.get("order", 0), int) else 0,
        })

    transitions.sort(key=lambda item: (item["order"], item["id"]))
    return {"enabled": True, "transitions": transitions}


def _workflow_transition_ids(workflow_metadata):
    return {item["id"] for item in workflow_metadata.get("transitions", [])}


def _normalize_rule(entity_name, raw, index=1, strict=False, workflow_metadata=None):
    raw = raw if isinstance(raw, dict) else {}
    workflow_metadata = workflow_metadata or {"enabled": False, "transitions": []}
    rule_id = str(raw.get("id") or f"notificacao_{index}").strip().lower().replace(" ", "_")
    event = str(raw.get("event") or "created")
    audience = str(raw.get("audience") or "users_with_view_permission")
    transition = str(raw.get("transition") or "").strip()

    if strict and event not in EVENTS:
        raise ValueError(f"Evento de notificação inválido em {entity_name}: {event}")
    if strict and audience not in AUDIENCES:
        raise ValueError(f"Público da notificação inválido em {entity_name}: {audience}")

    if event == WORKFLOW_EVENT:
        valid_transitions = _workflow_transition_ids(workflow_metadata)
        if strict and not workflow_metadata.get("enabled"):
            raise ValueError(f"Workflow não está ativo para {entity_name}.")
        if strict and transition not in valid_transitions:
            raise ValueError(f"Transição de workflow inválida em {entity_name}: {transition}")
    elif strict and transition:
        raise ValueError(f"Transição só pode ser informada para evento de workflow em {entity_name}.")

    if event not in EVENTS:
        event = "created"
        transition = ""
    if audience not in AUDIENCES:
        audience = "users_with_view_permission"

    normalized = {
        "id": rule_id,
        "enabled": bool(raw.get("enabled", True)),
        "event": event,
        "title": str(raw.get("title") or f"Atualização em {entity_name}"),
        "message": str(raw.get("message") or f"Houve uma atualização em {entity_name}."),
        "audience": audience,
    }
    if event == WORKFLOW_EVENT:
        normalized["transition"] = transition
    return normalized


def _normalize_entity_rules(entity_name, raw, strict=False, workflow_metadata=None):
    items = raw if isinstance(raw, list) else []
    result = []
    ids = set()
    for index, item in enumerate(items, start=1):
        rule = _normalize_rule(
            entity_name,
            item,
            index=index,
            strict=strict,
            workflow_metadata=workflow_metadata,
        )
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
    stored_workflows = _draft_workflows(sistema)
    workflow_metadata = {
        entity.nome: _workflow_event_metadata(stored_workflows.get(entity.nome))
        for entity in entities
    }
    notifications = {
        entity.nome: _normalize_entity_rules(
            entity.nome,
            stored.get(entity.nome),
            strict=False,
            workflow_metadata=workflow_metadata[entity.nome],
        )
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
            "workflow": workflow_metadata[entity.nome],
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

        stored_workflows = _draft_workflows(sistema)
        workflow_metadata = {
            name: _workflow_event_metadata(stored_workflows.get(name))
            for name in entity_names
        }
        normalized = {
            name: _normalize_entity_rules(
                name,
                rules,
                strict=True,
                workflow_metadata=workflow_metadata[name],
            )
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
