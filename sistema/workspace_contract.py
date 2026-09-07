"""GEN-072.1 — contrato canônico de Business Workspace & Navigation.

O Workspace organiza experiências existentes. Ele não redefine páginas, CRUDs,
dashboards ou relatórios; apenas mantém referências estáveis para essas capacidades.
"""
from copy import deepcopy


CONTRACT_VERSION = 1
DESTINATION_KINDS = ("advanced_page", "crud", "dashboard", "report")
CRUD_OPERATIONS = ("list", "view", "create", "update", "delete")
UNSAFE_TOKENS = ("__", "\\", "..", "/")


class WorkspaceContractError(ValueError):
    def __init__(self, code, message, *, section_id=None, item_id=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.section_id = section_id
        self.item_id = item_id

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.section_id:
            data["section_id"] = self.section_id
        if self.item_id:
            data["item_id"] = self.item_id
        return data


def default_workspace_config():
    return {"version": CONTRACT_VERSION, "home": "", "sections": []}


def _safe_id(value, *, code, section_id=None, item_id=None):
    value = str(value or "").strip()
    if not value or any(token in value for token in UNSAFE_TOKENS):
        raise WorkspaceContractError(
            code,
            "Identificador inválido ou inseguro.",
            section_id=section_id,
            item_id=item_id,
        )
    return value


def _label(value, *, code, section_id=None, item_id=None):
    value = str(value or "").strip()
    if not value:
        raise WorkspaceContractError(code, "Nome obrigatório.", section_id=section_id, item_id=item_id)
    return value


def _bool(value, *, code, section_id=None, item_id=None):
    if not isinstance(value, bool):
        raise WorkspaceContractError(code, "Valor booleano inválido.", section_id=section_id, item_id=item_id)
    return value


def _int(value, *, code, section_id=None, item_id=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceContractError(code, "Valor inteiro inválido.", section_id=section_id, item_id=item_id)
    if value < -10000 or value > 10000:
        raise WorkspaceContractError(code, "Valor fora do intervalo permitido.", section_id=section_id, item_id=item_id)
    return value


def _normalize_destination(raw, *, section_id, item_id):
    if not isinstance(raw, dict):
        raise WorkspaceContractError("invalid_destination", "Destino deve ser um objeto.", section_id=section_id, item_id=item_id)

    kind = str(raw.get("kind") or "").strip()
    if kind not in DESTINATION_KINDS:
        raise WorkspaceContractError("unknown_destination_kind", "Tipo de destino desconhecido.", section_id=section_id, item_id=item_id)

    ref = str(raw.get("ref") or "").strip()
    if not ref:
        raise WorkspaceContractError("destination_reference_required", "Destino exige referência explícita.", section_id=section_id, item_id=item_id)

    normalized = {"kind": kind, "ref": ref}
    if kind == "crud":
        operation = str(raw.get("operation") or "list").strip()
        if operation not in CRUD_OPERATIONS:
            raise WorkspaceContractError("invalid_crud_operation", "Operação CRUD inválida.", section_id=section_id, item_id=item_id)
        normalized["operation"] = operation
    return normalized


def _normalize_item(raw, *, section_id):
    if not isinstance(raw, dict):
        raise WorkspaceContractError("invalid_workspace_item", "Item deve ser um objeto.", section_id=section_id)
    item_id = _safe_id(raw.get("id"), code="invalid_workspace_item_id", section_id=section_id)
    return {
        "id": item_id,
        "label": _label(raw.get("label"), code="empty_workspace_item_label", section_id=section_id, item_id=item_id),
        "icon": str(raw.get("icon") or "").strip(),
        "enabled": _bool(raw.get("enabled", True), code="invalid_workspace_item_enabled", section_id=section_id, item_id=item_id),
        "order": _int(raw.get("order", 0), code="invalid_workspace_item_order", section_id=section_id, item_id=item_id),
        "destination": _normalize_destination(raw.get("destination"), section_id=section_id, item_id=item_id),
    }


def _normalize_section(raw):
    if not isinstance(raw, dict):
        raise WorkspaceContractError("invalid_workspace_section", "Seção deve ser um objeto.")
    section_id = _safe_id(raw.get("id"), code="invalid_workspace_section_id")
    raw_items = raw.get("items", [])
    if not isinstance(raw_items, list):
        raise WorkspaceContractError("invalid_workspace_items", "Itens devem ser uma lista.", section_id=section_id)

    items = []
    item_ids = set()
    for raw_item in raw_items:
        item = _normalize_item(raw_item, section_id=section_id)
        if item["id"] in item_ids:
            raise WorkspaceContractError("duplicate_workspace_item_id", "ID de item duplicado na seção.", section_id=section_id, item_id=item["id"])
        item_ids.add(item["id"])
        items.append(item)

    return {
        "id": section_id,
        "label": _label(raw.get("label"), code="empty_workspace_section_label", section_id=section_id),
        "icon": str(raw.get("icon") or "").strip(),
        "enabled": _bool(raw.get("enabled", True), code="invalid_workspace_section_enabled", section_id=section_id),
        "order": _int(raw.get("order", 0), code="invalid_workspace_section_order", section_id=section_id),
        "items": items,
    }


def normalize_workspace_config(raw_config, *, strict=True):
    raw_config = raw_config if isinstance(raw_config, dict) else {}
    version = raw_config.get("version", CONTRACT_VERSION)
    if version != CONTRACT_VERSION:
        if strict:
            raise WorkspaceContractError("unsupported_workspace_contract_version", "Versão do contrato de workspace não suportada.")
        version = CONTRACT_VERSION

    raw_sections = raw_config.get("sections", [])
    if not isinstance(raw_sections, list):
        if strict:
            raise WorkspaceContractError("invalid_workspace_sections", "Seções devem ser uma lista.")
        raw_sections = []

    sections = []
    section_ids = set()
    global_item_ids = set()
    for raw_section in raw_sections:
        try:
            section = _normalize_section(raw_section)
        except WorkspaceContractError:
            if strict:
                raise
            continue
        if section["id"] in section_ids:
            if strict:
                raise WorkspaceContractError("duplicate_workspace_section_id", "ID de seção duplicado.", section_id=section["id"])
            continue
        duplicate_item = next((item["id"] for item in section["items"] if item["id"] in global_item_ids), None)
        if duplicate_item:
            if strict:
                raise WorkspaceContractError("duplicate_workspace_item_id", "ID de item deve ser único no workspace.", section_id=section["id"], item_id=duplicate_item)
            continue
        section_ids.add(section["id"])
        global_item_ids.update(item["id"] for item in section["items"])
        sections.append(section)

    home = str(raw_config.get("home") or "").strip()
    if home and home not in global_item_ids:
        if strict:
            raise WorkspaceContractError("unknown_workspace_home", "Home referencia item inexistente.", item_id=home)
        home = ""

    return {"version": version, "home": home, "sections": deepcopy(sections)}


def workspace_item_map(config):
    normalized = normalize_workspace_config(config, strict=True)
    return {
        item["id"]: deepcopy(item)
        for section in normalized["sections"]
        for item in section["items"]
    }
