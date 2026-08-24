import ast
import keyword
import os
import re
import shutil

from django.template.loader import render_to_string
from django.utils.text import slugify

from .models import Sistema
from .runtime_validation import validate_generated_runtime


class GeradorService:
    """Single compilation pipeline from the persisted specification to Django."""

    def __init__(self, sistema_id):
        self.sistema = Sistema.objects.get(pk=sistema_id)
        self.nome_projeto = self._python_identifier(self.sistema.nome, fallback="projeto")
        self.diretorio_base = self.sistema.caminho_geracao
        self.logs = []

    @staticmethod
    def _python_identifier(value, fallback="item"):
        value = slugify(str(value or ""), allow_unicode=False).replace("-", "_")
        value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
        value = re.sub(r"_+", "_", value).strip("_") or fallback
        if value[0].isdigit(): value = f"_{value}"
        if keyword.iskeyword(value): value = f"{value}_"
        return value

    @staticmethod
    def _class_name(value, fallback="Modelo"):
        normalized = GeradorService._python_identifier(value, fallback=fallback)
        parts = [part for part in normalized.split("_") if part]
        return "".join(part[:1].upper() + part[1:] for part in parts) or fallback

    @staticmethod
    def _python_default(value):
        value = str(value or "").strip()
        if not value: return ""
        try:
            ast.literal_eval(value)
            return value
        except (ValueError, SyntaxError):
            return repr(value)

    def log(self, mensagem): self.logs.append(mensagem)

    def _prepare_context(self):
        modulos = list(self.sistema.modulos.prefetch_related("entidades__campos"))
        for modulo in modulos:
            modulo.app_name = self._python_identifier(modulo.nome, "app")
            modulo.entidades_geracao = list(modulo.entidades.all())
            modulo.entidades_crud = []
            for entidade in modulo.entidades_geracao:
                entidade.codigo_nome = self._python_identifier(entidade.nome, "entidade")
                entidade.classe_nome = self._class_name(entidade.nome)
                entidade.campos_geracao = list(entidade.campos.all())
                if entidade.gerar_crud_views:
                    modulo.entidades_crud.append(entidade)
                for campo in entidade.campos_geracao:
                    campo.codigo_nome = self._python_identifier(campo.nome, "campo")
                    campo.verbose_nome = campo.verbose_name or campo.nome
                    campo.default_python = self._python_default(campo.default_value)
                    campo.classe_relacionada = self._class_name(campo.entidade_relacionada.nome) if campo.eh_relacional and campo.entidade_relacionada else ""
        return {"sistema": self.sistema, "nome_projeto": self.nome_projeto, "modulos": modulos}

    def gerar_projeto_completo(self):
        if not self.diretorio_base: raise ValueError("Defina a pasta de destino antes de gerar o sistema.")
        try:
            if os.path.isdir(self.diretorio_base): shutil.rmtree(self.diretorio_base)
            os.makedirs(self.diretorio_base, exist_ok=True)
            self.log("🧹 Diretório de geração limpo antes da compilação")
            ctx = self._prepare_context()
            self._gerar_core(ctx)
            for modulo in ctx["modulos"]: self._gerar_modulo(modulo, ctx)
            self._gerar_templates_globais(ctx)
            self.log("🔎 Validando o projeto gerado antes de liberar a geração...")
            resultado = validate_generated_runtime(self.diretorio_base)
            for mensagem in resultado.get("messages", []): self.log(mensagem)
            for aviso in resultado.get("warnings", []): self.log(f"⚠️ {aviso}")
            self.log(f"✅ Validação concluída: {resultado.get('checked', 0)} itens verificados")
            if self.sistema.gerar_docker: self._gerar_docker()
            self.log("✅ Geração concluída com sucesso!")
            return self.logs
        except Exception as exc:
            self.log(f"❌ ERRO FATAL: {exc}")
            raise

    def _escrever_arquivo(self, caminho_relativo, template_name, contexto):
        caminho_full = os.path.join(self.diretorio_base, caminho_relativo)
        os.makedirs(os.path.dirname(caminho_full), exist_ok=True)
        with open(caminho_full, "w", encoding="utf-8") as f: f.write(render_to_string(template_name, contexto))
        self.log(f"Arquivo criado: {caminho_relativo}")

    def _gerar_requirements(self):
        requirements = ["Django>=5.2,<7", "python-dotenv>=1.0"]
        if self.sistema.banco_dados == "postgresql": requirements.append("psycopg[binary]>=3.2")
        elif self.sistema.banco_dados == "mysql": requirements.append("mysqlclient>=2.2")
        elif self.sistema.banco_dados == "sqlserver": requirements.append("mssql-django>=1.5")
        elif self.sistema.banco_dados == "oracle": requirements.append("oracledb>=2.0")
        if self.sistema.gerar_api_rest: requirements.append("djangorestframework>=3.15")
        with open(os.path.join(self.diretorio_base, "requirements.txt"), "w", encoding="utf-8") as f: f.write("\n".join(requirements) + "\n")
        self.log("Arquivo criado: requirements.txt")

    def _gerar_core(self, ctx):
        for path, template in [("manage.py", "manage.txt"), (f"{self.nome_projeto}/__init__.py", "init.txt"), (f"{self.nome_projeto}/settings.py", "settings.txt"), (f"{self.nome_projeto}/urls.py", "urls_root_v2.txt"), (f"{self.nome_projeto}/wsgi.py", "wsgi.txt"), (f"{self.nome_projeto}/context_processors.py", "navigation_context.txt")]:
            self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)
        self._gerar_requirements()
        os.makedirs(os.path.join(self.diretorio_base, "static"), exist_ok=True)
        os.makedirs(os.path.join(self.diretorio_base, "media"), exist_ok=True)
        self.log("✅ Diretórios static/ e media/ preparados")

    def _gerar_modulo(self, modulo, ctx):
        app_name = modulo.app_name
        entidades = modulo.entidades_geracao
        imports_por_app = {}
        for entidade in entidades:
            for campo in entidade.campos_geracao:
                if campo.eh_relacional and campo.entidade_relacionada:
                    app_pai = self._python_identifier(campo.entidade_relacionada.modulo.nome, "app")
                    if app_pai != app_name: imports_por_app.setdefault(app_pai, set()).add(campo.classe_relacionada)
        local_ctx = {**ctx, "app_name": app_name, "entidades": entidades, "entidades_crud": modulo.entidades_crud, "imports_por_app": {k: sorted(v) for k, v in imports_por_app.items()}}
        for path, template in [(f"{app_name}/__init__.py", "init.txt"), (f"{app_name}/models.py", "models.txt"), (f"{app_name}/migrations/__init__.py", "init.txt"), (f"{app_name}/forms.py", "forms_v2.txt"), (f"{app_name}/views.py", "views.txt"), (f"{app_name}/urls.py", "urls_app_v2.txt"), (f"{app_name}/admin.py", "admin_v2.txt"), (f"{app_name}/apps.py", "apps_config.txt")]:
            self._escrever_arquivo(path, f"gerador/snippets/{template}", local_ctx)
        if modulo.entidades_crud:
            self._escrever_arquivo("templates/registration/login.html", "gerador/snippets/login_html.txt", local_ctx)
            for entidade in modulo.entidades_crud:
                ent_ctx = {**local_ctx, "entidade": entidade, "entidade_nome_lower": entidade.codigo_nome}
                base_t = f"{app_name}/templates/{app_name}"
                self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_list.html", "gerador/snippets/html_list.txt", ent_ctx)
                self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_form.html", "gerador/snippets/html_form.txt", ent_ctx)
                self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_confirm_delete.html", "gerador/snippets/html_delete.txt", ent_ctx)

    def _gerar_templates_globais(self, ctx):
        self._escrever_arquivo("templates/base.html", "gerador/snippets/base_html.txt", ctx)
        self._escrever_arquivo("templates/index.html", "gerador/snippets/index_html.txt", ctx)

    def _gerar_docker(self):
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        for path, template in [("Dockerfile", "dockerfile.txt"), ("docker-compose.yml", "docker_compose.txt"), (".dockerignore", "dockerignore.txt")]:
            self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)
