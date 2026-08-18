from __future__ import annotations

from pathlib import Path

from django.conf import settings

from .compiler import SpecificationCompiler
from .forms_validation import validate_generated_forms
from .generation_validation import validate_generated_project
from .models import Sistema
from .package_validation import validate_generated_package
from .quality_validation import validate_generated_quality
from .runtime_validation import validate_generated_runtime
from .security_validation import validate_generated_security
from .specification import build_specification
from .specification_plan import CompilationPlan
from .validation import validate_specification


class GeradorService:
    """Application service for validating, planning and compiling systems."""

    def __init__(self, sistema_id):
        self.sistema = Sistema.objects.select_related("usuario").get(pk=sistema_id)
        self.diretorio_base = self._output_directory()
        self.logs: list[str] = []

    def _output_directory(self) -> str:
        root = Path(getattr(settings, "GERADOR_OUTPUT_ROOT", Path(settings.MEDIA_ROOT) / "generated")).resolve()
        user_root = root / str(self.sistema.usuario_id)
        nome_projeto = build_specification(self.sistema).technical_name
        return str((user_root / nome_projeto).resolve())

    def log(self, mensagem: str):
        self.logs.append(mensagem)

    def validar(self):
        self.log("🔎 Validando especificação...")
        validate_specification(self.sistema)
        self.log("✅ Especificação ORM válida.")

    def especificacao(self):
        return build_specification(self.sistema)

    def plano_compilacao(self):
        return CompilationPlan(self.especificacao())

    def gerar_projeto_completo(self):
        self.validar()
        try:
            spec = self.especificacao()
            self.log(f"🧾 Especificação GEN-{spec.version}: {spec.fingerprint[:12]}...")
            plan = CompilationPlan(spec)
            self.log(f"📋 Plano de compilação: {len(plan.artifacts())} artefatos.")
            compiler = SpecificationCompiler(spec)
            compiled = compiler.compile()
            output = Path(self.diretorio_base).resolve()
            output.mkdir(parents=True, exist_ok=True)
            expected_paths = {item.path for item in plan.artifacts()}
            written_paths: list[str] = []
            for artifact in compiled:
                destination = (output / artifact.path).resolve()
                if output not in destination.parents:
                    raise ValueError(f"Artefato fora do diretório de geração permitido: {artifact.path}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(artifact.content, encoding="utf-8", newline="\n")
                written_paths.append(artifact.path)
                self.log(f"Arquivo criado: {artifact.path}")
            if set(written_paths) != expected_paths:
                raise RuntimeError("O compilador não produziu exatamente os artefatos planejados.")

            self.log("🔬 Validando estrutura do projeto compilado...")
            validate_generated_project(spec, output)
            self.log("✅ Estrutura do projeto compilado está válida.")
            self.log("🧪 Validando contrato de runtime: templates, views e URLs...")
            runtime_artifacts = validate_generated_runtime(spec, output)
            self.log(f"✅ Contrato de runtime validado: {len(runtime_artifacts)} templates.")
            self.log("🧩 Validando contrato dos ModelForms...")
            form_artifacts = validate_generated_forms(spec, output)
            self.log(f"✅ ModelForms validados: {len(form_artifacts)} formulários.")
            self.log("🛡️ Executando validação final de qualidade...")
            quality_artifacts = validate_generated_quality(spec, output)
            self.log(f"✅ Qualidade do projeto validada: {len(quality_artifacts)} artefatos.")
            self.log("📦 Validando pacote de distribuição...")
            package_artifacts = validate_generated_package(spec, output)
            self.log(f"✅ Pacote validado: {len(package_artifacts)} arquivos essenciais.")
            self.log("🔐 Validando segurança dos artefatos...")
            security_artifacts = validate_generated_security(output)
            self.log(f"✅ Segurança validada: {len(security_artifacts)} arquivos analisados.")

            self.sistema.caminho_geracao = str(output)
            self.sistema.save(update_fields=["caminho_geracao", "atualizado_em"])
            self.log(f"📁 Projeto gerado em: {output}")
            self.log("✅ Compilação concluída com sucesso!")
            return self.logs
        except Exception as exc:
            self.log(f"❌ ERRO FATAL: {exc}")
            raise
