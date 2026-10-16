"""读取 data/ 下的规则表（安装后在包内 zh_math_reading/data，开发时在仓库根目录 data/）。"""

from __future__ import annotations

from functools import cache
from importlib import resources
from pathlib import Path

import yaml


def _read(name: str) -> str:
    repo_copy = Path(__file__).resolve().parents[2] / "data" / name
    if repo_copy.is_file():
        return repo_copy.read_text(encoding="utf-8")
    return resources.files("zh_math_reading").joinpath("data", name).read_text(encoding="utf-8")


@cache
def latex_rules() -> dict:
    return yaml.safe_load(_read("latex.yaml"))


@cache
def polyphones() -> dict:
    return yaml.safe_load(_read("polyphones.yaml"))
