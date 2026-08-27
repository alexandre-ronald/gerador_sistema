import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .builder_contracts import normalize_dashboard_config
from .models import Entidade, Sistema, VersaoGeracao

WIDGET_TYPES = (("metric", "KPI / Indicador", "bi bi-123"), ("table", "Tabela", "bi bi-table"), ("bar", "Gráfico de barras", "bi bi-bar-chart"), ("line", "Gráfico de linha", "bi bi-graph-up"), ("area", "Gráfico de área", "bi bi-graph-up-arrow"), ("pie", "Gráfico de pizza", "bi bi-pie-chart"), ("donut", "Gráfico de rosca", "bi bi-circle-half"))


def _draft(sistema):
    versao = sistema.versoes.filter(numero=0).first()
    if versao and isinstance(versao.estrutura_json, dict):
        return normalize_dashboard_config(versao.estrutura_json.get("dashboard"))
    return normalize_dashboard_config()


def _entity_fields(entities):
    """Expose model-field metadata so the Builder can offer real choices."""
    result = {}
    for entity in entities:
        fields = []
        for campo in entity.campos.select_related("entidade_relacionada").all().order_by("nome"):
            related = campo.entidade_relacionada.nome if campo.entidade_relacionada else ""
            fields.append({
                "name": campo.nome,
                "label": campo.verbose_name or campo.nome,
                "type": campo.tipo,
                "related": related,
            })
        result[entity.nome] = fields
    return result


@login_required
def dashboard_builder(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    entities = list(Entidade.objects.filter(modulo__sistema=sistema).select_related("modulo").prefetch_related("campos__entidade_relacionada").order_by("nome"))
    config = _draft(sistema)
    return render(request, "sistema/dashboard_builder.html", {"sistema": sistema, "entities": entities, "entity_fields_json": json.dumps(_entity_fields(entities), ensure_ascii=False), "config": config, "config_json": json.dumps(config, ensure_ascii=False), "widget_types": WIDGET_TYPES})


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
        versao, _ = VersaoGeracao.objects.get_or_create(sistema=sistema, numero=0, defaults={"descricao": "Rascunho do Dashboard", "estrutura_json": {}})
        estrutura = versao.estrutura_json if isinstance(versao.estrutura_json, dict) else {}
        estrutura["dashboard"] = config
        versao.estrutura_json = estrutura
        versao.descricao = "Rascunho do Dashboard"
        versao.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "dashboard": config})
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)
