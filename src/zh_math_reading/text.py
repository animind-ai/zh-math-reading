"""旁白句子的读法处理：展开 $...$、安全改写、风险检查。

书签 `{@name}` 原样保留：调用方在 normalize 之后再去掉书签、计算书签位置，位置自然对得上展开后的文本。
"""

from __future__ import annotations

import re

from .data import polyphones
from .latex import _PUNCT, join, read_latex

BOOKMARK = re.compile(r"\{@[A-Za-z_][A-Za-z0-9_]*\}")
_MARKS_AT_END = re.compile(r"(?:\{@[A-Za-z_][A-Za-z0-9_]*\})+$")
_LEADING_MARKS = re.compile(r"((?:\{@[A-Za-z_][A-Za-z0-9_]*\})*) *")
_MATH = re.compile(r"(?<!\\)\$(.+?)(?<!\\)\$")
_CN_NUMERALS = set("零一二三四五六七八九十百千万两")

# 命名句：“新名词：d 等差比数列” —— 冒号后的单个字母常被 TTS 吞掉，改成“新名词，叫 d 等差比数列”。
_NAMING_NOUN = re.compile(r"(名词|名字|名称|新概念|新定义)：((?:\{@[A-Za-z_][A-Za-z0-9_]*\})*)[ ]?([A-Za-z])(?![A-Za-z0-9])")
# “记为：d”“称为：d” —— 去掉冒号。
_NAMING_VERB = re.compile(r"(叫做|叫作|称为|称作|记为|记作|叫)：((?:\{@[A-Za-z_][A-Za-z0-9_]*\})*)[ ]?([A-Za-z])(?![A-Za-z0-9])")
_AFTER_PAUSE = re.compile(r"([：；:;])((?:\{@[A-Za-z_][A-Za-z0-9_]*\})*)[ ]*([A-Za-z])")
_SENTENCE_END = re.compile(r"[。！？!?]")
LONG_SENTENCE = 60


def visible(text: str) -> str:
    """去掉书签后的文本（TTS 真正念的内容）。"""
    return BOOKMARK.sub("", text)


def _needs_space(a: str, b: str) -> bool:
    return bool(a) and bool(b) and join(a, b) != a + b


def _lone_letter(text: str, end: int) -> bool:
    """text[end-1] 是一个字母：它后面（跳过空格）不是字母、数字或中文数字时，算“孤立字母”（不是 b 二、a n 这种带下标的写法）。"""
    rest = visible(text[end:]).lstrip(" ")
    if not rest:
        return True
    c = rest[0]
    return not (c.isascii() and c.isalnum()) and c not in _CN_NUMERALS and c not in _PUNCT


def _lead(text: str) -> re.Match:
    return _LEADING_MARKS.match(text)


def expand_math(text: str) -> str:
    """把句子里的 $...$ 换成读法；书签留在原处。

    公式两侧的空格按读法重新定：读法边上是字母且挨着中文时留一个空格（“数列 b n 的”），
    否则去掉作者为排版写的空格（“所以 $\\lambda$” → “所以拉姆达”）。空格总放在书签前面，书签仍指向公式读法的第一个字。
    """
    if "$" not in text:
        return text
    out, pos = "", 0
    for m in _MATH.finditer(text):
        if m.start() < pos:
            continue
        out += text[pos : m.start()]
        pieces = BOOKMARK.split(m.group(1))
        marks = BOOKMARK.findall(m.group(1))
        reading = read_latex(pieces[0])
        for mark, piece in zip(marks, pieces[1:]):
            said = read_latex(piece)
            reading += (" " if _needs_space(visible(reading)[-1:], said[:1]) else "") + mark + said
        said = visible(reading)
        # 左侧
        tail = _MARKS_AT_END.search(out)
        cut = tail.start() if tail else len(out)
        head, left_marks = out[:cut], out[cut:]
        stripped = head.rstrip(" ")
        if stripped:
            head = stripped + (" " if _needs_space(visible(stripped)[-1:], said[:1]) else "")
        out = head + left_marks + reading
        # 右侧
        pos = m.end()
        if text[pos : pos + 1] == "-" and not visible(text[pos + 1 :])[:1].isascii():
            pos += 1  # “$d$-等差比数列”里的连字符只是排版，读作“d 等差比数列”
        lead = _lead(text[pos:])
        rest = text[pos + lead.end() :]
        if rest and not rest.startswith("$"):
            out += (" " if _needs_space(said[-1:], visible(rest)[:1]) else "") + lead.group(1)
            pos += lead.end()
    out += text[pos:]
    return out.replace("\\$", "$")


def _rewrite_naming(text: str) -> str:
    def noun(m: re.Match) -> str:
        if not _lone_letter(m.string, m.end()):
            return m.group(0)
        return f"{m.group(1)}，叫 {m.group(2)}{m.group(3)}"

    def verb(m: re.Match) -> str:
        if not _lone_letter(m.string, m.end()):
            return m.group(0)
        return f"{m.group(1)} {m.group(2)}{m.group(3)}"

    return _NAMING_VERB.sub(verb, _NAMING_NOUN.sub(noun, text))


def normalize(spoken: str) -> str:
    """生成送给 TTS 的读法文本（书签保留）。

    - 展开 `$...$` 公式；
    - 命名句里冒号后的孤立字母改写（“新名词：d 等差比数列” → “新名词，叫 d 等差比数列”）。

    不含 `$`、也没有上述句式的文本原样返回（逐字节相同），已经合成过的音频缓存不受影响。
    多音字只在 lint() 里提示，不自动替换。
    """
    return _rewrite_naming(expand_math(spoken))


# ---------------------------------------------------------------- lint

def _context(text: str, start: int, end: int, width: int = 6) -> str:
    return text[max(0, start - width) : end + width]


def _polyphone_index() -> tuple[dict, dict[str, list[dict]]]:
    data = polyphones()
    by_first: dict[str, list[dict]] = {}
    for e in data["entries"]:
        by_first.setdefault(e["word"][0], []).append(e)
    for v in by_first.values():
        v.sort(key=lambda e: -len(e["word"]))
    return data["chars"], by_first


def polyphone_warnings(text: str) -> list[str]:
    """正向最大匹配扫一遍：命中 risky 词条、或 strict 多音字落在未收录的上下文里，都给出提示。"""
    chars, by_first = _polyphone_index()
    out, i = [], 0
    while i < len(text):
        hit = next((e for e in by_first.get(text[i], []) if text.startswith(e["word"], i)), None)
        if hit:
            if hit.get("risky"):
                tip = f"；可改成「{hit['rewrite']}」" if hit.get("rewrite") else ""
                out.append(f"多音字「{hit['char']}」在「{hit['word']}」里读 {hit['pinyin']}，TTS 容易读错（…{_context(text, i, i + len(hit['word']))}…）{tip}")
            i += len(hit["word"])
            continue
        c = text[i]
        if c in chars and chars[c].get("strict"):
            out.append(f"多音字「{c}」的上下文没有收录，确认读音（{chars[c]['why']}）：…{_context(text, i, i + 1)}…")
        i += 1
    return out


def lint(spoken: str) -> list[str]:
    """检查一句旁白里容易让 TTS 念错的写法，返回中文提示（空列表表示没问题）。"""
    text = visible(spoken)
    out = []
    if "$" in text or "\\" in text:
        out.append("还有没展开的公式或 LaTeX 命令（$ 或 \\）")
    for m in re.finditer(r"\d+(?:\.\d+)?", text):
        out.append(f"阿拉伯数字「{m.group(0)}」：写成中文数字，TTS 才会按中文念（…{_context(text, m.start(), m.end())}…）")
    for m in _AFTER_PAUSE.finditer(text):
        out.append(f"「{m.group(1)}」后紧跟字母「{m.group(3)}」：TTS 常把停顿后的字母吞掉（…{_context(text, m.start(), m.end())}…）；"
                   f"可以把「{m.group(1)}」换成逗号（命名句加“叫”），或调整语序让字母不在停顿之后")
    start = 0
    for m in [*_SENTENCE_END.finditer(text), None]:
        end = m.end() if m else len(text)
        sentence = text[start:end].strip()
        n = len(sentence.replace(" ", ""))
        if n > LONG_SENTENCE:
            out.append(f"句子太长（{n} 字 > {LONG_SENTENCE}）：TTS 容易漏掉或自己编一段，拆成两句（{sentence[:12]}…）")
        start = end
    out.extend(polyphone_warnings(text))
    return out
