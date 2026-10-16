"""阿拉伯数字 → 中文读法：12 → 十二，101 → 一百零一，3.14 → 三点一四。"""

from __future__ import annotations

DIGITS = "零一二三四五六七八九"
_SMALL_UNITS = ["", "十", "百", "千"]
_BIG_UNITS = ["", "万", "亿", "万亿"]


def _below_10000(n: int) -> str:
    """0 < n < 10000，不处理开头的“一十”。"""
    out, zero = [], False
    for i in range(3, -1, -1):
        d = n // 10**i % 10
        if d == 0:
            zero = bool(out)
            continue
        if zero:
            out.append("零")
            zero = False
        out.append(DIGITS[d] + _SMALL_UNITS[i])
    return "".join(out)


def cn_int(n: int) -> str:
    """整数读法。10–19 读“十几”，不读“一十几”；百位以上照常读“一百一十”。"""
    if n < 0:
        return "负" + cn_int(-n)
    if n == 0:
        return "零"
    groups = []
    while n:
        groups.append(n % 10000)
        n //= 10000
    out, need_zero = [], False
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            need_zero = bool(out)
            continue
        if out and (need_zero or g < 1000):
            out.append("零")
        out.append(_below_10000(g) + _BIG_UNITS[i])
        need_zero = False
    s = "".join(out)
    if s.startswith("一十"):
        s = s[1:]
    return s


def cn_number(text: str) -> str:
    """数字串读法：'12' → 十二，'3.14' → 三点一四，'007' 这类前导零逐位读。"""
    if "." in text:
        whole, frac = text.split(".", 1)
        return cn_number(whole or "0") + "点" + "".join(DIGITS[int(c)] for c in frac)
    if len(text) > 1 and text.startswith("0"):
        return "".join(DIGITS[int(c)] for c in text)
    return cn_int(int(text))
