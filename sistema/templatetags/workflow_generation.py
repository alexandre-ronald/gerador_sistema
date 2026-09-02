from copy import deepcopy

from django import template

from sistema.workflow import normalize_workflow_config

register = template.Library()


def _metadata(entidade):
    return {
        "name": entidade.nome,
        "label": entidade.nome,
        "fields": [
            {
                "name": campo.nome,
                "label": campo.verbose_name or campo.nome,
                "type": campo.tipo,
                "editable": True,
            }
            for campo in entidade.campos_geracao
        ],
    }


def _stored(entidade):
    sistema = entidade.modulo.sistema
    versao = sistema.versoes.filter(numero=0).first()
    estrutura = versao.estrutura_json if versao and isinstance(versao.estrutura_json, dict) else {}
    workflows = estrutura.get("workflows") if isinstance(estrutura.get("workflows"), dict) else {}
    return workflows.get(entidade.nome)


def _config(entidade):
    raw = _stored(entidade)
    if not isinstance(raw, dict):
        return {
            "enabled": False,
            "state_field": "",
            "state_field_code": "",
            "initial_state": "",
            "states": [],
            "transitions": [],
        }
    config = normalize_workflow_config(entidade.nome, _metadata(entidade), raw, strict=True)
    source = {campo.nome: campo for campo in entidade.campos_geracao}
    result = deepcopy(config)
    result["state_field_code"] = source[config["state_field"]].codigo_nome if config.get("state_field") in source else ""
    result["class_name"] = entidade.classe_nome
    result["entity_code"] = entidade.codigo_nome
    return result


@register.simple_tag
def workflow_generation_config(entidade):
    return _config(entidade)


@register.simple_tag
def module_has_workflow(entidades):
    return any(_config(entidade).get("enabled") for entidade in entidades)
