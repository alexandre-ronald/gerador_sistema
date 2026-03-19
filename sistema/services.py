import os
from django.template.loader import render_to_string
from django.conf import settings

class GeradorService:
    def __init__(self, sistema_id):
        from .models import Sistema, Modulo, Entidade
        self.sistema = Sistema.objects.get(id=sistema_id)
        self.base_path = self.sistema.caminho_geracao
        self.logs = []

    def registrar_log(self, mensagem):
        """Adiciona uma mensagem à lista de logs para o monitor do Wizard"""
        self.logs.append(mensagem)

    def _escrever_arquivo(self, caminho_relativo, template_name, contexto):
        """
        Renderiza um template e o salva no diretório de destino.
        caminho_relativo: ex: 'vendas/models.py'
        template_name: ex: 'gerador/snippets/models.txt'
        """
        # Define o caminho absoluto final
        caminho_completo = os.path.join(self.base_path, caminho_relativo)
        
        # Cria as pastas necessárias (ex: venv, templates/app, etc)
        os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
        
        # Renderiza o conteúdo usando o motor de templates do Django
        conteudo = render_to_string(template_name, contexto)
        
        with open(caminho_completo, "w", encoding="utf-8") as f:
            f.write(conteudo)
        
        self.registrar_log(f"✓ Arquivo gerado: {caminho_relativo}")

    def gerar_projeto_completo(self):
        """Executa a sequência lógica de geração para um sistema funcional"""
        self.registrar_log(f"🚀 Iniciando geração do sistema: {self.sistema.nome}")
        
        try:
            # 1. Estrutura de Pastas e Arquivos Base do Django
            self.registrar_log("⚙️ Configurando Core do Projeto...")
            self._gerar_core()

            # 2. Gerar cada Módulo (App) cadastrado
            for modulo in self.sistema.modulos.all():
                self.registrar_log(f"📦 Processando Módulo: {modulo.nome}")
                self._gerar_modulo(modulo)

            # 3. Gerar Templates Globais (Base.html, Login, etc)
            self.registrar_log("🎨 Gerando Layout e Autenticação...")
            self._gerar_templates_globais()

            self.registrar_log("✨ GERAÇÃO CONCLUÍDA COM SUCESSO!")
            self.registrar_log("👉 Próximos passos: criar venv, migrar e criar superuser.")
            
            return self.logs

        except Exception as e:
            self.registrar_log(f"❌ ERRO DURANTE A GERAÇÃO: {str(e)}")
            raise e

    def _gerar_core(self):
        """Gera settings.py, urls.py raiz e manage.py"""
        nome_projeto = self.sistema.nome.lower().replace(" ", "_")
        ctx = {'sistema': self.sistema, 'nome_projeto': nome_projeto}
        
        # Caminhos padrão do Django
        self._escrever_arquivo(f"{nome_projeto}/settings.py", 'gerador/snippets/settings.txt', ctx)
        self._escrever_arquivo(f"{nome_projeto}/urls.py", 'gerador/snippets/urls_root.txt', ctx)
        self._escrever_arquivo(f"{nome_projeto}/wsgi.py", 'gerador/snippets/wsgi.txt', ctx)
        self._escrever_arquivo(f"{nome_projeto}/__init__.py", 'gerador/snippets/init.txt', ctx)
        self._escrever_arquivo("manage.py", 'gerador/snippets/manage.txt', ctx)

    def _gerar_modulo(self, modulo):
        """Gera toda a estrutura interna de um App Django"""
        app_name = modulo.nome.lower()
        entidades = modulo.entidades.all()
        ctx = {'modulo': modulo, 'entidades': entidades, 'app_name': app_name}

        # Arquivos Python do App
        self._escrever_arquivo(f"{app_name}/models.py", 'gerador/snippets/models.txt', ctx)
        self._escrever_arquivo(f"{app_name}/views.py", 'gerador/snippets/views.txt', ctx)
        self._escrever_arquivo(f"{app_name}/urls.py", 'gerador/snippets/urls_app.txt', ctx)
        self._escrever_arquivo(f"{app_name}/forms.py", 'gerador/snippets/forms.txt', ctx)
        self._escrever_arquivo(f"{app_name}/admin.py", 'gerador/snippets/admin.txt', ctx)
        self._escrever_arquivo(f"{app_name}/apps.py", 'gerador/snippets/apps_config.txt', ctx)
        self._escrever_arquivo(f"{app_name}/__init__.py", 'gerador/snippets/init.txt', ctx)

        # Templates do App (CRUD)
        for entidade in entidades:
            ent_ctx = {'entidade': entidade, 'app_name': app_name}
            slug = entidade.nome.lower()
            self._escrever_arquivo(f"{app_name}/templates/{app_name}/{slug}_list.html", 'gerador/snippets/html_list.txt', ent_ctx)
            self._escrever_arquivo(f"{app_name}/templates/{app_name}/{slug}_form.html", 'gerador/snippets/html_form.txt', ent_ctx)
            self._escrever_arquivo(f"{app_name}/templates/{app_name}/{slug}_confirm_delete.html", 'gerador/snippets/html_delete.txt', ent_ctx)

    def _gerar_templates_globais(self):
        """Gera base.html, index.html e telas de login na raiz de templates"""
        ctx = {'sistema': self.sistema}
        self._escrever_arquivo("templates/base.html", 'gerador/snippets/base_html.txt', ctx)
        self._escrever_arquivo("templates/index.html", 'gerador/snippets/index_html.txt', ctx)
        self._escrever_arquivo("templates/registration/login.html", 'gerador/snippets/login_html.txt', ctx)