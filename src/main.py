from pathlib import Path
import traceback
import os
from typing import Any
import json
import logging

import markdown
from flask import Flask, render_template
from flask_socketio import SocketIO
import google.generativeai as genai
from backend.process_query import process_query_with_rag  # type: ignore[import-not-found]
from backend.knf_scraping import scrape_knf  # type: ignore[import-not-found]
from backend.show_pages import show_pages  # type: ignore[import-not-found]
from backend.custom_logger import CustomFormatter  # type: ignore[import-not-found]
from backend.chroma_instance import get_chroma_client  # type: ignore[import-not-found]


with open("config/config.json") as file:
    config = json.load(file)


log = logging.getLogger("__name__")
log.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
log.addHandler(ch)


# directory with pdf files
SCRAPED_FILES_DIR = "scraped_files"

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
PROJECT_ROOT = Path(__file__).parent.parent  # go up 2 times

scraped_dir = PROJECT_ROOT / "scraped_files"

if not scraped_dir.exists():
    scrape_knf(NUM_RETRIES, USER_AGENT_LIST)


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

chroma_client = get_chroma_client("exp_vector_db")
log.info("Vector DB initialized")

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
                pdf_name_to_show = str(pdf)
                container_title = pdf_name_to_show[25:-4]

                container_html = render_template(
                    "output.html",
                    container_title=container_title,
                    index=index,
                    output_index=output_index,
                )

                log.info(f"New container created for: {pdf_name_to_show}")
                socketio.emit("new_container", {"html": container_html})

                collection_name = pdf_name_to_show.replace(" ", "").lower()
                collection_name = replace_polish_chars(
                    collection_name
                )  # TODO: better solution for database naming
                collection_name = collection_name[25:60]

                accumulated_text = ""
                for result_chunk in process_query_with_rag(
                    prompt,
                    pdf,
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
                    ):  # TODO czy tu chodzi o slowo error w odpowiedzi? jezeli tak to do sprawdzenia
                        socketio.emit("error", {"message": "error in chunk response"})
                        return
                    elif "content" in result_chunk:
                        log.debug(f'Recived response chunk: {result_chunk["content"]}')
                        accumulated_text += result_chunk["content"]
                        markdown_content = markdown.markdown(accumulated_text)
                        socketio.emit(
                            "update_content",
                            {
                                "container_id": f"content-pdf{index}_{output_index}",
                                "html": markdown_content,
                            },
                        )
                    else:
                        socketio.emit("error", {"message": "unexpected error"})
                        return
            if not streaming:
                socketio.emit("stream_stopped")
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


@socketio.on("stop_processing")
def handle_stop() -> None:
    global streaming
    streaming = False
    log.info("Processing Stopped by User")


@app.route("/langchainChat")
def langchain_chat() -> Any:
    return render_template("langchainChat.html")


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
