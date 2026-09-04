import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Entidade, Sistema, VersaoGeracao


CRUD_EVENTS = {"created", "updated", "deleted"}
WORKFLOW_EVENT = "workflow_transition"
EVENTS = CRUD_EVENTS | {WORKFLOW_EVENT}
AUDIENCE_VIEW_PERMISSION = "users_with_view_permission"
AUDIENCE_ACTOR = "actor"
AUDIENCE_ROLE = "role"
AUDIENCES = {AUDIENCE_VIEW_PERMISSION, AUDIENCE_ACTOR, AUDIENCE_ROLE}
CHANNEL_IN_APP = "in_app"
CHANNELS = {CHANNEL_IN_APP}


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


def _draft_rbac(sistema):
    rbac = _draft_structure(sistema).get("rbac")
    return rbac if isinstance(rbac, dict) else {}


def _rbac_recipient_metadata(raw_rbac):
    if not isinstance(raw_rbac, dict) or raw_rbac.get("enabled") is not True:
        return {"enabled": False, "roles": []}

    roles = []
    for item in raw_rbac.get("roles") or []:
        if not isinstance(item, dict):
            continue
        role_id = str(item.get("id") or "").strip()
        label = str(item.get("label") or "").strip()
        group = str(item.get("group") or "").strip()
        if not role_id or not label or not group:
            continue
        roles.append({
            "id": role_id,
            "label": label,
            "group": group,
            "order": item.get("order", 0) if isinstance(item.get("order", 0), int) else 0,
        })

    roles.sort(key=lambda item: (item["order"], item["id"]))
    return {"enabled": True, "roles": roles}


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


def _rbac_role_ids(rbac_metadata):
    return {item["id"] for item in rbac_metadata.get("roles", [])}


def _normalize_channels(raw, entity_name, strict=False):
    if "channels" not in raw:
        return [CHANNEL_IN_APP]

    channels = raw.get("channels")
    if not isinstance(channels, list):
        if strict:
            raise ValueError(f"Canais da notificação inválidos em {entity_name}: esperado uma lista.")
        return [CHANNEL_IN_APP]
    if not channels:
        if strict:
            raise ValueError(f"A notificação em {entity_name} deve possuir ao menos um canal.")
        return [CHANNEL_IN_APP]

    normalized = []
    for value in channels:
        channel = str(value or "").strip()
        if channel not in CHANNELS:
            if strict:
                raise ValueError(f"Canal de notificação inválido em {entity_name}: {channel}")
            return [CHANNEL_IN_APP]
        if channel not in normalized:
            normalized.append(channel)
    return normalized


def _normalize_rule(entity_name, raw, index=1, strict=False, workflow_metadata=None, rbac_metadata=None):
    raw = raw if isinstance(raw, dict) else {}
    workflow_metadata = workflow_metadata or {"enabled": False, "transitions": []}
    rbac_metadata = rbac_metadata or {"enabled": False, "roles": []}
    rule_id = str(raw.get("id") or f"notificacao_{index}").strip().lower().replace(" ", "_")
    event = str(raw.get("event") or "created")
    audience = str(raw.get("audience") or AUDIENCE_VIEW_PERMISSION)
    transition = str(raw.get("transition") or "").strip()
    role = str(raw.get("role") or "").strip()
    channels = _normalize_channels(raw, entity_name, strict=strict)

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

    if audience == AUDIENCE_ROLE:
        valid_roles = _rbac_role_ids(rbac_metadata)
        if strict and not rbac_metadata.get("enabled"):
            raise ValueError(f"RBAC não está ativo para usar papel como destinatário em {entity_name}.")
        if strict and role not in valid_roles:
            raise ValueError(f"Papel destinatário inválido em {entity_name}: {role}")
    elif strict and role:
        raise ValueError(f"Papel só pode ser informado quando o destinatário for um papel em {entity_name}.")

    if event not in EVENTS:
        event = "created"
        transition = ""
    if audience not in AUDIENCES:
        audience = AUDIENCE_VIEW_PERMISSION
        role = ""

    normalized = {
        "id": rule_id,
        "enabled": bool(raw.get("enabled", True)),
        "event": event,
        "title": str(raw.get("title") or f"Atualização em {entity_name}"),
        "message": str(raw.get("message") or f"Houve uma atualização em {entity_name}."),
        "audience": audience,
        "channels": channels,
    }
    if event == WORKFLOW_EVENT:
        normalized["transition"] = transition
    if audience == AUDIENCE_ROLE:
        normalized["role"] = role
    return normalized


def _normalize_entity_rules(entity_name, raw, strict=False, workflow_metadata=None, rbac_metadata=None):
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
            rbac_metadata=rbac_metadata,
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
    rbac_metadata = _rbac_recipient_metadata(_draft_rbac(sistema))
    notifications = {
        entity.nome: _normalize_entity_rules(
            entity.nome,
            stored.get(entity.nome),
            strict=False,
            workflow_metadata=workflow_metadata[entity.nome],
            rbac_metadata=rbac_metadata,
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
        "recipient_metadata_json": json.dumps(rbac_metadata, ensure_ascii=False),
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
        rbac_metadata = _rbac_recipient_metadata(_draft_rbac(sistema))
        normalized = {
            name: _normalize_entity_rules(
                name,
                rules,
                strict=True,
                workflow_metadata=workflow_metadata[name],
                rbac_metadata=rbac_metadata,
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