import traceback
import logging
from pathlib import Path

import pdfplumber


log = logging.getLogger("__name__")


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
