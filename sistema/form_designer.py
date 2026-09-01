from copy import deepcopy


ALLOWED_WIDTHS = (3, 4, 6, 8, 12)
ALLOWED_WIDGETS = ("text", "textarea", "number", "date", "datetime", "checkbox", "select")

TEXT_TYPES = {"CharField", "TextField", "EmailField", "SlugField", "URLField", "UUIDField"}
NUMBER_TYPES = {"IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField", "PositiveSmallIntegerField", "FloatField", "DecimalField"}
DATE_TYPES = {"DateField"}
DATETIME_TYPES = {"DateTimeField"}
BOOLEAN_TYPES = {"BooleanField", "NullBooleanField"}
RELATION_TYPES = {"ForeignKey", "OneToOneField", "ManyToManyField"}


class FormDesignerError(ValueError):
    def __init__(self, code, message, *, field=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field

    def as_dict(self):
        data = {"code": self.code, "message": self.message}
        if self.field:
            data["field"] = self.field
        return data


def _safe_name(value, *, code="unsafe_name"):
    value = str(value or "").strip()
    if not value or "__" in value or "." in value or "/" in value or "\\" in value:
        raise FormDesignerError(code, "Nome inválido ou inseguro.")
    return value


def infer_widget(field_type):
    field_type = str(field_type or "CharField")
    if field_type == "TextField":
        return "textarea"
    if field_type in NUMBER_TYPES:
        return "number"
    if field_type in DATE_TYPES:
        return "date"
    if field_type in DATETIME_TYPES:
        return "datetime"
    if field_type in BOOLEAN_TYPES:
        return "checkbox"
    if field_type in RELATION_TYPES:
        return "select"
    return "text"


def compatible_widgets(field_type):
    field_type = str(field_type or "CharField")
    if field_type == "TextField":
        return ("text", "textarea")
    if field_type in TEXT_TYPES:
        return ("text", "textarea")
    if field_type in NUMBER_TYPES:
        return ("number",)
    if field_type in DATE_TYPES:
        return ("date",)
    if field_type in DATETIME_TYPES:
        return ("datetime",)
    if field_type in BOOLEAN_TYPES:
        return ("checkbox",)
    if field_type in RELATION_TYPES:
        return ("select",)
    return ("text",)


def _metadata_map(entity_metadata):
    fields = entity_metadata.get("fields") or []
    result = {}
    for item in fields:
        name = _safe_name(item.get("name"), code="invalid_metadata_field")
        result[name] = deepcopy(item)
    return result


def default_field_config(metadata, order):
    name = _safe_name(metadata.get("name"), code="invalid_metadata_field")
    field_type = str(metadata.get("type") or "CharField")
    label = str(metadata.get("label") or metadata.get("verbose_name") or name.replace("_", " ").title())
    editable = metadata.get("editable", True) is not False
    return {
        "name": name,
        "order": order,
        "section": "",
        "visible": bool(editable),
        "readonly": not bool(editable),
        "width": 12,
        "label": label,
        "placeholder": "",
        "help_text": str(metadata.get("help_text") or ""),
        "widget": infer_widget(field_type),
    }


def _normalize_section(item, order):
    section_id = _safe_name(item.get("id"), code="invalid_section_id")
    return {
        "id": section_id,
        "title": str(item.get("title") or section_id.replace("_", " ").title()),
        "description": str(item.get("description") or ""),
        "order": int(item.get("order", order)),
    }


def _normalize_field(item, metadata, fallback_order, section_ids):
    name = _safe_name(item.get("name"), code="invalid_field")
    field_type = str(metadata.get("type") or "CharField")
    base = default_field_config(metadata, fallback_order)

    visible = item.get("visible", base["visible"])
    readonly = item.get("readonly", base["readonly"])
    if not isinstance(visible, bool):
        raise FormDesignerError("invalid_visible", "visible deve ser booleano.", field=name)
    if not isinstance(readonly, bool):
        raise FormDesignerError("invalid_readonly", "readonly deve ser booleano.", field=name)

    try:
        width = int(item.get("width", base["width"]))
    except (TypeError, ValueError):
        raise FormDesignerError("invalid_width", "Largura inválida.", field=name)
    if width not in ALLOWED_WIDTHS:
        raise FormDesignerError("invalid_width", "Largura deve ser 3, 4, 6, 8 ou 12.", field=name)

    section = str(item.get("section") or "").strip()
    if section:
        _safe_name(section, code="invalid_section_reference")
        if section not in section_ids:
            raise FormDesignerError("unknown_section", "Seção referenciada não existe.", field=name)

    widget = str(item.get("widget") or base["widget"])
    if widget not in ALLOWED_WIDGETS or widget not in compatible_widgets(field_type):
        raise FormDesignerError("incompatible_widget", f"Widget {widget} incompatível com {field_type}.", field=name)

    return {
        "name": name,
        "order": int(item.get("order", fallback_order)),
        "section": section,
        "visible": visible,
        "readonly": readonly or metadata.get("editable", True) is False,
        "width": width,
        "label": str(item.get("label") if item.get("label") is not None else base["label"]),
        "placeholder": str(item.get("placeholder") or ""),
        "help_text": str(item.get("help_text") if item.get("help_text") is not None else base["help_text"]),
        "widget": widget,
    }


def normalize_form_config(entity_name, entity_metadata, config=None, *, strict=False):
    entity_name = _safe_name(entity_name, code="invalid_entity")
    metadata_name = str(entity_metadata.get("name") or entity_name)
    if metadata_name != entity_name:
        raise FormDesignerError("unknown_entity", "Entidade não corresponde ao metadata informado.")

    metadata = _metadata_map(entity_metadata)
    config = deepcopy(config or {})

    sections = []
    section_ids = set()
    for index, item in enumerate(config.get("sections") or []):
        section = _normalize_section(item, index)
        if section["id"] in section_ids:
            raise FormDesignerError("duplicate_section", "IDs de seção não podem se repetir.")
        section_ids.add(section["id"])
        sections.append(section)
    sections.sort(key=lambda item: (item["order"], item["id"]))

    configured = {}
    for index, item in enumerate(config.get("fields") or []):
        name = _safe_name(item.get("name"), code="invalid_field")
        if name not in metadata:
            if strict:
                raise FormDesignerError("unknown_field", "Campo não existe na entidade.", field=name)
            continue
        if name in configured:
            raise FormDesignerError("duplicate_field", "Campo não pode aparecer duas vezes.", field=name)
        configured[name] = _normalize_field(item, metadata[name], index, section_ids)

    fields = []
    for index, (name, item_metadata) in enumerate(metadata.items()):
        fields.append(configured.get(name) or default_field_config(item_metadata, len(configured) + index))
    fields.sort(key=lambda item: (item["order"], item["name"]))
    for index, item in enumerate(fields):
        item["order"] = index

    return {
        "title": str(config.get("title") or f"Cadastro de {entity_name}"),
        "sections": sections,
        "fields": fields,
    }
