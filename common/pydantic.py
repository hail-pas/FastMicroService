from __future__ import annotations

import inspect
from typing import Literal
from collections.abc import Callable

import pydantic
from fastapi import Form, Query
from fastapi.params import _Unset
from tortoise.contrib.pydantic.base import PydanticModel

from common.utils import filter_dict


def optional(*fields) -> Callable[[pydantic.BaseModel], pydantic.BaseModel]:
    """Decorator function used to modify a pydantic model's fields to all be optional.
    Alternatively, you can  also pass the field names that should be made optional as arguments
    to the decorator.
    Taken from https://github.com/samuelcolvin/pydantic/issues/1223#issuecomment-775363074.
    """

    def dec(_cls: pydantic.BaseModel) -> pydantic.BaseModel:
        for field in fields:
            _cls.model_fields[field].required = False  # type: ignore
        return _cls

    if fields and inspect.isclass(fields[0]) and issubclass(fields[0], pydantic.BaseModel):
        cls = fields[0]
        fields = cls.model_fields  # type: ignore
        return dec(cls)  # type: ignore

    return dec


def sub_fields_model(
    base_model: type[pydantic.BaseModel] | type[PydanticModel],
    fields: set[str],
) -> type[pydantic.BaseModel] | type[PydanticModel]:
    class ToModel(base_model):  # type: ignore
        pass

    ToModel.__fields__ = filter_dict(
        dict_obj=ToModel.__fields__,
        callback=lambda k, _: k in fields,  # type: ignore
    )
    ToModel.__config__.fields = filter_dict(
        dict_obj=ToModel.__config__.fields,
        callback=lambda k, _: k in fields,  # type: ignore
    )
    return ToModel


def create_parameter_from_field_info(
    type_: Literal["query", "form"],
    field_name: str,
    field_info: pydantic.fields.FieldInfo,
) -> inspect.Parameter:
    fastapi_parameter_cls = Form if type_ == "form" else Query

    attribute_set = field_info._attributes_set

    return inspect.Parameter(
        field_info.alias or field_name,
        inspect.Parameter.POSITIONAL_ONLY,
        default=fastapi_parameter_cls(  # type: ignore
            default=field_info.default,
            default_factory=field_info.default_factory,
            media_type="application/x-www-form-urlencoded",
            alias=field_info.alias,
            alias_priority=field_info.alias_priority,
            validation_alias=field_info.validation_alias,
            serialization_alias=field_info.serialization_alias,
            title=field_info.title,
            description=field_info.description,
            gt=attribute_set.get("gt"),
            ge=attribute_set.get("ge"),
            lt=attribute_set.get("lt"),
            le=attribute_set.get("le"),
            min_length=attribute_set.get("min_length"),
            max_length=attribute_set.get("max_length"),
            pattern=attribute_set.get("pattern"),
            multiple_of=attribute_set.get("multiple_of") or _Unset,
            allow_inf_nan=attribute_set.get("allow_inf_nan") or _Unset,
            max_digits=attribute_set.get("max_digits") or _Unset,
            decimal_places=attribute_set.get("decimal_places") or _Unset,
            example=field_info.examples,
            deprecated=field_info.deprecated,
            json_schema_extra=field_info.json_schema_extra,
            # min_length=field_info.metadata[0].min_length,
        ),
        annotation=field_info.annotation,
    )


def as_form(cls: type[pydantic.BaseModel]) -> type[pydantic.BaseModel]:
    new_parameters = []

    for field_name, field_info in cls.model_fields.items():
        new_parameters.append(create_parameter_from_field_info("form", field_name, field_info))

    async def as_form_func(**data) -> pydantic.BaseModel:
        return cls(**data)

    sig = inspect.signature(as_form_func)
    sig = sig.replace(parameters=new_parameters)
    as_form_func.__signature__ = sig  # type: ignore
    cls.as_form = as_form_func  # type: ignore
    return cls


def as_query(cls: type[pydantic.BaseModel]) -> type[pydantic.BaseModel]:
    new_parameters = []

    for field_name, model_field in cls.model_fields.items():
        new_parameters.append(create_parameter_from_field_info("query", field_name, model_field))

    async def as_query_func(**data) -> pydantic.BaseModel:
        return cls(**data)

    sig = inspect.signature(as_query_func)
    sig = sig.replace(parameters=new_parameters)
    as_query_func.__signature__ = sig  # type: ignore
    cls.as_query = as_query_func  # type: ignore
    return cls
