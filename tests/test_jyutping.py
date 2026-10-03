from lib.jyutping import annotate


def test_chinese_characters_get_jyutping():
    assert annotate("海闊天空") == [
        {"char": "海", "jyutping": "hoi2"},
        {"char": "闊", "jyutping": "fut3"},
        {"char": "天", "jyutping": "tin1"},
        {"char": "空", "jyutping": "hung1"},
    ]


def test_punctuation_has_no_jyutping():
    chars = annotate("你，好！")
    assert [c["char"] for c in chars] == ["你", "，", "好", "！"]
    assert chars[1]["jyutping"] is None and chars[3]["jyutping"] is None


def test_latin_words_stay_whole_and_keep_spaces():
    chars = annotate("I love  you 你")
    assert [c["char"] for c in chars] == ["I", " ", "love", " ", "you", " ", "你"]
    assert all(c["jyutping"] is None for c in chars[:-1])
    assert chars[-1]["jyutping"] == "nei5"


def test_apostrophes_and_digits_join_words():
    assert [c["char"] for c in annotate("don't 2046")] == ["don't", " ", "2046"]


def test_surrounding_whitespace_is_dropped():
    assert [c["char"] for c in annotate("  我  ")] == ["我"]
    assert annotate("   ") == []
