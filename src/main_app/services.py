import traceback
from collections.abc import Iterator

import markdown
import uuid
from flask import render_template, current_app
import google.generativeai as genai

from . import chroma_client, cache, log
from backend.chatbot.show_pages import show_pages
from backend.chatbot.process_query import (
    process_query_with_rag,
    process_chat_query_with_rag,
)
from backend.rag.vector_db_name_generation import (
    generate_vector_db_document_name,
    extract_title_from_filename,
)


def _get_model(data: dict) -> genai.GenerativeModel:
    """Helper function to configure and return a GenerativeAI model."""
    choosen_model = str(data.get("choosen_model", "gemini-2.0-flash"))
    show_pages_checkbox = str(data.get("show_pages_checkbox"))

    genai.configure(api_key=current_app.config["GEMINI_API_KEY"])

    system_instruction = show_pages(
        current_app.config["SYSTEM_PROMPT"], show_pages_checkbox
    )

    return genai.GenerativeModel(choosen_model, system_instruction=system_instruction)


def process_document_query(data: dict, sid: str) -> Iterator[dict]:
    """
    Generator function that processes a query against multiple documents and yields results.
    Handles the initial processing of user input and selected PDFs using a generative model.

    This function is triggered via a Socket.IO event when a user initiates processing.
    It validates the input prompt and selected PDF files, sets up the selected
    Gemini model, and processes each PDF using retrieval-augmented generation (RAG).
    The response is streamed back to the client in real time, rendered in markdown,
    and cached for future access.

    Each processed PDF results in the creation of a content container, which is
    dynamically sent to the frontend. If errors occur during processing, they are
    logged and sent to the client as error events.

    Examples:
        # Triggered internally by Socket.IO when the user starts processing:
        >>> process_text({
                "input": "Summarize the risks mentioned",
                "pdfFiles": ["KNF_2022_01.pdf"],
                "output_size": "short",
                "show_pages_checkbox": True,
                "choosen_model": "gemini-2.0-flash",
                ...
            })

    Args:
        data: A dictionary containing user input and options. Expected keys include:
            - "input": User’s prompt (str).
            - "pdfFiles": List of PDF filenames to process (List[str]).
            - "output_size": Approximate length of the response (str).
            - "show_pages_checkbox": Whether to include page numbers (bool or str).
            - "choosen_model": Selected Gemini model (str).
            - "change_length_checkbox": Whether output length can vary (bool or str).
            - "temperature_slider_value": Float controlling verbosity or detail (str or float).
            - "ragDocSlider": Toggle between RAG and document mode (str).
            - Other UI flags or settings.

    Returns:
        None. Results are streamed to the client via Socket.IO events:
            - "new_container": Sends a new HTML container for each PDF.
            - "update_content": Streams chunks of the model's response.
            - "processing_complete_for_container": Signals PDF completion.
            - "error": Sends error messages if validation or processing fails.
            - "stream_stopped": Indicates the end of the streaming session.

    Raises:
        Emits error events instead of raising exceptions directly.
        Internal exceptions are caught, logged, and passed to the client as messages.
    """
    try:
        prompt = data.get("input")
        selected_files = data.get("pdfFiles")

        if not prompt or not selected_files:
            raise ValueError("Missing prompt or selected files.")

        model = _get_model(data)
        pdf_dir = current_app.config["PDF_DIRECTORY"]

        for pdf_filename in selected_files:
            pdf_path = pdf_dir / pdf_filename
            pdf_name_to_show = extract_title_from_filename(pdf_filename)
            container_id = str(uuid.uuid4())

            log.info(
                f"Processing '{pdf_name_to_show}' for SID {sid} with container ID {container_id}"
            )

            yield {
                "event": "new_container",
                "payload": {
                    "id": container_id,
                    "title": pdf_name_to_show,
                },
            }

            accumulated_text = ""
            final_markdown_content = ""

            collection_name = generate_vector_db_document_name(
                pdf_path.stem,
                max_length=current_app.config["CHROMADB_MAX_FILENAME_LENGTH"],
            )

            rag_args = {
                "prompt": prompt,
                "pdf_name": pdf_name_to_show,
                "model": model,
                "change_length_checkbox": str(data.get("change_length_checkbox")),
                "enhancer_checkbox": str(data.get("prompt_enhancer")),
                "output_size": str(data.get("output_size")),
                "temperature_slider_value": float(
                    data.get("temperature_slider_value", 0.0)
                ),
                "chroma_client": chroma_client,
                "collection_name": collection_name,
                "rag_doc_slider": str(data.get("ragDocSlider")),
            }

            for chunk in process_query_with_rag(**rag_args):
                if "content" in chunk:
                    accumulated_text += chunk["content"]
                    yield {
                        "event": "update_content",
                        "payload": {
                            "container_id": container_id,
                            "chunk": chunk["content"],
                        },
                    }

            chat_history = [
                {"role": "user", "parts": [prompt]},
                {"role": "model", "parts": [accumulated_text]},
            ]
            data_to_cache = {
                "title": pdf_name_to_show,
                "content": markdown.markdown(accumulated_text),
                "chat_history": [
                    {"role": "user", "parts": [prompt]},
                    {"role": "model", "parts": [accumulated_text]},
                ],
                "collection_name": collection_name,
            }
            cache.set(container_id, data_to_cache, timeout=3600)

            session_map_key = f"session_map_{sid}"
            session_ids = cache.get(session_map_key) or []
            if container_id not in session_ids:
                session_ids.append(container_id)
                cache.set(session_map_key, session_ids, timeout=3600)

            yield {
                "event": "processing_complete_for_container",
                "payload": {"container_id": container_id},
            }

    except Exception as e:
        log.error(f"Service layer error in process_document_query for SID {sid}: {e}")
        traceback.print_exc()
        yield {"event": "error", "payload": {"message": str(e)}}


def process_chat_query(data: dict, sid: str) -> Iterator[dict]:
    """
    Generator function that processes a follow-up chat message and yields results.
    Handles incoming chat messages and generates a streamed response using cached document context.

    This function is triggered via a Socket.IO event when the user sends a new
    chat message related to a previously processed PDF. It loads the relevant
    cached document data and chat history, configures the Gemini model,
    and streams the generated response back to the frontend in real time.

    The function also updates the chat history in the cache after responding,
    enabling continued conversation with memory of previous exchanges.

    Examples:
        >>> handle_chat_message({
                "input": "What are the risks mentioned in the document?",
                "contentId": "content-pdf0_3",
                "output_size": "medium",
                "slider_value": 0.5,
                ...
            })

    Args:
        data: A dictionary containing chat message data and UI parameters. Expected keys include:
            - "input": User's chat message (prompt) (str).
            - "contentId": The ID of the document container (str).
            - "output_size": Desired response length (str).
            - "choosen_model": Selected Gemini model (str).
            - "slider_value": Level of detail or verbosity (float or str).
            - "show_pages_checkbox": Whether to include page numbers (bool or str).
            - "change_length_checkbox": Whether the output size can be adjusted (bool or str).

    Returns:
        None. Results are emitted via Socket.IO:
            - "receive_chat_message": Streams chat responses to the client.
            - "error": Emits errors if input is invalid or processing fails.
            - "stream_stopped": Indicates the end of streaming or failure.

    Raises:
        Does not raise exceptions directly. All exceptions are caught, logged,
        and emitted as error messages to the client.
    """
    try:
        content_id = data.get("contentId")
        prompt = data.get("input")
        cached_data = cache.get(content_id)

        if not all([content_id, prompt, cached_data]):
            raise ValueError(
                f"Missing data for chat: contentId, prompt, or cache miss for SID {sid}"
            )

        model = _get_model(data)

        chat_history = cached_data.get("chat_history", [])
        pdf_name = cached_data.get("title")
        collection_name = cached_data.get("collection_name")

        rag_args = {
            "prompt": prompt,
            "chat_history": chat_history,
            "pdf_name": pdf_name,
            "model": model,
            "change_length_checkbox": str(data.get("change_length_checkbox")),
            "enhancer_checkbox": str(data.get("prompt_enhancer")),
            "output_size": str(data.get("output_size")),
            "temperature_slider_value": float(
                data.get("temperature_slider_value", 0.0)
            ),
            "chroma_client": chroma_client,
            "collection_name": collection_name,
            "rag_doc_slider": str(data.get("ragDocSlider")),
        }

        accumulated_text = ""
        for chunk in process_chat_query_with_rag(**rag_args):
            if "content" in chunk:
                yield {
                    "event": "receive_chat_message",
                    "payload": {"message": chunk["content"]},
                }
                accumulated_text += chunk["content"]
            elif "error" in chunk:
                log.error(
                    f"Error chunk received in chat for SID {sid}: {chunk['error']}"
                )
                yield {"event": "error", "payload": {"message": chunk["error"]}}
                return

        chat_history.append({"role": "user", "parts": [prompt]})
        chat_history.append({"role": "model", "parts": [accumulated_text]})
        cached_data["chat_history"] = chat_history
        cache.set(content_id, cached_data, timeout=3600)
        log.info(f"Updated chat history in cache for contentId {content_id}")

    except Exception as e:
        log.error(f"Service layer error in process_chat_query for SID {sid}: {e}")
        traceback.print_exc()
        yield {"event": "error", "payload": {"message": str(e)}}
