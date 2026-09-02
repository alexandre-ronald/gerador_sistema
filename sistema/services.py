import ast
import json
import keyword
import os
import re
import shutil
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.utils.text import slugify

from .business_rules import normalize_business_rules_config
from .crud_designer import normalize_crud_config
from .form_designer import normalize_form_config
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

    def _draft_structure(self):
        versao = self.sistema.versoes.filter(numero=0).first()
        return versao.estrutura_json if versao and isinstance(versao.estrutura_json, dict) else {}

    def _dashboard_config(self):
        dashboard = self._draft_structure().get("dashboard")
        if isinstance(dashboard, dict):
            from .builder_contracts import normalize_dashboard_config
            return normalize_dashboard_config(dashboard)
        return {"enabled": False, "title": "Dashboard", "layout": "12-column", "refresh_seconds": 0, "widgets": []}

    def _forms_config(self):
        forms = self._draft_structure().get("forms"); return forms if isinstance(forms, dict) else {}

    def _cruds_config(self):
        cruds = self._draft_structure().get("cruds"); return cruds if isinstance(cruds, dict) else {}

    def _business_rules_config(self):
        rules = self._draft_structure().get("business_rules"); return rules if isinstance(rules, dict) else {}

    def _prepare_form_generation(self, entidade, forms_config):
        saved_config = forms_config.get(entidade.nome); has_saved_config = isinstance(saved_config, dict)
        metadata = {"name": entidade.nome, "label": entidade.nome, "fields": [{"name": c.nome, "label": c.verbose_name or c.nome, "type": c.tipo, "help_text": c.help_text or "", "editable": True} for c in entidade.campos_geracao]}
        config = normalize_form_config(entidade.nome, metadata, saved_config); source_fields = {c.nome: c for c in entidade.campos_geracao}; generated_fields = []
        for item in config["fields"]:
            source = source_fields.get(item["name"])
            if not source: continue
            field = SimpleNamespace(**item); field.codigo_nome = source.codigo_nome; field.tipo = source.tipo; generated_fields.append(field)
        entidade.form_designer_ready = has_saved_config; entidade.form_title = config["title"]; entidade.form_fields_all = generated_fields; entidade.form_fields = [f for f in generated_fields if f.visible]
        sections = []; general_fields = [f for f in entidade.form_fields if not f.section]
        if general_fields: sections.append(SimpleNamespace(id="", title="", description="", order=-1, fields=general_fields, is_general=True))
        for item in config["sections"]:
            section_fields = [f for f in entidade.form_fields if f.section == item["id"]]
            if section_fields: sections.append(SimpleNamespace(**item, fields=section_fields, is_general=False))
        entidade.form_sections = sections

    def _prepare_crud_generation(self, entidade, cruds_config):
        saved_config = cruds_config.get(entidade.nome); has_saved_config = isinstance(saved_config, dict)
        metadata = {"name": entidade.nome, "label": entidade.nome, "verbose_name_plural": entidade.nome_plural or entidade.nome, "fields": [{"name": c.nome, "label": c.verbose_name or c.nome, "type": c.tipo} for c in entidade.campos_geracao]}
        config = normalize_crud_config(entidade.nome, metadata, saved_config); source_fields = {c.nome: c for c in entidade.campos_geracao}; columns = []
        for item in config["columns"]:
            source = source_fields.get(item["field"])
            if not source: continue
            column = SimpleNamespace(**item); column.codigo_nome = source.codigo_nome; column.tipo = source.tipo; columns.append(column)
        search_fields = [source_fields[n].codigo_nome for n in config["search"]["fields"] if n in source_fields]; filters = []
        for item in config["filters"]:
            source = source_fields.get(item["field"])
            if not source: continue
            f = SimpleNamespace(**item); f.codigo_nome = source.codigo_nome; f.param = f"filter_{source.codigo_nome}"; f.tipo_campo = source.tipo; filters.append(f)
        default_order = config["default_order"]; generated_default_order = ""
        if default_order:
            descending = default_order.startswith("-"); original = default_order[1:] if descending else default_order; source = source_fields.get(original)
            if source: generated_default_order = f"-{source.codigo_nome}" if descending else source.codigo_nome
        entidade.crud_designer_ready = has_saved_config; entidade.crud_title = config["title"]; entidade.crud_page_size = config["page_size"]; entidade.crud_default_order = generated_default_order; entidade.crud_columns = columns; entidade.crud_visible_columns = [c for c in columns if c.visible]; entidade.crud_sortable_fields = [c.codigo_nome for c in columns if c.sortable]; entidade.crud_search_enabled = config["search"]["enabled"]; entidade.crud_search_fields = search_fields; entidade.crud_search_placeholder = config["search"]["placeholder"]; entidade.crud_filters = filters; entidade.crud_actions = SimpleNamespace(**config["actions"])

    def _prepare_business_rules_generation(self, entidade, rules_config):
        saved = rules_config.get(entidade.nome); has_saved = isinstance(saved, dict)
        metadata = {"name": entidade.nome, "label": entidade.nome, "fields": [{"name": c.nome, "label": c.verbose_name or c.nome, "type": c.tipo, "editable": True} for c in entidade.campos_geracao]}
        config = normalize_business_rules_config(entidade.nome, metadata, saved, strict=True) if has_saved else {"rules": []}; source_fields = {c.nome: c for c in entidade.campos_geracao}; generated_rules = []
        for item in config["rules"]:
            rule = dict(item); conditions = []; actions = []
            for condition in item["conditions"]:
                c = dict(condition); c["field"] = source_fields[c["field"]].codigo_nome
                if c.get("value_source") == "field": c["value"] = source_fields[c["value"]].codigo_nome
                conditions.append(c)
            for action in item["actions"]:
                a = dict(action)
                if a.get("field"): a["field"] = source_fields[a["field"]].codigo_nome
                if a.get("source_field"): a["source_field"] = source_fields[a["source_field"]].codigo_nome
                actions.append(a)
            rule["conditions"] = conditions; rule["actions"] = actions; generated_rules.append(rule)
        entidade.business_rules_ready = bool(generated_rules); entidade.business_rules = generated_rules

    def _prepare_context(self):
        modulos = list(self.sistema.modulos.prefetch_related("entidades__campos")); app_names = {}; dashboard = self._dashboard_config(); forms_config = self._forms_config(); cruds_config = self._cruds_config(); rules_config = self._business_rules_config()
        for widget in dashboard.get("widgets", []): widget["grid_column_start"] = int(widget.get("x", 0)) + 1; widget["grid_row_start"] = int(widget.get("y", 0)) + 1
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
                    if campo.codigo_nome in field_names: raise ValueError(f"Campos '{field_names[campo.codigo_nome]}' e '{campo.nome}' em '{entidade.nome}' geram o mesmo identificador '{campo.codigo_nome}'. Renomeie um deles.")
                    field_names[campo.codigo_nome] = campo.nome; campo.verbose_nome = campo.verbose_name or campo.nome; campo.default_python = self._python_default(campo.default_value)
                    if campo.eh_relacional and campo.entidade_relacionada: campo.classe_relacionada = self._class_name(campo.entidade_relacionada.nome); campo.app_relacionada = self._python_identifier(campo.entidade_relacionada.modulo.nome, "app")
                    else: campo.classe_relacionada = ""; campo.app_relacionada = ""
                self._prepare_form_generation(entidade, forms_config); self._prepare_crud_generation(entidade, cruds_config); self._prepare_business_rules_generation(entidade, rules_config)
        return {"sistema": self.sistema, "nome_projeto": self.nome_projeto, "modulos": modulos, "dashboard": dashboard, "dashboard_json": json.dumps(dashboard.get("widgets", []), ensure_ascii=False), "forms": forms_config, "cruds": cruds_config, "business_rules": rules_config}

    def _registrar_versao(self):
        ultimo = self.sistema.versoes.order_by("-numero").first(); numero = (ultimo.numero if ultimo else 0) + 1; estrutura = serialize_system_structure(self.sistema); self.versao_gerada = VersaoGeracao.objects.create(sistema=self.sistema, numero=numero, descricao=f"Geração automática v{numero}", estrutura_json=estrutura); self.log(f"🗂️ Versão de geração v{numero} registrada")

    def gerar_projeto_completo(self):
        if not self.diretorio_base: raise ValueError("Defina a pasta de destino antes de gerar o sistema.")
        try:
            if os.path.isdir(self.diretorio_base): shutil.rmtree(self.diretorio_base)
            os.makedirs(self.diretorio_base, exist_ok=True); self.log("🧹 Diretório de geração limpo antes da compilação"); ctx = self._prepare_context(); self._gerar_core(ctx)
            for modulo in ctx["modulos"]: self._gerar_modulo(modulo, ctx)
            self._gerar_templates_globais(ctx); self.log("🔎 Validando o projeto gerado antes de liberar a geração..."); resultado = validate_generated_runtime(self.diretorio_base)
            for mensagem in resultado.get("messages", []): self.log(mensagem)
            for aviso in resultado.get("warnings", []): self.log(f"⚠️ {aviso}")
            self.log(f"✅ Validação concluída: {resultado.get('checked', 0)} itens verificados")
            if self.sistema.gerar_docker: self._gerar_docker()
            self._registrar_versao(); self.log("✅ Geração concluída com sucesso!"); return self.logs
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
        for path, template in (("manage.py", "manage.txt"), (f"{self.nome_projeto}/__init__.py", "init.txt"), (f"{self.nome_projeto}/settings.py", "settings.txt"), (f"{self.nome_projeto}/urls.py", "urls_root_v2.txt"), (f"{self.nome_projeto}/wsgi.py", "wsgi.txt"), (f"{self.nome_projeto}/context_processors.py", "navigation_context.txt"), (f"{self.nome_projeto}/dashboard_data.py", "dashboard_data_views.txt")): self._escrever_arquivo(path, f"gerador/snippets/{template}", ctx)
        self._gerar_requirements(); os.makedirs(os.path.join(self.diretorio_base, "static"), exist_ok=True); os.makedirs(os.path.join(self.diretorio_base, "media"), exist_ok=True); self.log("✅ Diretórios static/ e media/ preparados")

    def _gerar_modulo(self, modulo, ctx):
        local_ctx = {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud, "imports_por_app": {}}
        for path, template in ((f"{modulo.app_name}/__init__.py", "init.txt"), (f"{modulo.app_name}/models.py", "models.txt"), (f"{modulo.app_name}/migrations/__init__.py", "init.txt"), (f"{modulo.app_name}/forms.py", "forms_v2.txt"), (f"{modulo.app_name}/business_rules.py", "business_rules_runtime.txt"), (f"{modulo.app_name}/views.py", "views.txt"), (f"{modulo.app_name}/urls.py", "urls_app_v2.txt"), (f"{modulo.app_name}/admin.py", "admin_v2.txt"), (f"{modulo.app_name}/apps.py", "apps_config.txt")): self._escrever_arquivo(path, f"gerador/snippets/{template}", local_ctx)
        for entidade in modulo.entidades_crud:
            ent_ctx = {**local_ctx, "entidade": entidade}; base_t = f"{modulo.app_name}/templates/{modulo.app_name}"
            for suffix, template in (("list", "html_list.txt"), ("form", "html_form.txt"), ("confirm_delete", "html_delete.txt")): self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_{suffix}.html", f"gerador/snippets/{template}", ent_ctx)
            if entidade.crud_designer_ready and entidade.crud_actions.view: self._escrever_arquivo(f"{base_t}/{entidade.codigo_nome}_detail.html", "gerador/snippets/html_detail.txt", ent_ctx)

    def _gerar_templates_globais(self, ctx):
        self._escrever_arquivo("templates/base.html", "gerador/snippets/base_html.txt", ctx); self._escrever_arquivo("templates/home.html", "gerador/snippets/home_html.txt", ctx); self._escrever_arquivo("templates/registration/login.html", "gerador/snippets/login_html.txt", ctx); self._escrever_arquivo("templates/dashboard.html", "gerador/snippets/dashboard_html.txt", ctx)

    def _gerar_docker(self):
        self._escrever_arquivo("Dockerfile", "gerador/snippets/dockerfile.txt", {"sistema": self.sistema, "nome_projeto": self.nome_projeto}); self._escrever_arquivo("docker-compose.yml", "gerador/snippets/docker_compose.txt", {"sistema": self.sistema, "nome_projeto": self.nome_projeto}); self._escrever_arquivo(".env.example", "gerador/snippets/env_example.txt", {"sistema": self.sistema})
