from __future__ import annotations

import keyword
import re

from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import Entidade, Sistema


SUPPORTED_DATABASES = {"sqlite3", "postgresql"}
SUPPORTED_FIELD_TYPES = {
    "CharField",
    "TextField",
    "IntegerField",
    "FloatField",
    "DecimalField",
    "BooleanField",
    "DateField",
    "DateTimeField",
    "TimeField",
    "EmailField",
    "URLField",
    "FileField",
    "ImageField",
    "ForeignKey",
    "ManyToManyField",
    "OneToOneField",
}
RELATION_TYPES = {"ForeignKey", "ManyToManyField", "OneToOneField"}
ON_DELETE_VALUES = {
    "models.CASCADE",
    "models.PROTECT",
    "models.SET_NULL",
    "models.RESTRICT",
}


def technical_name(value: str, fallback: str = "item") -> str:
    value = slugify(str(value or ""), allow_unicode=False).replace("-", "_")
    value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_").lower() or fallback
    if value[0].isdigit():
        value = f"_{value}"
    if keyword.iskeyword(value):
        value = f"{value}_"
    return value


def class_name(value: str, fallback: str = "Model") -> str:
    parts = re.findall(r"[A-Za-z0-9]+", str(value or ""))
    result = "".join(part[:1].upper() + part[1:] for part in parts)
    return result or fallback


def validate_specification(sistema: Sistema) -> None:
    errors: list[str] = []

    if sistema.banco_dados not in SUPPORTED_DATABASES:
        errors.append(
            f"Banco de dados '{sistema.banco_dados}' não é suportado nesta versão. "
            "Use SQLite ou PostgreSQL."
        )

    if not sistema.nome or not technical_name(sistema.nome):
        errors.append("O sistema precisa ter um nome válido.")

    modulos = list(
        sistema.modulos.prefetch_related("entidades__campos__entidade_relacionada")
    )
    module_names: set[str] = set()
    entity_names: set[tuple[int, str]] = set()

    for modulo in modulos:
        app_name = technical_name(modulo.nome)
        if app_name in module_names:
            errors.append(f"Módulos geram o mesmo nome técnico: '{app_name}'.")
        module_names.add(app_name)

        for entidade in modulo.entidades.all():
            model_name = class_name(entidade.nome)
            key = (modulo.pk, model_name.lower())
            if key in entity_names:
                errors.append(
                    f"Entidades duplicadas no módulo '{modulo.nome}': '{entidade.nome}'."
                )
            entity_names.add(key)

            field_names: set[str] = set()
            for campo in entidade.campos.all():
                field_name = technical_name(campo.nome, "campo")
                if field_name in field_names:
                    errors.append(
                        f"Campos duplicados em '{entidade.nome}': '{campo.nome}'."
                    )
                field_names.add(field_name)

                if campo.tipo not in SUPPORTED_FIELD_TYPES:
                    errors.append(
                        f"Tipo de campo não suportado: '{campo.tipo}' em "
                        f"'{entidade.nome}.{campo.nome}'."
                    )

                if campo.tipo == "DecimalField":
                    if campo.max_digits is None or campo.max_digits <= 0:
                        errors.append(
                            f"DecimalField '{entidade.nome}.{campo.nome}' precisa de max_digits."
                        )
                    if campo.decimal_places is None or campo.decimal_places < 0:
                        errors.append(
                            f"DecimalField '{entidade.nome}.{campo.nome}' precisa de decimal_places."
                        )
                    if (
                        campo.max_digits is not None
                        and campo.decimal_places is not None
                        and campo.decimal_places > campo.max_digits
                    ):
                        errors.append(
                            f"DecimalField '{entidade.nome}.{campo.nome}' possui "
                            "decimal_places maior que max_digits."
                        )

                if campo.tipo in {"CharField", "EmailField", "URLField"}:
                    if not campo.max_length or campo.max_length <= 0:
                        errors.append(
                            f"{campo.tipo} '{entidade.nome}.{campo.nome}' precisa de max_length."
                        )

                if campo.tipo in RELATION_TYPES:
                    if campo.entidade_relacionada_id is None:
                        errors.append(
                            f"Campo relacional '{entidade.nome}.{campo.nome}' "
                            "precisa de uma entidade relacionada."
                        )
                    if campo.on_delete not in ON_DELETE_VALUES:
                        errors.append(
                            f"on_delete inválido em '{entidade.nome}.{campo.nome}'."
                        )
                elif campo.entidade_relacionada_id is not None:
                    errors.append(
                        f"Campo '{entidade.nome}.{campo.nome}' possui entidade relacionada, "
                        "mas não é relacional."
                    )

                if campo.tipo in {"FileField", "ImageField"} and not campo.upload_to:
                    errors.append(
                        f"{campo.tipo} '{entidade.nome}.{campo.nome}' precisa de upload_to."
                    )

    if sistema.usar_custom_user:
        errors.append(
            "Custom User ainda não faz parte do GEN-0001. "
            "Desative 'Gerar Custom User Model' antes da geração."
        )

    if sistema.gerar_api_rest or any(
        entidade.gerar_endpoints_api
        for modulo in modulos
        for entidade in modulo.entidades.all()
    ):
        errors.append(
            "A geração de API REST será habilitada em uma fase posterior. "
            "Desative API REST para gerar com o GEN-0001."
        )

    if errors:
        raise ValidationError(errors)
