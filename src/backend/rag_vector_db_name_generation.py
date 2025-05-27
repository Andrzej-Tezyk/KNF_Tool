# current solution for database naming is garbage
# will fail if name too short
# TODO: come up with something better
# will most likely require major code changes


def replace_polish_chars(text: str) -> str:
    """
    Replaces polish characters with latin characters.
    This function replaces every diacritical sign of the Polish alphabet in a given string
    with their corresponding character from the Latin alphabet using a mapping dictionary.
    This function is used for document names only.
    Examples:
        >>> polish_to_ascii("Zażółć gęślą jaźń.")
        Zazolc gesla jazn.
    Args:
        text: A string of characters
    Returns:
        A string of characters without Polish diacritital signs.
    Raises:
        None
    """
    polish_to_ascii = {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ż": "z",
        "ź": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ż": "Z",
        "Ź": "Z",
    }

    return "".join(polish_to_ascii.get(c, c) for c in text)
