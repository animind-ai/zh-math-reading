import pytest

from zh_math_reading import read_latex
from zh_math_reading.data import latex_rules
from zh_math_reading.latex import fill, join, unknown_commands

EXAMPLES = latex_rules()["examples"]


@pytest.mark.parametrize("ex", EXAMPLES, ids=[e["tex"] for e in EXAMPLES])
def test_yaml_examples(ex):
    assert read_latex(ex["tex"]) == ex["say"]


def test_every_symbol_has_a_reading():
    for key, rule in latex_rules()["symbols"].items():
        got = read_latex(f"a{key} b")
        assert rule["say"] in got, (key, got)


@pytest.mark.parametrize("name, say", list(latex_rules()["greek"].items()))
def test_greek(name, say):
    assert read_latex("\\" + name) == say


@pytest.mark.parametrize("tex, say", [
    ("\\mathbb{N}", "自然数集"), ("\\mathbb{N}^*", "正整数集"), ("N^*", "正整数集"), ("\\mathbf N_+", "正整数集"),
    ("\\mathbb{Z}", "整数集"), ("\\mathbb{Q}", "有理数集"), ("\\mathbb{C}", "复数集"),
    ("R", "R"),  # 不加 \mathbb 的 R 当普通字母（可能是半径、点）
])
def test_sets(tex, say):
    assert read_latex(tex) == say


@pytest.mark.parametrize("tex, say", [
    ("x^{10}", "x 的十次方"),
    ("e^x", "e 的 x 次方"),
    ("2x^2", "二 x 的平方"),
    ("ax^2+bx+c", "a x 的平方加 b x 加 c"),
    ("n\\cdot 2^n", "n 乘二的 n 次方"),
    ("n 2^n", "n 乘二的 n 次方"),
    ("(n+1)^2", "n 加一的平方"),
    ("a_n^2", "a n 的平方"),
])
def test_powers(tex, say):
    assert read_latex(tex) == say


@pytest.mark.parametrize("tex, say", [
    ("\\frac{a+b}{c+d}+1", "c 加 d，分之 a 加 b，加一"),
    ("\\tfrac{3}{4}", "四分之三"),
    ("\\frac{1}{2^n}", "二的 n 次方分之一"),
    ("\\frac{1}{6}(k+1)", "六分之一乘 k 加一"),
])
def test_fractions(tex, say):
    assert read_latex(tex) == say


@pytest.mark.parametrize("tex, say", [
    ("x_1x_2", "x 一乘 x 二"),
    ("2b_4", "二倍的 b 四"),
    ("-2a", "负二 a"),
    ("2\\pi r", "二派 r"),
    ("a^{n+1}b", "a 的 n 加一次方乘 b"),
    ("g(x+1)=2", "g x 加一，等于二"),
    ("\\sin(x+1)", "sin x 加一"),
    ("\\ln x", "ln x"),
])
def test_implicit_multiplication_and_functions(tex, say):
    assert read_latex(tex) == say


@pytest.mark.parametrize("tex, say", [
    ("\\lim_{n\\to\\infty}a_n", "n 趋向于无穷大时的极限，a n"),
    ("\\binom{n}{k}", "组合数 C n k"),
    ("a:b", "a 比 b"),
    ("5!", "五的阶乘"),
    ("\\{x\\mid x>0\\}", "x 满足 x 大于零"),
    ("1,2,3,\\cdots", "一、二、三、等等"),
    ("x=1, y=2", "x 等于一，y 等于二"),
    ("a_1a_2\\cdots a_n", "a 一乘 a 二一直乘到 a n"),
    ("a_1\\cdot a_2\\cdot\\cdots\\cdot a_n", "a 一乘 a 二一直乘到 a n"),
    ("\\vec{a}\\perp\\vec{b}", "向量 a 垂直于向量 b"),
    ("\\left|x\\right|", "x 的绝对值"),
    ("\\displaystyle\\sum_{i=1}^{n}i", "i 从一到 n 求和，i"),
    ("\\sum a_k", "求和 a k"),
    ("\\overline{AB}", "A B"),
    ("x\\in[0,1)", "x 属于左闭右开区间零到一"),
    ("x\\in(0,+\\infty)", "x 属于开区间零到正无穷大"),
    ("[1,2]", "闭区间一到二"),
    ("(1,2]", "左开右闭区间一到二"),
    ("P(1,2)", "P 一、二"),
    ("a_n=\\begin{cases}1, & n=1\\\\ 2n, & n\\ge 2\\end{cases}", "a n 等于一，n 等于一；二 n，n 大于等于二"),
])
def test_misc(tex, say):
    assert read_latex(tex) == say


def test_unknown_commands_are_reported():
    assert unknown_commands("\\foo x + \\bar y") == ["\\foo"]
    assert read_latex("\\foo x") == "foo x"
    with pytest.raises(ValueError, match="foo"):
        read_latex("\\foo x", strict=True)


def test_join_spacing():
    assert join("a", "n") == "a n"
    assert join("二", "n") == "二 n"
    assert join("二", "的") == "二的"
    assert join("，", "a") == "，a"
    assert join("a ", "b") == "a b"
    assert fill("{base} {sub}", base="a", sub="八") == "a 八"
    assert fill("{den}分之{num}", den="二", num="n 加一") == "二分之 n 加一"
