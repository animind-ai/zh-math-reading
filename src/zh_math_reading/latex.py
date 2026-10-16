"""把一段 LaTeX 公式读成中文旁白：$a_{n+1}^2$ → “a n 加一的平方”。

规则表在 data/latex.yaml；这里只有解析和拼接：
- 字母原样念，字母和中文之间留一个空格（和 §6.7 讲稿一致），中文之间不留；
- 隐含乘法按讲稿习惯：数字乘字母直接连读（二 n），带下标的项之间念“乘”（a n 乘 a n 加二）；
- 带复合下标、复合分数的项后面跟运算符时补一个逗号停顿（a n 加一，等于 ……），
  多项式括号后面跟任何东西都停一下（n 加一，乘 n 加二）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .data import latex_rules
from .numbers import cn_number

_TOKEN = re.compile(r"\\([A-Za-z]+|.)|(\d+(?:\.\d+)?)|([A-Za-z])|(\s+)|([^\x00-\x7f]+)|(.)", re.S)
_PUNCT = set("，。、；：！？（）《》“”‘’…—,.;:!?()[] ")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_FRAC = {"frac", "dfrac", "tfrac", "cfrac"}
_TEXT = {"text", "mbox", "textrm", "textbf", "textit", "textsf"}
_VEC = {"vec", "overrightarrow"}
_ELLIPSIS = {"cdots", "ldots", "dots", "vdots", "ddots", "dotsb", "dotsc"}
_BIG = {"sum": "sum", "prod": "prod"}


def _ascii_alnum(c: str) -> bool:
    return c.isascii() and c.isalnum()


def join(a: str, b: str) -> str:
    """拼接两段读法：一边是字母数字、另一边不是空白或标点时，中间补一个空格。"""
    if not a:
        return b
    if not b:
        return a
    x, y = a[-1], b[0]
    if x.isspace() or y.isspace() or x in _PUNCT or y in _PUNCT:
        return a + b
    if _ascii_alnum(x) or _ascii_alnum(y):
        return a + " " + b
    return a + b


def fill(template: str, **values: str) -> str:
    out = ""
    for i, part in enumerate(_PLACEHOLDER.split(template)):
        out = join(out, values[part] if i % 2 else part.strip(" "))
    return out


@dataclass
class _Tok:
    kind: str  # cmd num letter cjk char
    value: str
    space_before: bool = False


@dataclass
class _Node:
    kind: str
    value: str = ""
    args: list = field(default_factory=list)
    extra: list = field(default_factory=list)
    sub: list | None = None
    sup: list | None = None
    arg: _Node | None = None
    flag: bool = False  # var: 用了 \mathbb / \mathbf；group: 是圆/方括号


@dataclass
class _Piece:
    text: str
    kind: str  # num var sub pow frac sqrt abs group expr func word text op rel unary ellipsis percent
    soft: bool = False  # 后面跟运算符/关系符时补逗号
    hard: bool = False  # 后面跟任何东西都补逗号
    func: bool = False  # 字母后面跟括号当函数调用
    raw: str = ""
    num_base: bool = False  # 乘方的底数是数字（2^n）


def _tokenize(tex: str) -> list[_Tok]:
    toks, space = [], False
    for m in _TOKEN.finditer(tex):
        cmd, num, letter, ws, cjk, char = m.groups()
        if ws is not None:
            space = True
            continue
        if cmd is not None:
            toks.append(_Tok("cmd", cmd, space))
        elif num is not None:
            toks.append(_Tok("num", num, space))
        elif letter is not None:
            toks.append(_Tok("letter", letter, space))
        elif cjk is not None:
            toks.append(_Tok("cjk", cjk, space))
        else:
            toks.append(_Tok("char", char, space))
        space = False
    return toks


class _Parser:
    def __init__(self, tex: str):
        self.rules = latex_rules()
        self.toks = _tokenize(tex)
        self.i = 0
        self.unknown: list[str] = []

    # ---- 词法辅助
    def peek(self) -> _Tok | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def at(self, kind: str, value: str) -> bool:
        t = self.peek()
        return t is not None and t.kind == kind and t.value == value

    def take(self) -> _Tok:
        t = self.toks[self.i]
        self.i += 1
        return t

    def expect(self, kind: str, value: str) -> None:
        if self.at(kind, value):
            self.i += 1

    # ---- 语法
    def seq(self, stop: tuple[str, str] | None = None, *more: tuple[str, str]) -> list[_Node]:
        stops = [s for s in (stop, *more) if s]
        items = []
        while self.peek() is not None and not any(self.at(*s) for s in stops):
            node = self.item()
            if node is None:
                continue
            if node.kind == "func" and self.peek() is not None and not any(self.at(*s) for s in stops) and not self._at_operator():
                node.arg = self.item()
            if node.kind == "group" and items and items[-1].kind == "op":
                node.extra = [items[-1].extra[1]]
            items.append(node)
        return items

    def _at_operator(self) -> bool:
        t = self.peek()
        if t.kind == "char":
            return t.value in "+-=<>/*,;:)]}|"
        return t.kind == "cmd" and "\\" + t.value in self.rules["symbols"]

    def arg(self) -> list[_Node]:
        if self.at("char", "{"):
            self.take()
            items = self.seq(("char", "}"))
            self.expect("char", "}")
            return items
        node = self.atom()
        return [node] if node is not None else []

    def raw_arg(self) -> str:
        if not self.at("char", "{"):
            t = self.take() if self.peek() else None
            return t.value if t else ""
        self.take()
        depth, out = 0, ""
        while self.peek() is not None:
            t = self.take()
            if t.kind == "char" and t.value == "{":
                depth += 1
            elif t.kind == "char" and t.value == "}":
                if depth == 0:
                    break
                depth -= 1
            out += (" " if t.space_before and out else "") + t.value
        return out

    def item(self) -> _Node | None:
        node = self.atom()
        return None if node is None else self.postfix(node)

    def postfix(self, node: _Node) -> _Node:
        sets = self.rules["sets"]
        while True:
            if self.at("char", "_"):
                self.take()
                sub = self.arg()
                if node.kind in ("big", "lim", "func"):
                    node.sub = sub
                elif node.kind == "var" and node.value + "+" in sets and _is_op(sub, "+"):
                    node = _Node("set", node.value + "+")
                else:
                    node = _Node("sub", args=[node], extra=sub)
            elif self.at("char", "^"):
                self.take()
                exp = self.arg()
                if node.kind in ("big", "func"):
                    node.sup = exp
                elif len(exp) == 1 and exp[0].kind == "cmd_circ":
                    node = _Node("degree", args=[node])
                elif len(exp) == 1 and exp[0].kind == "primemark":
                    node = _Node("prime", args=[node])
                elif node.kind == "var" and (_is_op(exp, "*") or _is_op(exp, "+")) and node.value + exp[0].extra[1] in sets:
                    node = _Node("set", node.value + exp[0].extra[1])
                else:
                    node = _Node("pow", args=[node], extra=exp)
            elif self.at("char", "'"):
                self.take()
                node = _Node("prime", args=[node])
            elif self.at("char", "!"):
                self.take()
                node = _Node("fact", args=[node])
            else:
                return node

    def atom(self) -> _Node | None:
        if self.peek() is None:
            return None
        t = self.take()
        r = self.rules
        if t.kind == "num":
            return _Node("num", t.value)
        if t.kind == "letter":
            return _Node("var", t.value)
        if t.kind == "cjk":
            return _Node("text", t.value)
        if t.kind == "char":
            v = t.value
            if v in "([":
                items = self.seq(("char", ")"), ("char", "]"))
                close = self.take().value if self.peek() is not None else ")"
                return _Node("group", v + close, args=items, flag=True)
            if v == "{":
                items = self.seq(("char", "}"))
                self.expect("char", "}")
                return _Node("seq", args=items)
            if v == "|":
                items = self.seq(("char", "|"))
                self.expect("char", "|")
                return _Node("abs", args=items)
            if v == ",":
                return _Node("comma")
            if v == ";":
                return _Node("text", "；")
            if v == "&":
                return _Node("comma")  # cases 里值和条件之间停一下
            if v == ":":
                return _Node("op", "比", extra=["op", ":"])
            if v == "*":
                return _Node("op", "乘", extra=["op", "*"])
            if v in r["symbols"]:
                s = r["symbols"][v]
                return _Node("op", s["say"], extra=[s["kind"], v])
            return None
        # 命令
        name = t.value
        if name in ("begin", "end"):
            self.raw_arg()  # 环境名本身不念
            return None
        if name == "\\":
            return _Node("text", "；")  # cases / aligned 的换行
        if name in r["ignore"]:
            if name in ("left", "right") and self.at("char", "."):
                self.take()
            return None
        if name in _FRAC:
            return _Node("frac", args=[self.arg(), self.arg()])
        if name == "sqrt":
            index = None
            if self.at("char", "["):
                self.take()
                index = self.seq(("char", "]"))
                self.expect("char", "]")
            return _Node("sqrt", args=[self.arg()], extra=index or [])
        if name in r["greek"]:
            return _Node("var", r["greek"][name])
        key = "\\" + name
        if key in r["symbols"]:
            s = r["symbols"][key]
            return _Node("op", s["say"], extra=[s["kind"], key])
        if name in r["functions"] or name == "log":
            return _Node("func", name)
        if name in _TEXT:
            return _Node("text", self.raw_arg())
        if name == "operatorname":
            return _Node("func", self.raw_arg())
        if name in r["passthrough"]:
            items = self.arg()
            if name in ("mathbb", "mathbf") and len(items) == 1 and items[0].kind == "var":
                items[0].flag = True
            return items[0] if len(items) == 1 else _Node("seq", args=items)
        if name in _VEC:
            return _Node("vec", args=[self.arg()])
        if name in _ELLIPSIS:
            return _Node("ellipsis")
        if name in _BIG:
            return _Node("big", _BIG[name])
        if name == "lim":
            return _Node("lim")
        if name in ("binom", "dbinom", "tbinom"):
            return _Node("binom", args=[self.arg(), self.arg()])
        if name == "{":
            items = self.seq(("cmd", "}"))
            self.expect("cmd", "}")
            return _Node("seq", args=items)
        if name == "%":
            return _Node("percent")
        if name == "circ":
            return _Node("cmd_circ")
        if name == "prime":
            return _Node("primemark")
        if name in ("}", "|"):
            return None
        self.unknown.append("\\" + name)
        return _Node("text", name)


def _is_op(items: list[_Node], raw: str) -> bool:
    return len(items) == 1 and items[0].kind == "op" and items[0].extra[1:] == [raw]


class _Reader:
    def __init__(self):
        self.r = latex_rules()

    def tpl(self, name: str, **values: str) -> str:
        return fill(self.r["templates"][name], **values)

    # 一串结点 → (读法, 是否复合)
    def seq(self, items: list[_Node]) -> tuple[str, bool]:
        parts: list[list[_Node]] = [[]]
        for n in items:
            if n.kind == "comma":
                parts.append([])
            else:
                parts[-1].append(n)
        if len(parts) == 1:
            return self.line(parts[0])
        parts = [p for p in parts if p]
        simple = all(len(p) == 1 for p in parts)
        sep = self.r["comma"]["list" if simple else "clause"]
        return sep.join(self.line(p)[0] for p in parts), True

    def line(self, items: list[_Node]) -> tuple[str, bool]:
        pieces = [p for p in (self.piece(n) for n in items) if p.text or p.kind in ("ellipsis", "percent")]
        pieces = self.combine(pieces)
        out, prev, compound = "", None, False
        for p in pieces:
            if p.kind in ("op", "rel"):
                if prev is None or prev.kind in ("op", "rel", "unary"):
                    if p.raw in ("-", "+"):
                        p = _Piece("负" if p.raw == "-" else "正", "unary")
                    out = join(out, p.text)
                    prev = p
                    continue
                compound = True
                if (prev.soft or prev.hard) and out and out[-1] not in _PUNCT:
                    out += "，"
                out = join(out, p.text)
            elif prev is None or prev.kind in ("op", "rel", "unary", "word", "text") or p.kind in ("word", "text"):
                out = join(out, p.text)
            elif self.juxtapose(prev, p):
                out = join(out, p.text)
            else:
                if prev.hard:
                    out += "，"
                out = join(join(out, "乘"), p.text)
            prev = p
        return out, compound

    @staticmethod
    def juxtapose(a: _Piece, b: _Piece) -> bool:
        if a.kind == "num":
            return b.kind in ("var", "sqrt") or (b.kind == "pow" and not b.num_base)
        if a.kind == "var":
            return b.kind == "var" or (b.kind == "pow" and not b.num_base) or b.raw == "tuple"
        return False

    def combine(self, pieces: list[_Piece]) -> list[_Piece]:
        out: list[_Piece] = []
        i = 0
        between = self.r["ellipsis"]
        while i < len(pieces):
            p = pieces[i]
            prev = out[-1] if out else None
            if p.kind == "percent":
                if prev is not None and prev.kind == "num":
                    out[-1] = _Piece(self.tpl("percent", arg=prev.text), "num")
                i += 1
                continue
            if p.kind == "ellipsis":
                nxt = pieces[i + 1] if i + 1 < len(pieces) else None
                if prev is not None and nxt is not None and prev.kind == "op" and nxt.kind == "op" and prev.text == nxt.text:
                    word = between["between_plus"] if prev.raw == "+" else between["between_times"] if prev.text == "乘" else None
                    if word:
                        out[-1] = _Piece(word, "op", raw="…")
                        i += 2
                        continue
                if prev is not None and nxt is not None and prev.kind not in ("op", "rel", "unary") and nxt.kind not in ("op", "rel"):
                    out.append(_Piece(between["between_times"], "op", raw="…"))  # a_1a_2\cdots a_n
                    i += 1
                    continue
                out.append(_Piece(between["other"], "word"))
                i += 1
                continue
            if prev is not None and prev.kind == "var" and prev.func and p.kind == "group":
                out[-1] = _Piece(join(prev.text, p.text), "sub", soft=p.hard or p.soft)
                i += 1
                continue
            if prev is not None and prev.kind == "num" and p.kind == "sub" and (len(out) < 2 or out[-2].kind != "unary"):
                out[-1] = _Piece(self.tpl("coef_sub", num=prev.text, arg=p.text), "sub", soft=p.soft)
                i += 1
                continue
            out.append(p)
            i += 1
        return out

    def piece(self, n: _Node) -> _Piece:
        r, k = self.r, n.kind
        if k == "num":
            return _Piece(cn_number(n.value), "num")
        if k == "var":
            if n.flag and n.value in r["sets"]:
                return _Piece(r["sets"][n.value], "var")
            return _Piece(n.value, "var", func=n.value in r["function_letters"])
        if k == "set":
            return _Piece(r["sets"][n.value], "var")
        if k == "text":
            return _Piece(n.value, "text")
        if k == "op":
            kind, raw = n.extra
            return _Piece(n.value, kind, raw=raw)
        if k == "seq":
            if len(n.args) == 1:
                return self.piece(n.args[0])
            text, comp = self.seq(n.args)
            return _Piece(text, "expr", soft=comp)
        if k == "group":
            commas = [i for i, x in enumerate(n.args) if x.kind == "comma"]
            prev_in = n.extra and n.extra[0] in ("\\in", "\\notin")
            if len(commas) == 1 and (n.value in r["interval"] and n.value != "()" or prev_in):
                i = commas[0]
                return _Piece(fill(r["interval"]["template"], kind=r["interval"][n.value], a=self.seq(n.args[:i])[0],
                                   b=self.seq(n.args[i + 1 :])[0]), "var")
            if len(n.args) == 1:
                p = self.piece(n.args[0])
                return _Piece(p.text, "group", soft=p.soft)
            text, comp = self.seq(n.args)
            if commas:
                return _Piece(text, "group", raw="tuple")  # 坐标 P(1,2)
            return _Piece(text, "group", hard=comp)
        if k == "abs":
            return _Piece(self.tpl("abs", arg=self.seq(n.args)[0]), "abs")
        if k == "frac":
            num, num_c = self.seq(n.args[0])
            den, den_c = self.seq(n.args[1])
            return _Piece(self.tpl("frac_den_compound" if den_c else "frac", num=num, den=den), "frac", soft=num_c)
        if k == "sqrt":
            arg, comp = self.seq(n.args[0])
            if n.extra:
                return _Piece(self.tpl("root", index=self.seq(n.extra)[0], arg=arg), "sqrt", soft=comp)
            return _Piece(self.tpl("sqrt_compound" if comp else "sqrt", arg=arg), "sqrt", soft=comp)
        if k == "sub":
            base = self.piece(n.args[0])
            sub, comp = self.seq(n.extra)
            return _Piece(self.tpl("sub", base=base.text, sub=sub), "sub", soft=comp or base.soft)
        if k == "pow":
            base = self.piece(n.args[0])
            return _Piece(join(base.text, self.power(n.extra)), "pow", soft=base.soft, num_base=base.kind == "num")
        if k == "degree":
            base = self.piece(n.args[0])
            return _Piece(join(base.text, r["powers"]["degree"]), base.kind)
        if k == "prime":
            base = self.piece(n.args[0])
            return _Piece(join(base.text, r["powers"]["prime"]), "var", func=base.func)
        if k == "fact":
            return _Piece(join(self.piece(n.args[0]).text, "的阶乘"), "pow")
        if k == "func":
            return self.function(n)
        if k == "vec":
            return _Piece(self.tpl("vector", arg=self.seq(n.args[0])[0]), "var")
        if k == "big":
            return self.big(n)
        if k == "lim":
            return _Piece(self.tpl("lim", cond=self.seq(n.sub or [])[0]), "word")
        if k == "binom":
            return _Piece(self.tpl("binom", n=self.seq(n.args[0])[0], k=self.seq(n.args[1])[0]), "var")
        if k == "ellipsis":
            return _Piece("", "ellipsis")
        if k == "percent":
            return _Piece("", "percent")
        if k == "cmd_circ":
            return _Piece(r["powers"]["degree"], "word")
        if k == "primemark":
            return _Piece(r["powers"]["prime"], "word")
        return _Piece("", "word")

    def power(self, exp: list[_Node]) -> str:
        powers = self.r["powers"]
        if len(exp) == 1 and exp[0].kind == "num" and exp[0].value in powers:
            return powers[exp[0].value]
        return fill(powers["template"], exp=self.seq(exp)[0])

    def function(self, n: _Node) -> _Piece:
        name = self.r["functions"].get(n.value, n.value)
        arg = self.piece(n.arg) if n.arg is not None else _Piece("", "word")
        if n.value == "log" and n.sub:
            text = self.tpl("log", base=self.seq(n.sub)[0], arg=arg.text)
        else:
            text = join(name, arg.text)
        if n.sup:
            text = join(text, self.power(n.sup))
        return _Piece(text, "func", soft=arg.soft or arg.hard)

    def big(self, n: _Node) -> _Piece:
        word = {"sum": "求和", "prod": "求积"}[n.value]
        if not n.sub or not n.sup:
            return _Piece(word, "word")
        eq = next((i for i, x in enumerate(n.sub) if x.kind == "op" and x.extra[1:] == ["="]), None)
        if eq is None:
            var, start = self.seq(n.sub)[0], ""
        else:
            var, start = self.seq(n.sub[:eq])[0], self.seq(n.sub[eq + 1 :])[0]
        return _Piece(self.tpl(n.value, var=var, **{"from": start, "to": self.seq(n.sup)[0]}), "word")


def read_latex(tex: str, *, strict: bool = False) -> str:
    """把 LaTeX 公式（不含 $）读成中文。strict=True 时遇到不认识的命令抛 ValueError。"""
    parser = _Parser(tex)
    items = parser.seq()
    if strict and parser.unknown:
        raise ValueError(f"不认识的 LaTeX 命令：{', '.join(parser.unknown)}")
    return _Reader().seq(items)[0]


def unknown_commands(tex: str) -> list[str]:
    parser = _Parser(tex)
    parser.seq()
    return parser.unknown
