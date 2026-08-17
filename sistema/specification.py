from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from django.core.exceptions import ValidationError

from .models import Campo, Entidade, Modulo, Sistema
from .validation import class_name, technical_name, validate_specification


SPECIFICATION_VERSION = "2.0"


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class SpecificationBuilder:
    """Converts the database-backed editor model into a canonical specification.

    GEN-0002 makes the specification an explicit domain object. The generator can
    consume this object instead of depending directly on Django ORM instances.
    """

    def __init__(self, sistema: Sistema):
        self.sistema = sistema

    def build(self) -> SystemSpec:
        validate_specification(self.sistema)

        sistema = (
            Sistema.objects.filter(pk=self.sistema.pk)
            .prefetch_related(
                "modulos__entidades__campos__entidade_relacionada__modulo"
            )
            .get()
        )

        modules: list[ModuleSpec] = []
        for modulo in sistema.modulos.all().order_by("id"):
            entities: list[EntitySpec] = []
            for entidade in modulo.entidades.all().order_by("id"):
                fields = tuple(
                    self._field_spec(campo)
                    for campo in entidade.campos.all().order_by("id")
                )
                entities.append(
                    EntitySpec(
                        name=entidade.nome,
                        class_name=class_name(entidade.nome),
                        technical_name=technical_name(entidade.nome, "model"),
                        plural_name=entidade.nome_plural or entidade.nome,
                        description=entidade.descricao,
                        generate_admin=entidade.gerar_admin,
                        generate_crud=entidade.gerar_crud_views,
                        generate_api=entidade.gerar_endpoints_api,
                        fields=fields,
                    )
                )
            modules.append(
                ModuleSpec(
                    name=modulo.nome,
                    technical_name=technical_name(modulo.nome, "app"),
                    description=modulo.descricao,
                    entities=tuple(entities),
                )
            )

        return SystemSpec(
            version=SPECIFICATION_VERSION,
            name=sistema.nome,
            technical_name=technical_name(sistema.nome, "projeto"),
            slug=sistema.slug,
            description=sistema.descricao,
            database=sistema.banco_dados,
            menu=sistema.tipo_menu,
            custom_user=sistema.usar_custom_user,
            rest_api=sistema.gerar_api_rest,
            docker=sistema.gerar_docker,
            audit=sistema.usar_auditoria,
            modules=tuple(modules),
        )

    @staticmethod
    def _field_spec(campo: Campo) -> FieldSpec:
        related_entity = campo.entidade_relacionada
        return FieldSpec(
            name=campo.nome,
            technical_name=technical_name(campo.nome, "campo"),
            type=campo.tipo,
            null=campo.null,
            blank=campo.blank,
            unique=campo.unique,
            default=str(campo.default_value or ""),
            max_length=campo.max_length,
            max_digits=campo.max_digits,
            decimal_places=campo.decimal_places,
            upload_to=campo.upload_to,
            related_entity=(
                class_name(related_entity.nome) if related_entity else None
            ),
            related_module=(
                technical_name(related_entity.modulo.nome, "app")
                if related_entity
                else None
            ),
            on_delete=campo.on_delete,
            related_name=campo.related_name_str,
            verbose_name=campo.verbose_name,
            help_text=campo.help_text,
        )


def build_specification(sistema: Sistema) -> SystemSpec:
    return SpecificationBuilder(sistema).build()


def validate_specification_object(specification: SystemSpec) -> None:
    """Validate invariants that must hold after ORM conversion."""
    errors: list[str] = []
    module_names: set[str] = set()

    for module in specification.modules:
        if module.technical_name in module_names:
            errors.append(f"Módulos duplicados: {module.technical_name}")
        module_names.add(module.technical_name)

        field_owner: dict[str, str] = {}
        for entity in module.entities:
            seen_fields: set[str] = set()
            for field_spec in entity.fields:
                if field_spec.technical_name in seen_fields:
                    errors.append(
                        f"Campos duplicados em {entity.class_name}: {field_spec.technical_name}"
                    )
                seen_fields.add(field_spec.technical_name)
                field_owner[field_spec.technical_name] = entity.class_name

    if errors:
        raise ValidationError(errors)
