from django.core.exceptions import ValidationError
from django.db import transaction
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


def _hex_color(value, default):
    value = _text(value, default)
    if len(value) != 7 or not value.startswith("#"):
        raise ValidationError(f"Cor inválida: {value}. Use o formato #RRGGBB.")
    try:
        int(value[1:], 16)
    except ValueError:
        raise ValidationError(f"Cor inválida: {value}. Use o formato #RRGGBB.")
    return value.lower()


def _entity_key(modulo_nome, entidade_nome):
    return (_text(modulo_nome).casefold(), _text(entidade_nome).casefold())


def save_system_structure(*, user, payload, sistema_id=None):
    if not isinstance(payload, dict):
        raise ValidationError("Payload do editor inválido.")
    data = payload.get("sistema") or {}
    nome = _text(data.get("nome"))
    if not nome:
        raise ValidationError("Informe o nome do sistema.")
    caminho = _text(data.get("caminho_geracao", data.get("caminho", "")))
    if not caminho:
        raise ValidationError("Informe a pasta de geração.")
    tipo_menu = _text(data.get("tipo_menu"), "lateral")
    banco = _text(data.get("banco_dados"), "sqlite3")
    if tipo_menu not in dict(Sistema.MENU_CHOICES):
        raise ValidationError("Estilo de menu inválido.")
    if banco not in dict(Sistema.BD_CHOICES):
        raise ValidationError("Banco de dados inválido.")

    with transaction.atomic():
        if sistema_id:
            sistema = Sistema.objects.filter(pk=sistema_id, usuario=user).first()
            if not sistema:
                raise ValidationError("Sistema não encontrado ou sem permissão.")
        else:
            sistema = Sistema(usuario=user)

        sistema.nome = nome
        sistema.descricao = _text(data.get("descricao"))
        tipo_sistema = _text(data.get("tipo_sistema"), sistema.tipo_sistema or Sistema.TIPO_VAZIO)
        if tipo_sistema not in dict(Sistema.TIPO_SISTEMA_CHOICES):
            raise ValidationError("Tipo inicial do sistema inválido.")
        sistema.tipo_sistema = tipo_sistema
        sistema.caminho_geracao = caminho
        sistema.tipo_menu = tipo_menu
        sistema.banco_dados = banco

        interface_modo = _text(data.get("interface_modo"), sistema.interface_modo or "automatico")
        interface_densidade = _text(data.get("interface_densidade"), sistema.interface_densidade or "confortavel")
        if interface_modo not in dict(Sistema.INTERFACE_MODO_CHOICES):
            raise ValidationError("Modo da interface inválido.")
        if interface_densidade not in dict(Sistema.INTERFACE_DENSIDADE_CHOICES):
            raise ValidationError("Densidade da interface inválida.")
        sistema.interface_modo = interface_modo
        sistema.interface_densidade = interface_densidade
        sistema.interface_nome = _text(data.get("interface_nome"), sistema.interface_nome or nome)
        sistema.interface_cor_primaria = _hex_color(
            data.get("interface_cor_primaria"),
            sistema.interface_cor_primaria or "#0d6efd",
        )
        sistema.interface_cor_destaque = _hex_color(
            data.get("interface_cor_destaque"),
            sistema.interface_cor_destaque or "#6f42c1",
        )
        sistema.interface_breadcrumb = _bool(
            data.get("interface_breadcrumb"),
            sistema.interface_breadcrumb,
        )
        sistema.interface_busca = _bool(
            data.get("interface_busca"),
            sistema.interface_busca,
        )
        sistema.interface_menu_usuario = _bool(
            data.get("interface_menu_usuario"),
            sistema.interface_menu_usuario,
        )

        sistema.usar_custom_user = _bool(data.get("usar_custom_user"), False)
        sistema.gerar_api_rest = _bool(data.get("gerar_api_rest"), False)
        sistema.gerar_docker = _bool(data.get("gerar_docker"), False)
        sistema.usar_auditoria = _bool(data.get("usar_auditoria"), False)
        sistema.save()
        sistema.modulos.all().delete()

        entity_map, pending, module_keys = {}, [], set()
        for index, mod_data in enumerate(payload.get("modulos") or [], start=1):
            mod_data = mod_data or {}
            mod_name = _text(mod_data.get("nome"))
            if not mod_name:
                raise ValidationError(f"Área {index}: informe o nome.")
            if mod_name.casefold() in module_keys:
                raise ValidationError(f"Área duplicada: {mod_name}.")
            module_keys.add(mod_name.casefold())
            modulo = Modulo.objects.create(
                sistema=sistema,
                nome=mod_name,
                descricao=_text(mod_data.get("descricao")),
            )
            entity_keys = set()
            for ent_index, ent_data in enumerate(mod_data.get("entidades") or [], start=1):
                ent_data = ent_data or {}
                ent_name = _text(ent_data.get("nome"))
                if not ent_name:
                    raise ValidationError(
                        f"Informação {mod_name} / {ent_index}: informe o nome."
                    )
                key = ent_name.casefold()
                crud = _bool(ent_data.get("gerar_crud_views"), True)
                campos = ent_data.get("campos") or []
                if key in entity_keys:
                    raise ValidationError(
                        f"Informação duplicada na área {mod_name}: {ent_name}."
                    )
                entity_keys.add(key)
                entidade = Entidade.objects.create(
                    modulo=modulo,
                    nome=ent_name,
                    nome_plural=_text(ent_data.get("nome_plural")) or f"{ent_name}s",
                    descricao=_text(ent_data.get("descricao")),
                    gerar_admin=_bool(ent_data.get("gerar_admin"), True),
                    gerar_crud_views=crud,
                    gerar_endpoints_api=_bool(ent_data.get("gerar_endpoints_api"), False),
                )
                entity_map[_entity_key(mod_name, ent_name)] = entidade
                pending.append((mod_name, ent_name, campos))

        for mod_name, ent_name, campos in pending:
            entidade = entity_map[_entity_key(mod_name, ent_name)]
            field_keys = set()
            for raw in campos:
                raw = raw or {}
                fname = _text(raw.get("nome"))
                tipo = _text(raw.get("tipo"), "CharField")
                if not fname:
                    raise ValidationError(f"Campo sem nome em {mod_name} / {ent_name}.")
                if fname.casefold() in field_keys:
                    raise ValidationError(f"Campo duplicado: {mod_name} / {ent_name} / {fname}.")
                field_keys.add(fname.casefold())
                if tipo not in ALLOWED_FIELD_TYPES:
                    raise ValidationError(f"Tipo de campo inválido: {tipo}.")

                rel, rel_name = None, _text(raw.get("rel"))
                if tipo in RELATIONAL_TYPES:
                    if not rel_name:
                        raise ValidationError(f"O campo relacional '{fname}' precisa de uma entidade destino.")
                    matches = [obj for (_, ek), obj in entity_map.items() if ek == rel_name.casefold()]
                    if len(matches) != 1:
                        raise ValidationError(f"Destino da relação '{rel_name}' é ambíguo ou não existe.")
                    rel = matches[0]

                max_length = _int_or_none(raw.get("max_length")) if tipo not in NO_MAX_LENGTH_TYPES else None
                if tipo in STRING_TYPES:
                    max_length = max_length or 255
                kwargs = {
                    "entidade": entidade,
                    "nome": fname,
                    "tipo": tipo,
                    "null": _bool(raw.get("null")),
                    "blank": _bool(raw.get("blank")),
                    "unique": _bool(raw.get("unique")),
                    "default_value": _text(raw.get("default_value", raw.get("default"))),
                    "max_length": max_length,
                    "max_digits": _int_or_none(raw.get("max_digits")) if tipo in DECIMAL_TYPES else None,
                    "decimal_places": _int_or_none(raw.get("decimal_places")) if tipo in DECIMAL_TYPES else None,
                    "upload_to": _text(raw.get("upload_to")),
                    "entidade_relacionada": rel,
                    "on_delete": _text(raw.get("on_delete"), "models.CASCADE"),
                    "related_name_str": _text(raw.get("related_name")),
                    "verbose_name": _text(raw.get("verbose_name")),
                    "help_text": _text(raw.get("help_text")),
                }
                if tipo == "DecimalField":
                    kwargs["max_digits"] = kwargs["max_digits"] or 10
                    kwargs["decimal_places"] = kwargs["decimal_places"] if kwargs["decimal_places"] is not None else 2
                Campo.objects.create(**kwargs)
        return sistema


def serialize_system_structure(sistema):
    caminho = sistema.caminho_geracao
    return {
        "sistema": {
            "nome": sistema.nome,
            "descricao": sistema.descricao,
            "tipo_sistema": sistema.tipo_sistema,
            "caminho": caminho,
            "caminho_geracao": caminho,
            "tipo_menu": sistema.tipo_menu,
            "interface_modo": sistema.interface_modo,
            "interface_densidade": sistema.interface_densidade,
            "interface_nome": sistema.interface_nome or sistema.nome,
            "interface_cor_primaria": sistema.interface_cor_primaria,
            "interface_cor_destaque": sistema.interface_cor_destaque,
            "interface_breadcrumb": sistema.interface_breadcrumb,
            "interface_busca": sistema.interface_busca,
            "interface_menu_usuario": sistema.interface_menu_usuario,
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
                                "nome": campo.nome,
                                "tipo": campo.tipo,
                                "null": campo.null,
                                "blank": campo.blank,
                                "unique": campo.unique,
                                "default_value": campo.default_value,
                                "max_length": campo.max_length,
                                "max_digits": campo.max_digits,
                                "decimal_places": campo.decimal_places,
                                "upload_to": campo.upload_to,
                                "rel": campo.entidade_relacionada.nome if campo.entidade_relacionada else "",
                                "on_delete": campo.on_delete,
                                "related_name": campo.related_name_str,
                                "verbose_name": campo.verbose_name,
                                "help_text": campo.help_text,
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
