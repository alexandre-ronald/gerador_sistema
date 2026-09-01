from django.utils import timezone

from .models import VersaoGeracao


class ValidationCenterService:
    """Consolida checks estruturais da definição sem modificar o sistema."""

    STATUSES = {"success", "warning", "error", "pending"}

    def __init__(self, sistema):
        self.sistema = sistema

    def validate(self):
        version = self.sistema.versoes.order_by("-numero").first()
        checks = [
            self._definition_check(),
            self._relationships_check(),
            self._generation_check(version),
            self._dashboard_check(version),
            self._runtime_check(version),
        ]
        counts = {status: sum(1 for check in checks if check["status"] == status) for status in self.STATUSES}
        overall_status = "error" if counts["error"] else ("warning" if counts["warning"] else ("pending" if counts["pending"] else "success"))
        return {
            "system": {"id": self.sistema.pk, "name": self.sistema.nome},
            "version": version.numero if version else None,
            "overall_status": overall_status,
            "release_ready": overall_status == "success",
            "total": len(checks),
            "successes": counts["success"],
            "warnings": counts["warning"],
            "errors": counts["error"],
            "pending": counts["pending"],
            "executed_at": timezone.now(),
            "checks": checks,
        }

    def _check(self, key, label, status, summary, details=None):
        if status not in self.STATUSES:
            raise ValueError(f"Status de validação inválido: {status}")
        return {"key": key, "label": label, "status": status, "summary": summary, "details": list(details or [])}

    def _definition_check(self):
        modules = list(self.sistema.modulos.prefetch_related("entidades__campos").all())
        entities = [entity for module in modules for entity in module.entidades.all()]
        fields = [field for entity in entities for field in entity.campos.all()]
        if not modules:
            return self._check("definition", "Definição e Models", "warning", "Sistema ainda não possui módulos.", ["Adicione pelo menos um módulo para iniciar a definição do domínio."])
        if not entities:
            return self._check("definition", "Definição e Models", "warning", "Módulos existentes ainda não possuem entidades.", [f"Módulos: {len(modules)}"])
        if not fields:
            return self._check("definition", "Definição e Models", "warning", "Entidades existentes ainda não possuem campos configurados.", [f"Entidades: {len(entities)}"])
        return self._check("definition", "Definição e Models", "success", "Estrutura de domínio configurada.", [f"{len(modules)} módulo(s)", f"{len(entities)} entidade(s)", f"{len(fields)} campo(s)"])

    def _relationships_check(self):
        relational = []
        invalid = []
        for module in self.sistema.modulos.prefetch_related("entidades__campos__entidade_relacionada"):
            for entity in module.entidades.all():
                for field in entity.campos.all():
                    if not field.eh_relacional:
                        continue
                    relational.append(field)
                    if field.entidade_relacionada_id is None:
                        invalid.append(f"{entity.nome}.{field.nome}: entidade destino não definida")
                    elif field.entidade_relacionada.modulo.sistema_id != self.sistema.pk:
                        invalid.append(f"{entity.nome}.{field.nome}: entidade destino pertence a outro sistema")
                    if field.on_delete == "models.SET_NULL" and not field.null:
                        invalid.append(f"{entity.nome}.{field.nome}: SET_NULL exige null=True")
        if invalid:
            return self._check("relationships", "Relacionamentos", "error", "Existem relacionamentos inconsistentes.", invalid)
        if not relational:
            return self._check("relationships", "Relacionamentos", "success", "Nenhum relacionamento inconsistente encontrado.", ["O sistema não possui campos relacionais."])
        return self._check("relationships", "Relacionamentos", "success", "Relacionamentos configurados corretamente.", [f"{len(relational)} relacionamento(s) validado(s)"])

    def _generation_check(self, version):
        if version is None:
            return self._check("generation", "Geração", "pending", "Nenhuma versão/draft disponível para validação.", ["Gere ou salve uma configuração para habilitar os checks de artefato."])
        structure = version.estrutura_json if isinstance(version.estrutura_json, dict) else {}
        if not structure:
            return self._check("generation", "Geração", "warning", "A versão existe, mas não possui estrutura serializada.", [f"Versão {version.numero}"])
        return self._check("generation", "Geração", "success", "Estrutura da versão disponível para validação.", [f"Versão {version.numero}", f"{len(structure)} seção(ões) no manifesto"])

    def _dashboard_check(self, version):
        if version is None:
            return self._check("dashboard", "Dashboard", "pending", "Dashboard ainda não possui uma versão para análise.")
        structure = version.estrutura_json if isinstance(version.estrutura_json, dict) else {}
        dashboard = structure.get("dashboard") or {}
        widgets = dashboard.get("widgets") or []
        if not dashboard or not dashboard.get("enabled", bool(widgets)):
            return self._check("dashboard", "Dashboard", "warning", "Dashboard ainda não está configurado/ativado.")
        invalid = []
        for index, widget in enumerate(widgets, start=1):
            try:
                x, y, width, height = int(widget.get("x", 0)), int(widget.get("y", 0)), int(widget.get("w", 4)), int(widget.get("h", 3))
            except (TypeError, ValueError):
                invalid.append(f"Widget {index}: coordenadas inválidas")
                continue
            if x < 0 or y < 0 or width < 1 or height < 1 or width > 12 or x + width > 12:
                invalid.append(f"Widget {index}: posição/tamanho fora do grid de 12 colunas")
        if invalid:
            return self._check("dashboard", "Dashboard", "error", "Dashboard possui widgets fora do contrato de layout.", invalid)
        return self._check("dashboard", "Dashboard", "success", "Dashboard respeita o contrato básico de layout.", [f"{len(widgets)} widget(s) analisado(s)"])

    def _runtime_check(self, version):
        if version is None or not version.arquivo_zip:
            return self._check("runtime", "Runtime", "pending", "Artefato gerado ainda não está disponível para validação de runtime.", ["Os checks de Python, templates, dependências e Django system check continuam sendo executados pelo validador de runtime durante a geração."])
        return self._check("runtime", "Runtime", "success", "Artefato de geração disponível.", ["A validação profunda do conteúdo do artefato permanece sob responsabilidade de GeneratedProjectRuntimeValidator."])


def validate_system(sistema):
    return ValidationCenterService(sistema).validate()
