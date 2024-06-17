from enum import Enum


class ValidateErrorTypeEnum(str, Enum):
    json_invalid = "json_invalid"
    json_type = "json_type"
    missing = "missing"

    # string_error
    string_too_short = "string_too_short"
    string_pattern_mismatch = "string_pattern_mismatch"

    # paser_error
    int_parsing = "int_parsing"
    decimal_parsing = "decimal_parsing"

    # value_error
    greater_than = "greater_than"
    multiple_of = "multiple_of"


DirectValidateErrorMsgTemplates = {
    ValidateErrorTypeEnum.json_invalid: ("请求体", "格式异常"),
}


# CN_ZH
ValidationErrorMsgTemplates = {
    # value_error
    ValidateErrorTypeEnum.json_type: "不是合法的JSON格式",
    ValidateErrorTypeEnum.missing: "缺少必填字段",
    ValidateErrorTypeEnum.string_too_short: "至少{min_length}个字符",
    ValidateErrorTypeEnum.int_parsing: "请输入正确的整数",
    ValidateErrorTypeEnum.greater_than: "必须大于{gt}",
    ValidateErrorTypeEnum.decimal_parsing: "请输入正确的小数",
    ValidateErrorTypeEnum.multiple_of: "必须是{multiple_of}的整数倍",
    ValidateErrorTypeEnum.string_pattern_mismatch: "格式不正确",
}
