from copy import deepcopy

from django import template

from sistema.workflow import normalize_workflow_config

register = template.Library()


def _empty_config():
    return {
        "enabled": False,
        "state_field": "",
        "state_field_code": "",
        "initial_state": "",
        "states": [],
        "transitions": [],
    }


def _metadata(entidade):
    campos = getattr(entidade, "campos_geracao", None) or []
    return {
        "name": getattr(entidade, "nome", ""),
        "label": getattr(entidade, "nome", ""),
        "fields": [
            {
                "name": getattr(campo, "nome", ""),
                "label": getattr(campo, "verbose_name", "") or getattr(campo, "nome", ""),
                "type": getattr(campo, "tipo", ""),
                "editable": True,
            }
            for campo in campos
        ],
    }


def _stored(entidade):
    modulo = getattr(entidade, "modulo", None)
    sistema = getattr(modulo, "sistema", None) if modulo is not None else None
    if sistema is None:
        return None
    versao = sistema.versoes.filter(numero=0).first()
    estrutura = versao.estrutura_json if versao and isinstance(versao.estrutura_json, dict) else {}
    workflows = estrutura.get("workflows") if isinstance(estrutura.get("workflows"), dict) else {}
    return workflows.get(getattr(entidade, "nome", ""))


def _config(entidade):
    raw = _stored(entidade)
    if not isinstance(raw, dict):
        return _empty_config()

    nome = getattr(entidade, "nome", "")
    campos = getattr(entidade, "campos_geracao", None) or []
    if not nome or not campos:
        return _empty_config()

    config = normalize_workflow_config(nome, _metadata(entidade), raw, strict=True)
    source = {getattr(campo, "nome", ""): campo for campo in campos}
    result = deepcopy(config)
    state_field = config.get("state_field")
    state_source = source.get(state_field)
    result["state_field_code"] = getattr(state_source, "codigo_nome", "") if state_source else ""
    result["class_name"] = getattr(entidade, "classe_nome", "")
    result["entity_code"] = getattr(entidade, "codigo_nome", "")
    return result


@register.simple_tag
def workflow_generation_config(entidade):
    return _config(entidade)


@register.simple_tag
def module_has_workflow(entidades):
    return any(_config(entidade).get("enabled") for entidade in entidades)
