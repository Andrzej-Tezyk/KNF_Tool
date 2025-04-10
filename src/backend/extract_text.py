import traceback
import re
import logging
from pathlib import Path

import pdfplumber


log = logging.getLogger("__name__")


POLISH_CHARS = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"


def clean_polish_spacing(text: str) -> str:
    """
    A problem with extracting text from .pdf in polish language was found. 
    When polish alphabet letter is within a word a " " is created before it.
    Random unnecessary spaces are created as a result of how pypdf2 works.
    PyPDF2 reconstruct text based on proximity, which isn't always accurate.
    Polish characters (or any accented glyphs) might be slightly offset in the font, 
    causing spacing algorithms to think they’re a new "word" and insert a space.
    Like: "słówko" -> "s ł ó wko"

    Args:
        text: Text extracted from pdf document.

    Returns:
        A string containing cleaned text.
    """

    # remove line breakes that are not paragraph breakes
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # remove spaces before Polish chars
    text = re.sub(rf"\s([{POLISH_CHARS}])", r"\1", text)

    # fix hypernated line breakes
    text = re.sub(r"-\s*\n\s*", "", text)

    return text.strip()

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts text from a PDF file.

    This function reads a PDF file, extracts text from each page, and concatenates
    the extracted text into a single string. If an error occurs during extraction,
    it logs the error and returns an empty string.

    Examples:
        >>> extract_text_from_pdf(Path("document.pdf"))
        'This is the extracted text from the PDF document.'

    Args:
        pdf_path: A Path object representing the PDF file to extract text from.

    Returns:
        A string containing the extracted text from the PDF. If an error occurs,
        an empty string is returned.

    Raises:
        Exception: Any exceptions encountered while reading or extracting text
        from the PDF are logged and handled.
    """

    try:
        with open(pdf_path, "rb") as file:
            full_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:  # some pages may return None
                        full_text += page_text + "\n\n"  # paragraph separator
            return full_text.strip()
    
    except Exception as e:
        log.error(f"Error processing {pdf_path}: {str(e)}")
        traceback.print_exc()
        return ""



'''
def extract_text_from_pdf(file_path: str) -> str:
    full_text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:  # Some pages may return None
                cleaned = clean_pdf_text(page_text)
                full_text += cleaned + "\n\n"  # Paragraph separator
    return full_text.strip()
'''