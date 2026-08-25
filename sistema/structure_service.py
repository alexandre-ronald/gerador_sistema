from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Campo, Entidade, Modulo, Sistema

ALLOWED_FIELD_TYPES = {choice[0] for choice in Campo.TIPO_CAMPO_CHOICES}
STRING_TYPES = {"CharField", "EmailField", "URLField"}
DECIMAL_TYPES = {"DecimalField"}
RELATIONAL_TYPES = {"ForeignKey", "ManyToManyField", "OneToOneField"}
NO_MAX_LENGTH_TYPES = {"TextField", "IntegerField", "FloatField", "DecimalField", "BooleanField", "DateField", "DateTimeField", "TimeField", *RELATIONAL_TYPES}

def _int_or_none(value):
    if value in (None, ""): return None
    try: number = int(value)
    except (TypeError, ValueError): raise ValidationError(f"Valor inteiro inválido: {value!r}")
    if number <= 0: raise ValidationError(f"Valor inteiro deve ser maior que zero: {value!r}")
    return number

def _bool(value, default=False):
    if value is None: return default
    if isinstance(value, bool): return value
    return str(value).strip().lower() in {"1", "true", "on", "yes", "sim"}

def _text(value, default=""): return str(value if value is not None else default).strip()
def _entity_key(modulo_nome, entidade_nome): return (_text(modulo_nome).casefold(), _text(entidade_nome).casefold())

def save_system_structure(*, user, payload, sistema_id=None):
    if not isinstance(payload, dict): raise ValidationError("Payload do editor inválido.")
    data = payload.get("sistema") or {}; nome = _text(data.get("nome"))
    if not nome: raise ValidationError("Informe o nome do sistema.")
    tipo_menu, banco = _text(data.get("tipo_menu"), "lateral"), _text(data.get("banco_dados"), "sqlite3")
    if tipo_menu not in dict(Sistema.MENU_CHOICES): raise ValidationError("Estilo de menu inválido.")
    if banco not in dict(Sistema.BD_CHOICES): raise ValidationError("Banco de dados inválido.")
    with transaction.atomic():
        if sistema_id:
            sistema = Sistema.objects.filter(pk=sistema_id, usuario=user).first()
            if not sistema: raise ValidationError("Sistema não encontrado ou sem permissão.")
        else: sistema = Sistema(usuario=user)
        # System Builder uses "caminho_geracao" as the canonical UI field.
        # Keep "caminho" as a backward-compatible payload alias.
        caminho = data.get("caminho_geracao", data.get("caminho", ""))
        sistema.nome, sistema.descricao, sistema.caminho_geracao = nome, _text(data.get("descricao")), _text(caminho)
        sistema.tipo_menu, sistema.banco_dados = tipo_menu, banco
        sistema.usar_custom_user = False
        sistema.gerar_api_rest = False
        sistema.gerar_docker = _bool(data.get("gerar_docker"), False)
        sistema.usar_auditoria = _bool(data.get("usar_auditoria"), False)
        sistema.save(); sistema.modulos.all().delete()
        entity_map, pending, module_keys = {}, [], set()
        for mod_data in payload.get("modulos") or []:
            mod_data = mod_data or {}; mod_name = _text(mod_data.get("nome")) or "Modulo"
            if mod_name.casefold() in module_keys: raise ValidationError(f"Módulo duplicado: {mod_name}.")
            module_keys.add(mod_name.casefold())
            modulo = Modulo.objects.create(sistema=sistema, nome=mod_name, descricao=_text(mod_data.get("descricao")))
            entity_keys = set()
            for ent_data in mod_data.get("entidades") or []:
                ent_data = ent_data or {}; ent_name = _text(ent_data.get("nome")) or "Entidade"; key = ent_name.casefold(); crud = _bool(ent_data.get("gerar_crud_views"), True); campos = ent_data.get("campos") or []
                if key in entity_keys: raise ValidationError(f"Entidade duplicada: {mod_name} / {ent_name}.")
                entity_keys.add(key)
                if crud and not campos: raise ValidationError(f"A entidade '{ent_name}' está com CRUD ativo, mas não possui campos.")
                entidade = Entidade.objects.create(modulo=modulo, nome=ent_name, nome_plural=_text(ent_data.get("nome_plural")) or f"{ent_name}s", descricao=_text(ent_data.get("descricao")), gerar_admin=_bool(ent_data.get("gerar_admin"), True), gerar_crud_views=crud, gerar_endpoints_api=False)
                entity_map[_entity_key(mod_name, ent_name)] = entidade; pending.append((mod_name, ent_name, campos))
        for mod_name, ent_name, campos in pending:
            entidade = entity_map[_entity_key(mod_name, ent_name)]; field_keys = set()
            for raw in campos:
                raw = raw or {}; fname, tipo = _text(raw.get("nome")), _text(raw.get("tipo"), "CharField")
                if not fname: raise ValidationError(f"Campo sem nome em {mod_name} / {ent_name}.")
                if fname.casefold() in field_keys: raise ValidationError(f"Campo duplicado: {mod_name} / {ent_name} / {fname}.")
                field_keys.add(fname.casefold())
                if tipo not in ALLOWED_FIELD_TYPES: raise ValidationError(f"Tipo de campo inválido: {tipo}.")
                rel, rel_name = None, _text(raw.get("rel"))
                if tipo in RELATIONAL_TYPES:
                    if not rel_name: raise ValidationError(f"O campo relacional '{fname}' precisa de uma entidade destino.")
                    matches = [obj for (_, ek), obj in entity_map.items() if ek == rel_name.casefold()]
                    if len(matches) != 1: raise ValidationError(f"Destino da relação '{rel_name}' é ambíguo ou não existe.")
                    rel = matches[0]
                max_length = _int_or_none(raw.get("max_length")) if tipo not in NO_MAX_LENGTH_TYPES else None
                if tipo in STRING_TYPES: max_length = max_length or 255
                kwargs = {"entidade": entidade, "nome": fname, "tipo": tipo, "null": _bool(raw.get("null")), "blank": _bool(raw.get("blank")), "unique": _bool(raw.get("unique")), "default_value": _text(raw.get("default_value", raw.get("default"))), "max_length": max_length, "max_digits": _int_or_none(raw.get("max_digits")) if tipo in DECIMAL_TYPES else None, "decimal_places": _int_or_none(raw.get("decimal_places")) if tipo in DECIMAL_TYPES else None, "upload_to": _text(raw.get("upload_to")), "entidade_relacionada": rel, "on_delete": _text(raw.get("on_delete"), "models.CASCADE"), "related_name_str": _text(raw.get("related_name")), "verbose_name": _text(raw.get("verbose_name")), "help_text": _text(raw.get("help_text"))}
                if tipo == "DecimalField": kwargs["max_digits"] = kwargs["max_digits"] or 10; kwargs["decimal_places"] = kwargs["decimal_places"] if kwargs["decimal_places"] is not None else 2
                Campo.objects.create(**kwargs)
        return sistema

def serialize_system_structure(sistema):
    return {"sistema": {"nome": sistema.nome, "descricao": sistema.descricao, "caminho": sistema.caminho_geracao, "tipo_menu": sistema.tipo_menu, "banco_dados": sistema.banco_dados, "usar_custom_user": sistema.usar_custom_user, "gerar_api_rest": sistema.gerar_api_rest, "gerar_docker": sistema.gerar_docker, "usar_auditoria": sistema.usar_auditoria}, "modulos": [{"nome": m.nome, "descricao": m.descricao, "entidades": [{"nome": e.nome, "nome_plural": e.nome_plural, "descricao": e.descricao, "gerar_admin": e.gerar_admin, "gerar_crud_views": e.gerar_crud_views, "gerar_endpoints_api": e.gerar_endpoints_api, "campos": [{"nome": c.nome, "tipo": c.tipo, "max_length": c.max_length, "max_digits": c.max_digits, "decimal_places": c.decimal_places, "rel": c.entidade_relacionada.nome if c.entidade_relacionada else None, "null": c.null, "blank": c.blank, "unique": c.unique, "default_value": c.default_value, "upload_to": c.upload_to, "related_name": c.related_name_str, "on_delete": c.on_delete, "verbose_name": c.verbose_name, "help_text": c.help_text} for c in e.campos.all()]} for e in m.entidades.all()]} for m in sistema.modulos.all()]}
