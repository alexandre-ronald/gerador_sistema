from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from django.template.loader import render_to_string

from .specification import SystemSpec
from .specification_plan import CompilationPlan

class _Collection(list):
    def all(self): return self

@dataclass(frozen=True)
class CompiledFile:
    path: str
    content: str
    kind: str

class SpecificationCompiler:
    def __init__(self, specification: SystemSpec, template_renderer: Callable[[str, dict], str] | None = None):
        self.specification=specification; self.plan=CompilationPlan(specification); self._render_template=template_renderer or render_to_string
    def compile(self):
        contexts=self._build_contexts(); compiled=[]
        for artifact in self.plan.artifacts():
            if artifact.kind=="static": compiled.append(CompiledFile(artifact.path,"",artifact.kind)); continue
            context=contexts.get(artifact.path)
            if context is None: raise RuntimeError(f"Nenhum contexto de compilação para o artefato: {artifact.path}")
            compiled.append(CompiledFile(artifact.path,self._render_template(self._template_for(artifact),context),artifact.kind))
        return tuple(compiled)
    def write(self,output_directory):
        output=Path(output_directory).resolve(); output.mkdir(parents=True,exist_ok=True); compiled=self.compile(); expected={i.path for i in self.plan.artifacts()}
        for item in compiled:
            destination=(output/item.path).resolve()
            if output not in destination.parents: raise ValueError(f"Artefato fora do diretório de saída: {item.path}")
            destination.parent.mkdir(parents=True,exist_ok=True); destination.write_text(item.content,encoding="utf-8",newline="\n")
        if {i.path for i in compiled}!=expected: raise RuntimeError("O compilador não produziu exatamente o plano de compilação.")
        return tuple(compiled)
    def _template_for(self,artifact):
        mapping={"manage.py":"gerador/snippets/manage.txt","settings.py":"gerador/snippets/settings.txt","urls.py":"gerador/snippets/urls_root.txt","wsgi.py":"gerador/snippets/wsgi.txt","__init__.py":"gerador/snippets/init.txt","base.html":"gerador/snippets/base_html.txt","index.html":"gerador/snippets/index_html.txt","login.html":"gerador/snippets/login_html.txt","requirements.txt":"gerador/snippets/requirements.txt","README.md":"gerador/snippets/readme.md",".gitignore":"gerador/snippets/gitignore.txt","models.py":"gerador/snippets/models.txt","forms.py":"gerador/snippets/forms.txt","views.py":"gerador/snippets/views.txt","urls.py:module":"gerador/snippets/urls_app_gen0012.txt","admin.py":"gerador/snippets/admin.txt","apps.py":"gerador/snippets/apps_config.txt","_list.html":"gerador/snippets/html_list_gen0013.txt","_detail.html":"gerador/snippets/html_detail.txt","_form.html":"gerador/snippets/html_form.txt","_confirm_delete.html":"gerador/snippets/html_delete.txt","Dockerfile":"gerador/snippets/dockerfile.txt","docker-compose.yml":"gerador/snippets/docker_compose.txt",".dockerignore":"gerador/snippets/dockerignore.txt","auditoria_apps.txt":"gerador/snippets/auditoria_apps.txt","auditoria_models.txt":"gerador/snippets/auditoria_models.txt","auditoria_admin.txt":"gerador/snippets/auditoria_admin.txt","auditoria_middleware.txt":"gerador/snippets/auditoria_middleware.txt","auditoria_request_context.txt":"gerador/snippets/auditoria_request_context.txt","auditoria_signals.txt":"gerador/snippets/auditoria_signals.txt","0001_initial.py":"gerador/snippets/auditoria_migration.txt"}
        path,name=artifact.path,Path(artifact.path).name
        if artifact.kind=="audit":
            if path.endswith("/admin.py"): return mapping["auditoria_admin.txt"]
            if path.endswith("migrations/__init__.py"): return mapping["__init__.py"]
            return mapping.get(name, "gerador/snippets/init.txt")
        if artifact.kind=="module": return mapping["urls.py:module"] if name=="urls.py" else mapping[name]
        if artifact.kind=="crud":
            if name.endswith("_list.html"): return mapping["_list.html"]
            if name.endswith("_detail.html"): return mapping["_detail.html"]
            if name.endswith("_form.html"): return mapping["_form.html"]
            return mapping["_confirm_delete.html"]
        if artifact.kind in {"docker","package"}: return mapping[name]
        if path.startswith("templates/registration/"): return mapping["login.html"]
        if path.startswith("templates/"): return mapping[name]
        if name in mapping: return mapping[name]
        raise KeyError(f"Artefato sem template conhecido: {path}")
    def _build_contexts(self):
        spec=self.specification; system=self._system_adapter(spec); modules=_Collection(self._module_adapter(m) for m in spec.modules); contexts={}; core={"sistema":system,"modulos":modules,"nome_projeto":spec.technical_name}
        for artifact in self.plan.artifacts():
            if artifact.kind in {"core","template","docker","package","audit"}: contexts[artifact.path]=core
        for module in spec.modules:
            adapter=self._module_adapter(module); module_ctx={"sistema":system,"modulos":modules,"app_name":module.technical_name,"entidades":adapter.entidades,"nome_projeto":spec.technical_name,"modulo":adapter,"imports_por_app":{}}
            for artifact in self.plan.artifacts():
                if artifact.module!=module.technical_name: continue
                if artifact.kind=="module": contexts[artifact.path]=module_ctx
                elif artifact.kind=="crud":
                    entity=next((i for i in adapter.entidades if i.classe_tecnica==artifact.entity),None)
                    if entity is None: raise RuntimeError(f"Entidade não encontrada no plano: {artifact.entity}")
                    contexts[artifact.path]={**module_ctx,"entidade":entity}
        return contexts
    @staticmethod
    def _system_adapter(spec): return SimpleNamespace(nome=spec.name,nome_tecnico=spec.technical_name,descricao=spec.description,slug=spec.slug,banco_dados=spec.database,tipo_menu=spec.menu,usar_custom_user=spec.custom_user,gerar_api_rest=spec.rest_api,gerar_docker=spec.docker,usar_auditoria=spec.audit,modulos=_Collection(SimpleNamespace(nome=m.name,nome_tecnico=m.technical_name) for m in spec.modules))
    def _module_adapter(self,module): return SimpleNamespace(nome=module.name,nome_tecnico=module.technical_name,descricao=module.description,entidades=_Collection(self._entity_adapter(e) for e in module.entities))
    def _entity_adapter(self,entity):
        fields=_Collection(self._field_adapter(f) for f in entity.fields)
        return SimpleNamespace(nome=entity.name,nome_plural=entity.plural_name,descricao=entity.description,gerar_admin=entity.generate_admin,gerar_crud_views=entity.generate_crud,gerar_endpoints_api=entity.generate_api,classe_tecnica=entity.class_name,nome_tecnico=entity.technical_name,campos=fields,campo_principal=fields[0] if fields else None)
    def _field_adapter(self,field):
        related_entity=None
        if field.related_entity:
            for cm in self.specification.modules:
                for candidate in cm.entities:
                    if candidate.class_name==field.related_entity:
                        related_entity=SimpleNamespace(nome=candidate.name,nome_plural=candidate.plural_name,classe_tecnica=candidate.class_name,nome_tecnico=candidate.technical_name,modulo=SimpleNamespace(nome=cm.name,nome_tecnico=cm.technical_name)); break
                if related_entity: break
        return SimpleNamespace(nome=field.name,nome_tecnico=field.technical_name,tipo=field.type,null=field.null,blank=field.blank,unique=field.unique,default_value=field.default,default_repr=self._default_repr(field.default),max_length=field.max_length,max_digits=field.max_digits,decimal_places=field.decimal_places,upload_to=field.upload_to,entidade_relacionada=related_entity,classe_relacionada=field.related_entity or "",related_module=field.related_module or "",on_delete=field.on_delete,related_name=field.related_name,related_name_str=field.related_name,verbose_name=field.verbose_name,help_text=field.help_text,eh_relacional=field.type in {"ForeignKey","OneToOneField","ManyToManyField"})
    @staticmethod
    def _default_repr(value):
        value=str(value or "").strip()
        if not value:return ""
        if value.lower()=="true":return "True"
        if value.lower()=="false":return "False"
        if value.lower() in {"none","null"}:return "None"
        try: float(value); return value
        except ValueError:return repr(value)

class ArtifactWriter:
    def __init__(self,output_directory): self.output_directory=Path(output_directory).resolve()
    def write(self,artifacts):
        self.output_directory.mkdir(parents=True,exist_ok=True); written=[]
        for artifact in artifacts:
            destination=(self.output_directory/artifact.path).resolve()
            if self.output_directory not in destination.parents: raise ValueError(f"Artefato fora do diretório permitido: {artifact.path}")
            destination.parent.mkdir(parents=True,exist_ok=True); destination.write_text(artifact.content,encoding="utf-8",newline="\n"); written.append(artifact.path)
        return tuple(written)

def compile_specification(specification): return SpecificationCompiler(specification).compile()
def write_compiled_specification(specification,output_directory): return ArtifactWriter(output_directory).write(SpecificationCompiler(specification).compile())
