import re
import socket
import string
import ipaddress

from _socket import gaierror

PHONE_REGEX_CN = re.compile(r"^1[3-9]\d{9}$")

PHONE_REGEX_GLOBAL = re.compile(r"^\+[1-9]\d{1,14}$")

EMAIL_REGEX = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

LETTER_DIGITS_ONLY_REGEX = re.compile(r"^[a-zA-Z0-9]+$")

ACCOUNT_USERNAME_REGEX = re.compile(r"^(?!\d+$)[a-zA-Z0-9]{6,20}$")

LICENSE_NO_REGEX = re.compile(
    r"^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]$",
)

URI_REGEX = re.compile(r"http[s]?://[^/]+(/[^?#]+)?")

VIN_REGEX = re.compile(r"^[a-zA-Z0-9]{17}$")

PASSWORD_REGEX = re.compile(
    r"(?!^[0-9A-Z]+$)"
    r"(?!^[0-9a-z]+$)"
    r"(?!^[0-9!@#$%^&*()\":<>,.';~\-?/·]+$)"
    r"(?!^[A-Za-z]+$)"
    r"(?!^[A-Z!@#$%^&*()\":<>,.';~\-?/·]+$)"
    r"(?!^[a-z!@#$%^&*()\":<>,.';~\-?/·]+$)"
    r"(^[A-Za-z0-9!@#$%^&*()\":<>,.';~\-?/·]{8,20}$)",
)


def only_alphabetic_numeric(value: str) -> bool:
    if value is None:
        return False
    options = string.ascii_letters + string.digits + "_"
    if not all(i in options for i in value):
        return False
    return True


def validate_ip_or_host(value: int | str) -> tuple[bool, str]:
    try:
        return True, str(ipaddress.ip_address(value))
    except ValueError:
        if isinstance(value, int):
            return False, "不支持数字IP - {value}"
        try:
            socket.gethostbyname(value)
            return True, value
        except gaierror as e:
            return False, f"获取HOST{value}失败: {e}"


def check_vin(vin: str) -> bool:
    # 定义对应值字典
    value_dict = {
        "0": 0,
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 6,
        "G": 7,
        "H": 8,
        "J": 1,
        "K": 2,
        "L": 3,
        "M": 4,
        "N": 5,
        "P": 7,
        "R": 9,
        "S": 2,
        "T": 3,
        "U": 4,
        "V": 5,
        "W": 6,
        "X": 7,
        "Y": 8,
        "Z": 9,
    }
    # 定义加权值列表
    weight_list = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
    total = 0
    if len(vin) != 17:
        return False
    for i in range(17):
        if i == 8:  # 跳过第 9 位，因为它是校验位
            continue
        if vin[i].isalpha() and vin[i].upper() not in value_dict:
            return False
        value = value_dict[vin[i].upper()] if vin[i].isalpha() else int(vin[i])
        total += value * weight_list[i]
    remainder = total % 11
    expected_check_digit = "X" if remainder == 10 else str(remainder)
    return vin[8] == expected_check_digit
