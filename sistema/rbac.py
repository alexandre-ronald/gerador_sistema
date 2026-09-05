from copy import deepcopy


CRUD_ACTIONS = ("list", "view", "create", "update", "delete")
CRUD_ACTION_SET = set(CRUD_ACTIONS)
UNSAFE_TOKENS = ("__", ".", "/", "\\")
ORDER_MIN = -10000
ORDER_MAX = 10000


class RBACError(ValueError):
    def __init__(self, code, message, *, role_id=None, entity=None, action=None, transition_id=None, report_id=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.role_id = role_id
        self.entity = entity
        self.action = action
        self.transition_id = transition_id
        self.report_id = report_id

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.role_id: data["role_id"] = self.role_id
        if self.entity: data["entity"] = self.entity
        if self.action: data["action"] = self.action
        if self.transition_id: data["transition_id"] = self.transition_id
        if self.report_id: data["report_id"] = self.report_id
        return data


def _safe_id(value, *, code, role_id=None, entity=None, transition_id=None, report_id=None):
    value = str(value or "").strip()
    if not value or any(token in value for token in UNSAFE_TOKENS):
        raise RBACError(code, "Identificador inválido ou inseguro.", role_id=role_id, entity=entity, transition_id=transition_id, report_id=report_id)
    return value


def _bool(value, *, code):
    if isinstance(value, bool): return value
    raise RBACError(code, "Valor booleano inválido.")


def _order(value, *, code, role_id=None):
    if isinstance(value, bool) or not isinstance(value, int) or value < ORDER_MIN or value > ORDER_MAX:
        raise RBACError(code, f"Ordem deve ser inteiro entre {ORDER_MIN} e {ORDER_MAX}.", role_id=role_id)
    return value


def _entity_metadata_map(entities_metadata):
    result = {}
    for item in entities_metadata or []:
        if not isinstance(item, dict): continue
        name = str(item.get("name") or "").strip()
        if not name or any(token in name for token in UNSAFE_TOKENS): continue
        result[name] = deepcopy(item)
    return result


def _workflow_transition_ids(workflows, entity_name):
    config = (workflows or {}).get(entity_name)
    if not isinstance(config, dict): return set()
    return {str(item["id"]).strip() for item in (config.get("transitions") or []) if isinstance(item, dict) and item.get("id")}


def _report_ids(reports, entity_name):
    collection = (reports or {}).get(entity_name)
    if not isinstance(collection, list): return set()
    return {str(item["id"]).strip() for item in collection if isinstance(item, dict) and item.get("id")}


def _normalize_role(item):
    if not isinstance(item, dict): raise RBACError("invalid_role", "Papel deve ser um objeto.")
    role_id = _safe_id(item.get("id"), code="invalid_role_id")
    label = str(item.get("label") or "").strip()
    if not label: raise RBACError("empty_role_label", "Papel exige um nome.", role_id=role_id)
    description = str(item.get("description") or "").strip()
    group = str(item.get("group") or label).strip()
    if not group: raise RBACError("empty_role_group", "Não foi possível definir o grupo interno do papel.", role_id=role_id)
    return {"id": role_id, "label": label, "description": description, "group": group, "order": _order(item.get("order", 0), code="invalid_role_order", role_id=role_id)}


def _normalize_actions(raw_actions, role_id, entity_name):
    if not isinstance(raw_actions, list): raise RBACError("invalid_role_actions", "Permissões da entidade devem ser uma lista.", role_id=role_id, entity=entity_name)
    seen = set()
    for value in raw_actions:
        action = str(value or "").strip()
        if action not in CRUD_ACTION_SET: raise RBACError("unknown_crud_action", "Ação CRUD desconhecida.", role_id=role_id, entity=entity_name, action=action or None)
        seen.add(action)
    return [action for action in CRUD_ACTIONS if action in seen]


def _normalize_role_ids(raw_role_ids, roles, *, entity_name, transition_id=None, report_id=None):
    if not isinstance(raw_role_ids, list):
        code = "invalid_report_roles" if report_id else "invalid_transition_roles"
        message = "Papéis autorizados para relatório devem ser uma lista." if report_id else "Papéis autorizados para transição devem ser uma lista."
        raise RBACError(code, message, entity=entity_name, transition_id=transition_id, report_id=report_id)
    result = []
    seen = set()
    for raw_role_id in raw_role_ids:
        role_id = _safe_id(raw_role_id, code="invalid_role_reference", entity=entity_name, transition_id=transition_id, report_id=report_id)
        if role_id not in roles:
            raise RBACError("unknown_role_reference", "Papel referenciado não existe.", role_id=role_id, entity=entity_name, transition_id=transition_id, report_id=report_id)
        if role_id not in seen: result.append(role_id); seen.add(role_id)
    return result


def _normalize_entity_policy(entity_name, raw_policy, roles, workflows):
    if not isinstance(raw_policy, dict): raise RBACError("invalid_entity_policy", "Política da entidade deve ser um objeto.", entity=entity_name)
    raw_roles = raw_policy.get("roles", {})
    if not isinstance(raw_roles, dict): raise RBACError("invalid_entity_roles", "Papéis da entidade devem ser um objeto.", entity=entity_name)
    normalized_roles = {}
    for raw_role_id, raw_actions in raw_roles.items():
        role_id = _safe_id(raw_role_id, code="invalid_role_reference", entity=entity_name)
        if role_id not in roles: raise RBACError("unknown_role_reference", "Papel referenciado não existe.", role_id=role_id, entity=entity_name)
        normalized_roles[role_id] = _normalize_actions(raw_actions, role_id, entity_name)
    raw_transitions = raw_policy.get("transitions", {})
    if not isinstance(raw_transitions, dict): raise RBACError("invalid_transition_permissions", "Permissões de transição devem ser um objeto.", entity=entity_name)
    known_transitions = _workflow_transition_ids(workflows, entity_name)
    normalized_transitions = {}
    for raw_transition_id, raw_role_ids in raw_transitions.items():
        transition_id = _safe_id(raw_transition_id, code="invalid_transition_reference", entity=entity_name)
        if transition_id not in known_transitions: raise RBACError("unknown_transition_reference", "Transição referenciada não existe no workflow da entidade.", entity=entity_name, transition_id=transition_id)
        normalized_transitions[transition_id] = _normalize_role_ids(raw_role_ids, roles, entity_name=entity_name, transition_id=transition_id)
    return {"roles": {key: normalized_roles[key] for key in sorted(normalized_roles)}, "transitions": {key: normalized_transitions[key] for key in sorted(normalized_transitions)}}


def _normalize_report_policies(raw_reports, roles, reports, metadata, *, strict):
    if raw_reports is None: return {}
    if not isinstance(raw_reports, dict): raise RBACError("invalid_report_policies", "Permissões de relatórios devem ser um objeto.")
    normalized = {}
    for raw_entity_name, raw_entity_reports in raw_reports.items():
        entity_name = _safe_id(raw_entity_name, code="invalid_report_entity")
        if entity_name not in metadata:
            if strict: raise RBACError("unknown_report_entity", "Entidade do relatório não existe.", entity=entity_name)
            continue
        if not isinstance(raw_entity_reports, dict): raise RBACError("invalid_entity_report_policies", "Permissões de relatórios da entidade devem ser um objeto.", entity=entity_name)
        known_reports = _report_ids(reports, entity_name)
        entity_result = {}
        for raw_report_id, raw_role_ids in raw_entity_reports.items():
            report_id = _safe_id(raw_report_id, code="invalid_report_reference", entity=entity_name)
            if report_id not in known_reports:
                if strict: raise RBACError("unknown_report_reference", "Relatório referenciado não existe.", entity=entity_name, report_id=report_id)
                continue
            entity_result[report_id] = _normalize_role_ids(raw_role_ids, roles, entity_name=entity_name, report_id=report_id)
        if entity_result: normalized[entity_name] = {key: entity_result[key] for key in sorted(entity_result)}
    return {key: normalized[key] for key in sorted(normalized)}


def normalize_rbac_config(entities_metadata, workflows, raw_config, *, strict=True, reports=None):
    if raw_config is None: raw_config = {}
    if not isinstance(raw_config, dict):
        if strict: raise RBACError("invalid_rbac_config", "Configuração RBAC deve ser um objeto.")
        raw_config = {}
    enabled = raw_config.get("enabled", False)
    if not isinstance(enabled, bool): raise RBACError("invalid_rbac_enabled", "Campo enabled deve ser booleano.")
    raw_roles = raw_config.get("roles", [])
    if not isinstance(raw_roles, list): raise RBACError("invalid_roles", "Papéis devem ser uma lista.")
    roles = {}
    for item in raw_roles:
        normalized = _normalize_role(item)
        if normalized["id"] in roles: raise RBACError("duplicate_role_id", "ID de papel duplicado.", role_id=normalized["id"])
        roles[normalized["id"]] = normalized
    raw_entities = raw_config.get("entities", {})
    if not isinstance(raw_entities, dict): raise RBACError("invalid_entity_policies", "Políticas de entidades devem ser um objeto.")
    metadata = _entity_metadata_map(entities_metadata)
    entities = {}
    for raw_entity_name, raw_policy in raw_entities.items():
        entity_name = _safe_id(raw_entity_name, code="invalid_rbac_entity")
        if entity_name not in metadata:
            if strict: raise RBACError("unknown_rbac_entity", "Entidade da política RBAC não existe.", entity=entity_name)
            continue
        try: entities[entity_name] = _normalize_entity_policy(entity_name, raw_policy, roles, workflows)
        except RBACError:
            if strict: raise
    try: report_policies = _normalize_report_policies(raw_config.get("reports"), roles, reports or {}, metadata, strict=strict)
    except RBACError:
        if strict: raise
        report_policies = {}
    return {"enabled": enabled, "roles": sorted(roles.values(), key=lambda item: (item["order"], item["id"])), "entities": {key: entities[key] for key in sorted(entities)}, "reports": report_policies}


def role_map(config):
    return {item["id"]: deepcopy(item) for item in (config or {}).get("roles", [])}


def entity_policy(config, entity_name):
    policies = (config or {}).get("entities") or {}; policy = policies.get(entity_name)
    return deepcopy(policy) if isinstance(policy, dict) else None


def report_roles(config, entity_name, report_id):
    policies = (config or {}).get("reports") or {}
    entity_reports = policies.get(entity_name) or {}
    roles = entity_reports.get(report_id)
    return deepcopy(roles) if isinstance(roles, list) else None
