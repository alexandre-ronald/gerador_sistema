from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Sistema
from .validation_center import validate_system


@login_required
def validation_center(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    report = validate_system(sistema)
    return render(
        request,
        "sistema/validation_center.html",
        {"sistema": sistema, "report": report},
    )
