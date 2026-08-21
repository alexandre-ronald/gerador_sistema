import ast
import keyword
import os
import re
import shutil
from pathlib import Path
from django.template.loader import render_to_string
from django.utils.text import slugify
from .models import Sistema, Modulo, Entidade
from .runtime_validation import validate_generated_runtime


class GeradorService:
    ALLOWED_FIELD_TYPES = {
        "CharField", "TextField", "IntegerField", "FloatField", "DecimalField",
        "BooleanField", "DateField", "DateTimeField", "TimeField", "EmailField",
        "URLField", "FileField", "ImageField", "ForeignKey", "ManyToManyField",
        "OneToOneField",
    }

    RELATION_FIELD_TYPES = {"ForeignKey", "OneToOneField", "ManyToManyField"}
    RELATED_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\+)?$")

    def __init__(self, sistema_id):
        self.sistema = Sistema.objects.get(pk=sistema_id)
        self.nome_projeto = self._python_identifier(self.sistema.nome, fallback="projeto")
        self.diretorio_base = Path(self.sistema.caminho_geracao).resolve()
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
        normalized = slugify(str(value or ""), allow_unicode=False).replace("-", " ")
        words = re.findall(r"[A-Za-z0-9]+", normalized)
        name = "".join(word[:1].upper() + word[1:] for word in words) or fallback
        if name[0].isdigit():
            name = f"Modelo{name}"
        if keyword.iskeyword(name):
            name = f"Modelo{name.title()}"
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

    @classmethod
    def _is_relation(cls, campo):
        return str(getattr(campo, "tipo", "") or "").strip() in cls.RELATION_FIELD_TYPES

    @classmethod
    def _field_type(cls, campo):
        tipo = str(getattr(campo, "tipo", "") or "").strip()
        if tipo not in cls.ALLOWED_FIELD_TYPES:
            entidade = getattr(getattr(campo, "entidade", None), "nome", "?")
            raise ValueError(
                f"Tipo de campo inválido para {entidade}.{getattr(campo, 'nome', '?')}: {tipo!r}"
            )
        return tipo

    @classmethod
    def _related_name(cls, campo):
        value = str(getattr(campo, "related_name_str", "") or "").strip()
        if not value:
            return ""
        if not cls.RELATED_NAME_RE.fullmatch(value):
            raise ValueError(
                f"related_name inválido para {getattr(getattr(campo, 'entidade', None), 'nome', '?')}."
                f"{getattr(campo, 'nome', '?')}: {value!r}. Use apenas letras, números e underscore, "
                "opcionalmente terminando com '+'."
            )
        return value

    @staticmethod
    def _python_literal(value):
        return repr(str(value or ""))

    def log(self, mensagem):
        self.logs.append(mensagem)

    def gerar_projeto_completo(self):
        try:
            if self.diretorio_base.is_dir():
                shutil.rmtree(self.diretorio_base)
            self.diretorio_base.mkdir(parents=True, exist_ok=True)
            self.log("🧹 Diretório de geração limpo antes da compilação")
            self._gerar_core()
            for modulo in self.sistema.modulos.all():
                self._gerar_modulo(modulo)
            if self.sistema.usar_auditoria:
                self._gerar_auditoria()
            self._gerar_templates_globais()
            self._validar_htmls_gerados()
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
        caminho_full = self.diretorio_base / Path(caminho_relativo)
        caminho_full.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho_full, "w", encoding="utf-8") as f:
            f.write(render_to_string(template_name, contexto))
        self.log(f"Arquivo criado: {caminho_relativo}")

    @staticmethod
    def _normalizar_caminho_geracao(caminho):
        return Path(caminho).resolve()

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
        entidade.verbose_python = self._python_literal(entidade.nome)
        entidade.verbose_plural_python = self._python_literal(entidade.nome_plural or entidade.nome)

        campos_compilados = list(entidade.campos.all())
        for campo in campos_compilados:
            campo.codigo_nome = self._python_identifier(campo.nome, "campo")
            campo.tipo_python = self._field_type(campo)
            campo.verbose_nome = campo.verbose_name or campo.nome
            campo.verbose_python = self._python_literal(campo.verbose_nome)
            campo.default_python = self._python_default(campo.default_value)
            related_name = self._related_name(campo)
            campo.related_name_python = self._python_literal(related_name) if related_name else ""
            campo.upload_to_python = self._python_literal(campo.upload_to) if campo.upload_to else repr("uploads/")
            campo.on_delete_python = campo.on_delete if campo.on_delete in {
                "models.CASCADE", "models.PROTECT", "models.SET_NULL", "models.RESTRICT"
            } else "models.CASCADE"
            campo.classe_relacionada = (
                self._class_name(campo.entidade_relacionada.nome)
                if self._is_relation(campo) and campo.entidade_relacionada
                else ""
            )
            if self._is_relation(campo) and not campo.entidade_relacionada:
                raise ValueError(f"Campo relacional sem entidade relacionada: {entidade.nome}.{campo.nome}")

        entidade.campos_compilados = campos_compilados
        return campos_compilados

    def _preparar_modulos(self):
        modulos = list(self.sistema.modulos.prefetch_related("entidades"))
        app_names = {}
        for modulo in modulos:
            modulo.app_name = self._python_identifier(modulo.nome, "app")
            anterior = app_names.get(modulo.app_name)
            if anterior is not None and anterior != modulo.nome:
                raise ValueError(
                    f"Colisão de nome de app após normalização: {anterior!r} e {modulo.nome!r} "
                    f"geram {modulo.app_name!r}. Renomeie um dos módulos."
                )
            app_names[modulo.app_name] = modulo.nome

            modulo.entidades_compiladas = list(modulo.entidades.all())
            class_names = {}
            for entidade in modulo.entidades_compiladas:
                self._preparar_entidade(entidade)
                anterior = class_names.get(entidade.classe_nome)
                if anterior is not None and anterior != entidade.nome:
                    raise ValueError(
                        f"Colisão de classe no módulo {modulo.nome!r}: {anterior!r} e {entidade.nome!r} "
                        f"geram {entidade.classe_nome!r}. Renomeie uma das entidades."
                    )
                class_names[entidade.classe_nome] = entidade.nome
        return modulos

    def _gerar_custom_user(self):
        if not self.sistema.usar_custom_user:
            return
        for path, template in [
            ("usuarios/__init__.py", "init.txt"),
            ("usuarios/apps.py", "custom_user_apps.txt"),
            ("usuarios/models.py", "custom_user_models.txt"),
            ("usuarios/admin.py", "custom_user_admin.txt"),
            ("usuarios/migrations/__init__.py", "init.txt"),
        ]:
            self._escrever_arquivo(path, f"gerador/snippets/{template}", {})
        self.log("🔐 Modelo de usuário customizado materializado em usuarios/")

    def _gerar_modulo(self, modulo):
        app_name = self._python_identifier(modulo.nome, "app")
        modulo.app_name = app_name
        entidades = list(modulo.entidades.all())
        imports_por_app = {}
        for entidade in entidades:
            self._preparar_entidade(entidade)
            for campo in entidade.campos_compilados:
                if self._is_relation(campo) and campo.entidade_relacionada:
                    app_pai = self._python_identifier(campo.entidade_relacionada.modulo.nome, "app")
                    if app_pai != app_name:
                        imports_por_app.setdefault(app_pai, set()).add(
                            self._class_name(campo.entidade_relacionada.nome)
                        )

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

        html_paths = []
        for entidade in entidades:
            ent_ctx = {**ctx, "entidade": entidade, "entidade_nome_lower": entidade.codigo_nome}
            base_t = f"{app_name}/templates/{app_name}"
            for filename, template in [
                (f"{entidade.codigo_nome}_list.html", "html_list.txt"),
                (f"{entidade.codigo_nome}_form.html", "html_form.txt"),
                (f"{entidade.codigo_nome}_confirm_delete.html", "html_delete.txt"),
            ]:
                path = f"{base_t}/{filename}"
                self._escrever_arquivo(path, f"gerador/snippets/{template}", ent_ctx)
                html_paths.append(path)

        if entidades and len(html_paths) != len(entidades) * 3:
            raise RuntimeError(
                f"Falha na materialização dos templates HTML do módulo {app_name}: "
                f"esperados {len(entidades) * 3}, gerados {len(html_paths)}"
            )

    def _gerar_auditoria(self):
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        templates = [
            ("auditoria/__init__.py", "init.txt"),
            ("auditoria/apps.py", "auditoria_apps.txt"),
            ("auditoria/models.py", "auditoria_models.txt"),
            ("auditoria/middleware.py", "auditoria_middleware.txt"),
            ("auditoria/migrations/__init__.py", "init.txt"),
            ("auditoria/migrations/0001_initial.py", "auditoria_migration_0001.txt"),
        ]
        for path, template in templates:
            self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)

    def _gerar_core(self):
        modulos = self._preparar_modulos()
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto, "modulos": modulos}
        for path, template in [
            ("manage.py", "manage.txt"),
            (f"{self.nome_projeto}/__init__.py", "init.txt"),
            (f"{self.nome_projeto}/settings.py", "settings.txt"),
            (f"{self.nome_projeto}/urls.py", "urls_root_v2.txt"),
            (f"{self.nome_projeto}/wsgi.py", "wsgi.txt"),
            ("requirements.txt", "requirements.txt"),
            ("instalacao.bat", "instalacao.txt"),
        ]:
            contexto = {**ctx, "banco_dados": self.sistema.banco_dados}
            self._escrever_arquivo(path, f"gerador/snippets/{template}", contexto)
        self._gerar_custom_user()
        (self.diretorio_base / "static").mkdir(parents=True, exist_ok=True)
        self.log("Diretório criado: static/")

    def _gerar_templates_globais(self):
        modulos = self._preparar_modulos()
        ctx = {"sistema": self.sistema, "modulos": modulos}
        self._escrever_arquivo("templates/base.html", "gerador/snippets/base_html.txt", ctx)
        self._escrever_arquivo("templates/index.html", "gerador/snippets/index_html.txt", ctx)

    def _validar_htmls_gerados(self):
        root = self._normalizar_caminho_geracao(self.diretorio_base)
        htmls = sorted(
            path for path in root.rglob("*.html")
            if "templates" in path.parts and not any(part in {".venv", "__pycache__"} for part in path.parts)
        )
        if not htmls:
            raise RuntimeError("Nenhum template HTML foi gerado para o sistema")
        self.log(f"🧩 HTMLs do sistema materializados: {len(htmls)} arquivo(s)")
