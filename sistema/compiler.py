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
            self.writer.write(artifact.path, self._render(artifact))
            generated.append(artifact.path)
        return CompilationResult(self.specification.fingerprint, tuple(generated))

    def _render(self, artifact: GenerationArtifact) -> str:
        spec = self.specification
        context = {"sistema": self._system_context(), "nome_projeto": spec.technical_name}
        if artifact.kind == "core":
            template = self.TEMPLATE_MAP["core"][artifact.path if artifact.path == "manage.py" else Path(artifact.path).name]
            return render_to_string(template, context)
        if artifact.kind == "template":
            return render_to_string(self.TEMPLATE_MAP["template"][artifact.path], context)
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
            }.get(Path(artifact.path).name, "gerador/snippets/init.txt" if artifact.path.endswith("migrations/__init__.py") else None)
            if not template:
                raise ValueError(f"Artefato de módulo sem template: {artifact.path}")
            return render_to_string(template, self._module_context(module))
        if artifact.kind == "crud":
            module = self._module(artifact.module)
            entity = next(e for e in module.entities if e.class_name == artifact.entity)
            filename = Path(artifact.path).name
            template = next((value for suffix, value in {
                "_list.html": "gerador/snippets/html_list.txt",
                "_form.html": "gerador/snippets/html_form.txt",
                "_confirm_delete.html": "gerador/snippets/html_delete.txt",
            }.items() if filename.endswith(suffix)), None)
            if not template:
                raise ValueError(f"Artefato CRUD sem template: {artifact.path}")
            return render_to_string(template, self._entity_context(module, entity))
        if artifact.kind == "docker":
            template = {
                "Dockerfile": "gerador/snippets/dockerfile.txt",
                "docker-compose.yml": "gerador/snippets/docker_compose.txt",
                ".dockerignore": "gerador/snippets/dockerignore.txt",
            }[artifact.path]
            return render_to_string(template, context)
        raise ValueError(f"Tipo de artefato desconhecido: {artifact.kind}")

    def _system_context(self):
        s = self.specification
        modules = [SimpleNamespace(nome=m.technical_name) for m in s.modules]
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
            modulos=SimpleNamespace(all=lambda: modules),
        )

    def _module(self, technical_name: str | None):
        if not technical_name:
            raise ValueError("Módulo obrigatório")
        return next(m for m in self.specification.modules if m.technical_name == technical_name)

    def _field(self, field: FieldSpec):
        related = None
        if field.related_entity:
            related = SimpleNamespace(
                nome=field.related_entity,
                classe_tecnica=field.related_entity,
                modulo=SimpleNamespace(nome=field.related_module or ""),
            )
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
            entidade_relacionada=related,
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
        return {**self._module_context(module), "entidade": self._entity(entity), "entidade_nome_lower": entity.technical_name}

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
