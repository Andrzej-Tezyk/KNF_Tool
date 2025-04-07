import re
import logging

import google.generativeai as genai
from cromadb 
from backend.extract_text import extract_text_from_pdf

log = logging.getLogger("__name__")

def split_text(text: str):
    """
    Splits a text string into a list of non-empty substrings based on the specified pattern.
    The "\n \n" pattern will split the document paragraph by paragraph
    Parameters:
    - text (str): The input text to be split.

    Returns:
    - List[str]: A list containing non-empty substrings obtained by splitting the input text.

    """
    split_text = re.split('\n \n', text)
    return [i for i in split_text if i != ""]

chunked_text = split_text(text=pdf_text)