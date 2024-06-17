from typing import Any

from pydantic import ValidationError
from fastapi._compat import ModelField, _regenerate_error_with_loc


def validate(
    self: ModelField,
    value: Any,  # ruff: noqa: ANN401
    values: dict[str, Any] = {},  # noqa: B006
    *,
    loc: tuple[int | str, ...] = (),
) -> tuple[Any, list[dict[str, Any]] | None]:
    try:
        return (
            self._type_adapter.validate_python(value, from_attributes=True),
            None,
        )
    except ValidationError as exc:
        errors = exc.errors(include_url=False)
        annotation = self.field_info.annotation
        if hasattr(annotation, "model_fields"):
            fields = annotation.model_fields  # type: ignore
            for e in errors:
                t = ()
                for current_loc in e["loc"]:
                    t = (
                        t + (fields[current_loc].title,)  # type: ignore
                        if current_loc in fields and fields[current_loc].title
                        else t + (current_loc,)
                    )
                e["loc"] = t
        else:
            for e in errors:
                if self.field_info.title:
                    e["loc"] = (self.field_info.title,)

        return None, _regenerate_error_with_loc(errors=errors, loc_prefix=loc)


def patch() -> None:
    # ValidationError loc 字段改为使用 title
    ModelField.validate = validate  # type: ignore
