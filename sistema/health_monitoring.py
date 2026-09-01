from django.db.models import Avg

from .models import RuntimeCheck


class HealthMonitoringService:
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"

    def __init__(self, sistema):
        self.sistema = sistema

    def environment_states(self):
        states = []
        ambientes = self.sistema.ambientes.select_related("release_atual").all()
        for ambiente in ambientes:
            snapshot = getattr(ambiente, "runtime_snapshot", None)
            desired = str(ambiente.release_atual.numero) if ambiente.release_atual_id else ""
            observed = snapshot.release_observada if snapshot else ""
            drift = bool(desired and observed and desired != observed)
            health = self._snapshot_health(snapshot, drift)
            checks = ambiente.runtime_checks.all()[:10]
            avg_latency = ambiente.runtime_checks.filter(online=True).aggregate(avg=Avg("latency_ms"))["avg"]
            states.append({
                "ambiente": ambiente,
                "snapshot": snapshot,
                "health": health,
                "drift": drift,
                "desired_release": desired,
                "observed_release": observed,
                "avg_latency_ms": int(round(avg_latency)) if avg_latency is not None else None,
                "checks": checks,
            })
        return states

    def summary(self, states=None):
        states = states if states is not None else self.environment_states()
        counters = {
            "total": len(states),
            self.HEALTHY: 0,
            self.DEGRADED: 0,
            self.OFFLINE: 0,
            self.UNKNOWN: 0,
            "drift": 0,
            "migrations_pending": 0,
        }
        for item in states:
            counters[item["health"]] += 1
            if item["drift"]:
                counters["drift"] += 1
            snapshot = item["snapshot"]
            if snapshot:
                counters["migrations_pending"] += snapshot.migrations_pending
        return counters

    def history(self, limit=50):
        return RuntimeCheck.objects.filter(
            ambiente__sistema=self.sistema
        ).select_related("ambiente")[:limit]

    def _snapshot_health(self, snapshot, drift):
        if snapshot is None:
            return self.UNKNOWN
        if not snapshot.online:
            return self.OFFLINE
        if str(snapshot.status or "").lower() != "ok":
            return self.DEGRADED
        if snapshot.migrations_pending > 0 or drift:
            return self.DEGRADED
        return self.HEALTHY
