import re
from decimal import Decimal

from tortoise import validators

from common.exceptions import ValidationError
from common.constant.messages import ValidationErrorMsgTemplates


class RegexValidator(validators.RegexValidator):
    error_type: str = "value_error.str.regex"
    error_message_template: str = ValidationErrorMsgTemplates[error_type]
    ctx: dict
    default_ctx: dict

    def __init__(
        self,
        pattern: str,
        flags: int | re.RegexFlag,
        error_message_template: str | None = None,
        default_ctx: dict | None = None,
    ) -> None:
        super().__init__(pattern, flags)
        self.default_ctx = default_ctx or {}
        if error_message_template:
            self.error_message_template = error_message_template

    def __call__(self, value: str) -> None:
        if value is None:
            return
        if not self.regex.match(value):
            raise ValidationError(
                error_type=self.error_type,
                error_message_template=self.error_message_template,
                ctx={
                    "value": value,
                    "regex": self.regex.pattern,
                    **self.default_ctx,
                },
            )


class MaxLengthValidator(validators.MaxLengthValidator):
    error_type: str = "value_error.any_str.max_length"
    error_message_template: str = ValidationErrorMsgTemplates[error_type]
    ctx: dict
    default_ctx: dict
    nullable: bool = False

    def __init__(
        self,
        max_length: int,
        error_message_template: str | None = None,
        nullable: bool = False,
        default_ctx: dict | None = None,
    ) -> None:
        super().__init__(max_length)
        self.default_ctx = default_ctx or {}
        self.nullable = nullable
        if error_message_template:
            self.error_message_template = error_message_template

    def __call__(self, value: str) -> None:
        if value is None:
            if self.nullable:
                return

            raise ValidationError(
                error_type="type_error.none.not_allowed",
                error_message_template=ValidationErrorMsgTemplates[
                    "type_error.none.not_allowed"
                ],
                ctx={
                    "value": value,
                    **self.default_ctx,
                },
            )

        if len(value) > self.max_length:
            raise ValidationError(
                error_type=self.error_type,
                error_message_template=self.error_message_template,
                ctx={
                    "value": value,
                    "limit_value": self.max_length,
                    **self.default_ctx,
                },
            )


class MinLengthValidator(validators.MinLengthValidator):
    error_type: str = "value_error.any_str.min_length"
    error_message_template: str = ValidationErrorMsgTemplates[error_type]
    ctx: dict
    default_ctx: dict
    nullable: bool = False

    def __init__(
        self,
        min_length: int,
        error_message_template: str | None = None,
        nullable: bool = False,
        default_ctx: dict | None = None,
    ) -> None:
        super().__init__(min_length)
        self.nullable = nullable
        self.default_ctx = default_ctx or {}
        if error_message_template:
            self.error_message_template = error_message_template

    def __call__(self, value: str) -> None:
        if value is None:
            if self.nullable:
                return

            raise ValidationError(
                error_type="type_error.none.not_allowed",
                error_message_template=ValidationErrorMsgTemplates[
                    "type_error.none.not_allowed"
                ],
                ctx={
                    "value": value,
                    **self.default_ctx,
                },
            )

        if len(value) < self.min_length:
            raise ValidationError(
                error_type=self.error_type,
                error_message_template=self.error_message_template,
                ctx={
                    "value": value,
                    "limit_value": self.min_length,
                    **self.default_ctx,
                },
            )


class MaxValueValidator(validators.MaxValueValidator):
    error_type: str = "value_error.number.not_le"
    error_message_template: str = ValidationErrorMsgTemplates[error_type]
    ctx: dict
    default_ctx: dict

    def __init__(
        self,
        max_value: int | float | Decimal,
        error_message_template: str | None = None,
        default_ctx: dict | None = None,
    ) -> None:
        super().__init__(max_value)
        self.default_ctx = default_ctx or {}
        if error_message_template:
            self.error_message_template = error_message_template

    def __call__(self, value: int | float | Decimal) -> None:
        if not isinstance(value, int | float | Decimal):
            raise ValidationError(
                error_type="type_error",
                error_message_template=ValidationErrorMsgTemplates[
                    "type_error"
                ],
                ctx={
                    "value": value,
                    **self.default_ctx,
                },
            )

        if value > self.max_value:
            raise ValidationError(
                error_type=self.error_type,
                error_message_template=self.error_message_template,
                ctx={
                    "value": value,
                    "limit_value": self.max_value,
                    **self.default_ctx,
                },
            )


class MinValueValidator(validators.MinValueValidator):
    error_type: str = "value_error.number.not_ge"
    error_message_template: str = ValidationErrorMsgTemplates[error_type]
    ctx: dict
    default_ctx: dict

    def __init__(
        self,
        min_value: int | float | Decimal,
        error_message_template: str | None = None,
        default_ctx: dict | None = None,
    ) -> None:
        super().__init__(min_value)
        self.default_ctx = default_ctx or {}
        if error_message_template:
            self.error_message_template = error_message_template

    def __call__(self, value: int | float | Decimal) -> None:
        if not isinstance(value, int | float | Decimal):
            raise ValidationError(
                error_type="type_error",
                error_message_template=ValidationErrorMsgTemplates[
                    "type_error"
                ],
                ctx={
                    "value": value,
                    **self.default_ctx,
                },
            )

        if value < self.min_value:
            raise ValidationError(
                error_type=self.error_type,
                error_message_template=self.error_message_template,
                ctx={
                    "value": value,
                    "limit_value": self.min_value,
                    **self.default_ctx,
                },
            )


class CommaSeparatedIntegerListValidator(
    validators.CommaSeparatedIntegerListValidator,
):
    def __init__(
        self,
        allow_negative: bool = False,
        error_message_template: str | None = None,
        default_ctx: dict | None = None,
    ) -> None:
        pattern = r"^{neg}\d+(?:{sep}{neg}\d+)*\Z".format(
            neg="(-)?" if allow_negative else "",
            sep=re.escape(","),
        )
        self.regex = RegexValidator(
            pattern,
            re.I,
            error_message_template,
            default_ctx,
        )

    def __call__(self, value: str) -> None:
        self.regex(value)
