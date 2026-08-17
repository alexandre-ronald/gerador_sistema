from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

from .compiler import CompilationResult, SpecificationCompiler
from .models import Sistema
from .specification import build_specification
from .specification_plan import CompilationPlan
from .validation import class_name, technical_name, validate_specification


class GeradorService:
    """Generate a Django project from a validated Sistema specification."""

    def __init__(self, sistema_id):
        self.sistema = Sistema.objects.select_related("usuario").get(pk=sistema_id)
        self.nome_projeto = technical_name(self.sistema.nome, "projeto")
        self.diretorio_base = self._output_directory()
        self.logs: list[str] = []

    def _output_directory(self) -> str:
        root = Path(
            getattr(
                settings,
                "GERADOR_OUTPUT_ROOT",
                Path(settings.MEDIA_ROOT) / "generated",
            )
        ).resolve()
        user_root = root / str(self.sistema.usuario_id)
        return str((user_root / self.nome_projeto).resolve())

    def log(self, mensagem):
        self.logs.append(mensagem)

    def validar(self):
        self.log("🔎 Validando especificação...")
        validate_specification(self.sistema)
        self.log("✅ Especificação válida.")

    def especificacao(self):
        """Return the canonical GEN-0002 specification for this system."""
        return build_specification(self.sistema)

    def plano_compilacao(self):
        """Return a deterministic generation plan without writing files."""
        return CompilationPlan(self.especificacao())

    def compilar_especificacao(self) -> CompilationResult:
        """Compile the canonical specification through the GEN-0003 compiler."""
        spec = self.especificacao()
        self.log(f"🔧 Compilando especificação {spec.fingerprint[:12]}...")
        result = SpecificationCompiler(spec, self.diretorio_base).compile()
        for artifact in result.artifacts:
            self.log(f"Arquivo criado: {artifact}")
        self.log("✅ Compilação concluída com sucesso!")
        return result

    def gerar_projeto_completo(self):
        self.validar()
        try:
            os.makedirs(self.diretorio_base, exist_ok=True)

            self._gerar_core()

            for modulo in self.sistema.modulos.prefetch_related(
                "entidades__campos__entidade_relacionada__modulo"
            ):
                self._gerar_modulo(modulo)

            self._gerar_templates_globais()

            if self.sistema.gerar_docker:
                self._gerar_docker()

            self.log(f"📁 Projeto gerado em: {self.diretorio_base}")
            self.log("✅ Geração concluída com sucesso!")
            return self.logs
        except Exception as exc:
            self.log(f"❌ ERRO FATAL: {exc}")
            raise

    def _escrever_arquivo(self, caminho_relativo, template_name, contexto):
        caminho_full = Path(self.diretorio_base) / caminho_relativo
        caminho_full.parent.mkdir(parents=True, exist_ok=True)
        conteudo = render_to_string(template_name, contexto)
        with caminho_full.open("w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(conteudo)
        self.log(f"Arquivo criado: {caminho_relativo}")

    def _gerar_docker(self):
        self.log("🐳 Criando arquivos do ambiente Docker...")
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        self._escrever_arquivo("Dockerfile", "gerador/snippets/dockerfile.txt", ctx)
        self._escrever_arquivo("docker-compose.yml", "gerador/snippets/docker_compose.txt", ctx)
        self._escrever_arquivo(".dockerignore", "gerador/snippets/dockerignore.txt", ctx)

    def _gerar_modulo(self, modulo):
        app_name = technical_name(modulo.nome, "app")
        entidades = list(modulo.entidades.prefetch_related("campos__entidade_relacionada__modulo"))
        imports_por_app = {}
        for entidade in entidades:
            setattr(entidade, "classe_tecnica", class_name(entidade.nome))
            setattr(entidade, "nome_tecnico", technical_name(entidade.nome, "model"))
            campos = list(entidade.campos.all())
            setattr(entidade, "campo_principal", campos[0] if campos else None)
            for campo in campos:
                tipo_str = str(campo.tipo).strip()
                setattr(campo, "eh_relacional", tipo_str in {"ForeignKey", "OneToOneField", "ManyToManyField"})
                setattr(campo, "nome_tecnico", technical_name(campo.nome, "campo"))
                setattr(campo, "default_repr", self._default_repr(campo.default_value))
                if campo.entidade_relacionada and campo.eh_relacional:
                    nome_classe = class_name(campo.entidade_relacionada.nome)
                    setattr(campo, "classe_relacionada", nome_classe)
                    app_pai = technical_name(campo.entidade_relacionada.modulo.nome, "app")
                    if app_pai != app_name:
                        imports_por_app.setdefault(app_pai, set()).add(nome_classe)
                else:
                    setattr(campo, "classe_relacionada", "")
        ctx = {"sistema": self.sistema, "app_name": app_name, "entidades": entidades,
               "imports_por_app": {key: sorted(values) for key, values in imports_por_app.items()},
               "nome_projeto": self.nome_projeto}
        self._escrever_arquivo(f"{app_name}/__init__.py", "gerador/snippets/init.txt", ctx)
        self._escrever_arquivo(f"{app_name}/models.py", "gerador/snippets/models.txt", ctx)
        self._escrever_arquivo(f"{app_name}/migrations/__init__.py", "gerador/snippets/init.txt", ctx)
        self._escrever_arquivo(f"{app_name}/forms.py", "gerador/snippets/forms.txt", ctx)
        self._escrever_arquivo(f"{app_name}/views.py", "gerador/snippets/views.txt", ctx)
        self._escrever_arquivo(f"{app_name}/urls.py", "gerador/snippets/urls_app.txt", ctx)
        self._escrever_arquivo(f"{app_name}/admin.py", "gerador/snippets/admin.txt", ctx)
        self._escrever_arquivo(f"{app_name}/apps.py", "gerador/snippets/apps_config.txt", ctx)
        self._escrever_arquivo("templates/registration/login.html", "gerador/snippets/login_html.txt", ctx)
        for entidade in entidades:
            ent_ctx = {**ctx, "entidade": entidade, "entidade_nome_lower": entidade.nome_tecnico}
            base_t = f"{app_name}/templates/{app_name}"
            self._escrever_arquivo(f"{base_t}/{entidade.nome_tecnico}_list.html", "gerador/snippets/html_list.txt", ent_ctx)
            self._escrever_arquivo(f"{base_t}/{entidade.nome_tecnico}_form.html", "gerador/snippets/html_form.txt", ent_ctx)
            self._escrever_arquivo(f"{base_t}/{entidade.nome_tecnico}_confirm_delete.html", "gerador/snippets/html_delete.txt", ent_ctx)

    @staticmethod
    def _default_repr(value):
        value = str(value or "").strip()
        if not value:
            return ""
        if value.lower() == "true":
            return "True"
        if value.lower() == "false":
            return "False"
        if value.lower() in {"none", "null"}:
            return "None"
        try:
            float(value)
            return value
        except ValueError:
            return repr(value)

    def _gerar_core(self):
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        self._escrever_arquivo("manage.py", "gerador/snippets/manage.txt", ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/__init__.py", "gerador/snippets/init.txt", ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/settings.py", "gerador/snippets/settings.txt", ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/urls.py", "gerador/snippets/urls_root.txt", ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/wsgi.py", "gerador/snippets/wsgi.txt", ctx)

    def _gerar_templates_globais(self):
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        self._escrever_arquivo("templates/base.html", "gerador/snippets/base_html.txt", ctx)
        self._escrever_arquivo("templates/index.html", "gerador/snippets/index_html.txt", ctx)
