import os
from django.template.loader import render_to_string
from django.utils.text import slugify
from .models import Sistema, Modulo, Entidade

class GeradorService:
    def __init__(self, sistema_id):
        self.sistema = Sistema.objects.get(pk=sistema_id)
        # Nome do projeto limpo (ex: "Meu Sistema" -> "meu_sistema")
        self.nome_projeto = slugify(self.sistema.nome).replace('-', '_')
        self.diretorio_base = self.sistema.caminho_geracao
        self.logs = []

    def log(self, mensagem):
        self.logs.append(mensagem)

    def gerar_projeto_completo(self):
        try:
            if not os.path.exists(self.diretorio_base):
                os.makedirs(self.diretorio_base, exist_ok=True)

            self._gerar_core()

            for modulo in self.sistema.modulos.all():
                self._gerar_modulo(modulo)

            self._gerar_templates_globais()

            print(self.sistema.gerar_docker)

            if self.sistema.gerar_docker:
                self._gerar_docker()

            self.log("✅ Geração concluída com sucesso!")
            return self.logs
        except Exception as e:
            self.log(f"❌ ERRO FATAL: {str(e)}")
            raise e

    def _escrever_arquivo(self, caminho_relativo, template_name, contexto):
        caminho_full = os.path.join(self.diretorio_base, caminho_relativo)
        os.makedirs(os.path.dirname(caminho_full), exist_ok=True)

        conteudo = render_to_string(template_name, contexto)

        with open(caminho_full, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        self.log(f"Arquivo criado: {caminho_relativo}")

    def _gerar_docker(self):
        self.log("🐳 Criando arquivos do ambiente Docker...")
        ctx = {
            'sistema': self.sistema,
            'nome_projeto': self.nome_projeto
        }

        self._escrever_arquivo('Dockerfile', 'gerador/snippets/dockerfile.txt', ctx)
        self._escrever_arquivo('docker-compose.yml', 'gerador/snippets/docker_compose.txt', ctx)
        self._escrever_arquivo('.dockerignore', 'gerador/snippets/dockerignore.txt', ctx)

    def _gerar_modulo(self, modulo):
        app_name = slugify(modulo.nome).replace('-', '_')
        entidades = modulo.entidades.all()

        imports_por_app = {}

        for entidade in entidades:
            for campo in entidade.campos.all():
                tipo_str = str(campo.tipo).strip()
                es_relacional = tipo_str in ['ForeignKey', 'OneToOneField', 'ManyToManyField']
                setattr(campo, 'eh_relacional', es_relacional)

                if es_relacional and campo.entidade_relacionada:
                    nome_classe = str(campo.entidade_relacionada.nome).replace(" ", "").title()
                    setattr(campo, 'classe_relacionada', nome_classe)

                    app_pai = slugify(campo.entidade_relacionada.modulo.nome).replace('-', '_')
                    if app_pai != app_name:
                        if app_pai not in imports_por_app:
                            imports_por_app[app_pai] = set()
                        imports_por_app[app_pai].add(nome_classe)
                else:
                    setattr(campo, 'classe_relacionada', "")

        ctx = {
            'sistema': self.sistema,
            'app_name': app_name,
            'entidades': entidades,
            'imports_por_app': {k: sorted(list(v)) for k, v in imports_por_app.items()},
            'nome_projeto': self.nome_projeto
        }

        self._escrever_arquivo(f"{app_name}/__init__.py", 'gerador/snippets/init.txt', ctx)
        self._escrever_arquivo(f"{app_name}/models.py", 'gerador/snippets/models.txt', ctx)
        self._escrever_arquivo(f"{app_name}/migrations/__init__.py", 'gerador/snippets/init.txt', ctx)
        self._escrever_arquivo(f"{app_name}/forms.py", 'gerador/snippets/forms.txt', ctx)
        self._escrever_arquivo(f"{app_name}/views.py", 'gerador/snippets/views.txt', ctx)
        self._escrever_arquivo(f"{app_name}/urls.py", 'gerador/snippets/urls_app.txt', ctx)
        self._escrever_arquivo(f"{app_name}/admin.py", 'gerador/snippets/admin.txt', ctx)
        self._escrever_arquivo(f"{app_name}/apps.py", 'gerador/snippets/apps_config.txt', ctx)
        self._escrever_arquivo('templates/registration/login.html', 'gerador/snippets/login_html.txt', ctx)

        for entidade in entidades:
            ent_ctx = {**ctx, 'entidade': entidade, 'entidade_nome_lower': entidade.nome.lower()}
            base_t = f"{app_name}/templates/{app_name}"
            self._escrever_arquivo(f"{base_t}/{entidade.nome.lower()}_list.html", 'gerador/snippets/html_list.txt', ent_ctx)
            self._escrever_arquivo(f"{base_t}/{entidade.nome.lower()}_form.html", 'gerador/snippets/html_form.txt', ent_ctx)
            self._escrever_arquivo(f"{base_t}/{entidade.nome.lower()}_confirm_delete.html", 'gerador/snippets/html_delete.txt', ent_ctx)

    def _gerar_core(self):
        ctx = {'sistema': self.sistema, 'nome_projeto': self.nome_projeto}
        self._escrever_arquivo('manage.py', 'gerador/snippets/manage.txt', ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/__init__.py", 'gerador/snippets/init.txt', ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/settings.py", 'gerador/snippets/settings.txt', ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/urls.py", 'gerador/snippets/urls_root.txt', ctx)
        self._escrever_arquivo(f"{self.nome_projeto}/wsgi.py", 'gerador/snippets/wsgi.txt', ctx)

    def _gerar_templates_globais(self):
        modulos = list(self.sistema.modulos.prefetch_related('entidades'))
        for modulo in modulos:
            modulo.app_name = slugify(modulo.nome).replace('-', '_')

        ctx = {
            'sistema': self.sistema,
            'modulos': modulos,
        }
        # base_html.txt is the single canonical generator template. Keeping one
        # source avoids divergent generated contracts between base_html.txt and
        # base_html_v2.txt.
        self._escrever_arquivo('templates/base.html', 'gerador/snippets/base_html.txt', ctx)
        self._escrever_arquivo('templates/index.html', 'gerador/snippets/index_html.txt', ctx)
