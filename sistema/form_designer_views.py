import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .form_designer import FormDesignerError, compatible_widgets, normalize_form_config
from .models import Entidade, Sistema, VersaoGeracao


def _field_metadata(field):
    return {
        "name": field.nome,
        "label": field.verbose_name or field.nome.replace("_", " ").title(),
        "type": field.tipo,
        "help_text": field.help_text or "",
        "editable": True,
        "widgets": list(compatible_widgets(field.tipo)),
    }


def _entity_metadata(entity):
    return {
        "name": entity.nome,
        "label": entity.nome,
        "fields": [_field_metadata(field) for field in entity.campos.all()],
    }


def _draft_forms(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        forms = versao.estrutura_json.get("forms")
        return forms if isinstance(forms, dict) else {}
    return {}


@login_required
def form_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    entities = list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .prefetch_related("campos")
        .order_by("nome")
    )
    metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
    stored = _draft_forms(sistema)
    forms = {}
    for entity in entities:
        forms[entity.nome] = normalize_form_config(
            entity.nome,
            metadata[entity.nome],
            stored.get(entity.nome),
        )
    return render(request, "sistema/form_designer.html", {
        "sistema": sistema,
        "entities": entities,
        "forms_json": json.dumps(forms, ensure_ascii=False),
        "entity_metadata_json": json.dumps(metadata, ensure_ascii=False),
    })


@login_required
@require_http_methods(["POST"])
def salvar_form_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_forms = payload.get("forms") if isinstance(payload, dict) else None
        if not isinstance(raw_forms, dict):
            raise FormDesignerError("invalid_forms", "Contrato forms inválido.")

        entities = list(
            Entidade.objects.filter(modulo__sistema=sistema)
            .prefetch_related("campos")
            .order_by("nome")
        )
        metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
        unknown = set(raw_forms) - set(metadata)
        if unknown:
            raise FormDesignerError("unknown_entity", f"Entidade não disponível: {sorted(unknown)[0]}")

        normalized = {}
        for entity_name, config in raw_forms.items():
            normalized[entity_name] = normalize_form_config(
                entity_name,
                metadata[entity_name],
                config,
                strict=True,
            )

        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do Form Designer", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["forms"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Form Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "forms": normalized})
    except FormDesignerError as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
