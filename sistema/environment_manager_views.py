from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .environment_manager import EnvironmentManagerService
from .models import Ambiente, Sistema, VersaoGeracao
from .runtime_agent import RuntimeAgentService


@login_required
def environment_manager(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    service = EnvironmentManagerService(sistema)
    return render(
        request,
        "sistema/environment_manager.html",
        {
            "sistema": sistema,
            "ambientes": service.environments(),
            "releases": service.released_versions(),
            "historico": service.history(),
        },
    )


@login_required
@require_POST
def update_environment(request, sistema_id, ambiente_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    ambiente = get_object_or_404(Ambiente, pk=ambiente_id, sistema=sistema)
    EnvironmentManagerService(sistema).update_environment(
        ambiente,
        nome=request.POST.get("nome"),
        url_base=request.POST.get("url_base"),
        ativo=request.POST.get("ativo") == "on",
    )
    messages.success(request, f"Ambiente {ambiente.nome} atualizado.")
    return redirect("sistema:environment_manager", sistema_id=sistema.pk)


@login_required
@require_POST
def promote_environment(request, sistema_id, ambiente_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    ambiente = get_object_or_404(Ambiente, pk=ambiente_id, sistema=sistema)
    versao = get_object_or_404(VersaoGeracao, pk=request.POST.get("version_id"), sistema=sistema)
    try:
        EnvironmentManagerService(sistema).promote(
            ambiente,
            versao,
            observacao=request.POST.get("observacao", ""),
        )
        messages.success(request, f"Release v{versao.numero} promovida para {ambiente.nome}.")
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect("sistema:environment_manager", sistema_id=sistema.pk)


@login_required
@require_POST
def check_runtime(request, sistema_id, ambiente_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    ambiente = get_object_or_404(Ambiente, pk=ambiente_id, sistema=sistema)
    try:
        snapshot = RuntimeAgentService(sistema).check_environment(ambiente)
        if snapshot.online:
            messages.success(request, f"Runtime Agent de {ambiente.nome} respondeu com status {snapshot.status or 'ok'}.")
        else:
            messages.warning(request, f"Runtime Agent de {ambiente.nome} indisponível: {snapshot.erro}")
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect("sistema:environment_manager", sistema_id=sistema.pk)
