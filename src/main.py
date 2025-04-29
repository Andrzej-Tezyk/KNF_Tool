from pathlib import Path
import traceback
import os
from typing import Any
import json
import logging

import markdown
from flask import Flask, render_template, request
import chromadb
from flask_socketio import SocketIO
from flask_caching import Cache
import google.generativeai as genai
from backend.process_query import process_query_with_rag, process_chat_query_with_rag  # type: ignore[import-not-found]
from backend.knf_scraping import scrape_knf  # type: ignore[import-not-found]
from backend.show_pages import show_pages  # type: ignore[import-not-found]
from backend.custom_logger import CustomFormatter  # type: ignore[import-not-found]
from backend.chroma_instance import get_chroma_client  # type: ignore[import-not-found]


# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Construct the path to config.json
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"

# Directory with pdf files
SCRAPED_FILES_DIR = PROJECT_ROOT / "scraped_files"

# Cache directory
CACHE_DIR = PROJECT_ROOT / ".cache"

# Chroma client path
CHROMA_CLIENT_DIR = str(PROJECT_ROOT / "exp_vector_db")

# Configure Flask-Caching
# Use FileSystemCache to persist across reloads during development
# Use SimpleCache for basic in-memory (similar to dict, won't survive reloads)
# For production, consider RedisCache or MemcachedCache if available
CACHE_CONFIG = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": CACHE_DIR,  # Store cache files in project root/.cache
    "CACHE_THRESHOLD": 500,  # Max number of items in cache
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


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")


# scrape if no documents on the server
if not SCRAPED_FILES_DIR.exists() or next(SCRAPED_FILES_DIR.iterdir(), None) is None:
    scrape_knf(SCRAPED_FILES_DIR, NUM_RETRIES, USER_AGENT_LIST)


def replace_polish_chars(text: str) -> str:
    """
    For documents names only.
    """
    polish_to_ascii = {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ż": "z",
        "ź": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ż": "Z",
        "Ź": "Z",
    }

    return "".join(polish_to_ascii.get(c, c) for c in text)


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
    log.info("App is up")
    pdf_dir = Path(SCRAPED_FILES_DIR)
    pdf_files = [pdf.name for pdf in pdf_dir.glob("*.pdf")] if pdf_dir.exists() else []
    return render_template("index.html", pdf_files=pdf_files)


@socketio.on("start_processing")
def process_text(data: dict) -> None:
    log.info("Started input processing")

    try:
        global output_index
        output_index += 1
        global streaming
        streaming = True

        # get data
        prompt = data.get("input")
        selected_files = data.get("pdfFiles")
        output_size = data.get("output_size")
        show_pages_checkbox = data.get("show_pages_checkbox")
        choosen_model = str(
            data.get("choosen_model", "gemini-2.0-flash")
        )  # second arg = default model
        change_lebgth_checkbox = data.get("change_length_checkbox")
        # enhancer_checkbox = data.get("enhancer_checkbox")
        enhancer_checkbox = "True"  # TODO: change when enhancer is ready
        slider_value = data.get("slider_value")

        show_pages_checkbox = str(show_pages_checkbox)
        change_lebgth_checkbox = str(change_lebgth_checkbox)
        enhancer_checkbox = str(enhancer_checkbox)

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
        log.debug(f"Change output size: {change_lebgth_checkbox}")
        log.debug(f"selected_model: {choosen_model}")

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
                pdf_name_to_show = str(pdf.stem.split("_", 1)[1])
                container_id = f"content-pdf{index}_{output_index}"  # Use current index

                container_html = render_template(
                    "output.html",
                    container_title=pdf_name_to_show,
                    container_id=container_id,
                )

                log.info(f"New container created for: {pdf_name_to_show}")
                socketio.emit("new_container", {"html": container_html})

                collection_name = pdf_name_to_show.replace(" ", "").lower()
                collection_name = replace_polish_chars(
                    collection_name
                )  # TODO: better solution for database naming
                collection_name = collection_name[:35]
                print("-" * 10, "COLLECTION NAME", "-" * 10)
                print(collection_name)

                accumulated_text = ""
                for result_chunk in process_query_with_rag(
                    prompt,
                    pdf_name_to_show,
                    model,
                    change_lebgth_checkbox,
                    enhancer_checkbox,
                    output_size,
                    slider_value,
                    chroma_client,
                    collection_name,
                ):
                    if not streaming:
                        break
                    if (
                        "error" in result_chunk
                    ):  # czy tu chodzi o slowo error w odpowiedzi? jezeli tak to do sprawdzenia
                        log.error(f"Error received in chunk")
                        socketio.emit("error", {"message": "error in chunk response"})
                        return
                    elif "content" in result_chunk:
                        log.debug(f'Recived response chunk: {result_chunk["content"]}')
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
                    chat_history = []
                    chat_history.append({"role": "user", "parts": [prompt]})
                    chat_history.append({"role": "model", "parts": [accumulated_text]})
                    data_to_cache = {
                        "title": pdf_name_to_show,
                        "content": final_markdown_content,
                        "chat_history": chat_history,
                    }
                    # Set a timeout (e.g., 1 hour = 3600 seconds)
                    cache.set(container_id, data_to_cache, timeout=600)
                    log.info(f"Stored content for {container_id} in cache.")
                    log.info(
                        f"Initial processing complete for {pdf_name_to_show} ({container_id}). Emitting completion signal."
                    )
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


@socketio.on("send_chat_message")
def handle_chat_message(data: dict) -> None:
    log.info("Received user input. Start processing.")

    try:
        global streaming
        streaming = True

        # get data
        prompt = data.get("input")
        content_id = data.get("contentId")
        output_size = data.get("output_size")
        show_pages_checkbox = data.get("show_pages_checkbox")
        # get cached data
        cached_data = cache.get(content_id)
        pdf_name = cached_data.get("title") if cached_data else None
        chat_history = cached_data.get("chat_history", [])
        print("-" * 10, "CHAT HISTORY", "-" * 10)
        print(chat_history)

        choosen_model = str(
            data.get("choosen_model", "gemini-2.0-flash")
        )  # second arg = default model
        change_lebgth_checkbox = data.get("change_length_checkbox")
        # enhancer_checkbox = data.get("enhancer_checkbox")
        enhancer_checkbox = "True"  # TODO: change when enhancer is ready
        slider_value = data.get("slider_value")

        show_pages_checkbox = str(show_pages_checkbox)
        change_lebgth_checkbox = str(change_lebgth_checkbox)
        enhancer_checkbox = str(enhancer_checkbox)

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

        if not cached_data:
            log.error(
                f"Validation Error: No cached data found for contentId: {content_id}. Cannot load document context or history."
            )
            socketio.emit(
                "error",
                {
                    "message": f"Could not load data for chat session '{content_id}'. It may have expired or is invalid."
                },
            )
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
                f"Cached data for '{content_id}' contained 'chat_history' but it was not a list (type: {type(chat_history)}). Initializing as empty list."
            )
            chat_history = []  # Reset to a valid empty list

        output_size = str(output_size)

        # debug logs for each document
        log.debug(f"Prompt: {prompt}")
        log.debug(f"Content id: {content_id}")
        log.debug(f"Pdf name (from cache): {pdf_name}")
        log.debug(
            f"Initial Chat History (loaded/initialized): {len(chat_history)} messages"
        )
        log.debug(f"Output size: {output_size}")
        log.debug(f"Show pages: {show_pages_checkbox}")
        log.debug(f"Change output size: {change_lebgth_checkbox}")
        log.debug(f"Selected model: {choosen_model}")

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

            collection_name = pdf_name_to_show.replace(" ", "").lower()
            collection_name = replace_polish_chars(
                collection_name
            )  # TODO: better solution for database naming
            collection_name = collection_name[:35]

            accumulated_text = ""
            for result_chunk in process_chat_query_with_rag(
                prompt,
                chat_history,
                pdf_name_to_show,
                model,
                change_lebgth_checkbox,
                enhancer_checkbox,
                output_size,
                slider_value,
                chroma_client,
                collection_name,
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
                cache.set(content_id, cached_data, timeout=600)
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
    global streaming
    streaming = False
    log.info("Processing Stopped by User")


@app.route("/documentChat")
def langchain_chat() -> Any:
    content_id = request.args.get("contentId")  # Get ID from URL query ?contentId=...
    log.info(f"Langchain chat request for contentId: {content_id}")

    # Retrieve data from cache
    cached_data = cache.get(content_id)
    log.debug(f"Cache lookup for {content_id} returned: {type(cached_data)}")

    if cached_data:
        container_title_chat = cached_data.get("title", "Unknown Title")
        content_chat = cached_data.get("content", "<p>Content not found.</p>")
        log.info(f"Found content for {content_id} in cache.")
    else:
        container_title_chat = "Error"
        content_chat = f"<p>Could not find content for ID: {content_id}. Cache might be empty or ID is invalid.</p>"
        log.warning(f"Content for {content_id} not found in cache.")

    return render_template(
        "documentChat.html",
        content_id=content_id,
        container_title_chat=container_title_chat,
        content_chat=content_chat,
    )


if __name__ == "__main__":
    cache_dir = app.config.get("CACHE_DIR")
    if cache_dir:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
