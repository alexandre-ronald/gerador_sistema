import ast
import keyword
import os
import re
import shutil

from django.template.loader import render_to_string
from django.utils.text import slugify

from .models import Sistema, VersaoGeracao
from .runtime_validation import validate_generated_runtime
from .structure_service import serialize_system_structure


class GeradorService:
    """Compilador único: especificação persistida -> projeto Django executável."""
    def __init__(self, sistema_id):
        self.sistema = Sistema.objects.get(pk=sistema_id)
        self.nome_projeto = self._python_identifier(self.sistema.nome, fallback="projeto")
        self.diretorio_base = self.sistema.caminho_geracao
        self.logs = []
        self.versao_gerada = None

    @staticmethod
    def _python_identifier(value, fallback="item"):
        value = slugify(str(value or ""), allow_unicode=False).replace("-", "_")
        value = re.sub(r"[^a-zA-Z0-9_]", "_", value); value = re.sub(r"_+", "_", value).strip("_") or fallback
        if value[0].isdigit(): value = f"_{value}"
        if keyword.iskeyword(value): value = f"{value}_"
        return value

    @staticmethod
    def _class_name(value, fallback="Modelo"):
        normalized = GeradorService._python_identifier(value, fallback=fallback)
        return "".join(part[:1].upper() + part[1:] for part in normalized.split("_") if part) or fallback

    @staticmethod
    def _python_default(value):
        value = str(value or "").strip()
        if not value: return ""
        try: ast.literal_eval(value); return value
        except (ValueError, SyntaxError): return repr(value)

    def log(self, mensagem): self.logs.append(mensagem)

    def _dashboard_config(self):
        versao = self.sistema.versoes.filter(numero=0).first()
        if versao and isinstance(versao.estrutura_json, dict):
            dashboard = versao.estrutura_json.get("dashboard")
            if isinstance(dashboard, dict):
                from .builder_contracts import normalize_dashboard_config
                return normalize_dashboard_config(dashboard)
        return {"enabled": False, "title": "Dashboard", "layout": "12-column", "refresh_seconds": 0, "widgets": []}

    def _prepare_context(self):
        modulos = list(self.sistema.modulos.prefetch_related("entidades__campos")); app_names = {}
        for modulo in modulos:
            modulo.app_name = self._python_identifier(modulo.nome, "app")
            if modulo.app_name in app_names: raise ValueError(f"Módulos '{app_names[modulo.app_name]}' e '{modulo.nome}' geram o mesmo app Python '{modulo.app_name}'. Renomeie um deles.")
            app_names[modulo.app_name] = modulo.nome; modulo.entidades_geracao = list(modulo.entidades.all()); modulo.entidades_crud = []; class_names = {}
            for entidade in modulo.entidades_geracao:
                entidade.codigo_nome = self._python_identifier(entidade.nome, "entidade"); entidade.classe_nome = self._class_name(entidade.nome)
                if entidade.classe_nome in class_names: raise ValueError(f"Entidades '{class_names[entidade.classe_nome]}' e '{entidade.nome}' no módulo '{modulo.nome}' geram a mesma classe '{entidade.classe_nome}'.")
                class_names[entidade.classe_nome] = entidade.nome; entidade.campos_geracao = list(entidade.campos.all())
                if entidade.gerar_crud_views: modulo.entidades_crud.append(entidade)
                field_names = {}
                for campo in entidade.campos_geracao:
                    campo.codigo_nome = self._python_identifier(campo.nome, "campo")
                    if campo.codigo_nome in field_names: raise ValueError(f"Campos '{field_names[campo.codigo_nome]}' e '{campo.nome}' em '{entidade.nome}' geram o mesmo identificador '{campo.codigo_nome}'.")
                    field_names[campo.codigo_nome] = campo.nome; campo.verbose_nome = campo.verbose_name or campo.nome; campo.default_python = self._python_default(campo.default_value)
                    if campo.eh_relacional and campo.entidade_relacionada:
                        campo.classe_relacionada = self._class_name(campo.entidade_relacionada.nome)
                        campo.app_relacionada = self._python_identifier(campo.entidade_relacionada.modulo.nome, "app")
                    else: campo.classe_relacionada = ""; campo.app_relacionada = ""
        return {"sistema": self.sistema, "nome_projeto": self.nome_projeto, "modulos": modulos, "dashboard": self._dashboard_config()}

    def _registrar_versao(self):
        ultimo = self.sistema.versoes.order_by("-numero").first()
        numero = (ultimo.numero if ultimo else 0) + 1
        estrutura = serialize_system_structure(self.sistema)
        self.versao_gerada = VersaoGeracao.objects.create(sistema=self.sistema, numero=numero, descricao=f"Geração automática v{numero}", estrutura_json=estrutura)
        self.log(f"🗂️ Versão de geração v{numero} registrada")

    def gerar_projeto_completo(self):
        if not self.diretorio_base: raise ValueError("Defina a pasta de destino antes de gerar o sistema.")
        try:
            if os.path.isdir(self.diretorio_base): shutil.rmtree(self.diretorio_base)
            os.makedirs(self.diretorio_base, exist_ok=True); self.log("🧹 Diretório de geração limpo antes da compilação")
            ctx = self._prepare_context(); self._gerar_core(ctx)
            for modulo in ctx["modulos"]: self._gerar_modulo(modulo, ctx)
            self._gerar_templates_globais(ctx); self.log("🔎 Validando o projeto gerado antes de liberar a geração...")
            resultado = validate_generated_runtime(self.diretorio_base)
            for mensagem in resultado.get("messages", []): self.log(mensagem)
            for aviso in resultado.get("warnings", []): self.log(f"⚠️ {aviso}")
            self.log(f"✅ Validação concluída: {resultado.get('checked', 0)} itens verificados")
            if self.sistema.gerar_docker: self._gerar_docker()
            self._registrar_versao()
            self.log("✅ Geração concluída com sucesso!"); return self.logs
        except Exception as exc: self.log(f"❌ ERRO FATAL: {exc}"); raise

    def _escrever_arquivo(self, caminho_relativo, template_name, contexto):
        caminho_full = os.path.join(self.diretorio_base, caminho_relativo); os.makedirs(os.path.dirname(caminho_full), exist_ok=True)
        with open(caminho_full, "w", encoding="utf-8") as f: f.write(render_to_string(template_name, contexto))
        self.log(f"Arquivo criado: {caminho_relativo}")

    def _gerar_requirements(self):
        requirements = ["Django>=5.2,<7", "python-dotenv>=1.0"]
        if self.sistema.banco_dados == "postgresql": requirements.append("psycopg[binary]>=3.2")
        elif self.sistema.banco_dados == "mysql": requirements.append("mysqlclient>=2.2")
        elif self.sistema.banco_dados == "sqlserver": requirements.append("mssql-django>=1.5")
        elif self.sistema.banco_dados == "oracle": requirements.append("oracledb>=2.0")
        with open(os.path.join(self.diretorio_base, "requirements.txt"), "w", encoding="utf-8") as f: f.write("\n".join(requirements) + "\n")
        self.log("Arquivo criado: requirements.txt")

    def _gerar_core(self, ctx):
        for path, template in (("manage.py", "manage.txt"), (f"{self.nome_projeto}/__init__.py", "init.txt"), (f"{self.nome_projeto}/settings.py", "settings.txt"), (f"{self.nome_projeto}/urls.py", "urls_root_v2.txt"), (f"{self.nome_projeto}/wsgi.py", "wsgi.txt"), (f"{self.nome_projeto}/context_processors.py", "navigation_context.txt")):
            self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)
        self._gerar_requirements(); os.makedirs(os.path.join(self.diretorio_base, "static"), exist_ok=True); os.makedirs(os.path.join(self.diretorio_base, "media"), exist_ok=True)
        self.log("✅ Diretórios static/ e media/ preparados")

    def _gerar_modulo(self, modulo, ctx):
        local_ctx = {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud, "imports_por_app": {}}
        for path, template in ((f"{modulo.app_name}/__init__.py", "init.txt"), (f"{modulo.app_name}/models.py", "models.txt"), (f"{modulo.app_name}/migrations/__init__.py", "init.txt"), (f"{modulo.app_name}/forms.py", "forms_v2.txt"), (f"{modulo.app_name}/views.py", "views.txt"), (f"{modulo.app_name}/urls.py", "urls_app_v2.txt"), (f"{modulo.app_name}/admin.py", "admin_v2.txt"), (f"{modulo.app_name}/apps.py", "apps_config.txt")):
            self._escrever_arquivo(path, f"gerador/snippets/{template}", local_ctx)
        for entidade in modulo.entidades_crud:
            ent_ctx = {**local_ctx, "entidade": entidade}; base_t = f"{modulo.app_name}/templates/{modulo.app_name}"
            for suffix, template in (("list", "html_list.txt"), ("form", "html_form.txt"), ("confirm_delete", "html_delete.txt")):
                self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_{suffix}.html", f"gerador/snippets/{template}", ent_ctx)

    def _gerar_templates_globais(self, ctx):
        self._escrever_arquivo("templates/base.html", "gerador/snippets/base_html.txt", ctx)
        self._escrever_arquivo("templates/index.html", "gerador/snippets/index_html.txt", ctx)
        self._escrever_arquivo("templates/dashboard.html", "gerador/snippets/dashboard_html.txt", ctx)
        self._escrever_arquivo("templates/registration/login.html", "gerador/snippets/login_html.txt", ctx)

    def _gerar_docker(self):
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        for path, template in (("Dockerfile", "dockerfile.txt"), ("docker-compose.yml", "docker_compose.txt"), (".dockerignore", "dockerignore.txt")): self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)