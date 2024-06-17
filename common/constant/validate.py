from enum import Enum


class ValidateErrorTypeEnum(str, Enum):
    json_invalid = "json_invalid"
    json_type = "json_type"
    string_too_short = "string_too_short"
    missing = "missing"
    int_parsing = "int_parsing"


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
}
