import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .builder_contracts import normalize_dashboard_config
from .models import Entidade, Sistema, VersaoGeracao

WIDGET_TYPES = (
    ("metric", "Indicador", "bi bi-123"),
    ("table", "Tabela", "bi bi-table"),
    ("bar", "Barras", "bi bi-bar-chart"),
    ("line", "Linha", "bi bi-graph-up"),
    ("area", "Área", "bi bi-graph-up-arrow"),
    ("pie", "Pizza", "bi bi-pie-chart"),
    ("donut", "Rosca", "bi bi-circle-half"),
)


def _draft(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        return normalize_dashboard_config(versao.estrutura_json.get("dashboard"))
    return normalize_dashboard_config()


def _field_metadata(field):
    related = field.entidade_relacionada
    return {
        "name": field.nome,
        "label": field.verbose_name or field.nome.replace("_", " ").title(),
        "type": field.tipo,
        "nullable": bool(field.null),
        "relational": field.eh_relacional,
        "related_entity": related.nome if related else "",
        "related_label": field.related_name_str or "__str__",
        "numeric": field.tipo in {"IntegerField", "FloatField", "DecimalField"},
        "decimal": field.tipo == "DecimalField",
    }


def _entity_metadata(entities):
    return {
        entity.nome: {
            "name": entity.nome,
            "label": entity.nome,
            "module": entity.modulo.nome,
            "fields": [_field_metadata(field) for field in entity.campos.all()],
        }
        for entity in entities
    }


@login_required
def dashboard_builder(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    entities = list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .prefetch_related("campos__entidade_relacionada")
        .order_by("nome")
    )
    config = _draft(sistema)
    metadata = _entity_metadata(entities)
    return render(request, "sistema/dashboard_builder.html", {
        "sistema": sistema,
        "entities": entities,
        "config": config,
        "config_json": json.dumps(config, ensure_ascii=False),
        "entity_metadata_json": json.dumps(metadata, ensure_ascii=False),
        "widget_types": WIDGET_TYPES,
    })


@login_required
@require_http_methods(["POST"])
def salvar_dashboard(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        config = normalize_dashboard_config(payload)
        allowed_entities = set(Entidade.objects.filter(modulo__sistema=sistema).values_list("nome", flat=True))
        for widget in config["widgets"]:
            if widget["entity"] and widget["entity"] not in allowed_entities:
                return JsonResponse({"status": "erro", "mensagem": f"Entidade não disponível: {widget['entity']}"}, status=400)
        versao, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do Dashboard", "estrutura_json": {}},
        )
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["dashboard"] = config
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Dashboard"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "dashboard": config})
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
