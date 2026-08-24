from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Campo, Entidade, Modulo, Sistema


ALLOWED_FIELD_TYPES = {choice[0] for choice in Campo.TIPO_CAMPO_CHOICES}
STRING_TYPES = {"CharField", "EmailField", "URLField"}
DECIMAL_TYPES = {"DecimalField"}
RELATIONAL_TYPES = {"ForeignKey", "ManyToManyField", "OneToOneField"}
NO_MAX_LENGTH_TYPES = {"TextField", "IntegerField", "FloatField", "DecimalField", "BooleanField", "DateField", "DateTimeField", "TimeField", *RELATIONAL_TYPES}


def _int_or_none(value):
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Valor inteiro inválido: {value!r}")
    if number <= 0:
        raise ValidationError(f"Valor inteiro deve ser maior que zero: {value!r}")
    return number


def _bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "on", "yes", "sim"}


def _text(value, default=""):
    return str(value if value is not None else default).strip()


def _entity_key(modulo_nome, entidade_nome):
    return (_text(modulo_nome).casefold(), _text(entidade_nome).casefold())


def save_system_structure(*, user, payload, sistema_id=None):
    if not isinstance(payload, dict):
        raise ValidationError("Payload do editor inválido.")

    sistema_data = payload.get("sistema") or {}
    nome = _text(sistema_data.get("nome"))
    if not nome:
        raise ValidationError("Informe o nome do sistema.")
    tipo_menu = _text(sistema_data.get("tipo_menu"), "lateral")
    banco_dados = _text(sistema_data.get("banco_dados"), "sqlite3")
    if tipo_menu not in dict(Sistema.MENU_CHOICES):
        raise ValidationError("Estilo de menu inválido.")
    if banco_dados not in dict(Sistema.BD_CHOICES):
        raise ValidationError("Banco de dados inválido.")

    with transaction.atomic():
        if sistema_id:
            sistema = Sistema.objects.filter(pk=sistema_id, usuario=user).first()
            if not sistema:
                raise ValidationError("Sistema não encontrado ou sem permissão.")
        else:
            sistema = Sistema(usuario=user)

        sistema.nome = nome
        sistema.descricao = _text(sistema_data.get("descricao"))
        sistema.caminho_geracao = _text(sistema_data.get("caminho"))
        sistema.tipo_menu = tipo_menu
        sistema.banco_dados = banco_dados
        sistema.usar_custom_user = _bool(sistema_data.get("usar_custom_user"), True)
        sistema.gerar_api_rest = _bool(sistema_data.get("gerar_api_rest"), False)
        sistema.gerar_docker = _bool(sistema_data.get("gerar_docker"), False)
        sistema.usar_auditoria = _bool(sistema_data.get("usar_auditoria"), False)
        sistema.save()
        sistema.modulos.all().delete()

        entity_map = {}
        pending_fields = []
        for mod_data in payload.get("modulos") or []:
            mod_data = mod_data or {}
            modulo_nome = _text(mod_data.get("nome")) or "Modulo"
            modulo = Modulo.objects.create(sistema=sistema, nome=modulo_nome, descricao=_text(mod_data.get("descricao")))
            for ent_data in mod_data.get("entidades") or []:
                ent_data = ent_data or {}
                entidade_nome = _text(ent_data.get("nome")) or "Entidade"
                gerar_crud = _bool(ent_data.get("gerar_crud_views"), True)
                campos = ent_data.get("campos") or []
                if gerar_crud and not campos:
                    raise ValidationError(f"A entidade '{entidade_nome}' está com CRUD ativo, mas não possui campos.")
                entidade = Entidade.objects.create(
                    modulo=modulo,
                    nome=entidade_nome,
                    nome_plural=_text(ent_data.get("nome_plural")) or f"{entidade_nome}s",
                    descricao=_text(ent_data.get("descricao")),
                    gerar_admin=_bool(ent_data.get("gerar_admin"), True),
                    gerar_crud_views=gerar_crud,
                    gerar_endpoints_api=_bool(ent_data.get("gerar_endpoints_api"), False) and sistema.gerar_api_rest,
                )
                key = _entity_key(modulo_nome, entidade_nome)
                if key in entity_map:
                    raise ValidationError(f"Entidade duplicada: {modulo_nome} / {entidade_nome}.")
                entity_map[key] = entidade
                pending_fields.append((modulo_nome, entidade_nome, campos))

        for modulo_nome, entidade_nome, campos in pending_fields:
            entidade = entity_map[_entity_key(modulo_nome, entidade_nome)]
            for campo_data in campos:
                campo_data = campo_data or {}
                nome_campo = _text(campo_data.get("nome"))
                if not nome_campo:
                    raise ValidationError(f"Campo sem nome em {modulo_nome} / {entidade_nome}.")
                tipo = _text(campo_data.get("tipo"), "CharField")
                if tipo not in ALLOWED_FIELD_TYPES:
                    raise ValidationError(f"Tipo de campo inválido: {tipo}.")

                rel = None
                rel_nome = _text(campo_data.get("rel"))
                if tipo in RELATIONAL_TYPES:
                    if not rel_nome:
                        raise ValidationError(f"O campo relacional '{nome_campo}' precisa de uma entidade destino.")
                    matches = [obj for (mod_key, ent_key), obj in entity_map.items() if ent_key == rel_nome.casefold()]
                    if len(matches) != 1:
                        raise ValidationError(f"Destino da relação '{rel_nome}' é ambíguo ou não existe.")
                    rel = matches[0]

                max_length = _int_or_none(campo_data.get("max_length")) if tipo not in NO_MAX_LENGTH_TYPES else None
                if tipo in STRING_TYPES:
                    max_length = max_length or 255
                kwargs = {
                    "entidade": entidade,
                    "nome": nome_campo,
                    "tipo": tipo,
                    "null": _bool(campo_data.get("null")),
                    "blank": _bool(campo_data.get("blank")),
                    "unique": _bool(campo_data.get("unique")),
                    "default_value": _text(campo_data.get("default_value", campo_data.get("default"))),
                    "max_length": max_length,
                    "max_digits": _int_or_none(campo_data.get("max_digits")) if tipo in DECIMAL_TYPES else None,
                    "decimal_places": _int_or_none(campo_data.get("decimal_places")) if tipo in DECIMAL_TYPES else None,
                    "upload_to": _text(campo_data.get("upload_to")),
                    "entidade_relacionada": rel,
                    "on_delete": _text(campo_data.get("on_delete"), "models.CASCADE"),
                    "related_name_str": _text(campo_data.get("related_name")),
                    "verbose_name": _text(campo_data.get("verbose_name")),
                    "help_text": _text(campo_data.get("help_text")),
                }
                if tipo == "DecimalField":
                    kwargs["max_digits"] = kwargs["max_digits"] or 10
                    kwargs["decimal_places"] = kwargs["decimal_places"] if kwargs["decimal_places"] is not None else 2
                Campo.objects.create(**kwargs)
        return sistema


def serialize_system_structure(sistema):
    return {
        "sistema": {
            "nome": sistema.nome,
            "descricao": sistema.descricao,
            "caminho": sistema.caminho_geracao,
            "tipo_menu": sistema.tipo_menu,
            "banco_dados": sistema.banco_dados,
            "usar_custom_user": sistema.usar_custom_user,
            "gerar_api_rest": sistema.gerar_api_rest,
            "gerar_docker": sistema.gerar_docker,
            "usar_auditoria": sistema.usar_auditoria,
        },
        "modulos": [
            {
                "nome": modulo.nome,
                "descricao": modulo.descricao,
                "entidades": [
                    {
                        "nome": entidade.nome,
                        "nome_plural": entidade.nome_plural,
                        "descricao": entidade.descricao,
                        "gerar_admin": entidade.gerar_admin,
                        "gerar_crud_views": entidade.gerar_crud_views,
                        "gerar_endpoints_api": entidade.gerar_endpoints_api,
                        "campos": [
                            {
                                "nome": campo.nome, "tipo": campo.tipo,
                                "max_length": campo.max_length, "max_digits": campo.max_digits,
                                "decimal_places": campo.decimal_places,
                                "rel": campo.entidade_relacionada.nome if campo.entidade_relacionada else None,
                                "null": campo.null, "blank": campo.blank, "unique": campo.unique,
                                "default_value": campo.default_value, "upload_to": campo.upload_to,
                                "related_name": campo.related_name_str, "on_delete": campo.on_delete,
                                "verbose_name": campo.verbose_name, "help_text": campo.help_text,
                            }
                            for campo in entidade.campos.all()
                        ],
                    }
                    for entidade in modulo.entidades.all()
                ],
            }
            for modulo in sistema.modulos.all()
        ],
    }
