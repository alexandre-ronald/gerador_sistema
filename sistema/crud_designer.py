from copy import deepcopy


ALLOWED_PAGE_SIZES = (10, 25, 50, 100)
ALLOWED_FILTER_TYPES = ("text", "select", "boolean", "date", "relation")

TEXT_TYPES = {"CharField", "TextField", "EmailField", "SlugField", "URLField", "UUIDField"}
NUMBER_TYPES = {"IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField", "PositiveSmallIntegerField", "FloatField", "DecimalField"}
DATE_TYPES = {"DateField", "DateTimeField"}
BOOLEAN_TYPES = {"BooleanField", "NullBooleanField"}
RELATION_TYPES = {"ForeignKey", "OneToOneField"}
UNSAFE_LIST_TYPES = {"FileField", "ImageField", "ManyToManyField"}


class CrudDesignerError(ValueError):
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
        raise CrudDesignerError(code, "Nome inválido ou inseguro.")
    return value


def _metadata_map(entity_metadata):
    result = {}
    for item in entity_metadata.get("fields") or []:
        name = _safe_name(item.get("name"), code="invalid_metadata_field")
        result[name] = deepcopy(item)
    return result


def _field_type(metadata):
    return str(metadata.get("type") or "CharField")


def _label(metadata):
    name = str(metadata.get("name") or "")
    return str(metadata.get("label") or metadata.get("verbose_name") or name.replace("_", " ").title())


def is_searchable(metadata):
    return _field_type(metadata) in TEXT_TYPES


def is_sortable(metadata):
    return _field_type(metadata) not in {"ManyToManyField"}


def compatible_filter_types(metadata):
    field_type = _field_type(metadata)
    if field_type in BOOLEAN_TYPES:
        return ("boolean",)
    if field_type in DATE_TYPES:
        return ("date",)
    if field_type in RELATION_TYPES:
        return ("relation", "select")
    if metadata.get("choices"):
        return ("select",)
    if field_type in TEXT_TYPES or field_type in NUMBER_TYPES:
        return ("text",)
    return ()


def default_column_config(metadata, order):
    name = _safe_name(metadata.get("name"), code="invalid_metadata_field")
    return {
        "field": name,
        "label": _label(metadata),
        "order": order,
        "visible": _field_type(metadata) not in UNSAFE_LIST_TYPES,
        "sortable": is_sortable(metadata),
    }


def default_crud_config(entity_name, entity_metadata):
    metadata = _metadata_map(entity_metadata)
    columns = [default_column_config(item, index) for index, item in enumerate(metadata.values())]
    search_fields = [name for name, item in metadata.items() if is_searchable(item)]
    return {
        "title": str(entity_metadata.get("plural_label") or entity_metadata.get("verbose_name_plural") or entity_name),
        "page_size": 25,
        "default_order": "",
        "columns": columns,
        "search": {
            "enabled": bool(search_fields),
            "fields": search_fields,
            "placeholder": f"Pesquisar {entity_name.lower()}",
        },
        "filters": [],
        "actions": {"create": True, "view": True, "edit": True, "delete": True},
    }


def _normalize_column(item, metadata, fallback_order):
    field = _safe_name(item.get("field"), code="invalid_column_field")
    visible = item.get("visible", True)
    sortable = item.get("sortable", is_sortable(metadata))
    if not isinstance(visible, bool):
        raise CrudDesignerError("invalid_column_visible", "visible deve ser booleano.", field=field)
    if not isinstance(sortable, bool):
        raise CrudDesignerError("invalid_column_sortable", "sortable deve ser booleano.", field=field)
    if sortable and not is_sortable(metadata):
        raise CrudDesignerError("incompatible_sort", "Campo não suporta ordenação.", field=field)
    try:
        order = int(item.get("order", fallback_order))
    except (TypeError, ValueError):
        raise CrudDesignerError("invalid_column_order", "Ordem da coluna inválida.", field=field)
    return {
        "field": field,
        "label": str(item.get("label") if item.get("label") is not None else _label(metadata)),
        "order": order,
        "visible": visible,
        "sortable": sortable,
    }


def _normalize_search(config, metadata, base, *, strict):
    config = config if isinstance(config, dict) else {}
    enabled = config.get("enabled", base["enabled"])
    if not isinstance(enabled, bool):
        raise CrudDesignerError("invalid_search_enabled", "enabled deve ser booleano.")
    fields = []
    seen = set()
    for raw_name in config.get("fields", base["fields"]):
        name = _safe_name(raw_name, code="invalid_search_field")
        if name not in metadata:
            if strict:
                raise CrudDesignerError("unknown_search_field", "Campo de busca não existe.", field=name)
            continue
        if name in seen:
            raise CrudDesignerError("duplicate_search_field", "Campo de busca não pode se repetir.", field=name)
        if not is_searchable(metadata[name]):
            raise CrudDesignerError("incompatible_search_field", "Campo não é compatível com busca textual.", field=name)
        seen.add(name)
        fields.append(name)
    return {
        "enabled": enabled and bool(fields),
        "fields": fields,
        "placeholder": str(config.get("placeholder") if config.get("placeholder") is not None else base["placeholder"]),
    }


def _normalize_filter(item, metadata, fallback_order):
    field = _safe_name(item.get("field"), code="invalid_filter_field")
    filter_type = str(item.get("type") or "").strip()
    if filter_type not in ALLOWED_FILTER_TYPES or filter_type not in compatible_filter_types(metadata):
        raise CrudDesignerError("incompatible_filter", "Tipo de filtro incompatível com o campo.", field=field)
    try:
        order = int(item.get("order", fallback_order))
    except (TypeError, ValueError):
        raise CrudDesignerError("invalid_filter_order", "Ordem do filtro inválida.", field=field)
    return {
        "field": field,
        "label": str(item.get("label") if item.get("label") is not None else _label(metadata)),
        "type": filter_type,
        "order": order,
    }


def _normalize_actions(config, base):
    config = config if isinstance(config, dict) else {}
    actions = {}
    for name in ("create", "view", "edit", "delete"):
        value = config.get(name, base[name])
        if not isinstance(value, bool):
            raise CrudDesignerError("invalid_action", f"A ação {name} deve ser booleana.", field=name)
        actions[name] = value
    return actions


def normalize_crud_config(entity_name, entity_metadata, config=None, *, strict=False):
    entity_name = _safe_name(entity_name, code="invalid_entity")
    metadata_name = str(entity_metadata.get("name") or entity_name)
    if metadata_name != entity_name:
        raise CrudDesignerError("unknown_entity", "Entidade não corresponde ao metadata informado.")

    metadata = _metadata_map(entity_metadata)
    config = deepcopy(config or {})
    base = default_crud_config(entity_name, entity_metadata)

    try:
        page_size = int(config.get("page_size", base["page_size"]))
    except (TypeError, ValueError):
        raise CrudDesignerError("invalid_page_size", "Paginação inválida.")
    if page_size not in ALLOWED_PAGE_SIZES:
        raise CrudDesignerError("invalid_page_size", "Paginação deve ser 10, 25, 50 ou 100.")

    configured_columns = {}
    for index, item in enumerate(config.get("columns") or []):
        field = _safe_name(item.get("field"), code="invalid_column_field")
        if field not in metadata:
            if strict:
                raise CrudDesignerError("unknown_column_field", "Campo da coluna não existe.", field=field)
            continue
        if field in configured_columns:
            raise CrudDesignerError("duplicate_column", "Campo não pode aparecer em duas colunas.", field=field)
        configured_columns[field] = _normalize_column(item, metadata[field], index)

    if config.get("columns") is not None:
        columns = list(configured_columns.values())
    else:
        columns = deepcopy(base["columns"])
    columns.sort(key=lambda item: (item["order"], item["field"]))
    for index, item in enumerate(columns):
        item["order"] = index

    search = _normalize_search(config.get("search"), metadata, base["search"], strict=strict)

    filters = []
    seen_filters = set()
    for index, item in enumerate(config.get("filters") or []):
        field = _safe_name(item.get("field"), code="invalid_filter_field")
        if field not in metadata:
            if strict:
                raise CrudDesignerError("unknown_filter_field", "Campo do filtro não existe.", field=field)
            continue
        if field in seen_filters:
            raise CrudDesignerError("duplicate_filter", "Campo não pode possuir dois filtros nesta versão.", field=field)
        seen_filters.add(field)
        filters.append(_normalize_filter(item, metadata[field], index))
    filters.sort(key=lambda item: (item["order"], item["field"]))
    for index, item in enumerate(filters):
        item["order"] = index

    default_order = str(config.get("default_order") or "").strip()
    if default_order:
        descending = default_order.startswith("-")
        order_field = default_order[1:] if descending else default_order
        order_field = _safe_name(order_field, code="invalid_default_order")
        column = next((item for item in columns if item["field"] == order_field), None)
        if column is None or not column["sortable"]:
            raise CrudDesignerError("invalid_default_order", "Ordenação padrão deve usar uma coluna ordenável.", field=order_field)
        default_order = f"-{order_field}" if descending else order_field

    return {
        "title": str(config.get("title") or base["title"]),
        "page_size": page_size,
        "default_order": default_order,
        "columns": columns,
        "search": search,
        "filters": filters,
        "actions": _normalize_actions(config.get("actions"), base["actions"]),
    }
