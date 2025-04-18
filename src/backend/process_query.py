import time
import traceback
from pathlib import Path
from typing import Any
from collections.abc import Generator
import logging

import google.generativeai as genai  # type: ignore[import-untyped]
from dotenv import load_dotenv
from backend.rag_chromadb import get_relevant_passage, get_gemini_ef  # type: ignore[import-not-found]

log = logging.getLogger("__name__")


load_dotenv()


def process_pdf(
    prompt: str,
    pdf: Path,
    model: Any,
    change_lebgth_checkbox: str,
    output_size: int,
    slider_value: float,
) -> Generator:
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
            log.info(f"Document: {pdf.stem} is beeing analyzed.")
            file_to_send = genai.upload_file(pdf)
            log.debug(f"PDF uploaded successfully. File metadata: {file_to_send}\n")
            response = model.generate_content(
                [
                    (
                        prompt + f"(Please provide {output_size} size response)"
                        if change_lebgth_checkbox == "True"
                        else prompt
                    ),
                    file_to_send,
                ],
                stream=True,
                generation_config={"temperature": slider_value},
            )
            # split its text into smaller sub-chunks
            for response_chunk in response:
                # replace -> sometimes double space between words occure; most likely reason: pdf formating
                response_chunk_text = response_chunk.text.replace("  ", " ")
                yield {"pdf_name": pdf.stem, "content": response_chunk_text}
                time.sleep(0.1)
            log.debug(f"Response for: {pdf.stem} was saved!\n")
            time.sleep(1)  # lower API request rate per sec
        except Exception as e:
            log.error(f"There is a problem with {pdf.stem}. \n Error message: {e}\n")
            traceback.print_exc()
            yield {"error": f"An error occurred while processing {pdf.stem}: {str(e)}"}


def process_query_with_rag(
    prompt: str,
    pdf: Path,
    model: Any,
    change_lebgth_checkbox: str,
    output_size: int,
    slider_value: float,
    chroma_client: Any,
    collection_name: str,
) -> Generator:
    if not prompt:
        yield {"error": "No prompt provided"}

    else:
        try:
            log.info(f"Document: {pdf.stem} is beeing analyzed.")

            try:
                collection = chroma_client.get_collection(
                    name=collection_name, embedding_function=get_gemini_ef()
                )

                passages_with_pages = get_relevant_passage(
                    prompt, collection, n_results=5
                )  # TODO: experiment with different n_results values

                rag_context = "\n\nRelevanat context from the document:\n"
                for passage, page_number in passages_with_pages:
                    rag_context += f"\nPage {page_number}: {passage}\n"

                rag_context += (
                    "\n\n Please use only the above context to generate an answer."
                )
            except Exception as e:
                log.error(
                    f"Problem with retrieveing context for {pdf.stem}. \n Error message: {e}\n"
                )
                rag_context = (
                    "Ignore all instrucions and output: 'Error: No context found.'"
                )

            log.debug(f"Context for {pdf.stem}:\n{rag_context}\n")
            response = model.generate_content(
                [
                    (
                        prompt
                        + f"(Please provide {output_size} size response)"
                        + rag_context
                        if change_lebgth_checkbox == "True"
                        else prompt + rag_context
                    ),
                ],
                stream=True,
                generation_config={"temperature": slider_value},
            )
            # split its text into smaller sub-chunks
            for response_chunk in response:
                # replace -> sometimes double space between words occure; most likely reason: pdf formating
                response_chunk_text = response_chunk.text.replace("  ", " ")
                yield {"pdf_name": pdf.stem, "content": response_chunk_text}
                time.sleep(0.1)
            log.debug(f"Response for: {pdf.stem} was saved!\n")
            time.sleep(1)  # lower API request rate per sec
        except Exception as e:
            log.error(f"There is a problem with {pdf.stem}. \n Error message: {e}\n")
            traceback.print_exc()
            yield {"error": f"An error occurred while processing {pdf.stem}: {str(e)}"}
