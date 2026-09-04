from django import template

register = template.Library()


def _stored(entidade):
    modulo = getattr(entidade, "modulo", None)
    sistema = getattr(modulo, "sistema", None) if modulo is not None else None
    if sistema is None:
        return None
    versao = sistema.versoes.filter(numero=0).first()
    estrutura = versao.estrutura_json if versao and isinstance(versao.estrutura_json, dict) else {}
    reports = estrutura.get("reports") if isinstance(estrutura.get("reports"), dict) else {}
    return reports.get(getattr(entidade, "nome", ""))


def _empty_config():
    return {"enabled": False, "id": "", "title": "", "description": "", "columns": [], "filters": [], "order_by_code": ""}


def _raw_items(entidade):
    raw = _stored(entidade)
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [raw]
    return []


def _config_from_raw(entidade, raw, index=1):
    if not isinstance(raw, dict) or not raw.get("enabled"):
        return _empty_config()
    campos = getattr(entidade, "campos_geracao", None) or []
    source = {getattr(campo, "nome", ""): campo for campo in campos}
    report_id = str(raw.get("id") or f"relatorio_{index}").strip().lower()
    columns = []
    for name in raw.get("fields", []):
        campo = source.get(name)
        if campo is None:
            continue
        columns.append({"field": name,"code": getattr(campo, "codigo_nome", name),"label": getattr(campo, "verbose_name", "") or name.replace("_", " ").title(),"field_type": getattr(campo, "tipo", "")})
    filters = []
    for item in raw.get("filters", []):
        if isinstance(item, str): item = {"field": item, "type": "contains"}
        if not isinstance(item, dict): continue
        campo = source.get(item.get("field"))
        if campo is None: continue
        code = getattr(campo, "codigo_nome", item.get("field")); filter_type = item.get("type") or "contains"
        filters.append({"field": item.get("field"),"code": code,"label": getattr(campo, "verbose_name", "") or item.get("field", "").replace("_", " ").title(),"field_type": getattr(campo, "tipo", ""),"type": filter_type,"param": f"report_{code}","param_from": f"report_{code}_from","param_to": f"report_{code}_to"})
    order_by = str(raw.get("order_by") or ""); descending = order_by.startswith("-"); order_name = order_by[1:] if descending else order_by; order_source = source.get(order_name); order_code = getattr(order_source, "codigo_nome", "") if order_source else ""
    if order_code and descending: order_code = f"-{order_code}"
    entity_code = getattr(entidade, "codigo_nome", "")
    return {"enabled": True,"id": report_id,"title": str(raw.get("title") or f"Relatório de {getattr(entidade, 'nome', '')}"),"description": str(raw.get("description") or ""),"columns": columns,"filters": filters,"order_by_code": order_code,"view_name": f"{entity_code}_report_{report_id}","template_name": f"{entity_code}_report_{report_id}.html"}


def _configs(entidade):
    result = []
    for index, raw in enumerate(_raw_items(entidade), start=1):
        config = _config_from_raw(entidade, raw, index)
        if config.get("enabled"): result.append(config)
    return result


@register.simple_tag
def report_generation_config(entidade, report_id=None):
    configs = _configs(entidade)
    if report_id:
        for config in configs:
            if config.get("id") == report_id:
                return config
        return _empty_config()
    return configs[0] if configs else _empty_config()


@register.simple_tag
def report_generation_configs(entidade):
    return _configs(entidade)


@register.simple_tag
def module_has_reports(entidades):
    return any(_configs(entidade) for entidade in entidades)
