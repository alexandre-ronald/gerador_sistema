import json
import re

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Entidade, Sistema, VersaoGeracao


TEXT_TYPES = {"CharField", "TextField", "EmailField", "SlugField", "URLField"}
NUMBER_TYPES = {"IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField", "PositiveSmallIntegerField", "FloatField", "DecimalField"}
DATE_TYPES = {"DateField", "DateTimeField", "TimeField"}
BOOLEAN_TYPES = {"BooleanField", "NullBooleanField"}
RELATION_TYPES = {"ForeignKey", "OneToOneField", "ManyToManyField"}
REPORT_ID_RE = re.compile(r"^[a-z0-9_]+$")


def _filter_options(field_type):
    if field_type in NUMBER_TYPES or field_type in DATE_TYPES:
        return ["exact", "gte", "lte", "range"]
    if field_type in BOOLEAN_TYPES or field_type in RELATION_TYPES:
        return ["exact"]
    return ["contains", "exact", "startswith"]


def _default_filter_type(field_type):
    return "contains" if field_type in TEXT_TYPES or field_type not in NUMBER_TYPES | DATE_TYPES | BOOLEAN_TYPES | RELATION_TYPES else "exact"


def _field_metadata(field):
    return {
        "name": field.nome,
        "label": field.verbose_name or field.nome.replace("_", " ").title(),
        "type": field.tipo,
        "filter_options": _filter_options(field.tipo),
        "default_filter_type": _default_filter_type(field.tipo),
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


def _default_report(entity_name, metadata, report_id="relatorio_1"):
    return {
        "id": report_id,
        "enabled": False,
        "title": f"Relatório de {entity_name}",
        "description": "",
        "fields": [field["name"] for field in metadata["fields"][:5]],
        "filters": [],
        "order_by": "",
    }


def _normalize_report(entity_name, metadata, raw, strict=False, fallback_id="relatorio_1"):
    raw = raw if isinstance(raw, dict) else {}
    field_map = {field["name"]: field for field in metadata["fields"]}
    available_fields = set(field_map)
    report_id = str(raw.get("id") or fallback_id).strip().lower()
    if strict and (not report_id or not REPORT_ID_RE.match(report_id)):
        raise ValueError(f"Identificador de relatório inválido: {report_id}")
    if not report_id or not REPORT_ID_RE.match(report_id):
        report_id = fallback_id

    fields = raw.get("fields") if isinstance(raw.get("fields"), list) else []
    fields = [name for name in fields if name in available_fields]
    if not fields:
        fields = [field["name"] for field in metadata["fields"][:5]]

    raw_filters = raw.get("filters") if isinstance(raw.get("filters"), list) else []
    filters = []
    for item in raw_filters:
        if isinstance(item, str):
            name, filter_type = item, field_map.get(item, {}).get("default_filter_type", "contains")
        elif isinstance(item, dict):
            name, filter_type = item.get("field", ""), item.get("type", "")
        else:
            continue
        if name not in available_fields:
            if strict:
                raise ValueError(f"Filtro não disponível no relatório: {name}")
            continue
        allowed = field_map[name]["filter_options"]
        if filter_type not in allowed:
            if strict:
                raise ValueError(f"Tipo de filtro não disponível para {field_map[name]['label']}: {filter_type}")
            filter_type = field_map[name]["default_filter_type"]
        filters.append({"field": name, "type": filter_type})

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
        "id": report_id,
        "enabled": bool(raw.get("enabled", False)),
        "title": str(raw.get("title") or f"Relatório de {entity_name}"),
        "description": str(raw.get("description") or ""),
        "fields": fields,
        "filters": filters,
        "order_by": order_by,
    }


def _normalize_report_collection(entity_name, metadata, raw, strict=False):
    if isinstance(raw, dict):
        raw_items = [raw]
    elif isinstance(raw, list):
        raw_items = raw
    elif raw is None:
        return [_default_report(entity_name, metadata)]
    else:
        if strict:
            raise ValueError(f"Configuração de relatórios inválida para {entity_name}.")
        return [_default_report(entity_name, metadata)]

    normalized = []
    ids = set()
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            if strict:
                raise ValueError(f"Relatório inválido em {entity_name}.")
            continue
        report = _normalize_report(entity_name, metadata, item, strict=strict, fallback_id=f"relatorio_{index}")
        if report["id"] in ids:
            if strict:
                raise ValueError(f"Identificador de relatório repetido: {report['id']}")
            report["id"] = f"relatorio_{index}"
        ids.add(report["id"])
        normalized.append(report)
    return normalized


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
        entity.nome: _normalize_report_collection(entity.nome, metadata[entity.nome], stored.get(entity.nome), strict=False)
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
            name: _normalize_report_collection(name, metadata[name], config, strict=True)
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
