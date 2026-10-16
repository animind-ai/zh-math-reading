from pathlib import Path

import pytest

from zh_math_reading import lint, normalize
from zh_math_reading.text import BOOKMARK, expand_math, polyphone_warnings, visible

FIXTURE = Path(__file__).parent / "fixtures" / "s67_say.txt"
S67 = [line for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]


def marks(text: str) -> dict[str, int]:
    """书签 → 在去掉书签后的文本里的位置（和 animind-voice 的算法一致）。"""
    out, removed = {}, 0
    for m in BOOKMARK.finditer(text):
        out[m.group(0)] = m.start() - removed
        removed += len(m.group(0))
    return out


# ---------------------------------------------------------------- 不改动已有文本

def test_s67_sentences_are_unchanged():
    assert len(S67) == 69
    for s in S67:
        assert normalize(s) == s


def test_text_without_math_is_byte_identical():
    for s in ["今天来看数列压轴题。", "关键就在这一句：{@k}二阶差数列是等差数列。", "a n 加一的平方", ""]:
        assert normalize(s) == s


# ---------------------------------------------------------------- 展开公式：用 p01/p02 人工写好的读法做往返检查

@pytest.mark.parametrize("tex_sentence, human", [
    ("第一问，{@p1}$a_n=2^n$，判断它是不是，是的话求 $d$。",
     "第一问，{@p1}a n 等于二的 n 次方，判断它是不是，是的话求 d。"),
    ("第二问，{@p2}数列 $b_n$ 从第一项起就是等差比数列，而且 $d=1$；$b_1=1$，$b_2=2$，求通项公式。",
     "第二问，{@p2}数列 b n 从第一项起就是等差比数列，而且 d 等于一；b 一等于一，b 二等于二，求通项公式。"),
    ("第三问，{@p3}在第二问的条件下，$S_n\\ge\\lambda b_n$ 对任意 $n$ 都成立，求拉姆达的取值范围。",
     "第三问，{@p3}在第二问的条件下，S n 大于等于拉姆达乘 b n 对任意 n 都成立，求拉姆达的取值范围。"),
    ("{@bound}得到 $\\lambda\\le\\dfrac{n+1}{2}$，而且要对每一个 $n$ 都成立。",
     "{@bound}得到拉姆达小于等于二分之 n 加一，而且要对每一个 n 都成立。"),
    ("{@min}所以拉姆达要小于等于它的最小值。{@one}$n=1$ 时最小，是一。{@ans}所以 $\\lambda\\le 1$。",
     "{@min}所以拉姆达要小于等于它的最小值。{@one}n 等于一时最小，是一。{@ans}所以拉姆达小于等于一。"),
    ("{@ineq}不等式变成：$\\frac{1}{2}n(n+1)$，大于等于拉姆达乘 $n$。{@sign}$n$ 是正数，两边除以 $n$，不等号方向不变。",
     "{@ineq}不等式变成：二分之一乘 n 乘 n 加一，大于等于拉姆达乘 n。{@sign}n 是正数，两边除以 n，不等号方向不变。"),
    ("如果 $d=0$，{@zero}它就是：$a_{n+1}^2=a_na_{n+2}$。{@mean}这正是等比中项！",
     "如果 d 等于零，{@zero}它就是：a n 加一的平方，等于 a n 乘 a n 加二。{@mean}这正是等比中项！"),
    ("{@r1}$a_{n+1}^2$，是 $2^{2n+2}$；",
     "{@r1}a n 加一的平方，是二的二 n 加二次方；"),
    ("{@mid}于是 $b_n+b_{n+2}=2b_{n+1}$。这是等差中项！",
     "{@mid}于是 b n 加 b n 加二，等于二倍的 b n 加一。这是等差中项！"),
    ("{@div}再同时除以 $b_{n+1}b_{n+2}$。",
     "{@div}再同时除以 b n 加一乘 b n 加二。"),
    ("最后加三十六，{@a7}得一百二十一。所以，{@ans}$A_8=121$。",
     "最后加三十六，{@a7}得一百二十一。所以，{@ans}A 八等于一百二十一。"),
    ("$b_n$ 再相邻相减，得到的 $c_n$，{@c}叫二阶差数列。",
     "b n 再相邻相减，得到的 c n，{@c}叫二阶差数列。"),
    ("所以 {@b5}$b_5$，就等于首项三，加上 $c_1$ 到 $c_4$，这四个数的和。",
     "所以 {@b5}b 五，就等于首项三，加上 c 一到 c 四，这四个数的和。"),
    ("最底下的二阶差数列，首项三，公差一，所以 $c_n=n+2$。",
     "最底下的二阶差数列，首项三，公差一，所以 c n 等于 n 加二。"),
    ("这一串是等差数列求和：一共 $n-1$ 项。", "这一串是等差数列求和：一共 n 减一项。"),
    ("由上一问，$a_n=\\frac{1}{3^n-1}$。", "由上一问，a n 等于三的 n 次方减一，分之一。"),
    ("再证明：前 $n$ 项和 $S_n<\\frac{3}{4}$。", "再证明：前 n 项和 S n 小于四分之三。"),
    ("第一问，$a_n=4^n$，证明它是指数型数列。", "第一问，a n 等于四的 n 次方，证明它是指数型数列。"),
    ("{@tri}$k\\cdot 2^{n+2-k}$", "{@tri}k 乘二的 n 加二减 k 次方"),
])
def test_round_trip_against_human_readings(tex_sentence, human):
    assert normalize(tex_sentence) == human


# ---------------------------------------------------------------- 书签

def test_bookmarks_stay_in_place_and_offsets_follow_expansion():
    src = "后一项减前一项，得到的 {@b}$b_n$，叫一阶差数列；{@c}$c_{n+1}$ 也一样。"
    out = normalize(src)
    assert out == "后一项减前一项，得到的 {@b}b n，叫一阶差数列；{@c}c n 加一也一样。"
    plain, pos = visible(out), marks(out)
    assert plain[pos["{@b}"]:].startswith("b n")
    assert plain[pos["{@c}"]:].startswith("c n 加一")


def test_space_goes_before_bookmark():
    out = normalize("叫{@x}$d${@y}等差")
    assert out == "叫 {@x}d {@y}等差"
    plain, pos = visible(out), marks(out)
    assert plain[pos["{@x}"]] == "d" and plain[pos["{@y}"]] == "等"


def test_bookmark_inside_formula():
    out = normalize("$a_n{@m}=2^n$")
    assert out == "a n {@m}等于二的 n 次方"
    assert visible(out)[marks(out)["{@m}"]] == "等"


def test_spacing_around_formulas():
    assert expand_math("数列$b_n$的通项") == "数列 b n 的通项"
    assert expand_math("所以 $\\lambda$ 最小") == "所以拉姆达最小"
    assert expand_math("$a_n$ $b_n$") == "a n b n"
    assert expand_math("是“$0$-等差比数列”") == "是“零等差比数列”"
    assert expand_math("价格 \\$5") == "价格 $5"


# ---------------------------------------------------------------- 安全改写

def test_naming_colon_rewrite():
    assert normalize("这一题，题目又造了一个新名词：d 等差比数列。") == "这一题，题目又造了一个新名词，叫 d 等差比数列。"
    assert normalize("新名词：{@name}d 等差比数列") == "新名词，叫 {@name}d 等差比数列"
    assert normalize("新名词：$d$-等差比数列") == "新名词，叫 d 等差比数列"
    assert normalize("把它记为：S 数列") == "把它记为 S 数列"


def test_naming_rewrite_skips_subscripted_letters():
    # “b 二”“a n”是带下标的写法，不是孤立字母，不改（也保证已有讲稿逐字节不变）
    for s in ["新名词：a n 数列", "新名词：b 二数列", "先翻译：d 等于零，就是等比。"]:
        assert normalize(s) == s


# ---------------------------------------------------------------- lint

def test_lint_lone_letter_after_colon_and_semicolon():
    w = lint("得到：{@ratio}b n 加 b n 加二")
    assert len(w) == 1 and "「：」后紧跟字母「b」" in w[0]
    w = lint("就是我们熟悉的等比数列；{@ne}d 不等于零")
    assert any("「；」后紧跟字母「d」" in x for x in w)
    assert lint("新名词，叫 d 等差比数列。") == []


def test_lint_long_sentence():
    long = "如果一个数列" + "从某一项起后面每一个都满足这个条件" * 4 + "。"
    w = lint(long)
    assert any("句子太长" in x for x in w)
    assert not any("句子太长" in x for x in lint("短句。" * 30))


def test_lint_digits_and_leftover_latex():
    assert any("阿拉伯数字「12」" in x for x in lint("第 12 项"))
    assert any("没展开的公式" in x for x in lint("数列 $b_n$"))


def test_lint_polyphones():
    assert any("差了" in x and "chà" in x for x in lint("中间差了三项"))
    assert any("得证明" in x and "děi" in x for x in lint("猜出来的不算数，得证明。"))
    assert any("倒数第" in x for x in lint("倒数第二项"))
    assert lint("一阶差数列再相邻相减") == []
    assert lint("公差为一的等差数列") == []
    assert lint("要做三次差才变成常数") == []
    # strict 字落在没收录的上下文里
    assert any("「行」的上下文没有收录" in x for x in lint("这样就行"))
    assert any("「重」的上下文没有收录" in x for x in lint("重积分"))


def test_polyphone_longest_match():
    # “公差一个”按最长匹配切成“公差”，不会被“差一个”(chà) 误报
    assert polyphone_warnings("首项一，公差一个都不少") == []
    assert polyphone_warnings("和等比差一个常数")


def test_lint_flags_on_s67():
    flagged = {s for s in S67 if lint(s)}
    # 回听报告里真正吞字的两句都被提示
    assert any(s.startswith("得到：{@ratio}b n 加") for s in flagged)
    assert any("{@ne}d 不等于零" in s for s in flagged)
    assert len(flagged) < len(S67) // 3
