# current solution for database naming is garbage
# will fail if name too short
# TODO: come up with something better
# will most likely require major code changes

from pathlib import Path
import re


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


def generate_vector_db_document_name(doc_path: Path, max_length=60) -> str:
    """
    Generates name for a chromadb database.
    """
    name = str(doc_path).replace("(plik PDF)", "")
    name = name.replace(" ", "_").lower()
    name = name if len(str(name)) <= max_length else name[0:max_length]
    name = name[0:-1] if name[-1] == "_" else name  # removing '_' from the ends
    name = name[1:] if name[0] == "_" else name
    name = replace_polish_chars(name)
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name


def extract_title_from_filename(filename: str) -> str:
    """
    Extracts document title for frontend display
    """
    stem = filename[:-4] if filename.lower().endswith(".pdf") else filename
    parts = stem.split("_", 2)
    if len(parts) == 3:
        title = parts[2]
        title = title.replace("(plik PDF)", "")
        title = title[0:-1] if title[-1] == "_" else title  # removing '_' from the ends
        title = title[1:] if title[0] == "_" else title
        title = title[0:-1] if title[-1] == " " else title  # removing ' ' from the ends
        title = title[1:] if title[0] == " " else title
        return title
    return stem
