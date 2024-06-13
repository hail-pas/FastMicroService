# ruff: noqa
from enum import IntEnum, StrEnum, EnumMeta


class MyEnumMeta(EnumMeta):
    def __call__(cls, value, label: str):  # type: ignore
        if label is None:
            return super().__call__(value)
        obj = super().__call__(value)  # type: ignore
        obj._value_ = value
        obj.label = label
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
        obj.label = label  # type: ignore
        return obj


class IntEnumMore(IntEnum, metaclass=MyEnumMeta):
    _dict: dict[int, str]
    _help_text: str

    def __new__(cls, value, label):  # type: ignore
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label  # type: ignore
        return obj
