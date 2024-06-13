import inspect
from datetime import datetime
from collections.abc import Callable

import pydantic
from fastapi import Form
from pydantic.fields import ModelField
from tortoise.contrib.pydantic.base import PydanticModel

from common.utils import DATETIME_FORMAT_STRING, filter_dict


def optional(*fields) -> Callable[[pydantic.BaseModel], pydantic.BaseModel]:
    """Decorator function used to modify a pydantic model's fields to all be optional.
    Alternatively, you can  also pass the field names that should be made optional as arguments
    to the decorator.
    Taken from https://github.com/samuelcolvin/pydantic/issues/1223#issuecomment-775363074.
    """

    def dec(_cls: pydantic.BaseModel) -> pydantic.BaseModel:
        for field in fields:
            _cls.__fields__[field].required = False
        return _cls

    if (
        fields
        and inspect.isclass(fields[0])
        and issubclass(fields[0], pydantic.BaseModel)
    ):
        cls = fields[0]
        fields = cls.__fields__  # type: ignore
        return dec(cls)  # type: ignore

    return dec


class DateTimeFormatConfig:
    json_encoders = {
        datetime: lambda v: v.strftime(DATETIME_FORMAT_STRING),
    }


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


def as_form(cls: type[pydantic.BaseModel]) -> type[pydantic.BaseModel]:
    new_parameters = []

    for _field_name, model_field in cls.__fields__.items():
        model_field: ModelField  # type: ignore

        new_parameters.append(
            inspect.Parameter(
                model_field.alias,
                inspect.Parameter.POSITIONAL_ONLY,
                default=Form(...)
                if model_field.required
                else Form(model_field.default),
                annotation=model_field.outer_type_,
            ),
        )

    async def as_form_func(**data) -> pydantic.BaseModel:
        return cls(**data)

    sig = inspect.signature(as_form_func)
    sig = sig.replace(parameters=new_parameters)
    as_form_func.__signature__ = sig  # type: ignore
    cls.as_form = as_form_func  # type: ignore
    return cls
