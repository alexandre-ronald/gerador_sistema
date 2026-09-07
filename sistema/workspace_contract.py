"""GEN-072.1 — contrato canônico de Business Workspace & Navigation.

O Workspace organiza experiências existentes. Ele não redefine páginas, CRUDs,
dashboards, relatórios ou workflows; apenas mantém referências estáveis para essas capacidades.
"""
from copy import deepcopy


CONTRACT_VERSION = 1
DESTINATION_KINDS = ("advanced_page", "crud", "dashboard", "report", "workflow")
CRUD_OPERATIONS = ("list", "view", "create", "update", "delete")
UNSAFE_TOKENS = ("__", "\\", "..", "/")


class WorkspaceContractError(ValueError):
    def __init__(self, code, message, *, workspace_id=None, section_id=None, item_id=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.workspace_id = workspace_id
        self.section_id = section_id
        self.item_id = item_id

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.workspace_id: data["workspace_id"] = self.workspace_id
        if self.section_id: data["section_id"] = self.section_id
        if self.item_id: data["item_id"] = self.item_id
        return data


def default_workspace_config():
    return {"version": CONTRACT_VERSION, "default_workspace": "", "workspaces": []}


def _safe_id(value, *, code, workspace_id=None, section_id=None, item_id=None):
    value = str(value or "").strip()
    if not value or any(token in value for token in UNSAFE_TOKENS):
        raise WorkspaceContractError(code, "Identificador inválido ou inseguro.", workspace_id=workspace_id, section_id=section_id, item_id=item_id)
    return value


def _label(value, *, code, workspace_id=None, section_id=None, item_id=None):
    value = str(value or "").strip()
    if not value:
        raise WorkspaceContractError(code, "Nome obrigatório.", workspace_id=workspace_id, section_id=section_id, item_id=item_id)
    return value


def _bool(value, *, code, workspace_id=None, section_id=None, item_id=None):
    if not isinstance(value, bool):
        raise WorkspaceContractError(code, "Valor booleano inválido.", workspace_id=workspace_id, section_id=section_id, item_id=item_id)
    return value


def _int(value, *, code, workspace_id=None, section_id=None, item_id=None):
    if isinstance(value, bool) or not isinstance(value, int) or value < -10000 or value > 10000:
        raise WorkspaceContractError(code, "Valor inteiro inválido.", workspace_id=workspace_id, section_id=section_id, item_id=item_id)
    return value


def _normalize_destination(raw, *, workspace_id, section_id, item_id):
    if not isinstance(raw, dict):
        raise WorkspaceContractError("invalid_destination", "Destino deve ser um objeto.", workspace_id=workspace_id, section_id=section_id, item_id=item_id)
    kind = str(raw.get("kind") or "").strip()
    if kind not in DESTINATION_KINDS:
        raise WorkspaceContractError("unknown_destination_kind", "Tipo de destino desconhecido.", workspace_id=workspace_id, section_id=section_id, item_id=item_id)
    ref = str(raw.get("ref") or "").strip()
    if not ref:
        raise WorkspaceContractError("destination_reference_required", "Destino exige referência explícita.", workspace_id=workspace_id, section_id=section_id, item_id=item_id)
    normalized = {"kind": kind, "ref": ref}
    if kind == "crud":
        operation = str(raw.get("operation") or "list").strip()
        if operation not in CRUD_OPERATIONS:
            raise WorkspaceContractError("invalid_crud_operation", "Operação CRUD inválida.", workspace_id=workspace_id, section_id=section_id, item_id=item_id)
        normalized["operation"] = operation
    return normalized


def _normalize_item(raw, *, workspace_id, section_id):
    if not isinstance(raw, dict): raise WorkspaceContractError("invalid_workspace_item", "Item deve ser um objeto.", workspace_id=workspace_id, section_id=section_id)
    item_id = _safe_id(raw.get("id"), code="invalid_workspace_item_id", workspace_id=workspace_id, section_id=section_id)
    return {"id": item_id,"label": _label(raw.get("label"), code="empty_workspace_item_label", workspace_id=workspace_id, section_id=section_id, item_id=item_id),"icon": str(raw.get("icon") or "").strip(),"enabled": _bool(raw.get("enabled", True), code="invalid_workspace_item_enabled", workspace_id=workspace_id, section_id=section_id, item_id=item_id),"order": _int(raw.get("order", 0), code="invalid_workspace_item_order", workspace_id=workspace_id, section_id=section_id, item_id=item_id),"destination": _normalize_destination(raw.get("destination"), workspace_id=workspace_id, section_id=section_id, item_id=item_id)}


def _normalize_section(raw, *, workspace_id):
    if not isinstance(raw, dict): raise WorkspaceContractError("invalid_workspace_section", "Seção deve ser um objeto.", workspace_id=workspace_id)
    section_id = _safe_id(raw.get("id"), code="invalid_workspace_section_id", workspace_id=workspace_id)
    raw_items = raw.get("items", [])
    if not isinstance(raw_items, list): raise WorkspaceContractError("invalid_workspace_items", "Itens devem ser uma lista.", workspace_id=workspace_id, section_id=section_id)
    items=[]; item_ids=set()
    for raw_item in raw_items:
        item=_normalize_item(raw_item, workspace_id=workspace_id, section_id=section_id)
        if item["id"] in item_ids: raise WorkspaceContractError("duplicate_workspace_item_id", "ID de item duplicado no workspace.", workspace_id=workspace_id, section_id=section_id, item_id=item["id"])
        item_ids.add(item["id"]); items.append(item)
    return {"id":section_id,"label":_label(raw.get("label"), code="empty_workspace_section_label", workspace_id=workspace_id, section_id=section_id),"icon":str(raw.get("icon") or "").strip(),"enabled":_bool(raw.get("enabled",True), code="invalid_workspace_section_enabled", workspace_id=workspace_id, section_id=section_id),"order":_int(raw.get("order",0), code="invalid_workspace_section_order", workspace_id=workspace_id, section_id=section_id),"items":items}


def _normalize_workspace(raw):
    if not isinstance(raw, dict): raise WorkspaceContractError("invalid_workspace", "Workspace deve ser um objeto.")
    workspace_id=_safe_id(raw.get("id"), code="invalid_workspace_id"); raw_sections=raw.get("sections", [])
    if not isinstance(raw_sections,list): raise WorkspaceContractError("invalid_workspace_sections", "Seções devem ser uma lista.", workspace_id=workspace_id)
    sections=[]; section_ids=set(); item_ids=set()
    for raw_section in raw_sections:
        section=_normalize_section(raw_section, workspace_id=workspace_id)
        if section["id"] in section_ids: raise WorkspaceContractError("duplicate_workspace_section_id", "ID de seção duplicado.", workspace_id=workspace_id, section_id=section["id"])
        duplicate_item=next((item["id"] for item in section["items"] if item["id"] in item_ids),None)
        if duplicate_item: raise WorkspaceContractError("duplicate_workspace_item_id", "ID de item deve ser único no workspace.", workspace_id=workspace_id, section_id=section["id"], item_id=duplicate_item)
        section_ids.add(section["id"]); item_ids.update(item["id"] for item in section["items"]); sections.append(section)
    home=str(raw.get("home") or "").strip()
    if home and home not in item_ids: raise WorkspaceContractError("unknown_workspace_home", "Home referencia item inexistente no workspace.", workspace_id=workspace_id, item_id=home)
    return {"id":workspace_id,"label":_label(raw.get("label"), code="empty_workspace_label", workspace_id=workspace_id),"description":str(raw.get("description") or "").strip(),"icon":str(raw.get("icon") or "").strip(),"enabled":_bool(raw.get("enabled",True), code="invalid_workspace_enabled", workspace_id=workspace_id),"order":_int(raw.get("order",0), code="invalid_workspace_order", workspace_id=workspace_id),"home":home,"sections":sections}


def normalize_workspace_config(raw_config, *, strict=True):
    raw_config=raw_config if isinstance(raw_config,dict) else {}; version=raw_config.get("version",CONTRACT_VERSION)
    if version != CONTRACT_VERSION:
        if strict: raise WorkspaceContractError("unsupported_workspace_contract_version", "Versão do contrato de workspace não suportada.")
        version=CONTRACT_VERSION
    raw_workspaces=raw_config.get("workspaces",[])
    if not isinstance(raw_workspaces,list):
        if strict: raise WorkspaceContractError("invalid_workspaces", "Workspaces devem ser uma lista.")
        raw_workspaces=[]
    workspaces=[]; workspace_ids=set()
    for raw_workspace in raw_workspaces:
        try: workspace=_normalize_workspace(raw_workspace)
        except WorkspaceContractError:
            if strict: raise
            continue
        if workspace["id"] in workspace_ids:
            if strict: raise WorkspaceContractError("duplicate_workspace_id", "ID de workspace duplicado.", workspace_id=workspace["id"])
            continue
        workspace_ids.add(workspace["id"]); workspaces.append(workspace)
    default_workspace=str(raw_config.get("default_workspace") or "").strip()
    if default_workspace and default_workspace not in workspace_ids:
        if strict: raise WorkspaceContractError("unknown_default_workspace", "Workspace default referencia workspace inexistente.", workspace_id=default_workspace)
        default_workspace=""
    return {"version":version,"default_workspace":default_workspace,"workspaces":deepcopy(workspaces)}


def workspace_map(config):
    normalized=normalize_workspace_config(config,strict=True); return {workspace["id"]:deepcopy(workspace) for workspace in normalized["workspaces"]}


def workspace_item_map(config, workspace_id):
    workspace=workspace_map(config).get(workspace_id)
    if workspace is None: raise WorkspaceContractError("unknown_workspace", "Workspace inexistente.", workspace_id=workspace_id)
    return {item["id"]:deepcopy(item) for section in workspace["sections"] for item in section["items"]}
