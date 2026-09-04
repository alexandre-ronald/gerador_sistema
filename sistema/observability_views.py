import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import ObservabilityEvent, Sistema


def _owned_system(request, sistema_id):
    return get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)


def _filtered_events(request, sistema):
    events = ObservabilityEvent.objects.filter(sistema=sistema).select_related("ambiente", "usuario")
    period = request.GET.get("period", "7")
    if period != "all":
        try:
            days = max(1, min(int(period), 365))
        except (TypeError, ValueError):
            days = 7
        events = events.filter(created_at__gte=timezone.now() - timedelta(days=days))
    level = request.GET.get("level", "").strip().upper()
    category = request.GET.get("category", "").strip().upper()
    environment = request.GET.get("environment", "").strip()
    source = request.GET.get("source", "").strip()
    query = request.GET.get("q", "").strip()
    if level:
        events = events.filter(level=level)
    if category:
        events = events.filter(category=category)
    if environment:
        events = events.filter(ambiente_id=environment)
    if source:
        events = events.filter(source=source)
    if query:
        events = events.filter(
            Q(event_name__icontains=query)
            | Q(message__icontains=query)
            | Q(source__icontains=query)
            | Q(object_type__icontains=query)
            | Q(object_id__icontains=query)
        )
    return events


@login_required
def monitoring_center(request, sistema_id):
    sistema = _owned_system(request, sistema_id)
    events = _filtered_events(request, sistema)
    paginator = Paginator(events, 30)
    page_obj = paginator.get_page(request.GET.get("page"))
    recent_errors = ObservabilityEvent.objects.filter(
        sistema=sistema,
        level__in=[ObservabilityEvent.LEVEL_ERROR, ObservabilityEvent.LEVEL_CRITICAL],
        created_at__gte=timezone.now() - timedelta(days=7),
    )
    context = {
        "sistema": sistema,
        "page_obj": page_obj,
        "total": events.count(),
        "errors": events.filter(level__in=[ObservabilityEvent.LEVEL_ERROR, ObservabilityEvent.LEVEL_CRITICAL]).count(),
        "warnings": events.filter(level=ObservabilityEvent.LEVEL_WARNING).count(),
        "affected_environments": recent_errors.exclude(ambiente=None).values("ambiente_id").distinct().count(),
        "levels": ObservabilityEvent.LEVEL_CHOICES,
        "categories": ObservabilityEvent.CATEGORY_CHOICES,
        "environments": sistema.ambientes.all(),
        "sources": ObservabilityEvent.objects.filter(sistema=sistema).exclude(source="").values_list("source", flat=True).distinct().order_by("source"),
    }
    return render(request, "sistema/monitoring_center.html", context)


@login_required
def monitoring_event_detail(request, sistema_id, event_id):
    sistema = _owned_system(request, sistema_id)
    event = get_object_or_404(
        ObservabilityEvent.objects.select_related("ambiente", "usuario"),
        pk=event_id,
        sistema=sistema,
    )
    timeline = ObservabilityEvent.objects.filter(
        sistema=sistema,
        correlation_id=event.correlation_id,
    ).select_related("ambiente", "usuario").order_by("created_at", "id")
    return render(request, "sistema/monitoring_event_detail.html", {
        "sistema": sistema,
        "event": event,
        "timeline": timeline,
        "context_json": json.dumps(event.context, ensure_ascii=False, indent=2, default=str),
    })
