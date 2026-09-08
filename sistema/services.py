import ast
import json
import keyword
import os
import re
import shutil
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.utils.text import slugify

from .advanced_page_generation import prepare_advanced_pages_generation
from .api_designer import normalize_api_config
from .business_rules import normalize_business_rules_config
from .crud_designer import normalize_crud_config
from .form_designer import normalize_form_config
from .integration_center import normalize_integrations_config
from .models import Sistema, VersaoGeracao
from .runtime_validation import validate_generated_runtime
from .structure_service import serialize_system_structure
from .workspace_semantics import validate_workspace_destinations


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

    def _notifications_config(self):
        raw = self._draft_structure().get("notifications")
        if not isinstance(raw, dict): return {"enabled": False, "entities": {}}
        entities = {}; enabled = False
        for entity_name, rules in raw.items():
            if not isinstance(rules, list): continue
            normalized_rules = []
            for rule in rules:
                if not isinstance(rule, dict): continue
                item = dict(rule); normalized_rules.append(item)
                if item.get("enabled", True) is True: enabled = True
            entities[str(entity_name)] = normalized_rules
        return {"enabled": enabled, "entities": entities}

    def _integrations_config(self):
        integrations = self._draft_structure().get("integrations")
        if not isinstance(integrations, dict): return {"enabled": False, "items": []}
        return normalize_integrations_config(integrations, strict=True)

    def _api_config(self):
        structure = self._draft_structure(); raw = structure.get("api")
        if not isinstance(raw, dict): return {"enabled": False, "prefix": "api", "version": "v1", "authentication": "session_basic", "entities": {}}
        workflows = structure.get("workflows") if isinstance(structure.get("workflows"), dict) else {}; metadata = []
        for modulo in self.sistema.modulos.prefetch_related("entidades__campos"):
            for entidade in modulo.entidades.all():
                workflow = workflows.get(entidade.nome) if isinstance(workflows.get(entidade.nome), dict) else {}
                metadata.append({"name": entidade.nome,"label": entidade.nome,"api_eligible": bool(entidade.gerar_endpoints_api),"workflow_state_field": str(workflow.get("state_field") or "") if workflow.get("enabled") else "","fields": [{"name": c.nome,"label": c.verbose_name or c.nome,"type": c.tipo,"editable": True} for c in entidade.campos.all()]})
        return normalize_api_config(self.sistema.gerar_api_rest, metadata, raw, strict=True)

    def _prepare_form_generation(self, entidade, forms_config):
        saved_config = forms_config.get(entidade.nome); has_saved_config = isinstance(saved_config, dict); metadata = {"name": entidade.nome,"label": entidade.nome,"fields": [{"name": c.nome,"label": c.verbose_name or c.nome,"type": c.tipo,"help_text": c.help_text or "","editable": True} for c in entidade.campos_geracao]}; config = normalize_form_config(entidade.nome, metadata, saved_config); source_fields = {c.nome: c for c in entidade.campos_geracao}; generated_fields = []
        for item in config["fields"]:
            source = source_fields.get(item["name"])
            if not source: continue
            field = SimpleNamespace(**item); field.codigo_nome = source.codigo_nome; field.tipo = source.tipo; generated_fields.append(field)
        entidade.form_designer_ready = has_saved_config; entidade.form_title = config["title"]; entidade.form_fields_all = generated_fields; entidade.form_fields = [f for f in generated_fields if f.visible]; sections = []; general_fields = [f for f in entidade.form_fields if not f.section]
        if general_fields: sections.append(SimpleNamespace(id="", title="", description="", order=-1, fields=general_fields, is_general=True))
        for item in config["sections"]:
            section_fields = [f for f in entidade.form_fields if f.section == item["id"]]
            if section_fields: sections.append(SimpleNamespace(**item, fields=section_fields, is_general=False))
        entidade.form_sections = sections

    def _prepare_crud_generation(self, entidade, cruds_config):
        saved_config = cruds_config.get(entidade.nome); has_saved_config = isinstance(saved_config, dict); metadata = {"name": entidade.nome,"label": entidade.nome,"verbose_name_plural": entidade.nome_plural or entidade.nome,"fields": [{"name": c.nome,"label": c.verbose_name or c.nome,"type": c.tipo} for c in entidade.campos_geracao]}; config = normalize_crud_config(entidade.nome, metadata, saved_config); source_fields = {c.nome: c for c in entidade.campos_geracao}; columns = []
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
        saved = rules_config.get(entidade.nome); has_saved = isinstance(saved, dict); metadata = {"name": entidade.nome,"label": entidade.nome,"fields": [{"name": c.nome,"label": c.verbose_name or c.nome,"type": c.tipo,"editable": True} for c in entidade.campos_geracao]}; config = normalize_business_rules_config(entidade.nome, metadata, saved, strict=True) if has_saved else {"rules": []}; source_fields = {c.nome: c for c in entidade.campos_geracao}; generated_rules = []
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

    def _prepare_api_generation(self, entidade, api_config, workflows):
        saved = (api_config.get("entities") or {}).get(entidade.nome); entidade.api_enabled = bool(api_config.get("enabled") and isinstance(saved, dict) and saved.get("enabled"))
        if not entidade.api_enabled: return
        source_fields = {c.nome: c for c in entidade.campos_geracao}; code = lambda name: "id" if name == "id" else source_fields[name].codigo_nome; entidade.api_endpoint = saved["endpoint"]; entidade.api_operations = SimpleNamespace(**saved["operations"]); methods = {"head", "options"}
        if saved["operations"]["list"] or saved["operations"]["retrieve"]: methods.add("get")
        if saved["operations"]["create"]: methods.add("post")
        if saved["operations"]["update"]: methods.add("put")
        if saved["operations"]["partial_update"]: methods.add("patch")
        if saved["operations"]["destroy"]: methods.add("delete")
        entidade.api_http_methods = sorted(methods); entidade.api_fields = [code(n) for n in saved["fields"]]; entidade.api_read_only_fields = [code(n) for n in saved["read_only_fields"]]; entidade.api_search_fields = [code(n) for n in saved["search_fields"]]; entidade.api_ordering_fields = [code(n) for n in saved["ordering_fields"]]; entidade.api_default_ordering = [("-" if n.startswith("-") else "") + code(n[1:] if n.startswith("-") else n) for n in saved["default_ordering"]]; entidade.api_page_size = saved["page_size"]; workflow = workflows.get(entidade.nome) if isinstance(workflows.get(entidade.nome), dict) else {}; entidade.api_has_workflow = bool(workflow.get("enabled"))

    def _prepare_context(self):
        modulos = list(self.sistema.modulos.prefetch_related("entidades__campos")); app_names = {}; dashboard = self._dashboard_config(); forms_config = self._forms_config(); cruds_config = self._cruds_config(); rules_config = self._business_rules_config(); api_config = self._api_config(); integrations_config = self._integrations_config(); notifications_config = self._notifications_config(); structure = self._draft_structure(); workflows = structure.get("workflows") if isinstance(structure.get("workflows"), dict) else {}
        for widget in dashboard.get("widgets", []): widget["grid_column_start"] = int(widget.get("x", 0)) + 1; widget["grid_row_start"] = int(widget.get("y", 0)) + 1
        all_entities = []
        for modulo in modulos:
            modulo.app_name = self._python_identifier(modulo.nome, "app")
            if notifications_config["enabled"] and modulo.app_name == "djangoforge_notifications": raise ValueError("O nome de módulo 'djangoforge_notifications' é reservado para a Central de Notificações.")
            if modulo.app_name in app_names: raise ValueError(f"Módulos '{app_names[modulo.app_name]}' e '{modulo.nome}' geram o mesmo app Python '{modulo.app_name}'. Renomeie um deles.")
            app_names[modulo.app_name] = modulo.nome; modulo.entidades_geracao = list(modulo.entidades.all()); modulo.entidades_crud = []; modulo.entidades_api = []; class_names = {}
            for entidade in modulo.entidades_geracao:
                entidade.codigo_nome = self._python_identifier(entidade.nome, "entidade"); entidade.classe_nome = self._class_name(entidade.nome)
                if entidade.classe_nome in class_names: raise ValueError(f"Entidades '{class_names[entidade.classe_nome]}' e '{entidade.nome}' no módulo '{modulo.nome}' geram a mesma classe '{entidade.classe_nome}'. Renomeie um deles.")
                class_names[entidade.classe_nome] = entidade.nome; entidade.campos_geracao = list(entidade.campos.all()); all_entities.append(entidade)
                if entidade.gerar_crud_views: modulo.entidades_crud.append(entidade)
                field_names = {}
                for campo in entidade.campos_geracao:
                    campo.codigo_nome = self._python_identifier(campo.nome, "campo")
                    if campo.codigo_nome in field_names: raise ValueError(f"Campos '{field_names[campo.codigo_nome]}' e '{campo.nome}' em '{entidade.nome}' geram o mesmo identificador '{campo.codigo_nome}'. Renomeie um deles.")
                    field_names[campo.codigo_nome] = campo.nome; campo.verbose_nome = campo.verbose_name or campo.nome; campo.default_python = self._python_default(campo.default_value)
                    if campo.eh_relacional and campo.entidade_relacionada: campo.classe_relacionada = self._class_name(campo.entidade_relacionada.nome); campo.app_relacionada = self._python_identifier(campo.entidade_relacionada.modulo.nome, "app")
                    else: campo.classe_relacionada = ""; campo.app_relacionada = ""
                self._prepare_form_generation(entidade, forms_config); self._prepare_crud_generation(entidade, cruds_config); self._prepare_business_rules_generation(entidade, rules_config); self._prepare_api_generation(entidade, api_config, workflows)
                if entidade.api_enabled: modulo.entidades_api.append(entidade)
        advanced_pages = prepare_advanced_pages_generation(structure.get("advanced_pages"), entities=all_entities)
        workspaces = validate_workspace_destinations(structure.get("workspaces"), structure, entities=all_entities)
        return {"sistema": self.sistema,"nome_projeto": self.nome_projeto,"modulos": modulos,"dashboard": dashboard,"dashboard_json": json.dumps(dashboard.get("widgets", []), ensure_ascii=False),"forms": forms_config,"cruds": cruds_config,"business_rules": rules_config,"api": api_config,"integrations": integrations_config,"integrations_python": repr(integrations_config),"notifications": notifications_config,"advanced_pages": advanced_pages,"workspaces": workspaces,"workspaces_python": repr(workspaces)}

    def _registrar_versao(self):
        ultimo = self.sistema.versoes.order_by("-numero").first(); numero = (ultimo.numero if ultimo else 0) + 1; estrutura = serialize_system_structure(self.sistema); self.versao_gerada = VersaoGeracao.objects.create(sistema=self.sistema, numero=numero, descricao=f"Geração automática v{numero}", estrutura_json=estrutura); self.log(f"🗂️ Versão de geração v{numero} registrada.")

    def gerar(self):
        try:
            self.log("🚀 Iniciando geração..."); self._registrar_versao(); context = self._prepare_context()
            if os.path.exists(self.diretorio_base): shutil.rmtree(self.diretorio_base)
            os.makedirs(self.diretorio_base); self._gerar_estrutura(context); self._gerar_apps(context); self._gerar_templates(context); self._gerar_arquivos_raiz(context); self._gerar_docker(context)
            validation = validate_generated_runtime(self.diretorio_base)
            if not validation.ok:
                details = "; ".join(validation.errors[:5]); raise RuntimeError(f"Validação do runtime gerado falhou: {details}")
            self.log("🔎 Runtime gerado validado com sucesso."); self.log("✅ Sistema gerado com sucesso!"); return True
        except Exception as e: self.log(f"❌ Erro: {str(e)}"); return False

    def _write(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "w", encoding="utf-8").write(content)

    def _render(self, template, context): return render_to_string(f"gerador/snippets/{template}", context)

    def _gerar_estrutura(self, context):
        p = os.path.join(self.diretorio_base, self.nome_projeto); os.makedirs(p, exist_ok=True)
        self._write(os.path.join(p, "__init__.py"), "")
        self._write(os.path.join(p, "settings.py"), self._render("settings.txt", context)); self._write(os.path.join(p, "urls.py"), self._render("urls_projeto.txt", context)); self._write(os.path.join(p, "views.py"), self._render("project_views.txt", context)); self._write(os.path.join(p, "navigation.py"), self._render("navigation_context.txt", context)); self._write(os.path.join(p, "advanced_pages.py"), self._render("advanced_pages_runtime.txt", context)); self._write(os.path.join(p, "wsgi.py"), self._render("wsgi.txt", context))

    def _gerar_apps(self, context):
        for modulo in context["modulos"]:
            app_dir = os.path.join(self.diretorio_base, modulo.app_name); os.makedirs(os.path.join(app_dir, "migrations"), exist_ok=True); self._write(os.path.join(app_dir, "__init__.py"), ""); self._write(os.path.join(app_dir, "migrations", "__init__.py"), ""); ctx = {**context, "modulo": modulo}
            self._write(os.path.join(app_dir, "apps.py"), self._render("apps_config.txt", ctx)); self._write(os.path.join(app_dir, "models.py"), self._render("models_v2.txt", ctx)); self._write(os.path.join(app_dir, "forms.py"), self._render("forms_v2.txt", ctx)); self._write(os.path.join(app_dir, "business_rules.py"), self._render("business_rules_runtime.txt", ctx)); self._write(os.path.join(app_dir, "views.py"), self._render("views_v2.txt", ctx)); self._write(os.path.join(app_dir, "urls.py"), self._render("urls_app.txt", ctx)); self._write(os.path.join(app_dir, "admin.py"), self._render("admin_v2.txt", ctx)); self._write(os.path.join(app_dir, "rbac.py"), self._render("rbac_runtime.txt", ctx))
            if modulo.entidades_api: self._write(os.path.join(app_dir, "serializers.py"), self._render("api_serializers.txt", ctx)); self._write(os.path.join(app_dir, "api_views.py"), self._render("api_views.txt", ctx)); self._write(os.path.join(app_dir, "api_urls.py"), self._render("api_urls.txt", ctx))
            templates_dir = os.path.join(app_dir, "templates", modulo.app_name); os.makedirs(templates_dir, exist_ok=True)
            for entidade in modulo.entidades_crud:
                ectx = {**ctx, "entidade": entidade}; self._write(os.path.join(templates_dir, f"{entidade.codigo_nome}_list.html"), self._render("html_list.txt", ectx)); self._write(os.path.join(templates_dir, f"{entidade.codigo_nome}_form.html"), self._render("html_form.txt", ectx)); self._write(os.path.join(templates_dir, f"{entidade.codigo_nome}_detail.html"), self._render("html_detail.txt", ectx)); self._write(os.path.join(templates_dir, f"{entidade.codigo_nome}_confirm_delete.html"), self._render("html_delete.txt", ectx))
                for report in getattr(entidade, "report_configs", []): self._write(os.path.join(templates_dir, f"{entidade.codigo_nome}_report_{report.id}.html"), self._render("html_report.txt", {**ectx, "report": report}))
        if context.get("notifications", {}).get("enabled"): self._gerar_notification_app(context)

    def _gerar_notification_app(self, context):
        app_dir = os.path.join(self.diretorio_base, "djangoforge_notifications"); os.makedirs(os.path.join(app_dir, "migrations"), exist_ok=True); self._write(os.path.join(app_dir, "__init__.py"), self._render("notification_init.txt", context)); self._write(os.path.join(app_dir, "apps.py"), self._render("notification_apps.txt", context)); self._write(os.path.join(app_dir, "models.py"), self._render("notification_models.txt", context)); self._write(os.path.join(app_dir, "views.py"), self._render("notification_views.txt", context)); self._write(os.path.join(app_dir, "urls.py"), self._render("notification_urls.txt", context)); self._write(os.path.join(app_dir, "admin.py"), self._render("notification_admin.txt", context)); self._write(os.path.join(app_dir, "migrations", "__init__.py"), ""); self._write(os.path.join(app_dir, "migrations", "0001_initial.py"), self._render("notification_migration_0001.txt", context)); templates_dir = os.path.join(app_dir, "templates", "djangoforge_notifications"); os.makedirs(templates_dir, exist_ok=True); self._write(os.path.join(templates_dir, "notification_list.html"), self._render("notification_list_html.txt", context))

    def _gerar_templates(self, context):
        t = os.path.join(self.diretorio_base, "templates"); os.makedirs(t, exist_ok=True); self._write(os.path.join(t, "base.html"), self._render("base_html.txt", context)); self._write(os.path.join(t, "index.html"), self._render("index_html.txt", context)); self._write(os.path.join(t, "home.html"), self._render("home_html.txt", context)); self._write(os.path.join(t, "dashboard.html"), self._render("dashboard_html.txt", context)); self._write(os.path.join(t, "advanced_page.html"), self._render("advanced_page_html.txt", context)); registration = os.path.join(t, "registration"); os.makedirs(registration, exist_ok=True); self._write(os.path.join(registration, "login.html"), self._render("login_html.txt", context)); self._write(os.path.join(registration, "profile.html"), self._render("profile_html.txt", context)); self._write(os.path.join(registration, "password_change_form.html"), self._render("password_change_form.txt", context)); self._write(os.path.join(registration, "password_change_done.html"), self._render("password_change_done.txt", context)); self._write(os.path.join(t, "users_list.html"), self._render("users_list.txt", context)); self._write(os.path.join(t, "user_form.html"), self._render("user_form.txt", context)); self._write(os.path.join(t, "roles_list.html"), self._render("roles_list.txt", context))

    def _gerar_arquivos_raiz(self, context):
        self._write(os.path.join(self.diretorio_base, "manage.py"), self._render("manage.txt", context)); self._write(os.path.join(self.diretorio_base, "requirements.txt"), self._render("requirements.txt", context)); self._write(os.path.join(self.diretorio_base, ".env.example"), self._render("env_example.txt", context)); self._write(os.path.join(self.diretorio_base, "README.md"), self._render("readme.txt", context)); self._write(os.path.join(self.diretorio_base, "integration_config.py"), self._render("integration_config.txt", context)); self._write(os.path.join(self.diretorio_base, "integration_client.py"), self._render("integration_client.txt", context)); self._write(os.path.join(self.diretorio_base, "integration_triggers.py"), self._render("integration_triggers.txt", context)); self._write(os.path.join(self.diretorio_base, "integration_tasks.py"), self._render("integration_tasks.txt", context)); self._write(os.path.join(self.diretorio_base, "integration_runtime.py"), self._render("integration_runtime.txt", context))

    def _gerar_docker(self, context):
        if not self.sistema.gerar_docker: return
        self._write(os.path.join(self.diretorio_base, "Dockerfile"), self._render("dockerfile.txt", context)); self._write(os.path.join(self.diretorio_base, "docker-compose.yml"), self._render("docker_compose.txt", context)); self._write(os.path.join(self.diretorio_base, ".dockerignore"), self._render("dockerignore.txt", context))
