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
        return value

    @staticmethod
    def _class_name(value, fallback="Modelo"):
        words = re.findall(r"[A-Za-z0-9]+", str(value or ""))
        name = "".join(word[:1].upper() + word[1:] for word in words) or fallback
        if name[0].isdigit():
            name = f"Modelo{name}"
        return name

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
        conteudo = render_to_string(template_name, contexto)
        with open(caminho_full, "w", encoding="utf-8") as f:
            f.write(conteudo)
        self.log(f"Arquivo criado: {caminho_relativo}")

    def _gerar_docker(self):
        self.log("🐳 Criando arquivos do ambiente Docker...")
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        self._escrever_arquivo("Dockerfile", "gerador/snippets/dockerfile.txt", ctx)
        self._escrever_arquivo("docker-compose.yml", "gerador/snippets/docker_compose.txt", ctx)
        self._escrever_arquivo(".dockerignore", "gerador/snippets/dockerignore.txt", ctx)

    def _preparar_entidade(self, entidade):
        entidade.codigo_nome = self._python_identifier(entidade.nome, "entidade")
        entidade.classe_nome = self._class_name(entidade.nome)
        for campo in entidade.campos.all():
            campo.codigo_nome = self._python_identifier(campo.nome, "campo")
            campo.verbose_nome = campo.verbose_name or campo.nome
            tipo_str = str(campo.tipo).strip()
            campo.eh_relacional = tipo_str in ["ForeignKey", "OneToOneField", "ManyToManyField"]
            campo.classe_relacionada = self._class_name(campo.entidade_relacionada.nome) if campo.eh_relacional and campo.entidade_relacionada else ""
        return entidade

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

        ctx = {"sistema": self.sistema, "app_name": app_name, "entidades": entidades,
               "imports_por_app": {k: sorted(v) for k, v in imports_por_app.items()},
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
            ent_ctx = {**ctx, "entidade": entidade, "entidade_nome_lower": entidade.codigo_nome}
            base_t = f"{app_name}/templates/{app_name}"
            self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_list.html", "gerador/snippets/html_list.txt", ent_ctx)
            self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_form.html", "gerador/snippets/html_form.txt", ent_ctx)
            self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_confirm_delete.html", "gerador/snippets/html_delete.txt", ent_ctx)

    def _gerar_core(self):
        ctx = {"sistema": self.sistema, "nome_projeto": self.nome_projeto}
        self._escrever_arquivo("manage.py", "gerador/snippets/manage.txt", ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/__init__.py", "gerador/snippets/init.txt", ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/settings.py", "gerador/snippets/settings.txt", ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/urls.py", "gerador/snippets/urls_root.txt", ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/wsgi.py", "gerador/snippets/wsgi.txt", ctx)

    def _gerar_templates_globais(self):
        modulos = list(self.sistema.modulos.prefetch_related("entidades"))
        for modulo in modulos:
            modulo.app_name = self._python_identifier(modulo.nome, "app")
            for entidade in modulo.entidades.all():
                self._preparar_entidade(entidade)
        ctx = {"sistema": self.sistema, "modulos": modulos}
        self._escrever_arquivo("templates/base.html", "gerador/snippets/base_html.txt", ctx)
        self._escrever_arquivo("templates/index.html", "gerador/snippets/index_html.txt", ctx)
