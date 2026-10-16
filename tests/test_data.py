from zh_math_reading.data import latex_rules, polyphones


def test_polyphone_entries_are_complete():
    data = polyphones()
    entries = data["entries"]
    assert len(entries) >= 40
    words = [e["word"] for e in entries]
    assert len(words) == len(set(words)), "词条重复"
    for e in entries:
        assert e["char"] in e["word"], e
        assert e["pinyin"] and e["why"], e
        if e.get("rewrite"):
            assert e.get("risky"), e
    for c, info in data["chars"].items():
        assert len(c) == 1 and info["default"] and info["why"]
        assert any(e["char"] == c for e in entries), f"「{c}」没有词条"


def test_latex_rules_shape():
    r = latex_rules()
    for key, rule in r["symbols"].items():
        assert rule["kind"] in ("op", "rel", "word"), key
    assert len(r["examples"]) >= 50
    assert r["powers"]["2"] == "的平方" and r["powers"]["3"] == "的立方"
