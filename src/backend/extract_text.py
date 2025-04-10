import traceback
import re
import logging
from pathlib import Path

from PyPDF2 import PdfReader


log = logging.getLogger("__name__")


POLISH_CHARS = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"


def clean_polish_spacing(text: str) -> str:
    """
    A problem with extracting text from .pdf in polish language was found. 
    When polish alphabet letter is within a word a " " is created before it.
    Like: "słówko" -> "s ł ó wko"

    Args:
        text: Text extracted from pdf document.

    Returns:
        A string containing cleaned text.
    """
    return re.sub(rf"\s([{POLISH_CHARS}])", r"\1", text)

def extract_text_from_pdf(pdf_path: Path, language: str) -> str:
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
            pdf = PdfReader(file)
            log.debug(f"Number of pages: {len(pdf.pages)}")

            text = ""
            try:
                for page in pdf.pages:  # loop through all pages
                    text += page.extract_text()
            except Exception as e:
                log.error(f"Something went wrong with {pdf_path}. Error messange: {e}")
                traceback.print_exc()

        if language == "polish":
            text = clean_polish_spacing(text)

        text = text.replace("  ", " ")

        return text
    
    except Exception as e:
        log.error(f"Error processing {pdf_path}: {str(e)}")
        traceback.print_exc()
        return ""
