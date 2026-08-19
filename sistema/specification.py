from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from django.core.exceptions import ValidationError

from .models import Campo, Sistema
from .validation import class_name, technical_name, validate_specification

SPECIFICATION_VERSION = "2.1"

@dataclass(frozen=True)
class FieldSpec:
    name: str
    technical_name: str
    type: str
    null: bool = False
    blank: bool = False
    unique: bool = False
    default: str = ""
    max_length: int | None = None
    max_digits: int | None = None
    decimal_places: int | None = None
    upload_to: str = ""
    related_entity: str | None = None
    related_module: str | None = None
    on_delete: str = "models.CASCADE"
    related_name: str = ""
    verbose_name: str = ""
    help_text: str = ""

@dataclass(frozen=True)
class EntitySpec:
    name: str
    class_name: str
    technical_name: str
    plural_name: str
    description: str
    generate_admin: bool
    generate_crud: bool
    generate_api: bool
    fields: tuple[FieldSpec, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ModuleSpec:
    name: str
    technical_name: str
    description: str
    entities: tuple[EntitySpec, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class SystemSpec:
    version: str
    name: str
    technical_name: str
    slug: str
    description: str
    database: str
    menu: str
    custom_user: bool
    rest_api: bool
    docker: bool
    audit: bool
    modules: tuple[ModuleSpec, ...] = field(default_factory=tuple)
    def to_dict(self) -> dict[str, Any]: return asdict(self)
    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    @property
    def fingerprint(self) -> str: return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

class SpecificationBuilder:
    def __init__(self, sistema: Sistema): self.sistema = sistema
    def build(self) -> SystemSpec:
        validate_specification(self.sistema)
        sistema = Sistema.objects.filter(pk=self.sistema.pk).prefetch_related("modulos__entidades__campos__entidade_relacionada__modulo").get()
        modules = []
        for modulo in sistema.modulos.all().order_by("id"):
            entities = []
            for entidade in modulo.entidades.all().order_by("id"):
                fields = tuple(self._field_spec(campo) for campo in entidade.campos.all().order_by("id"))
                entities.append(EntitySpec(entidade.nome, class_name(entidade.nome), technical_name(entidade.nome, "model"), entidade.nome_plural or entidade.nome, entidade.descricao, entidade.gerar_admin, entidade.gerar_crud_views, entidade.gerar_endpoints_api, fields))
            modules.append(ModuleSpec(modulo.nome, technical_name(modulo.nome, "app"), modulo.descricao, tuple(entities)))
        return SystemSpec(SPECIFICATION_VERSION, sistema.nome, technical_name(sistema.nome, "projeto"), sistema.slug, sistema.descricao, sistema.banco_dados, sistema.tipo_menu, sistema.usar_custom_user, sistema.gerar_api_rest, sistema.gerar_docker, sistema.usar_auditoria, tuple(modules))
    @staticmethod
    def _field_spec(campo: Campo) -> FieldSpec:
        related = campo.entidade_relacionada
        return FieldSpec(campo.nome, technical_name(campo.nome, "campo"), campo.tipo, campo.null, campo.blank, campo.unique, str(campo.default_value or ""), campo.max_length, campo.max_digits, campo.decimal_places, campo.upload_to, class_name(related.nome) if related else None, technical_name(related.modulo.nome, "app") if related else None, campo.on_delete, campo.related_name, campo.verbose_name, campo.help_text)

def build_specification(sistema: Sistema) -> SystemSpec: return SpecificationBuilder(sistema).build()

def validate_specification_object(specification: SystemSpec) -> None:
    errors = []
    module_names: set[str] = set()
    for module in specification.modules:
        if module.technical_name in module_names: errors.append(f"Módulos duplicados: {module.technical_name}")
        module_names.add(module.technical_name)
        for entity in module.entities:
            seen_fields: set[str] = set()
            for field_spec in entity.fields:
                if field_spec.technical_name in seen_fields: errors.append(f"Campos duplicados em {entity.class_name}: {field_spec.technical_name}")
                seen_fields.add(field_spec.technical_name)
    if errors: raise ValidationError(errors)
