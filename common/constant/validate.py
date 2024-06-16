from enum import Enum


class ValidateErrorTypeEnum(str, Enum):
    json_invalid = "json_invalid"
    string_too_short = "string_too_short"


DirectValidateErrorMsgTemplates = {
    "json_invalid": ("请求体", "格式异常"),
}


# CN_ZH
ValidationErrorMsgTemplates = {
    # value_error
    "json_type": "不是合法的JSON格式",
    "string_too_short": "至少{min_length}个字符",
    "value_error.extra": "禁止的额外参数",
    "value_error.missing": "缺少必填字段",
    "value_error.any_str.max_length": "最长不超过{limit_value}个字符",
    "value_error.const": "不合法的参数值'{given}', 合法候选项为{permitted}",
    "value_error.str.regex": "请输入正确的值",
    "value_error.date": "请输入正确的日期格式",
    "value_error.number.not_gt": "必须大于{limit_value}",
    "value_error.number.not_ge": "必须大于等于{limit_value}",
    "value_error.number.not_lt": "必须小于{limit_value}",
    "value_error.number.not_le": "必须小于等于{limit_value}",
    "value_error.decimal.max_places": "小数位数不能大于{decimal_places}位",
    # type_error
    "type_error": "类型错误",
    "type_error.enum": "值错误, 可选值:{enum_values}",
    "type_error.none.not_allowed": "不允许为空值",
    "type_error.integer": "请输入正确的整数",
}
