import pytest

from zh_math_reading import cn_int, cn_number


@pytest.mark.parametrize(
    "n, say",
    [
        (0, "零"), (1, "一"), (2, "二"), (10, "十"), (11, "十一"), (15, "十五"), (20, "二十"), (21, "二十一"),
        (36, "三十六"), (100, "一百"), (101, "一百零一"), (110, "一百一十"), (121, "一百二十一"),
        (1000, "一千"), (1010, "一千零一十"), (10000, "一万"), (10001, "一万零一"), (100000, "十万"),
        (120000, "十二万"), (100000000, "一亿"), (-4, "负四"),
    ],
)
def test_cn_int(n, say):
    assert cn_int(n) == say


@pytest.mark.parametrize("text, say", [("12", "十二"), ("0.5", "零点五"), ("3.14", "三点一四"), ("007", "零零七"), ("0", "零")])
def test_cn_number(text, say):
    assert cn_number(text) == say
