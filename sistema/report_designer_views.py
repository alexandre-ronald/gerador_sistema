import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Entidade, Sistema, VersaoGeracao


def _field_metadata(field):
    return {
        "name": field.nome,
        "label": field.verbose_name or field.nome.replace("_", " ").title(),
        "type": field.tipo,
    }


def _entity_metadata(entity):
    return {
        "name": entity.nome,
        "label": entity.nome,
        "fields": [_field_metadata(field) for field in entity.campos.all()],
    }


def _draft_reports(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        reports = versao.estrutura_json.get("reports")
        return reports if isinstance(reports, dict) else {}
    return {}


def _normalize_report(entity_name, metadata, raw, strict=False):
    raw = raw if isinstance(raw, dict) else {}
    available_fields = {field["name"] for field in metadata["fields"]}
    fields = raw.get("fields") if isinstance(raw.get("fields"), list) else []
    fields = [name for name in fields if name in available_fields]
    if not fields:
        fields = [field["name"] for field in metadata["fields"][:5]]

    filters = raw.get("filters") if isinstance(raw.get("filters"), list) else []
    filters = [name for name in filters if name in available_fields]
    order_by = raw.get("order_by", "")
    order_field = order_by.lstrip("-") if isinstance(order_by, str) else ""
    if order_field not in available_fields:
        order_by = ""

    if strict:
        requested_fields = raw.get("fields")
        if not isinstance(requested_fields, list):
            raise ValueError("Os campos do relatório são inválidos.")
        invalid = [name for name in requested_fields if name not in available_fields]
        if invalid:
            raise ValueError(f"Campo não disponível no relatório: {invalid[0]}")

    return {
        "enabled": bool(raw.get("enabled", False)),
        "title": str(raw.get("title") or f"Relatório de {entity_name}"),
        "description": str(raw.get("description") or ""),
        "fields": fields,
        "filters": filters,
        "order_by": order_by,
    }


@login_required
def report_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    entities = list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .prefetch_related("campos")
        .order_by("nome")
    )
    metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
    stored = _draft_reports(sistema)
    reports = {
        entity.nome: _normalize_report(entity.nome, metadata[entity.nome], stored.get(entity.nome), strict=False)
        for entity in entities
    }
    return render(request, "sistema/report_designer.html", {
        "sistema": sistema,
        "reports_json": json.dumps(reports, ensure_ascii=False),
        "entity_metadata_json": json.dumps(metadata, ensure_ascii=False),
    })


@login_required
@require_POST
def salvar_reports(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_reports = payload.get("reports") if isinstance(payload, dict) else None
        if not isinstance(raw_reports, dict):
            return JsonResponse({"status": "erro", "mensagem": "Configuração de relatórios inválida."}, status=400)

        entities = list(Entidade.objects.filter(modulo__sistema=sistema).prefetch_related("campos").order_by("nome"))
        metadata = {entity.nome: _entity_metadata(entity) for entity in entities}
        unknown = set(raw_reports) - set(metadata)
        if unknown:
            return JsonResponse({"status": "erro", "mensagem": f"Informação não disponível: {sorted(unknown)[0]}"}, status=400)

        normalized = {
            name: _normalize_report(name, metadata[name], config, strict=True)
            for name, config in raw_reports.items()
        }
        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do Report Designer", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["reports"] = normalized
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Report Designer"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "reports": normalized})
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": str(exc)}, status=400)
