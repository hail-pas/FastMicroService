# ruff: noqa
from enum import IntEnum, StrEnum, EnumMeta
from typing import Annotated

import orjson
from pydantic.functional_validators import BeforeValidator


class MyEnumMeta(EnumMeta):
    def __call__(cls, value, label: str = ""):  # type: ignore
        obj = super().__call__(value)  # type: ignore
        obj._value_ = value
        if label:
            obj._label = label
        else:
            obj._label = obj._dict[value]
        return obj

    def __new__(metacls, cls, bases, classdict):  # type: ignore
        enum_class = super().__new__(metacls, cls, bases, classdict)
        enum_class._dict = {member.value: member.label for member in enum_class}  # type: ignore
        enum_class._help_text = ", ".join([f"{member.value}: {member.label}" for member in enum_class])  # type: ignore
        return enum_class


class StrEnumMore(StrEnum, metaclass=MyEnumMeta):
    _dict: dict[str, str]
    _help_text: str

    def __new__(cls, value, label: str = ""):  # type: ignore
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._label = label  # type: ignore
        return obj

    @property
    def label(self):
        """The value of the Enum member."""
        return self._label  # type: ignore


class IntEnumMore(IntEnum, metaclass=MyEnumMeta):
    _dict: dict[int, str]
    _help_text: str

    def __new__(cls, value, label: str = ""):  # type: ignore
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._label = label  # type: ignore
        return obj

    @property
    def label(self):
        """The value of the Enum member."""
        return self._label  # type: ignore


RoundFloat = Annotated[
    float,
    BeforeValidator(lambda x: round(x, 2)),
    # PlainSerializer(
    #     lambda x: round(x, 2),
    #     return_type=float,
    # )
]


DictFromStr = Annotated[dict, BeforeValidator(lambda x: orjson.loads(x) if isinstance(x, str) else x)]
