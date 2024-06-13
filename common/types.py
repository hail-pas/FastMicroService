from enum import IntEnum, StrEnum, EnumMeta

class MyEnumMeta(EnumMeta):
    def __call__(cls, value, label=None):
        if label is None:
            return super().__call__(value)
        obj = super().__call__(value)
        obj._value_ = value
        obj.label = label
        return obj

    def __new__(metacls, cls, bases, classdict):
        enum_class = super().__new__(metacls, cls, bases, classdict)
        enum_class._dict = {member.value: member.label for member in enum_class}
        enum_class._help_text = ", ".join([f"{member.value}: {member.label}" for member in enum_class])
        return enum_class

class StrEnumMore(StrEnum, metaclass=MyEnumMeta):
    _dict: dict[str, str]
    _help_text: str

    def __new__(cls, value, label):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

class IntEnumMore(IntEnum, metaclass=MyEnumMeta):
    _dict: dict[int, str]
    _help_text: str

    def __new__(cls, value, label):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

    @property
    def dict(cls):
        return {}
