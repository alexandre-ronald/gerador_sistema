import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .advanced_pages import normalize_advanced_pages_config
from .builder_contracts import normalize_dashboard_config
from .models import Entidade, Sistema, VersaoGeracao
from .workspace_contract import WorkspaceContractError, normalize_workspace_config
from .workspace_semantics import WorkspaceSemanticError, validate_workspace_destinations


def _draft_structure(sistema):
    version = sistema.versoes.filter(numero=0).first()
    if version and isinstance(version.estrutura_json, dict):
        return version.estrutura_json
    return {}


def _entities(sistema):
    return list(
        Entidade.objects.filter(modulo__sistema=sistema)
        .select_related("modulo")
        .order_by("modulo__nome", "nome")
    )


def _experience_catalog(structure, entities):
    experiences = []

    advanced = normalize_advanced_pages_config(structure.get("advanced_pages"), strict=False)
    for page in advanced.get("pages", []):
        # Contexto record exige um PK e não pode ser aberto diretamente pela navegação
        # do Workspace. O acesso permanece pelos entrypoints da entidade.
        if page.get("enabled") and (page.get("context") or {}).get("kind") != "record":
            experiences.append({
                "kind": "advanced_page",
                "ref": page["id"],
                "label": page.get("name") or page["id"],
                "group": "Páginas de negócio",
            })

    raw_cruds = structure.get("cruds") if isinstance(structure.get("cruds"), dict) else {}
    for entity in entities:
        if not raw_cruds or entity.nome in raw_cruds:
            experiences.append({
                "kind": "crud",
                "ref": entity.nome,
                "operation": "list",
                "label": entity.nome,
                "group": "Cadastros e consultas",
            })

    dashboard = normalize_dashboard_config(structure.get("dashboard"))
    if dashboard.get("enabled"):
        experiences.append({
            "kind": "dashboard",
            "ref": "dashboard",
            "label": dashboard.get("title") or "Dashboard",
            "group": "Painéis",
        })

    reports = structure.get("reports") if isinstance(structure.get("reports"), dict) else {}
    for entity_name, collection in reports.items():
        items = collection if isinstance(collection, list) else [collection] if isinstance(collection, dict) else []
        for report in items:
            if isinstance(report, dict) and report.get("enabled") and report.get("id"):
                experiences.append({
                    "kind": "report",
                    "ref": f"{entity_name}:{report['id']}",
                    "label": report.get("title") or report.get("name") or report["id"],
                    "group": "Relatórios",
                })

    return experiences


@login_required
def workspace_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    structure = _draft_structure(sistema)
    entities = _entities(sistema)
    raw_config = structure.get("workspaces") if isinstance(structure.get("workspaces"), dict) else None
    config = normalize_workspace_config(raw_config, strict=False)
    return render(request, "sistema/workspace_designer.html", {
        "sistema": sistema,
        "workspaces_json": json.dumps(config, ensure_ascii=False),
        "experience_catalog_json": json.dumps(_experience_catalog(structure, entities), ensure_ascii=False),
    })


@login_required
@require_http_methods(["POST"])
def salvar_workspace_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body or "{}")
        raw_config = payload.get("workspaces") if isinstance(payload, dict) else None
        if not isinstance(raw_config, dict):
            raise WorkspaceContractError("invalid_workspaces_config", "Contrato de workspaces inválido.")

        structure = _draft_structure(sistema)
        entities = _entities(sistema)
        normalized = validate_workspace_destinations(raw_config, structure, entities=entities)

        version, _ = VersaoGeracao.objects.get_or_create(
            sistema=sistema,
            numero=0,
            defaults={"descricao": "Rascunho do Workspace Designer", "estrutura_json": {}},
        )
        structure = version.estrutura_json if isinstance(version.estrutura_json, dict) else {}
        structure["workspaces"] = normalized
        version.estrutura_json = structure
        version.descricao = "Rascunho do Workspace Designer"
        version.save(update_fields=["estrutura_json", "descricao"])
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id, "workspaces": normalized})
    except (WorkspaceContractError, WorkspaceSemanticError) as exc:
        return JsonResponse({"status": "erro", "erro": exc.as_dict(), "mensagem": exc.message}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"status": "erro", "mensagem": f"Configuração inválida: {exc}"}, status=400)