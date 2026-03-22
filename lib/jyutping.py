import ToJyutping


def annotate(text: str) -> list[dict]:
    """Convert text to list of {char, jyutping} dicts.

    Punctuation and whitespace get jyutping=None.
    """
    result = []
    pairs = ToJyutping.get_jyutping_list(text)
    for char, jp in pairs:
        if char.strip() == "":
            continue
        result.append({"char": char, "jyutping": jp if jp else None})
    return result
