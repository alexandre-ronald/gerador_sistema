import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Entidade, Sistema, VersaoGeracao
from .workflow import WorkflowError, compatible_state_fields, normalize_workflow_config


def _field_metadata(field):
    return {
        "name": field.nome,
        "label": field.verbose_name or field.nome.replace("_", " ").title(),
        "type": field.tipo,
        "editable": True,
        "auto_created": False,
    }


def _entity_metadata(entity):
    metadata = {
        "name": entity.nome,
        "label": entity.nome,
        "fields": [_field_metadata(field) for field in entity.campos.all()],
    }
    metadata["compatible_state_fields"] = compatible_state_fields(metadata)
    return metadata


def _infer_state_field(entity_metadata, config):
    """Preenche automaticamente um campo de etapa quando a intenção é inequívoca."""
    if not isinstance(config, dict) or not config.get("enabled") or str(config.get("state_field") or "").strip():
        return config

    compatible = entity_metadata.get("compatible_state_fields") or []
    names = [str(item.get("name") or "").strip() for item in compatible if str(item.get("name") or "").strip()]
    preferred = ("status", "situacao", "situação", "estado")
    selected = next((name for wanted in preferred for name in names if name.casefold() == wanted.casefold()), None)
    if selected is None:
        selected = next((name for wanted in preferred for name in names if wanted.casefold() in name.casefold()), None)
    if selected is None and len(names) == 1:
        selected = names[0]
    if selected is None:
        return config

    inferred = dict(config)
    inferred["state_field"] = selected
    return inferred


def _draft_workflows(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        workflows = versao.estrutura_json.get("workflows")
        return workflows if isinstance(workflows, dict) else {}
    return {}


@login_required
def workflow_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    entities = list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .prefetch_related("campos")
        .order_by("nome")
    )
    metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
    stored = _draft_workflows(sistema)
    workflows = {}
    for entity in entities:
        workflows[entity.nome] = normalize_workflow_config(
            entity.nome,
            metadata[entity.nome],
            stored.get(entity.nome),
            strict=False,
        )

    return render(request, "sistema/workflow_designer.html", {
        "sistema": sistema,
        "entities": entities,
        "workflows_json": json.dumps(workflows, ensure_ascii=False),
        "entity_metadata_json": json.dumps(metadata, ensure_ascii=False),
    })


@login_required
@require_http_methods(["POST"])
def salvar_workflows(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_workflows = payload.get("workflows") if isinstance(payload, dict) else None
        if not isinstance(raw_workflows, dict):
            raise WorkflowError("invalid_workflows_config", "Contrato workflows inválido.")

        entities = list(
            Entidade.objects.filter(modulo__sistema=sistema)
            .prefetch_related("campos")
            .order_by("nome")
        )
        metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
        unknown = set(raw_workflows) - set(metadata)
        if unknown:
            raise WorkflowError("unknown_workflow_entity", f"Entidade não disponível: {sorted(unknown)[0]}")

        normalized = {}
        for entity_name, config in raw_workflows.items():
            config = _infer_state_field(metadata[entity_name], config)
            normalized[entity_name] = normalize_workflow_config(
                entity_name,
                metadata[entity_name],
                config,
                strict=True,
            )

        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do Workflow Designer", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["workflows"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Workflow Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])

        return JsonResponse({
            "status": "sucesso",
            "sistema_id": sistema.id,
            "workflows": normalized,
        })
    except WorkflowError as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
