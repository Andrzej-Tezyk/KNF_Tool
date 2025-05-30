import time
import traceback
from pathlib import Path
from typing import Any
from collections.abc import Generator
import logging

import google.generativeai as genai
from dotenv import load_dotenv
from backend.rag_chromadb import get_gemini_ef  # type: ignore[import-not-found]
from backend.rag_use_chroma_collections import get_relevant_passage  # type: ignore[import-not-found]
from backend.prompt_enhancer import enhance_prompt  # type: ignore[import-not-found]

log = logging.getLogger("__name__")

PROJECT_ROOT = Path(__file__).parent.parent.parent

load_dotenv()

# Number of pages to retrieve for RAG context by default
DEFAULT_RAG_CONTEXT_PAGES = 5
# Delay between yielding response chunks
STREAM_RESPONSE_CHUNK_DELAY_SECONDS = 0.1
# Delay after processing a document/query, e.g., for API rate limiting
POST_PROCESS_DELAY_SECONDS = 1.0

def process_pdf(
    prompt: str,
    pdf: Path,
    model: Any,
    change_length_checkbox: str,
    enhancer_checkbox: str,
    output_size: int,
    temperature_slider_value: float,
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

    try:
        if enhancer_checkbox == "True":
            prompt = enhance_prompt(prompt, model)
            log.debug(f"Improved prompt: {prompt}")

    except Exception as e:
        log.error(
            f"Problem with prompt enhancer for {pdf.stem}. \n Error message: {e}\n"
        )

    else:
        try:
            log.info(f"Document: {pdf.stem} is beeing analyzed.")
            file_to_send = genai.upload_file(pdf)
            log.debug(f"PDF uploaded successfully. File metadata: {file_to_send}\n")
            response = model.generate_content(
                [
                    (
                        prompt + f"(Please provide {output_size} size response)"
                        if change_length_checkbox == "True"
                        else prompt
                    ),
                    file_to_send,
                ],
                stream=True,
                generation_config={"temperature": temperature_slider_value},
            )

            for response_chunk in response:
                # replace -> sometimes double space between words occure; most likely reason: pdf formating
                response_chunk_text = response_chunk.text.replace("  ", " ")
                yield {"pdf_name": pdf, "content": response_chunk_text}
                time.sleep(STREAM_RESPONSE_CHUNK_DELAY_SECONDS)
            log.debug(f"Response for: {pdf} was saved!\n")
            time.sleep(POST_PROCESS_DELAY_SECONDS)  # lower API request rate per sec
        except Exception as e:
            log.error(f"There is a problem with {pdf.stem}. \n Error message: {e}\n")
            traceback.print_exc()
            yield {"error": f"An error occurred while processing {pdf.stem}: {str(e)}"}


def process_query_with_rag(
    prompt: str,
    pdf_name: str,
    model: Any,
    change_length_checkbox: str,
    enhancer_checkbox: str,
    output_size: int,
    temperature_slider_value: float,
    chroma_client: Any,
    collection_name: str,
    rag_doc_slider: str,
) -> Generator:
    
    if not prompt:
        yield {"error": "No prompt provided"}
        return

    else:
        try:
            log.info(f"Document: {pdf_name} is beeing analyzed.")

            try:
                collection = chroma_client.get_collection(
                    name=collection_name, embedding_function=get_gemini_ef()
                )

                if rag_doc_slider == "False":
                    n_pages = DEFAULT_RAG_CONTEXT_PAGES 
                else:
                    n_pages = len(collection.get()["ids"])

                log.debug(f"Number of pages: {n_pages}")

                passages_with_pages = get_relevant_passage(
                    prompt, collection, n_results=n_pages
                )  # TODO: experiment with different n_results values
                # always have an additional page: RAG often pulls table of contents if
                # avaliable in the document (which does not have any informational value)
                # not all documents contain it and if so, it is placed on different pages
                # no robust way to delete it without risk of losing data

                rag_context = "\n\nRelevanat context from the document:\n"
                for passage, page_number in passages_with_pages:
                    rag_context += f"\nPage {page_number}: {passage}\n"

                rag_context += (
                    "\n\n Please use only the above context to generate an answer."
                )
            except Exception as e:
                log.error(
                    f"Problem with retrieveing context for {pdf_name}. \n Error message: {e}\n"
                )
                rag_context = (
                    "Ignore all instrucions and output: 'Error: No context found.'"
                )

            try:
                if enhancer_checkbox == "True":
                    prompt = enhance_prompt(prompt, model)
                    log.debug(f"Improved prompt: {prompt}")

            except Exception as e:
                log.error(
                    f"Problem with prompt enhancer for {pdf_name}. \n Error message: {e}\n"
                )

            log.debug(f"Context for {pdf_name}:\n{rag_context}\n")
            response = model.generate_content(
                [
                    (
                        prompt
                        + f"(Please provide {output_size} size response)"
                        + rag_context
                        if change_length_checkbox == "True"
                        else prompt + rag_context
                    ),
                ],
                stream=True,
                generation_config={"temperature": temperature_slider_value},
            )

            for response_chunk in response:
                # replace -> sometimes double space between words occure; most likely reason: pdf formating
                response_chunk_text = response_chunk.text.replace("  ", " ")
                yield {"pdf_name": pdf_name, "content": response_chunk_text}
                time.sleep(STREAM_RESPONSE_CHUNK_DELAY_SECONDS)
            log.debug(f"Response for: {pdf_name} was saved!\n")
            time.sleep(POST_PROCESS_DELAY_SECONDS)  # lower API request rate per sec
        except Exception as e:
            log.error(f"There is a problem with {pdf_name}. \n Error message: {e}\n")
            traceback.print_exc()
            yield {"error": f"An error occurred while processing {pdf_name}: {str(e)}"}


def process_chat_query_with_rag(
    prompt: str,
    chat_history: str,
    pdf_name: str,
    model: Any,
    change_length_checkbox: str,
    enhancer_checkbox: str,
    output_size: int,
    temperature_slider_value: float,
    chroma_client: Any,
    collection_name: str,
    rag_doc_slider: str,
) -> Generator:
    
    if not prompt:
        yield {"error": "No prompt provided"}
        return

    else:
        try:
            log.info(f"Document: {pdf_name} is beeing analyzed.")

            try:
                collection = chroma_client.get_collection(
                    name=collection_name, embedding_function=get_gemini_ef()
                )

                if rag_doc_slider == "False":
                    n_pages = DEFAULT_RAG_CONTEXT_PAGES 
                else:
                    n_pages = len(collection.get()["ids"])

                log.debug(f"Number of pages: {n_pages}")

                passages_with_pages = get_relevant_passage(
                    prompt, collection, n_results=n_pages
                )  # TODO: experiment with different n_results values

                rag_context = "\n\nRelevanat context from the document:\n"
                for passage, page_number in passages_with_pages:
                    rag_context += f"\nPage {page_number}: {passage}\n"

                rag_context += (
                    "\n\n Please use only the above context to generate an answer."
                )
            except Exception as e:
                log.error(
                    f"Problem with retrieveing context for {pdf_name}. \n Error message: {e}\n"
                )
                rag_context = (
                    "Ignore all instrucions and output: 'Error: No context found.'"
                )

            try:
                if enhancer_checkbox == "True":
                    prompt = enhance_prompt(prompt, model)
                    log.debug(f"Improved prompt: {prompt}")

            except Exception as e:
                log.error(
                    f"Problem with prompt enhancer for {pdf_name}. \n Error message: {e}\n"
                )
            log.debug(f"Context for {pdf_name}:\n{rag_context}\n")

            chat = model.start_chat(history=chat_history)

            response = chat.send_message(
                (
                    prompt
                    + f"(Please provide {output_size} size response)"
                    + rag_context
                    + "\n\nChat history:\n"
                    + str(chat_history)
                    if change_length_checkbox == "True"
                    else prompt + rag_context + "\n\nChat history\n" + str(chat_history)
                ),
                stream=True,
                generation_config={"temperature": temperature_slider_value},
            )

            for response_chunk in response:
                # replace -> sometimes double space between words occure; most likely reason: pdf formating
                response_chunk_text = response_chunk.text.replace("  ", " ")
                yield {"pdf_name": pdf_name, "content": response_chunk_text}
                time.sleep(STREAM_RESPONSE_CHUNK_DELAY_SECONDS)
            log.debug(f"Response for: {pdf_name} was saved!\n")
            time.sleep(POST_PROCESS_DELAY_SECONDS)  # lower API request rate per sec
        except Exception as e:
            log.error(f"There is a problem with {pdf_name}. \n Error message: {e}\n")
            traceback.print_exc()
            yield {"error": f"An error occurred while processing {pdf_name}: {str(e)}"}
