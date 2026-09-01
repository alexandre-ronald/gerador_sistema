from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .health_monitoring import HealthMonitoringService
from .models import Sistema


@login_required
def health_monitoring(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    service = HealthMonitoringService(sistema)
    states = service.environment_states()
    return render(
        request,
        "sistema/health_monitoring.html",
        {
            "sistema": sistema,
            "states": states,
            "summary": service.summary(states),
            "historico": service.history(),
        },
    )
