import ast
import keyword
import os
import re
import shutil
from django.template.loader import render_to_string
from django.utils.text import slugify
from .models import Sistema, Modulo, Entidade
from .runtime_validation import validate_generated_runtime


class GeradorService:
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
        if value[0].isdigit():
            value = f"_{value}"
        if keyword.iskeyword(value):
            value = f"{value}_"
        return value

    @staticmethod
    def _class_name(value, fallback="Modelo"):
        """Converte o nome exibido em um identificador de classe Python válido.

        A normalização passa obrigatoriamente por _python_identifier, que usa
        slugify(allow_unicode=False) para remover acentos. Assim, por exemplo,
        "Funcionário" vira "Funcionario" e nunca "FuncionRio".
        """
        normalized = GeradorService._python_identifier(value, fallback=fallback)
        parts = [part for part in normalized.split("_") if part]
        name = "".join(part[:1].upper() + part[1:] for part in parts) or fallback
        if name[0].isdigit():
            name = f"Modelo{name}"
        return name

    @staticmethod
    def _python_default(value):
        value = str(value or "").strip()
        if not value:
            return ""
        try:
            ast.literal_eval(value)
            return value
        except (ValueError, SyntaxError):
            return repr(value)

    def log(self, mensagem):
        self.logs.append(mensagem)

    def gerar_projeto_completo(self):
        try:
            if os.path.isdir(self.diretorio_base):
                shutil.rmtree(self.diretorio_base)
            os.makedirs(self.diretorio_base, exist_ok=True)
            self.log("🧹 Diretório de geração limpo antes da compilação")
            self._gerar_core()
            for modulo in self.sistema.modulos.all():
                self._gerar_modulo(modulo)
            self._gerar_templates_globais()
            self.log("🔎 Iniciando validação do projeto gerado...")
            resultado_validacao = validate_generated_runtime(self.diretorio_base)
            for mensagem in resultado_validacao.get("messages", []):
                self.log(mensagem)
            for aviso in resultado_validacao.get("warnings", []):
                self.log(f"⚠️ {aviso}")
            self.log(f"✅ Validação concluída: {resultado_validacao.get('checked', 0)} itens verificados")
            if self.sistema.gerar_docker:
                self._gerar_docker()
            self.log("✅ Geração concluída com sucesso!")
            return self.logs
        except Exception as e:
            self.log(f"❌ ERRO FATAL: {str(e)}")
            raise

    def _escrever_arquivo(self, caminho_relativo, template_name, contexto):
        caminho_full = os.path.join(self.diretorio_base, caminho_relativo)
        os.makedirs(os.path.dirname(caminho_full), exist_ok=True)
        with open(caminho_full, "w", encoding="utf-8") as f:
            f.write(render_to_string(template_name, contexto))
        self.log(f"Arquivo criado: {caminho_relativo}")

    def _gerar_requirements(self):
        requirements = ["Django>=5.2,<7", "python-dotenv>=1.0"]
        if self.sistema.banco_dados == "postgresql":
            requirements.append("psycopg[binary]>=3.2")
        elif self.sistema.banco_dados == "mysql":
            requirements.append("mysqlclient>=2.2")
        elif self.sistema.banco_dados == "sqlserver":
            requirements.append("mssql-django>=1.5")
        elif self.sistema.banco_dados == "oracle":
            requirements.append("oracledb>=2.0")
        if self.sistema.gerar_api_rest:
            requirements.append("djangorestframework>=3.15")
        path = os.path.join(self.diretorio_base, "requirements.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(requirements) + "\n")
        self.log("Arquivo criado: requirements.txt")

    def _gerar_docker(self):
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        for path, template in [
            ("Dockerfile", "dockerfile.txt"),
            ("docker-compose.yml", "docker_compose.txt"),
            (".dockerignore", "dockerignore.txt"),
        ]:
            self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)

    def _preparar_entidade(self, entidade):
        entidade.codigo_nome = self._python_identifier(entidade.nome, "entidade")
        entidade.classe_nome = self._class_name(entidade.nome)
        for campo in entidade.campos.all():
            campo.codigo_nome = self._python_identifier(campo.nome, "campo")
            campo.verbose_nome = campo.verbose_name or campo.nome
            campo.default_python = self._python_default(campo.default_value)
            campo.classe_relacionada = (
                self._class_name(campo.entidade_relacionada.nome)
                if campo.eh_relacional and campo.entidade_relacionada
                else ""
            )

    def _gerar_modulo(self, modulo):
        app_name = self._python_identifier(modulo.nome, "app")
        modulo.app_name = app_name
        entidades = list(modulo.entidades.all())
        imports_por_app = {}
        for entidade in entidades:
            self._preparar_entidade(entidade)
            for campo in entidade.campos.all():
                if campo.eh_relacional and campo.entidade_relacionada:
                    app_pai = self._python_identifier(campo.entidade_relacionada.modulo.nome, "app")
                    if app_pai != app_name:
                        imports_por_app.setdefault(app_pai, set()).add(campo.classe_relacionada)
        ctx = {
            "sistema": self.sistema,
            "app_name": app_name,
            "entidades": entidades,
            "imports_por_app": {k: sorted(v) for k, v in imports_por_app.items()},
            "nome_projeto": self.nome_projeto,
        }
        templates = [
            (f"{app_name}/__init__.py", "init.txt"),
            (f"{app_name}/models.py", "models.txt"),
            (f"{app_name}/migrations/__init__.py", "init.txt"),
            (f"{app_name}/forms.py", "forms_v2.txt"),
            (f"{app_name}/views.py", "views.txt"),
            (f"{app_name}/urls.py", "urls_app_v2.txt"),
            (f"{app_name}/admin.py", "admin_v2.txt"),
            (f"{app_name}/apps.py", "apps_config.txt"),
        ]
        for path, template in templates:
            self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)
        self._escrever_arquivo("templates/registration/login.html", "gerador/snippets/login_html.txt", ctx)
        for entidade in entidades:
            ent_ctx = {**ctx, "entidade": entidade, "entidade_nome_lower": entidade.codigo_nome}
            base_t = f"{app_name}/templates/{app_name}"
            self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_list.html", "gerador/snippets/html_list.txt", ent_ctx)
            self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_form.html", "gerador/snippets/html_form.txt", ent_ctx)
            self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_confirm_delete.html", "gerador/snippets/html_delete.txt", ent_ctx)

    def _gerar_core(self):
        modulos = list(self.sistema.modulos.prefetch_related("entidades"))
        for modulo in modulos:
            modulo.app_name = self._python_identifier(modulo.nome, "app")
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto, "modulos": modulos}
        for path, template in [
            ("manage.py", "manage.txt"),
            (f"{self.nome_projeto}/__init__.py", "init.txt"),
            (f"{self.nome_projeto}/settings.py", "settings.txt"),
            (f"{self.nome_projeto}/urls.py", "urls_root_v2.txt"),
            (f"{self.nome_projeto}/wsgi.py", "wsgi.txt"),
        ]:
            self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)
        self._gerar_requirements()
        os.makedirs(os.path.join(self.diretorio_base, "static"), exist_ok=True)
        os.makedirs(os.path.join(self.diretorio_base, "media"), exist_ok=True)
        self.log("✅ Diretórios static/ e media/ preparados")

    def _gerar_templates_globais(self):
        modulos = list(self.sistema.modulos.prefetch_related("entidades"))
        for modulo in modulos:
            modulo.app_name = self._python_identifier(modulo.nome, "app")
            for entidade in modulo.entidades.all():
                self._preparar_entidade(entidade)
        ctx = {"sistema": self.sistema, "modulos": modulos}
        self._escrever_arquivo("templates/base.html", "gerador/snippets/base_html.txt", ctx)
        self._escrever_arquivo("templates/index.html", "gerador/snippets/index_html.txt", ctx)
