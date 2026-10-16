"""命令行：

    zh-math-reading read 'a_{n+1}^2'          # 公式 → 读法
    zh-math-reading normalize '数列 $b_n$ 的通项'  # 句子 → 送给 TTS 的读法
    zh-math-reading lint '新名词：d 等差比数列'     # 检查容易念错的写法

不给文本时从标准输入逐行读取。lint 有提示时退出码为 1。
"""

from __future__ import annotations

import argparse
import sys

from .latex import read_latex
from .text import lint, normalize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zh-math-reading")
    parser.add_argument("command", choices=["read", "normalize", "lint"])
    parser.add_argument("text", nargs="*")
    args = parser.parse_args(argv)
    lines = args.text or [line.rstrip("\n") for line in sys.stdin if line.strip()]
    found = 0
    for line in lines:
        if args.command == "read":
            print(read_latex(line))
        elif args.command == "normalize":
            print(normalize(line))
        else:
            warnings = lint(normalize(line))
            found += len(warnings)
            for w in warnings:
                print(f"⚠ {w}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
