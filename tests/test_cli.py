from zh_math_reading.cli import main


def test_cli(capsys):
    assert main(["read", "a_{n+1}"]) == 0
    assert capsys.readouterr().out.strip() == "a n 加一"
    assert main(["normalize", "数列 $b_n$ 的通项"]) == 0
    assert capsys.readouterr().out.strip() == "数列 b n 的通项"
    assert main(["lint", "得到：b n 加一"]) == 1
    assert "后紧跟字母" in capsys.readouterr().out
    assert main(["lint", "公差为一"]) == 0
