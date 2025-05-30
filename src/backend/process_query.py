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
# RAG context header
RAG_CONTEXT_HEADER = "\n\nRelevant context from the document:\n"
# RAG context footer
RAG_CONTEXT_FOOTER = "\n\nPlease use only the above context to generate an answer."
# RAG error during context retrieval prompt instruction
RAG_CONTEXT_ERROR_PROMPT_INSTRUCTION = "Ignore all instructions and output: 'Error: No context found.'"

def _build_final_llm_prompt(
    base_prompt: str,
    change_length_flag: str,
    output_size: int,
    enhancer_flag: str,
    model: Any,
    identifier: str,
    rag_context: str | None = None,
    chat_history: str | None = None
) -> str:
    """
    Enhances (optionally) and constructs the final prompt string for the LLM.

    Args:
        base_prompt: The initial prompt.
        change_length_flag: String flag ("True"/"False") to add output size instruction.
        output_size: The desired output size (e.g., number of words).
        enhancer_flag: String flag ("True"/"False") to enable prompt enhancement.
        model: The generative model (passed to enhance_prompt).
        identifier: A string identifier (like a PDF name/stem) for logging.
        rag_context: Optional RAG context string.
        chat_history: Optional string containing the chat history.

    Returns:
        The (potentially enhanced) and fully assembled prompt string for the LLM.
    """
    processed_prompt = base_prompt

    if enhancer_flag == "True":
        try:
            log.debug(f"Original prompt for '{identifier}': '{processed_prompt[:100]}...'")
            processed_prompt = enhance_prompt(processed_prompt, model) # enhance_prompt modifies the prompt
            log.debug(f"Improved prompt for '{identifier}': '{processed_prompt[:100]}...'")
        except Exception as e:
            log.error(
                f"Problem with prompt enhancer for '{identifier}'. Using original prompt. Error: {e}\n",
                exc_info=True
            )

    final_prompt_parts = [processed_prompt]

    if change_length_flag == "True":
        final_prompt_parts.append(f" (Please provide approximately {output_size} words response)")

    if rag_context:
        final_prompt_parts.append(rag_context)

    if chat_history:
        final_prompt_parts.append(f"\n\nChat history:\n{chat_history}")
        
    assembled_prompt = "".join(final_prompt_parts)
    log.debug(f"Assembled final LLM prompt (first 200 chars): '{assembled_prompt[:200]}...'")
    return assembled_prompt

def _get_rag_context(
    prompt: str,
    pdf_name: str,
    chroma_client: Any,
    collection_name: str,
    rag_doc_slider: str,
    embedding_function: Any,
) -> str:
    """
    Retrieves and formats the RAG context from ChromaDB.

    Args:
        prompt: The user's query to find relevant passages.
        pdf_name: The name/identifier of the PDF for logging.
        chroma_client: The ChromaDB client instance.
        collection_name: The name of the ChromaDB collection.
        rag_doc_slider: String flag ("True" to use all chunks, "False" for default_n_pages).
        embedding_function: The embedding function for the ChromaDB collection.
        default_n_pages: The default number of pages/passages to retrieve.

    Returns:
        A string containing the formatted RAG context, or an error instruction string
        if context retrieval fails.
    """
    try:
        log.debug(f"Attempting to retrieve RAG context for '{pdf_name}' with prompt: '{prompt}'")
        collection = chroma_client.get_collection(
            name=collection_name, embedding_function=embedding_function
        )

        total_chunks_in_collection = collection.count()

        if rag_doc_slider == "True":
            n_results = total_chunks_in_collection
            log.debug(f"Using all {n_results} available document chunks for RAG context for '{pdf_name}'.")
        else:
            n_results = DEFAULT_RAG_CONTEXT_PAGES
            if n_results > total_chunks_in_collection and total_chunks_in_collection > 0:
                n_results = total_chunks_in_collection
                log.debug(f"Default n_pages ({DEFAULT_RAG_CONTEXT_PAGES}) exceeds total chunks in collection ({total_chunks_in_collection}). Using {n_results} for '{pdf_name}'.")
            elif total_chunks_in_collection == 0:
                log.warning(f"No documents found in collection '{collection_name}' for '{pdf_name}'. RAG context will be empty.")
                return RAG_CONTEXT_ERROR_PROMPT_INSTRUCTION # Or an empty context string if preferred
            log.debug(f"Using {n_results} document chunks (default or capped) for RAG context for '{pdf_name}'.")

        if n_results == 0:
            log.warning(f"No document chunks to retrieve for RAG context for '{pdf_name}' (n_results is 0).")
            return RAG_CONTEXT_ERROR_PROMPT_INSTRUCTION

        passages_with_pages = get_relevant_passage(
            prompt, collection, n_results=n_results
        )   # TODO: experiment with different n_results values
        # always have an additional page: RAG often pulls table of contents if
        # avaliable in the document (which does not have any informational value)
        # not all documents contain it and if so, it is placed on different pages
        # no robust way to delete it without risk of losing data

        if not passages_with_pages:
            log.warning(f"No relevant passages found by get_relevant_passage for '{pdf_name}'.")
            # Depending on desired behavior, could return error or just empty context
            return RAG_CONTEXT_ERROR_PROMPT_INSTRUCTION

        context_parts = [RAG_CONTEXT_HEADER]
        for passage, page_number in passages_with_pages:
            context_parts.append(f"Page {page_number}: {passage}\n") # Corrected typo "Relevanat" implicitly by new string
        context_parts.append(RAG_CONTEXT_FOOTER)
        
        rag_context = "".join(context_parts)
        log.debug(f"Successfully retrieved and formatted RAG context for '{pdf_name}'.")
        return rag_context

    except Exception as e:
        log.error(
            f"Problem retrieving RAG context for '{pdf_name}'. Error: {e}\n",
            exc_info=True
        )
        return RAG_CONTEXT_ERROR_PROMPT_INSTRUCTION

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
        return

    try:
        log.info(f"Document: {pdf.stem} is beeing analyzed.")
        file_to_send = genai.upload_file(pdf)
        log.debug(f"PDF uploaded successfully. File metadata: {file_to_send}\n")

        final_llm_prompt_for_model = _build_final_llm_prompt(
            base_prompt=prompt,
            change_length_flag=change_length_checkbox,
            output_size=output_size,
            enhancer_flag=enhancer_checkbox,
            model=model,
            identifier=pdf.stem
        ) 
        response = model.generate_content(
            [final_llm_prompt_for_model, file_to_send], # Pass the assembled prompt
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
    
    rag_context = _get_rag_context(
        prompt=prompt,
        pdf_name=pdf_name,
        chroma_client=chroma_client,
        collection_name=collection_name,
        rag_doc_slider=rag_doc_slider,
        embedding_function=get_gemini_ef(),
    )
    log.debug(f"Context for {pdf_name}:\n{rag_context}\n")

    final_llm_prompt = _build_final_llm_prompt(
        base_prompt=prompt,
        change_length_flag=change_length_checkbox,
        output_size=output_size,
        enhancer_flag=enhancer_checkbox,
        model=model,
        identifier=pdf_name,
        rag_context=rag_context
    )

    try:
        response = model.generate_content(
            [final_llm_prompt],
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
    
    rag_context = _get_rag_context(
        prompt=prompt,
        pdf_name=pdf_name,
        chroma_client=chroma_client,
        collection_name=collection_name,
        rag_doc_slider=rag_doc_slider,
        embedding_function=get_gemini_ef(),
    )
    log.debug(f"Context for {pdf_name} (chat query):\n{rag_context}\n")

    final_llm_prompt = _build_final_llm_prompt(
        base_prompt=prompt,
        change_length_flag=change_length_checkbox,
        output_size=output_size,
        enhancer_flag=enhancer_checkbox,
        model=model,
        identifier=pdf_name,
        rag_context=rag_context,
        chat_history=chat_history
    )

    try:
        log.info(f"Generating chat response for query on '{pdf_name}' with final prompt: '{final_llm_prompt[:200]}...'")
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(
            [final_llm_prompt],
            stream=True,
            generation_config=genai.types.GenerationConfig(temperature=temperature_slider_value),
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
