from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .application_preview import build_preview_shell
from .models import Sistema


@login_required
def application_preview(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    preview = build_preview_shell(
        sistema,
        selected_entity_id=request.GET.get("entidade"),
        page_kind=request.GET.get("pagina", "list"),
    )
    return render(
        request,
        "sistema/application_preview.html",
        {"sistema": sistema, "preview": preview},
    )
