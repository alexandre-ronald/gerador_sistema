from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from django.template.loader import render_to_string

from .artifact_writer import ArtifactWriter
from .specification import EntitySpec, FieldSpec, SystemSpec, validate_specification_object
from .specification_plan import CompilationPlan, GenerationArtifact


@dataclass(frozen=True)
class CompilationResult:
    specification_fingerprint: str
    artifacts: tuple[str, ...]


class SpecificationCompiler:
    """Compile a canonical SystemSpec into Django source artifacts."""

    TEMPLATE_MAP = {
        "core": {
            "manage.py": "gerador/snippets/manage.txt",
            "settings.py": "gerador/snippets/settings.txt",
            "urls.py": "gerador/snippets/urls_root.txt",
            "wsgi.py": "gerador/snippets/wsgi.txt",
        },
        "template": {
            "templates/base.html": "gerador/snippets/base_html.txt",
            "templates/index.html": "gerador/snippets/index_html.txt",
            "templates/registration/login.html": "gerador/snippets/login_html.txt",
        },
    }

    def __init__(self, specification: SystemSpec, output_root: str | Path):
        self.specification = specification
        self.writer = ArtifactWriter(output_root)

    def compile(self) -> CompilationResult:
        validate_specification_object(self.specification)
        plan = CompilationPlan(self.specification)
        generated: list[str] = []

        for artifact in plan.artifacts():
            content = self._render(artifact)
            self.writer.write(artifact.path, content)
            generated.append(artifact.path)

        return CompilationResult(
            specification_fingerprint=self.specification.fingerprint,
            artifacts=tuple(generated),
        )

    def _render(self, artifact: GenerationArtifact) -> str:
        spec = self.specification
        if artifact.kind == "core":
            if artifact.path == "manage.py":
                template = self.TEMPLATE_MAP["core"][artifact.path]
                return render_to_string(template, {"sistema": self._system_context(), "nome_projeto": spec.technical_name})
            suffix = artifact.path.rsplit("/", 1)[-1]
            template = self.TEMPLATE_MAP["core"][suffix]
            return render_to_string(template, {"sistema": self._system_context(), "nome_projeto": spec.technical_name})

        if artifact.kind == "template":
            template = self.TEMPLATE_MAP["template"][artifact.path]
            return render_to_string(template, {"sistema": self._system_context(), "nome_projeto": spec.technical_name})

        if artifact.kind == "module":
            module = self._module(artifact.module)
            template = {
                "__init__.py": "gerador/snippets/init.txt",
                "models.py": "gerador/snippets/models.txt",
                "forms.py": "gerador/snippets/forms.txt",
                "views.py": "gerador/snippets/views.txt",
                "urls.py": "gerador/snippets/urls_app.txt",
                "admin.py": "gerador/snippets/admin.txt",
                "apps.py": "gerador/snippets/apps_config.txt",
            }.get(Path(artifact.path).name)
            if artifact.path.endswith("migrations/__init__.py"):
                template = "gerador/snippets/init.txt"
            if not template:
                raise ValueError(f"Artefato de módulo sem template: {artifact.path}")
            return render_to_string(template, self._module_context(module))

        if artifact.kind == "crud":
            module = self._module(artifact.module)
            entity = next(e for e in module.entities if e.class_name == artifact.entity)
            templates = {
                "_list.html": "gerador/snippets/html_list.txt",
                "_form.html": "gerador/snippets/html_form.txt",
                "_confirm_delete.html": "gerador/snippets/html_delete.txt",
            }
            filename = Path(artifact.path).name
            template = next((v for k, v in templates.items() if filename.endswith(k)), None)
            if not template:
                raise ValueError(f"Artefato CRUD sem template: {artifact.path}")
            return render_to_string(template, self._entity_context(module, entity))

        if artifact.kind == "docker":
            templates = {
                "Dockerfile": "gerador/snippets/dockerfile.txt",
                "docker-compose.yml": "gerador/snippets/docker_compose.txt",
                ".dockerignore": "gerador/snippets/dockerignore.txt",
            }
            template = templates[artifact.path]
            return render_to_string(template, {"sistema": self._system_context(), "nome_projeto": spec.technical_name})

        raise ValueError(f"Tipo de artefato desconhecido: {artifact.kind}")

    def _system_context(self):
        s = self.specification
        return SimpleNamespace(
            nome=s.name,
            slug=s.slug,
            descricao=s.description,
            banco_dados=s.database,
            tipo_menu=s.menu,
            usar_custom_user=s.custom_user,
            gerar_api_rest=s.rest_api,
            gerar_docker=s.docker,
            usar_auditoria=s.audit,
        )

    def _module(self, technical_name: str | None):
        if not technical_name:
            raise ValueError("Módulo obrigatório")
        return next(m for m in self.specification.modules if m.technical_name == technical_name)

    def _field(self, field: FieldSpec):
        return SimpleNamespace(
            nome=field.name,
            nome_tecnico=field.technical_name,
            tipo=field.type,
            null=field.null,
            blank=field.blank,
            unique=field.unique,
            default_repr=self._default_repr(field.default),
            max_length=field.max_length,
            max_digits=field.max_digits,
            decimal_places=field.decimal_places,
            upload_to=field.upload_to,
            on_delete=field.on_delete,
            related_name_str=field.related_name,
            verbose_name=field.verbose_name,
            help_text=field.help_text,
            entidade_relacionada=SimpleNamespace(
                nome=field.related_entity,
                classe_tecnica=field.related_entity,
                modulo=SimpleNamespace(nome=field.related_module or ""),
            ) if field.related_entity else None,
            classe_relacionada=field.related_entity or "",
        )

    def _entity(self, entity: EntitySpec):
        fields = [self._field(f) for f in entity.fields]
        return SimpleNamespace(
            nome=entity.name,
            nome_tecnico=entity.technical_name,
            classe_tecnica=entity.class_name,
            nome_plural=entity.plural_name,
            descricao=entity.description,
            gerar_admin=entity.generate_admin,
            gerar_crud_views=entity.generate_crud,
            gerar_endpoints_api=entity.generate_api,
            campos=SimpleNamespace(all=lambda: fields),
            campo_principal=fields[0] if fields else None,
        )

    def _module_context(self, module):
        entities = [self._entity(e) for e in module.entities]
        imports: dict[str, set[str]] = {}
        for entity in module.entities:
            for field in entity.fields:
                if field.related_entity and field.related_module and field.related_module != module.technical_name:
                    imports.setdefault(field.related_module, set()).add(field.related_entity)
        return {
            "sistema": self._system_context(),
            "app_name": module.technical_name,
            "entidades": entities,
            "imports_por_app": {k: sorted(v) for k, v in imports.items()},
            "nome_projeto": self.specification.technical_name,
        }

    def _entity_context(self, module, entity):
        ctx = self._module_context(module)
        current = self._entity(entity)
        return {**ctx, "entidade": current, "entidade_nome_lower": entity.technical_name}

    @staticmethod
    def _default_repr(value: str) -> str:
        value = (value or "").strip()
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
