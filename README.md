# zh-math-reading

数学讲解旁白的中文读法：把 LaTeX 公式读成中文，收录数学语境的多音字，并在送给 TTS 之前检查容易念错的写法。

`animind-voice` 合成旁白前用它处理 scene-spec 里 `say` 的文本：旁白里可以直接写 `$a_{n+1}^2$`，合成时念成“a n 加一的平方”。

## 用法

```python
from zh_math_reading import read_latex, normalize, lint

read_latex(r"a_{n+1}^2-a_na_{n+2}=d")
# 'a n 加一的平方，减 a n 乘 a n 加二，等于 d'

normalize(r"第二问，{@p2}数列 $b_n$ 从第一项起就是等差比数列，而且 $d=1$。")
# '第二问，{@p2}数列 b n 从第一项起就是等差比数列，而且 d 等于一。'

lint("得到：{@ratio}b n 加 b n 加二")
# ['「：」后紧跟字母「b」：TTS 常把停顿后的字母吞掉（…）；…']
```

命令行：

```bash
uv run zh-math-reading read 'x_{n+1}=px_n+q'        # x n 加一，等于 p 乘 x n 加 q
uv run zh-math-reading normalize '新名词：$d$-等差比数列'  # 新名词，叫 d 等差比数列
uv run zh-math-reading lint '中间差了三项'               # 提示“差了”读 chà；有提示时退出码为 1
```

### `read_latex(tex) -> str`

读法风格取自 §6.7 已经配好音的讲稿：

| 写法 | 读法 |
|---|---|
| `a_n`、`a_{n+1}`、`A_8` | a n、a n 加一、A 八 |
| `x^2`、`x^3`、`2^n`、`2^{2n+2}` | x 的平方、x 的立方、二的 n 次方、二的二 n 加二次方 |
| `\frac{1}{2}`、`\dfrac{n+1}{2}`、`\frac{1}{3^n-1}` | 二分之一、二分之 n 加一、三的 n 次方减一，分之一 |
| `a_na_{n+2}`、`2b_{n+1}`、`2n`、`\frac{1}{6}n` | a n 乘 a n 加二、二倍的 b n 加一、二 n、六分之一乘 n |
| `(n+1)(n+2)` | n 加一，乘 n 加二 |
| `a_1+a_2+\cdots+a_n` | a 一加 a 二一直加到 a n |
| `\le`、`\ge`、`\ne`、`\cdot`、`\times` | 小于等于、大于等于、不等于、乘、乘 |
| `\lambda`、`\alpha`、`\pi` | 拉姆达、阿尔法、派 |
| `n\in\mathbf{N}^*`、`[0,1)` | n 属于正整数集、左闭右开区间零到一 |
| `\sqrt{x+1}`、`\log_2 x`、`\|x-1\|` | 根号下 x 加一、以二为底 x 的对数、x 减一的绝对值 |
| `121`、`3.14`、`50\%` | 一百二十一、三点一四、百分之五十 |

拼接规则：字母两侧留一个空格（TTS 不会把相邻字母粘成英文单词），中文之间不留；带复合下标或多项式括号的项后面跟运算符时补一个逗号停顿。完整规则表和 70 多条示例在 [`data/latex.yaml`](data/latex.yaml)，示例同时是测试用例。不认识的命令按名字原样输出，`read_latex(tex, strict=True)` 会报错。

### `normalize(spoken) -> str`

生成送给 TTS 的文本：

- 展开句子里的 `$...$`，并按读法重新安排公式两侧的空格（`数列$b_n$的` → `数列 b n 的`，`所以 $\lambda$` → `所以拉姆达`）；`$d$-等差比数列` 里排版用的连字符去掉；
- 命名句里冒号后的孤立字母改写：`新名词：d 等差比数列` → `新名词，叫 d 等差比数列`（TTS 常把冒号后的单个字母吞掉）；
- 书签 `{@name}` 原样保留，展开时补的空格放在书签前面，书签仍指向公式读法的第一个字。调用方在 normalize 之后再去掉书签、计算位置即可。

**不含 `$`、也没有命名句式的文本原样返回（逐字节相同）**，已经合成过的音频缓存不受影响。多音字只提示、不自动替换。

### `lint(spoken) -> list[str]`

返回中文提示：

- 冒号、分号后紧跟字母（§6.7 回听报告里，“得到：b n 加 b n 加二”“；d 不等于零”都吞了字）；
- 句子超过 60 字（容易漏一段或编一段）；
- 阿拉伯数字、没展开的 `$` 或 `\`；
- 多音字：命中 `risky` 词条（“差了” chà、“得证明” děi、“倒数第” shǔ……），或 `strict` 多音字（差、重、行、率、长、调、奇、称）出现在没有收录的上下文里。

## 数据

- [`data/polyphones.yaml`](data/polyphones.yaml)：20 个多音字、110 多个数学词条，每条有读音和收录原因，部分附替换说法。按正向最大匹配查词，“公差一个”不会被“差一个”误报。
- [`data/latex.yaml`](data/latex.yaml)：符号、希腊字母、函数、数集、乘方、模板和示例。

## 开发

```bash
uv sync
uv run pytest
uvx ruff check .
```

## 作者与许可

作者：Boxi Yu（[@BoxiYu](https://github.com/BoxiYu)）

代码以 [MIT 许可](LICENSE)发布；`data/` 下的读法数据和 `tests/fixtures/` 里的旁白以 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh-hans) 发布，转载和改编请署名 Boxi Yu。
