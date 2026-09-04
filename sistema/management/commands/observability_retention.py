from django.core.management.base import BaseCommand, CommandError

from sistema.models import Sistema
from sistema.observability_retention import purge_observability_events


class Command(BaseCommand):
    help = "Aplica a política de retenção dos eventos de observabilidade. Por padrão apenas simula a limpeza."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Efetiva a exclusão dos eventos expirados.")
        parser.add_argument("--system-id", type=int, dest="sistema_id", help="Restringe a limpeza a um sistema.")

    def handle(self, *args, **options):
        sistema_id = options.get("sistema_id")
        if sistema_id is not None and not Sistema.objects.filter(pk=sistema_id).exists():
            raise CommandError(f"Sistema {sistema_id} não encontrado.")

        result = purge_observability_events(
            sistema_id=sistema_id,
            apply=bool(options.get("apply")),
        )

        mode = "APLICADO" if result["applied"] else "SIMULAÇÃO"
        self.stdout.write(self.style.MIGRATE_HEADING(f"Observability retention · {mode}"))
        for level, info in result["by_level"].items():
            self.stdout.write(f"{level:8} retenção={info['days']:4}d expirados={info['count']}")
        self.stdout.write(f"Total elegível: {result['total']}")
        if result["applied"]:
            self.stdout.write(self.style.SUCCESS(f"Eventos removidos: {result['deleted']}"))
        else:
            self.stdout.write("Nenhum registro foi removido. Use --apply para efetivar a limpeza.")
