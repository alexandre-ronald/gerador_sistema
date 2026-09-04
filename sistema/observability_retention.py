from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import ObservabilityEvent


DEFAULT_RETENTION_DAYS = {
    ObservabilityEvent.LEVEL_DEBUG: 14,
    ObservabilityEvent.LEVEL_INFO: 30,
    ObservabilityEvent.LEVEL_WARNING: 90,
    ObservabilityEvent.LEVEL_ERROR: 180,
    ObservabilityEvent.LEVEL_CRITICAL: 365,
}


def retention_policy():
    configured = getattr(settings, "DJANGOFORGE_OBSERVABILITY_RETENTION_DAYS", {}) or {}
    policy = DEFAULT_RETENTION_DAYS.copy()
    for level, days in configured.items():
        normalized = str(level).upper()
        if normalized not in policy:
            continue
        try:
            days = int(days)
        except (TypeError, ValueError):
            continue
        if days > 0:
            policy[normalized] = min(days, 3650)
    return policy


def retention_preview(*, sistema_id=None, now=None):
    now = now or timezone.now()
    base = ObservabilityEvent.objects.all()
    if sistema_id is not None:
        base = base.filter(sistema_id=sistema_id)

    policy = retention_policy()
    by_level = {}
    total = 0
    for level, days in policy.items():
        cutoff = now - timedelta(days=days)
        count = base.filter(level=level, created_at__lt=cutoff).count()
        by_level[level] = {
            "days": days,
            "cutoff": cutoff,
            "count": count,
        }
        total += count
    return {"total": total, "by_level": by_level}


def purge_observability_events(*, sistema_id=None, apply=False, now=None):
    now = now or timezone.now()
    preview = retention_preview(sistema_id=sistema_id, now=now)
    deleted = 0

    if not apply or preview["total"] == 0:
        return {**preview, "deleted": 0, "applied": False}

    base = ObservabilityEvent.objects.all()
    if sistema_id is not None:
        base = base.filter(sistema_id=sistema_id)

    with transaction.atomic():
        for level, info in preview["by_level"].items():
            qs = base.filter(level=level, created_at__lt=info["cutoff"])
            level_deleted, _ = qs.delete()
            deleted += level_deleted

    return {**preview, "deleted": deleted, "applied": True}
