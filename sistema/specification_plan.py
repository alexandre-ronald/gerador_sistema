from dataclasses import dataclass

from .specification import SystemSpec


@dataclass(frozen=True)
class GenerationArtifact:
    path: str
    kind: str
    module: str | None = None
    entity: str | None = None


class CompilationPlan:
    """Deterministic list of artifacts that a SystemSpec must generate."""
    def __init__(self, specification: SystemSpec): self.specification = specification

    def artifacts(self) -> tuple[GenerationArtifact, ...]:
        spec=self.specification
        result=[GenerationArtifact("manage.py","core"),GenerationArtifact(f"{spec.technical_name}/__init__.py","core"),GenerationArtifact(f"{spec.technical_name}/settings.py","core"),GenerationArtifact(f"{spec.technical_name}/urls.py","core"),GenerationArtifact(f"{spec.technical_name}/wsgi.py","core"),GenerationArtifact("templates/base.html","template"),GenerationArtifact("templates/index.html","template"),GenerationArtifact("templates/registration/login.html","template"),GenerationArtifact("requirements.txt","package"),GenerationArtifact("README.md","package"),GenerationArtifact(".gitignore","package"),GenerationArtifact("static/.gitkeep","static")]
        for module in spec.modules:
            app=module.technical_name
            result.extend([GenerationArtifact(f"{app}/__init__.py","module",app),GenerationArtifact(f"{app}/models.py","module",app),GenerationArtifact(f"{app}/migrations/__init__.py","module",app),GenerationArtifact(f"{app}/forms.py","module",app),GenerationArtifact(f"{app}/views.py","module",app),GenerationArtifact(f"{app}/urls.py","module",app),GenerationArtifact(f"{app}/admin.py","module",app),GenerationArtifact(f"{app}/apps.py","module",app)])
            for entity in module.entities:
                base=f"{app}/templates/{app}"
                result.extend([GenerationArtifact(f"{base}/{entity.technical_name}_list.html","crud",app,entity.class_name),GenerationArtifact(f"{base}/{entity.technical_name}_detail.html","crud",app,entity.class_name),GenerationArtifact(f"{base}/{entity.technical_name}_form.html","crud",app,entity.class_name),GenerationArtifact(f"{base}/{entity.technical_name}_confirm_delete.html","crud",app,entity.class_name)])
        if spec.docker: result.extend([GenerationArtifact("Dockerfile","docker"),GenerationArtifact("docker-compose.yml","docker"),GenerationArtifact(".dockerignore","docker")])
        return tuple(result)

    def paths(self) -> tuple[str,...]: return tuple(item.path for item in self.artifacts())
