# ruff: noqa
from enum import IntEnum, StrEnum, EnumMeta
from typing import Annotated
from datetime import datetime as origin_datetime

from pydantic import PlainSerializer


class MyEnumMeta(EnumMeta):
    def __call__(cls, value, label: str):  # type: ignore
        if label is None:
            return super().__call__(value)
        obj = super().__call__(value)  # type: ignore
        obj._value_ = value
        obj._label = label
        return obj

    def __new__(metacls, cls, bases, classdict):  # type: ignore
        enum_class = super().__new__(metacls, cls, bases, classdict)
        enum_class._dict = {member.value: member.label for member in enum_class}  # type: ignore
        enum_class._help_text = ", ".join([f"{member.value}: {member.label}" for member in enum_class])  # type: ignore
        return enum_class


class StrEnumMore(StrEnum, metaclass=MyEnumMeta):
    _dict: dict[str, str]
    _help_text: str

    def __new__(cls, value, label):  # type: ignore
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

    def __new__(cls, value, label):  # type: ignore
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._label = label  # type: ignore
        return obj

    @property
    def label(self):
        """The value of the Enum member."""
        return self._label  # type: ignore


datetime = Annotated[
    origin_datetime,
    PlainSerializer(lambda _datetime: _datetime.strftime("%Y-%m-%d %H:%M:%S"), return_type=origin_datetime),
]
