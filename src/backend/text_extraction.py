import time
import traceback
from pathlib import Path
from typing import Any
from collections.abc import Generator

import google.generativeai as genai  # type: ignore[import-untyped]
from dotenv import load_dotenv
from PyPDF2 import PdfReader

load_dotenv()


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
            pdf = PdfReader(file)
            print(f"Number of pages: {len(pdf.pages)}")

            text = ""
            try:
                for page in pdf.pages:  # loop through all pages
                    text += page.extract_text()
            except Exception as e:
                print(f"Something went wrong with {pdf_path}. Error messange: {e}")
                traceback.print_exc()
        return text
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        traceback.print_exc()
        return ""


def process_pdf(prompt: str, pdf: Path, model: Any, change_lebgth_checkbox: str, output_size: int, slider_value: int) -> Generator:
    """Processes a single PDF document using the provided prompt and returns the result.

    This function uploads a PDF document, sends it to a model with the given prompt,
    and retrieves a generated response. The response
    text is cleaned to remove double spaces before being returned.

    Examples:
        >>> process_pdf("Summarize this document", Path("report.pdf"), model, 100)
        {'pdf_name': 'report', 'content': 'This document summarizes ...'}

    Args:
        prompt: A string containing the user’s prompt for processing the document.
        pdf: A Path object representing the PDF file to be processed.
        model: A generative AI model used to process the document.
        output_size: A string defining the approximate word limit for the response.

    Returns:
        A dictionary containing:
        - "pdf_name": The name of the processed PDF (without extension).
        - "content": The generated response text.
        - "error": An error message if processing fails.

    Raises:
        Exception: If an error occurs during processing, it is logged and returned
        in the response dictionary.
    """

    if not prompt:
        yield {"error": "No prompt provided"}

    else:
        try:
            print(f"Document: {pdf.stem} is beeing analyzed.")
            file_to_send = genai.upload_file(pdf)
            print(f"PDF uploaded successfully. File metadata: {file_to_send}\n")
            response = model.generate_content(
                [
                    prompt
                    + f"(Please provide {output_size} size response)" if change_lebgth_checkbox == "True" else prompt,
                    file_to_send,
                ],
                stream=True, generation_config = {"temperature":slider_value}
            )
            # split its text into smaller sub-chunks
            for response_chunk in response:
                # clean up the chunk text (removes extra spaces)
                chunk_text = response_chunk.text.replace("  ", " ")
                words = chunk_text.split(" ")
                sub_chunk = ""
                for word in words:
                    sub_chunk = sub_chunk + " " + word if sub_chunk else word
                    if len(sub_chunk.split()) >= 3:  # size of subchunk here
                        yield {"pdf_name": pdf.stem, "content": sub_chunk + " "}
                        sub_chunk = ""
                        time.sleep(0.2)
                # yield remaining words
                if sub_chunk:
                    yield {"pdf_name": pdf.stem, "content": sub_chunk + " "}
                    time.sleep(0.1)
            print(f"Response for: {pdf.stem} was saved!\n")
            time.sleep(1)  # lower API request rate per sec
        except Exception as e:
            print(f"There is a problem with {pdf.stem}. \n Error message: {e}\n")
            traceback.print_exc()
            yield {"error": f"An error occurred while processing {pdf.stem}: {str(e)}"}
