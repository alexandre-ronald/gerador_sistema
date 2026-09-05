from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .application_blueprint import build_application_inventory
from .models import Sistema


@login_required
def application_blueprint(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    blueprint = build_application_inventory(sistema)
    return render(
        request,
        "sistema/application_blueprint.html",
        {"sistema": sistema, "blueprint": blueprint, "inventory": blueprint["inventory"]},
    )
