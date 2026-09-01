from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Sistema, VersaoGeracao
from .release_manager import ReleaseManagerService


@login_required
def release_manager(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    service = ReleaseManagerService(sistema)
    versions = list(service.versions())
    latest_release = next((version for version in versions if version.status == VersaoGeracao.STATUS_RELEASED), None)
    return render(request, "sistema/release_manager.html", {
        "sistema": sistema,
        "versions": versions,
        "latest_release": latest_release,
    })


@login_required
@require_POST
def validate_release(request, sistema_id, version_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    version = get_object_or_404(VersaoGeracao, pk=version_id, sistema=sistema)
    try:
        report = ReleaseManagerService(sistema).validate_version(version)
        if report["release_ready"]:
            messages.success(request, f"Versão v{version.numero} validada com sucesso.")
        else:
            messages.warning(request, f"Versão v{version.numero} não passou pelo Quality Gate.")
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect("sistema:release_manager", sistema_id=sistema.pk)


@login_required
@require_POST
def publish_release(request, sistema_id, version_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    version = get_object_or_404(VersaoGeracao, pk=version_id, sistema=sistema)
    try:
        ReleaseManagerService(sistema).release(version, request.POST.get("changelog", ""))
        messages.success(request, f"Release v{version.numero} publicada.")
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect("sistema:release_manager", sistema_id=sistema.pk)
