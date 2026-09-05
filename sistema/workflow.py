from copy import deepcopy


TEXT_STATE_TYPES = {"CharField", "TextField", "SlugField"}
UNSAFE_TOKENS = ("__", ".", "/", "\\")
ORDER_MIN = -10000
ORDER_MAX = 10000


class WorkflowError(ValueError):
    def __init__(self, code, message, *, field=None, state_id=None, transition_id=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.state_id = state_id
        self.transition_id = transition_id

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.field:
            data["field"] = self.field
        if self.state_id:
            data["state_id"] = self.state_id
        if self.transition_id:
            data["transition_id"] = self.transition_id
        return data


def _safe_id(value, *, code, transition_id=None, state_id=None):
    value = str(value or "").strip()
    if not value or any(token in value for token in UNSAFE_TOKENS):
        raise WorkflowError(code, "Identificador inválido ou inseguro.", transition_id=transition_id, state_id=state_id)
    return value


def _bool(value, *, code, transition_id=None, state_id=None):
    if isinstance(value, bool):
        return value
    raise WorkflowError(code, "Valor booleano inválido.", transition_id=transition_id, state_id=state_id)


def _order(value, *, code, transition_id=None, state_id=None):
    if isinstance(value, bool) or not isinstance(value, int) or value < ORDER_MIN or value > ORDER_MAX:
        raise WorkflowError(code, f"Ordem deve ser inteiro entre {ORDER_MIN} e {ORDER_MAX}.", transition_id=transition_id, state_id=state_id)
    return value


def _entity_field_id(value):
    value = str(value or "").strip()
    if not value:
        raise WorkflowError(
            "missing_state_field",
            "Escolha onde guardar a etapa atual antes de salvar o fluxo.",
            field="state_field",
        )
    return _safe_id(value, code="invalid_state_field")


def _initial_state_id(value):
    value = str(value or "").strip()
    if not value:
        raise WorkflowError(
            "missing_initial_state",
            "Defina a etapa inicial antes de salvar o fluxo.",
        )
    return _safe_id(value, code="invalid_initial_state")


def _metadata_map(entity_metadata):
    fields = {}
    for item in entity_metadata.get("fields") or []:
        name = _safe_id(item.get("name"), code="invalid_metadata_field")
        fields[name] = deepcopy(item)
    return fields


def compatible_state_fields(entity_metadata):
    result = []
    for item in entity_metadata.get("fields") or []:
        name = str(item.get("name") or "").strip()
        if not name or any(token in name for token in UNSAFE_TOKENS):
            continue
        field_type = str(item.get("type") or "")
        if field_type not in TEXT_STATE_TYPES:
            continue
        if item.get("editable") is False or item.get("auto_created"):
            continue
        result.append(deepcopy(item))
    return result


def _normalize_state(item):
    state_id = _safe_id(item.get("id"), code="invalid_state_id")
    label = str(item.get("label") or "").strip()
    if not label:
        raise WorkflowError("empty_state_label", "Estado exige um rótulo.", state_id=state_id)
    return {
        "id": state_id,
        "label": label,
        "final": _bool(item.get("final", False), code="invalid_state_final", state_id=state_id),
        "order": _order(item.get("order", 0), code="invalid_state_order", state_id=state_id),
    }


def _normalize_transition(item, states):
    transition_id = _safe_id(item.get("id"), code="invalid_transition_id")
    label = str(item.get("label") or "").strip()
    if not label:
        raise WorkflowError("empty_transition_label", "Transição exige um rótulo.", transition_id=transition_id)

    raw_from = item.get("from")
    if not isinstance(raw_from, list) or not raw_from:
        raise WorkflowError("empty_transition_from", "Transição exige ao menos um estado de origem.", transition_id=transition_id)

    origins = []
    seen = set()
    for value in raw_from:
        state_id = _safe_id(value, code="invalid_transition_origin", transition_id=transition_id)
        if state_id not in states:
            raise WorkflowError("unknown_transition_origin", "Estado de origem não existe.", state_id=state_id, transition_id=transition_id)
        if states[state_id]["final"]:
            raise WorkflowError("final_state_has_outgoing_transition", "Estado final não pode possuir transição de saída.", state_id=state_id, transition_id=transition_id)
        if state_id not in seen:
            origins.append(state_id)
            seen.add(state_id)

    destination = _safe_id(item.get("to"), code="invalid_transition_destination", transition_id=transition_id)
    if destination not in states:
        raise WorkflowError("unknown_transition_destination", "Estado destino não existe.", state_id=destination, transition_id=transition_id)

    confirm = _bool(item.get("confirm", False), code="invalid_transition_confirm", transition_id=transition_id)
    confirm_message = str(item.get("confirm_message") or "").strip()
    if confirm and not confirm_message:
        confirm_message = f"Confirmar transição '{label}'?"

    return {
        "id": transition_id,
        "label": label,
        "from": origins,
        "to": destination,
        "enabled": _bool(item.get("enabled", True), code="invalid_transition_enabled", transition_id=transition_id),
        "confirm": confirm,
        "confirm_message": confirm_message,
        "order": _order(item.get("order", 0), code="invalid_transition_order", transition_id=transition_id),
    }


def normalize_workflow_config(entity_name, entity_metadata, raw_config, *, strict=True):
    if not isinstance(raw_config, dict):
        if strict:
            raise WorkflowError("invalid_workflow_config", "Configuração de workflow deve ser um objeto.")
        raw_config = {}

    fields = _metadata_map(entity_metadata)
    enabled = raw_config.get("enabled", False)
    if not isinstance(enabled, bool):
        raise WorkflowError("invalid_workflow_enabled", "Campo enabled deve ser booleano.")

    if not raw_config and not enabled:
        return {
            "enabled": False,
            "state_field": "",
            "initial_state": "",
            "states": [],
            "transitions": [],
        }

    state_field = _entity_field_id(raw_config.get("state_field"))
    if state_field not in fields:
        if strict:
            raise WorkflowError("unknown_state_field", "Campo de estado não existe na entidade.", field=state_field)
        return {
            "enabled": False,
            "state_field": "",
            "initial_state": "",
            "states": [],
            "transitions": [],
        }

    field_metadata = fields[state_field]
    field_type = str(field_metadata.get("type") or "")
    if field_type not in TEXT_STATE_TYPES or field_metadata.get("editable") is False or field_metadata.get("auto_created"):
        raise WorkflowError("incompatible_state_field", "Campo de estado é incompatível com workflow.", field=state_field)

    raw_states = raw_config.get("states")
    if not isinstance(raw_states, list) or not raw_states:
        raise WorkflowError("workflow_without_states", "Adicione pelo menos uma etapa antes de salvar o fluxo.")

    states = {}
    for item in raw_states:
        if not isinstance(item, dict):
            raise WorkflowError("invalid_state", "Estado deve ser um objeto.")
        normalized = _normalize_state(item)
        if normalized["id"] in states:
            raise WorkflowError("duplicate_state_id", "ID de estado duplicado.", state_id=normalized["id"])
        states[normalized["id"]] = normalized

    initial_state = _initial_state_id(raw_config.get("initial_state"))
    if initial_state not in states:
        raise WorkflowError("unknown_initial_state", "Estado inicial não existe.", state_id=initial_state)

    raw_transitions = raw_config.get("transitions", [])
    if not isinstance(raw_transitions, list):
        raise WorkflowError("invalid_transitions", "Lista de transições inválida.")

    transitions = {}
    for item in raw_transitions:
        if not isinstance(item, dict):
            raise WorkflowError("invalid_transition", "Transição deve ser um objeto.")
        normalized = _normalize_transition(item, states)
        if normalized["id"] in transitions:
            raise WorkflowError("duplicate_transition_id", "ID de transição duplicado.", transition_id=normalized["id"])
        transitions[normalized["id"]] = normalized

    return {
        "enabled": enabled,
        "state_field": state_field,
        "initial_state": initial_state,
        "states": sorted(states.values(), key=lambda item: (item["order"], item["id"])),
        "transitions": sorted(transitions.values(), key=lambda item: (item["order"], item["id"])),
    }


def normalize_workflows_config(entities_metadata, raw_workflows, *, strict=True):
    if raw_workflows is None:
        return {}
    if not isinstance(raw_workflows, dict):
        raise WorkflowError("invalid_workflows_config", "Configuração de workflows deve ser um objeto.")

    metadata_map = {str(item.get("name") or ""): item for item in entities_metadata or []}
    result = {}
    for entity_name, config in raw_workflows.items():
        safe_entity = _safe_id(entity_name, code="invalid_workflow_entity")
        metadata = metadata_map.get(safe_entity)
        if metadata is None:
            if strict:
                raise WorkflowError("unknown_workflow_entity", "Entidade do workflow não existe.")
            continue
        result[safe_entity] = normalize_workflow_config(safe_entity, metadata, config, strict=strict)
    return result
