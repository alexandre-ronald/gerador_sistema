import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .crud_designer import CrudDesignerError, compatible_filter_types, normalize_crud_config
from .models import Entidade, Sistema, VersaoGeracao


def _field_metadata(field):
    metadata = {
        "name": field.nome,
        "label": field.verbose_name or field.nome.replace("_", " ").title(),
        "type": field.tipo,
        "filter_types": list(compatible_filter_types({"type": field.tipo})),
    }
    choices = getattr(field, "choices", None)
    if choices:
        metadata["choices"] = choices
        metadata["filter_types"] = list(compatible_filter_types(metadata))
    return metadata


def _entity_metadata(entity):
    return {
        "name": entity.nome,
        "label": entity.nome,
        "fields": [_field_metadata(field) for field in entity.campos.all()],
    }


def _draft_cruds(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        cruds = versao.estrutura_json.get("cruds")
        return cruds if isinstance(cruds, dict) else {}
    return {}


@login_required
def crud_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    entities = list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .prefetch_related("campos")
        .order_by("nome")
    )
    metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
    stored = _draft_cruds(sistema)
    cruds = {}
    for entity in entities:
        cruds[entity.nome] = normalize_crud_config(
            entity.nome,
            metadata[entity.nome],
            stored.get(entity.nome),
        )
    return render(request, "sistema/crud_designer.html", {
        "sistema": sistema,
        "entities": entities,
        "cruds_json": json.dumps(cruds, ensure_ascii=False),
        "entity_metadata_json": json.dumps(metadata, ensure_ascii=False),
    })


@login_required
@require_http_methods(["POST"])
def salvar_crud_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_cruds = payload.get("cruds") if isinstance(payload, dict) else None
        if not isinstance(raw_cruds, dict):
            raise CrudDesignerError("invalid_cruds", "Contrato cruds inválido.")

        entities = list(
            Entidade.objects.filter(modulo__sistema=sistema)
            .prefetch_related("campos")
            .order_by("nome")
        )
        metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
        unknown = set(raw_cruds) - set(metadata)
        if unknown:
            raise CrudDesignerError("unknown_entity", f"Entidade não disponível: {sorted(unknown)[0]}")

        normalized = {}
        for entity_name, config in raw_cruds.items():
            normalized[entity_name] = normalize_crud_config(
                entity_name,
                metadata[entity_name],
                config,
                strict=True,
            )

        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do CRUD Designer", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["cruds"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do CRUD Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "cruds": normalized})
    except CrudDesignerError as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
