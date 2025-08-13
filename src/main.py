from pathlib import Path
import traceback
import os
import uuid
from typing import Any
import json
import logging
from dotenv import load_dotenv

import markdown
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from flask_caching import Cache
import google.generativeai as genai
from backend.process_query import process_query_with_rag, process_chat_query_with_rag
from backend.knf_scraping import scrape_knf
from backend.show_pages import show_pages
from backend.custom_logger import CustomFormatter
from backend.chroma_instance import get_chroma_client

# from backend.rag_setup_db_async import CHROMADB_MAX_FILENAME_LENGTH
from backend.rag_vector_db_name_generation import (
    generate_vector_db_document_name,
    extract_title_from_filename,
)


# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Construct the path to config.json
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"

# Directory with pdf files
SCRAPED_FILES_DIR = PROJECT_ROOT / "scraped_files"

# Cache directory
CACHE_DIR = PROJECT_ROOT / "cache"

# Chroma client path
CHROMA_CLIENT_DIR = str(PROJECT_ROOT / "chroma_vector_db")
CHROMADB_MAX_FILENAME_LENGTH = 60

# Configure Flask-Caching
CACHE_CONFIG = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": CACHE_DIR,
    "CACHE_THRESHOLD": 500,
}

with open(CONFIG_PATH) as file:
    config = json.load(file)

log = logging.getLogger("__name__")
log.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
log.addHandler(ch)

NUM_RETRIES = 5

# agents to avoid being blocked by the website
USER_AGENT_LIST = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/"
        + "605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
    ),
    "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
    ),
]


SYSTEM_PROMPT = config["system_prompt"]


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")


# scrape if no documents on the server
if not SCRAPED_FILES_DIR.exists() or next(SCRAPED_FILES_DIR.iterdir(), None) is None:
    scrape_knf(SCRAPED_FILES_DIR, NUM_RETRIES, USER_AGENT_LIST)


# flask
app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

chroma_client = get_chroma_client(CHROMA_CLIENT_DIR)
log.info("Vector DB initialized")

# Initialize cache
app.config.from_mapping(CACHE_CONFIG)
cache = Cache(app)


streaming: bool = False
output_index: int = -1


@app.route("/")
def index() -> str:
    """Serves the main page of the application with a list of available PDF files.

    This route handler is mapped to the root URL ("/"). When accessed, it logs
    that the application is running, scans the designated directory for PDF files,
    and renders the homepage template with those files listed.

    This enables users to see which documents are available for analysis.

    Examples:
        None

    Returns:
        A rendered HTML page (index.html) with the following context:
        - pdf_files: A list of available PDF filenames in the scraped directory.

    Raises:
        None directly
    """

    log.info("App is up")
    pdf_dir = Path(SCRAPED_FILES_DIR)
    pdf_files = [pdf.name for pdf in pdf_dir.glob("*.pdf")] if pdf_dir.exists() else []
    pdf_files = sorted(pdf_files, key=lambda x: extract_title_from_filename(x).lower())
    pdf_titles = {pdf: extract_title_from_filename(pdf) for pdf in pdf_files}
    return render_template("index.html", pdf_files=pdf_files, pdf_titles=pdf_titles)


@socketio.on("clear_cache")
def handle_clear_cache() -> None:
    """
    Clears all cached chat instances (UUIDs) created by the current client's session.
    Triggered by a button press on the main page.
    """
    global output_index
    sid = request.sid  # type: ignore[attr-defined]
    session_map_key = f"session_map_{sid}"
    session_content_ids = cache.get(session_map_key)

    if session_content_ids:
        log.info(f"Clear event for sid: {sid}. Clearing session's cached entries.")
        for container_id in session_content_ids:
            if cache.delete(container_id):
                log.info(f"Deleted cache for key: {container_id}")
        cache.delete(session_map_key)
        log.info(f"Deleted session map for sid: {sid}")
    else:
        log.info(f"Clear event for sid: {sid}. No session map found to clear.")

    output_index = -1
    log.info(f"Output index reset for sid: {sid}")


@socketio.on("reset_chat_history")
def handle_reset_chat_history(data: dict) -> None:
    """
    Finds a specific chat session by its UUID and resets its history,
    keeping only the first two messages (initial prompt and response).
    """
    content_id = data.get("contentId")
    if not content_id:
        log.warning("Received reset_chat_history event without a contentId.")
        return

    log.info(f"Resetting chat history for UUID: {content_id}")

    cached_data = cache.get(content_id)

    if cached_data and "chat_history" in cached_data:
        cached_data["chat_history"] = cached_data["chat_history"][:2]
        cache.set(content_id, cached_data, timeout=3600)
        log.info(f"Successfully reset history for UUID: {content_id}")
        socketio.emit("history_reset_success", {"contentId": content_id})
    else:
        log.warning(f"Could not find data to reset for UUID: {content_id}")


@socketio.on("start_processing")
def process_text(data: dict) -> None:  # noqa: C901
    """Handles the initial processing of user input and selected PDFs using a generative model.

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
            - "slider_value": Float controlling verbosity or detail (str or float).
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

    log.info("Started input processing")

    try:
        global output_index
        output_index += 1
        global streaming
        streaming = True
        sid = request.sid  # type: ignore[attr-defined]

        log.info(f"SID start_processing main page: {request.sid}")  # type: ignore[attr-defined]
        # get data
        prompt = data.get("input")
        selected_files = data.get("pdfFiles")
        output_size = data.get("output_size")
        show_pages_checkbox = str(data.get("show_pages_checkbox"))
        choosen_model = str(
            data.get("choosen_model", "gemini-2.0-flash")
        )  # second arg = default model
        change_length_checkbox = str(data.get("change_length_checkbox"))
        enhancer_checkbox = str(data.get("prompt_enhancer"))
        slider_value = data.get("slider_value")
        rag_doc_slider = str(data.get("ragDocSlider"))

        if slider_value is not None:
            slider_value = float(slider_value)
        else:
            slider_value = 0.0

        if not prompt:
            log.error("No prompt provided")
            socketio.emit("error", {"message": "No input provided"})
            streaming = False
            socketio.emit("stream_stopped")
            return

        if not selected_files or selected_files == []:
            log.error("no selected files")
            socketio.emit("error", {"message": "No files selected"})
            streaming = False
            socketio.emit("stream_stopped")
            return

        output_size = str(output_size)

        # debug logs for each document
        log.debug(f"prompt: {prompt}")
        log.debug(f"selected files: {selected_files}")
        log.debug(f"output size: {output_size}")
        log.debug(f"Show pages: {show_pages_checkbox}")
        log.debug(f"Change output size: {change_length_checkbox}")
        log.debug(f"selected_model: {choosen_model}")
        log.debug(f"Prompt enhancer: {enhancer_checkbox}")
        log.debug(f"RAG or document: {rag_doc_slider}")

        # files
        pdf_dir = Path(SCRAPED_FILES_DIR)

        pdfs_to_scan = [pdf_dir / file_name for file_name in selected_files]

        for pdf in pdfs_to_scan:
            log.info(pdf)

        # model instance inside the function to allow multiple models
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            choosen_model,
            system_instruction=show_pages(SYSTEM_PROMPT, show_pages_checkbox),
        )  # another models to be used: "gemini-2.0-flash-thinking-exp-01-21" "gemini-2.0-flash"

        try:
            for index, pdf in enumerate(pdfs_to_scan):
                if not streaming:
                    break
                # document title extraction
                pdf_parts = pdf.stem.split("_", 2)
                if len(pdf_parts) == 3:
                    doc_id, timestamp, title = pdf_parts
                    pdf_name_to_show = title.lstrip("_").rstrip("_")
                else:
                    pdf_name_to_show = pdf.stem.lstrip("_").rstrip("_")  # fallback

                container_id = str(uuid.uuid4())
                log.info(f"Generated unique container ID (UUID): {container_id}")

                container_html = render_template(
                    "output.html",
                    container_title=pdf_name_to_show,
                    container_id=container_id,
                )

                log.info(f"New container created for: {pdf_name_to_show}")
                socketio.emit("new_container", {"html": container_html})

                collection_name = generate_vector_db_document_name(
                    pdf.stem, max_length=CHROMADB_MAX_FILENAME_LENGTH
                )
                print("-" * 10, "COLLECTION NAME", "-" * 10)
                print(collection_name)

                accumulated_text = ""

                for result_chunk in process_query_with_rag(
                    prompt,
                    pdf_name_to_show,
                    model,
                    change_length_checkbox,
                    enhancer_checkbox,
                    output_size,
                    slider_value,
                    chroma_client,
                    collection_name,
                    rag_doc_slider,
                ):
                    if not streaming:
                        break
                    if "error" in result_chunk:
                        log.error("Error received in chunk")
                        error_message = {"message": "error in chunk response"}
                        socketio.emit("error", error_message)
                        return
                    elif "content" in result_chunk:
                        log.debug(f'Received response chunk: {result_chunk["content"]}')
                        accumulated_text += result_chunk["content"]
                        markdown_content = markdown.markdown(accumulated_text)
                        final_markdown_content = (
                            markdown_content  # Keep track of the latest full content
                        )
                        socketio.emit(
                            "update_content",
                            {
                                "container_id": container_id,
                                "html": markdown_content,
                            },
                        )
                    else:
                        socketio.emit("error", {"message": "unexpected error"})
                        return
                if streaming:
                    chat_history = [
                        {"role": "user", "parts": [prompt]},
                        {"role": "model", "parts": [accumulated_text]},
                    ]
                    data_to_cache = {
                        "title": pdf_name_to_show,
                        "content": final_markdown_content,
                        "chat_history": chat_history,
                        "collection_name": collection_name,
                    }
                    # Set a timeout (e.g., 1 hour = 3600 seconds)
                    cache.set(container_id, data_to_cache, timeout=3600)
                    log.info(f"Stored content for unique key {container_id} in cache.")
                    log.info(
                        f"Initial processing complete for container ID: {container_id}."
                        "Emitting completion signal."
                    )
                    session_map_key = f"session_map_{sid}"
                    session_content_ids = cache.get(session_map_key) or []
                    if container_id not in session_content_ids:
                        session_content_ids.append(container_id)
                        cache.set(session_map_key, session_content_ids, timeout=3600)
                        log.info(f"Added {container_id} to session map for sid: {sid}")
                    # Emit a custom event indicating completion for THIS container
                    socketio.emit(
                        "processing_complete_for_container",
                        {"container_id": container_id},
                    )
                else:
                    log.info(
                        f"Processing stopped for {pdf_name_to_show} ({container_id}). Not emitting completion signal."
                    )

            if not streaming:
                socketio.emit("stream_stopped")
                log.info("Stream stopped during file processing.")
        except Exception as e:
            log.error(f"An error occurred in the generate function: {e}")
            traceback.print_exc()
            socketio.emit(
                "error", {"message": f"An unexpected error occurred: {str(e)}"}
            )

        streaming = False
        socketio.emit("stream_stopped")

    except Exception as e:
        log.error(f"An error occurred in the generate function: {e}")
        traceback.print_exc()
        socketio.emit("error", {"message": f"An unexpected error occurred: {str(e)}"})
        streaming = False


# Linter C901 error ignored -> func will be refactored during complex code refactor
@socketio.on("send_chat_message")
def handle_chat_message(data: dict) -> None:  # noqa: C901
    """Handles incoming chat messages and generates a streamed response using cached document context.

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

    log.info("Received user input. Start processing.")

    try:
        global streaming
        streaming = True

        # get data
        prompt = data.get("input")
        content_id = data.get("contentId")

        # get cached data
        cached_data = cache.get(content_id)
        if not cached_data:
            log.error(f"Validation Error: No cached data found for UUID: {content_id}.")
            socketio.emit(
                "error",
                {
                    "message": f"Could not load data for chat session '{content_id}'. It may have expired."
                },
            )
            streaming = False
            socketio.emit("stream_stopped")
            return

        pdf_name = cached_data.get("title") if cached_data else None
        chat_history = cached_data.get("chat_history", [])
        rag_doc_slider = str(data.get("ragDocSlider"))
        print("-" * 10, "CHAT HISTORY", "-" * 10)
        print(chat_history)

        output_size = str(data.get("output_size"))
        show_pages_checkbox = str(data.get("show_pages_checkbox"))
        choosen_model = str(
            data.get("choosen_model", "gemini-2.0-flash")
        )  # second arg = default model
        change_length_checkbox = str(data.get("change_length_checkbox"))
        enhancer_checkbox = str(data.get("prompt_enhancer"))
        slider_value = data.get("slider_value")

        if slider_value is not None:
            slider_value = float(slider_value)
        else:
            slider_value = 0.0

        if not prompt:
            log.error("No prompt provided by user")
            socketio.emit("error", {"message": "No input provided"})
            streaming = False
            socketio.emit("stream_stopped")
            return

        if not content_id:
            log.error(
                f"Content ID missing or cached data not found for ID: {content_id}"
            )
            socketio.emit("error", {"message": "No content ID for the chat provided"})
            streaming = False
            socketio.emit("stream_stopped")
            return

        if not pdf_name:
            log.error(f"PDF name not found in cache for content ID: {content_id}")
            socketio.emit("error", {"message": "No pdf name provided"})
            streaming = False
            socketio.emit("stream_stopped")
            return

        if not isinstance(chat_history, list):
            log.warning(
                f"Cached data for '{content_id}' contained 'chat_history' but it was not a list:"
                f"(type: {type(chat_history)}). Initializing as empty list."
            )

        # debug logs for each document
        log.debug(f"Prompt: {prompt}")
        log.debug(f"Content id: {content_id}")
        log.debug(f"Pdf name (from cache): {pdf_name}")
        log.debug(
            f"Initial Chat History (loaded/initialized): {len(chat_history)} messages"
        )
        log.debug(f"Output size: {output_size}")
        log.debug(f"Show pages: {show_pages_checkbox}")
        log.debug(f"Change output size: {change_length_checkbox}")
        log.debug(f"Selected model: {choosen_model}")
        log.debug(f"RAG or document: {rag_doc_slider}")
        log.debug(f"Prompt enhancer: {enhancer_checkbox}")

        # model instance inside the function to allow multiple models
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            choosen_model,
            system_instruction=show_pages(SYSTEM_PROMPT, show_pages_checkbox),
        )  # another models to be used: "gemini-2.0-flash-thinking-exp-01-21" "gemini-2.0-flash"

        try:
            if not streaming:
                socketio.emit("stream_stopped")
                log.info("Stream stopped before file processing.")
            pdf_name_to_show = pdf_name

            collection_name = cached_data.get("collection_name")
            if not collection_name:
                # fallback for old cache entries
                collection_name = generate_vector_db_document_name(
                    pdf_name, max_length=CHROMADB_MAX_FILENAME_LENGTH
                )

            # print("-" * 10, "COLLECTION NAME HANDLING CHAT MESSAGE", "-" * 10)
            # print(collection_name)

            accumulated_text = ""
            for result_chunk in process_chat_query_with_rag(
                prompt,
                chat_history,
                pdf_name_to_show,
                model,
                change_length_checkbox,
                enhancer_checkbox,
                output_size,
                slider_value,
                chroma_client,
                collection_name,
                rag_doc_slider,
            ):
                if not streaming:
                    log.info("Stopping chat processing due to streaming flag.")
                    break
                # Check the structure of the yielded chunk
                if "content" in result_chunk:
                    log.debug(f'Recived response chunk: {result_chunk["content"]}')
                    accumulated_text += result_chunk["content"]
                    chunk_text = result_chunk["content"]
                    socketio.emit("receive_chat_message", {"message": chunk_text})

                elif "error" in result_chunk:
                    error_message = result_chunk["error"]
                    log.error(
                        f"Error chunk from process_query_with_rag: {error_message}"
                    )
                    # --- Emit an error message to the frontend ---
                    socketio.emit("receive_chat_message", {"error": error_message})
                    # If an error occurs in a chunk, stop processing the rest of the stream
                    break
                else:
                    socketio.emit("error", {"message": "unexpected error"})
                    return
            if streaming:
                chat_history.append({"role": "user", "parts": [prompt]})
                chat_history.append({"role": "model", "parts": [accumulated_text]})
                cached_data["chat_history"] = (
                    chat_history  # <-- Assign the updated list back into the dictionary
                )
                cache.set(content_id, cached_data, timeout=3600)
                log.info(f"Stored updated data for {content_id} in cache.")

            if not streaming:
                socketio.emit("stream_stopped")
                log.info("Stream stopped during request processing.")

        except Exception as e:
            log.error(f"An error occurred in the generate function: {e}")
            traceback.print_exc()
            socketio.emit(
                "error", {"message": f"An unexpected error occurred: {str(e)}"}
            )

        streaming = False
        socketio.emit("stream_stopped")

    except Exception as e:
        log.error(f"An error occurred in the generate function: {e}")
        traceback.print_exc()
        socketio.emit("error", {"message": f"An unexpected error occurred: {str(e)}"})
        streaming = False


@socketio.on("stop_processing")
def handle_stop() -> None:
    """Stops the current processing stream when triggered by the client.

    This function sets the global streaming flag to False, effectively stopping
    any ongoing data generation or response processing.

    Examples:
        None

    Returns:
        None

    Raises:
        None
    """

    global streaming
    streaming = False
    log.info("Processing Stopped by User")


@socketio.on("disconnect")
def handle_disconnect() -> None:
    """Handles cache cleanup for all UUIDs created by a client's session."""
    sid = request.sid  # type: ignore[attr-defined]
    session_map_key = f"session_map_{sid}"
    session_content_ids = cache.get(session_map_key)

    if session_content_ids:
        log.info(f"Disconnect event for sid: {sid}. Cleaning up cached entries.")
        for container_id in session_content_ids:
            if cache.delete(container_id):
                log.info(f"Deleted cache for key: {container_id}")
            else:
                log.warning(
                    f"Attempted to delete non-existent cache key: {container_id}"
                )

        cache.delete(session_map_key)
        log.info(f"Deleted session map for sid: {sid}")
    else:
        log.info(
            f"Disconnect event for sid: {sid}. No session map found, no cleanup needed."
        )


@app.route("/documentChat")
def document_chat() -> Any:
    """Serves the document chat page using cached content based on the provided content ID.

    Retrieves cached data (title and content) for a given contentId passed as a query parameter
    and renders a chat interface for continued conversation with the document.

    Examples:
        None

    Returns:
        Rendered HTML page (documentChat.html) with:
        - content_id: The ID of the requested content.
        - container_title_chat: The title of the document.
        - content_chat: The previously generated content or an error message.

    Raises:
        None
    """

    content_id = request.args.get("contentId")  # Get ID from URL query ?contentId=...
    log.info(f"Langchain chat request for contentId: {content_id}")

    # Retrieve data from cache
    cached_data = cache.get(content_id)
    log.debug(f"Cache lookup for {content_id} returned: {type(cached_data)}")

    if cached_data:
        container_title_chat = cached_data.get("title", "Unknown Title")
        content_chat = cached_data.get("content", "<p>Content not found.</p>")
        chat_history = cached_data.get("chat_history", [])
        log.info(f"Found content for {content_id} in cache.")
        log.info(f"Found {len(chat_history)} messages in history for {content_id}.")

        for message in chat_history:
            if message.get("role") == "model" and message.get("parts"):
                # Convert the raw markdown in 'parts' to HTML
                raw_markdown = message["parts"][0]
                message["parts"][0] = markdown.markdown(raw_markdown)
    else:
        container_title_chat = "Error"
        content_chat = f"<p>Could not find content for ID: {content_id}. Cache might be empty or ID is invalid.</p>"
        chat_history = []
        log.warning(f"Content for {content_id} not found in cache.")

    return render_template(
        "documentChat.html",
        content_id=content_id,
        container_title_chat=container_title_chat,
        content_chat=content_chat,
        chat_history=chat_history,
    )


if __name__ == "__main__":
    cache_dir = app.config.get("CACHE_DIR")
    if cache_dir:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
