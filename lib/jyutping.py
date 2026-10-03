import ToJyutping


def _is_word_char(char: str) -> bool:
    return (char.isascii() and char.isalnum()) or char in "'’"


def annotate(text: str) -> list[dict]:
    """Convert text to list of {char, jyutping} dicts.

    Punctuation, Latin words and spaces get jyutping=None. Runs of Latin
    letters/digits are merged into one token ("love", not "l", "o", ...) and
    whitespace collapses to a single " " token so mixed-language lyrics keep
    their word boundaries.
    """
    result = []
    for char, jp in ToJyutping.get_jyutping_list(text):
        if char.isspace():
            if result and result[-1]["char"] != " ":
                result.append({"char": " ", "jyutping": None})
            continue
        if (
            not jp
            and _is_word_char(char)
            and result
            and result[-1]["jyutping"] is None
            and all(_is_word_char(c) for c in result[-1]["char"])
        ):
            result[-1]["char"] += char
            continue
        result.append({"char": char, "jyutping": jp or None})
    if result and result[-1]["char"] == " ":
        result.pop()
    return result
