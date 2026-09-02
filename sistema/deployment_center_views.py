import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from .deployment_center import DeploymentCenterError
from .deployment_service import DeploymentService
from .models import Ambiente, DeploymentPlan, Sistema, VersaoGeracao


@login_required
@ensure_csrf_cookie
def deployment_center(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    service = DeploymentService(sistema)
    ambientes = sistema.ambientes.select_related("release_atual").order_by("tipo")
    return render(request, "sistema/deployment_center.html", {
        "sistema": sistema,
        "ambientes": ambientes,
        "deployment_config": service.config(tolerant=True),
        "plans": service.plans(),
    })


@login_required
@require_POST
def save_deployment_config(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        config = DeploymentService(sistema).save_config(payload)
        return JsonResponse({"ok": True, "deployment": config})
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": {"code": "invalid_json", "message": "JSON inválido."}}, status=400)
    except DeploymentCenterError as exc:
        return JsonResponse({"ok": False, "error": exc.as_dict()}, status=400)
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": {"code": "validation_error", "message": exc.messages[0]}}, status=400)


@login_required
@require_POST
def create_deployment_plan(request, sistema_id, ambiente_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    ambiente = get_object_or_404(Ambiente, pk=ambiente_id, sistema=sistema)
    versao = get_object_or_404(VersaoGeracao, pk=request.POST.get("version_id"), sistema=sistema)
    try:
        plan = DeploymentService(sistema).create_plan(ambiente=ambiente, versao=versao, user=request.user)
        messages.success(request, f"Plano #{plan.pk} criado para {ambiente.nome} / v{versao.numero}.")
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect("sistema:deployment_center", sistema_id=sistema.pk)


@login_required
@require_POST
def validate_deployment_plan(request, sistema_id, plan_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    plan = get_object_or_404(DeploymentPlan, pk=plan_id, sistema=sistema)
    try:
        plan = DeploymentService(sistema).validate_plan(plan)
        if plan.status == DeploymentPlan.STATUS_READY:
            messages.success(request, f"Plano #{plan.pk} validado e pronto para execução.")
        else:
            messages.error(request, plan.erro or "Plano reprovado na validação.")
    except (ValidationError, DeploymentCenterError) as exc:
        messages.error(request, getattr(exc, "message", None) or str(exc))
    return redirect("sistema:deployment_center", sistema_id=sistema.pk)


@login_required
@require_POST
def cancel_deployment_plan(request, sistema_id, plan_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    plan = get_object_or_404(DeploymentPlan, pk=plan_id, sistema=sistema)
    try:
        DeploymentService(sistema).cancel_plan(plan)
        messages.success(request, f"Plano #{plan.pk} cancelado.")
    except (ValidationError, DeploymentCenterError) as exc:
        messages.error(request, getattr(exc, "message", None) or str(exc))
    return redirect("sistema:deployment_center", sistema_id=sistema.pk)
