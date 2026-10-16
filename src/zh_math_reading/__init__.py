"""数学旁白的中文读法：LaTeX 转读法、多音字检查、给 TTS 用的安全改写。"""

from .latex import read_latex
from .numbers import cn_int, cn_number
from .text import lint, normalize

__all__ = ["cn_int", "cn_number", "lint", "normalize", "read_latex"]
