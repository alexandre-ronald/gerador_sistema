from __future__ import annotations

import json
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .forms import SistemaForm
from .models import Campo, Entidade, Modulo, Sistema


def ownership_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        system_id = kwargs.get("sistema_id", kwargs.get("pk"))
        if system_id is None:
            raise Http404
        get_object_or_404(Sistema, pk=system_id, usuario=request.user)
        return view_func(request, *args, **kwargs)
    return wrapped


def _as_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Valor inteiro inválido: {value!r}")


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "sim", "on"}
    return bool(value)


def _validate_payload(payload):
    if not isinstance(payload, dict):
        raise ValidationError("O corpo da requisição deve ser um objeto JSON.")
    sistema_data = payload.get("sistema")
    if not isinstance(sistema_data, dict):
        raise ValidationError("A seção 'sistema' é obrigatória.")
    nome = str(sistema_data.get("nome") or "").strip()
    if not nome:
        raise ValidationError("O sistema precisa de um nome.")
    modulos = payload.get("modulos", [])
    if not isinstance(modulos, list):
        raise ValidationError("'modulos' deve ser uma lista.")
    seen_modules = set()
    seen_entities = set()
    for mod_data in modulos:
        if not isinstance(mod_data, dict):
            raise ValidationError("Cada módulo deve ser um objeto JSON.")
        mod_name = str(mod_data.get("nome") or "").strip()
        if not mod_name:
            raise ValidationError("Todo módulo precisa de um nome.")
        module_key = mod_name.casefold()
        if module_key in seen_modules:
            raise ValidationError(f"Módulo duplicado: {mod_name}.")
        seen_modules.add(module_key)
        entities = mod_data.get("entidades", [])
        if not isinstance(entities, list):
            raise ValidationError(f"Entidades do módulo '{mod_name}' devem ser uma lista.")
        for ent_data in entities:
            if not isinstance(ent_data, dict):
                raise ValidationError("Cada entidade deve ser um objeto JSON.")
            ent_name = str(ent_data.get("nome") or "").strip()
            if not ent_name:
                raise ValidationError(f"Entidade sem nome no módulo '{mod_name}'.")
            entity_key = (module_key, ent_name.casefold())
            if entity_key in seen_entities:
                raise ValidationError(f"Entidade duplicada: {ent_name}.")
            seen_entities.add(entity_key)


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def criar_sistema_seguro(request):
    """Exibe o formulário com GET e cria o sistema com POST."""
    if request.method == "GET":
        return render(request, "sistema/editor.html", {"form": SistemaForm()})

    form = SistemaForm(request.POST)
    if form.is_valid():
        sistema = form.save(commit=False)
        sistema.usuario = request.user
        sistema.save()
        messages.success(request, f"Sistema '{sistema.nome}' criado com sucesso!")
        return redirect("sistema:lista")
    return render(request, "sistema/editor.html", {"form": form}, status=400)


@require_http_methods(["GET"])
@login_required
@ownership_required
def editar_sistema_seguro(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    estrutura = {
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
        "modulos": [],
    }
    for modulo in sistema.modulos.all():
        mod_data = {"nome": modulo.nome, "entidades": []}
        for entidade in modulo.entidades.all():
            ent_data = {"nome": entidade.nome, "nome_plural": entidade.nome_plural, "campos": []}
            for campo in entidade.campos.all():
                ent_data["campos"].append({
                    "nome": campo.nome,
                    "tipo": campo.tipo,
                    "max_length": campo.max_length,
                    "max_digits": campo.max_digits,
                    "decimal_places": campo.decimal_places,
                    "rel": campo.entidade_relacionada.nome if campo.entidade_relacionada else None,
                    "null": campo.null,
                    "blank": campo.blank,
                    "unique": campo.unique,
                    "default": campo.default_value,
                    "upload_to": campo.upload_to,
                    "related_name": campo.related_name_str,
                    "on_delete": campo.on_delete,
                    "verbose_name": campo.verbose_name,
                    "help_text": campo.help_text,
                })
            mod_data["entidades"].append(ent_data)
        estrutura["modulos"].append(mod_data)
    return render(request, "sistema/editor.html", {"estrutura_json": json.dumps(estrutura), "sistema_id": sistema.id})


def _save_payload(data, sistema):
    sistema_data = data["sistema"]
    sistema.nome = str(sistema_data["nome"]).strip()
    sistema.descricao = sistema_data.get("descricao", "")
    sistema.caminho_geracao = ""
    sistema.banco_dados = sistema_data.get("banco_dados", "sqlite3")
    sistema.tipo_menu = sistema_data.get("tipo_menu", "lateral")
    sistema.usar_custom_user = _as_bool(sistema_data.get("usar_custom_user", False))
    sistema.gerar_api_rest = _as_bool(sistema_data.get("gerar_api_rest", False))
    sistema.gerar_docker = _as_bool(sistema_data.get("gerar_docker", False))
    sistema.usar_auditoria = _as_bool(sistema_data.get("usar_auditoria", False))
    sistema.full_clean()
    sistema.save()

    sistema.modulos.all().delete()
    entities_by_name = {}
    for mod_data in data.get("modulos", []):
        modulo = Modulo.objects.create(sistema=sistema, nome=str(mod_data["nome"]).strip(), descricao=mod_data.get("descricao", ""))
        for ent_data in mod_data.get("entidades", []):
            entidade = Entidade.objects.create(
                modulo=modulo,
                nome=str(ent_data["nome"]).strip(),
                nome_plural=ent_data.get("nome_plural", ""),
                descricao=ent_data.get("descricao", ""),
                gerar_admin=_as_bool(ent_data.get("gerar_admin", True)),
                gerar_crud_views=_as_bool(ent_data.get("gerar_crud_views", False)),
                gerar_endpoints_api=_as_bool(ent_data.get("gerar_endpoints_api", False)),
            )
            entities_by_name[entidade.nome] = entidade

    for mod_data in data.get("modulos", []):
        for ent_data in mod_data.get("entidades", []):
            entidade = entities_by_name[ent_data["nome"]]
            for campo_data in ent_data.get("campos", []):
                campo = Campo(
                    entidade=entidade,
                    nome=str(campo_data.get("nome") or "").strip(),
                    tipo=campo_data.get("tipo", "CharField"),
                    null=_as_bool(campo_data.get("null", False)),
                    blank=_as_bool(campo_data.get("blank", False)),
                    unique=_as_bool(campo_data.get("unique", False)),
                    default_value=str(campo_data.get("default_value", campo_data.get("default", "")) or ""),
                    max_length=_as_int(campo_data.get("max_length")),
                    max_digits=_as_int(campo_data.get("max_digits")),
                    decimal_places=_as_int(campo_data.get("decimal_places")),
                    upload_to=str(campo_data.get("upload_to") or ""),
                    on_delete=campo_data.get("on_delete", "models.CASCADE"),
                    related_name_str=str(campo_data.get("related_name") or ""),
                    verbose_name=str(campo_data.get("verbose_name") or ""),
                    help_text=str(campo_data.get("help_text") or ""),
                )
                rel_nome = campo_data.get("rel")
                if rel_nome:
                    campo.entidade_relacionada = entities_by_name.get(rel_nome)
                campo.full_clean()
                campo.save()


@require_http_methods(["PUT"])
@login_required
@ownership_required
@csrf_protect
def atualizar_sistema_seguro(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        data = json.loads(request.body or "{}")
        _validate_payload(data)
        with transaction.atomic():
            _save_payload(data, sistema)
        return JsonResponse({"status": "ok", "sistema_id": sistema.id})
    except (ValueError, TypeError, json.JSONDecodeError, ValidationError) as exc:
        return JsonResponse({"status": "erro", "mensagem": str(exc)}, status=400)


@require_http_methods(["POST"])
@login_required
@csrf_protect
def salvar_modelo_seguro(request):
    try:
        data = json.loads(request.body or "{}")
        _validate_payload(data)
        nome = str(data["sistema"]["nome"]).strip()
        sistema = Sistema.objects.filter(usuario=request.user, nome=nome).first()
        if sistema is None:
            sistema = Sistema(usuario=request.user, nome=nome)
        with transaction.atomic():
            _save_payload(data, sistema)
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id})
    except (ValueError, TypeError, json.JSONDecodeError, ValidationError) as exc:
        return JsonResponse({"status": "erro", "mensagem": str(exc)}, status=400)


def secured(view_func):
    return login_required(csrf_protect(ownership_required(view_func)))


def secured_get(view_func):
    return login_required(ownership_required(view_func))


def secured_post(view_func):
    return login_required(csrf_protect(ownership_required(require_http_methods(["POST"])(view_func))))
