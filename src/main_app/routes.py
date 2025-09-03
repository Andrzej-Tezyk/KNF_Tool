from pathlib import Path

import markdown
from flask import Blueprint, render_template, request, send_from_directory, current_app
from werkzeug.wrappers import Response

from backend.rag.vector_db_name_generation import extract_title_from_filename
from . import cache, log

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index() -> str:
    log.info("App is up")
    pdf_dir = Path(current_app.config["PDF_DIRECTORY"])
    pdf_files = sorted(
        [pdf.name for pdf in pdf_dir.glob("*.pdf")] if pdf_dir.exists() else [],
        key=lambda x: extract_title_from_filename(x).lower(),
    )
    pdf_titles = {pdf: extract_title_from_filename(pdf) for pdf in pdf_files}
    return render_template("index.html", pdf_files=pdf_files, pdf_titles=pdf_titles)


@main_bp.route("/files/<path:filename>")
def serve_file(filename: str) -> Response:
    return send_from_directory(current_app.config["PDF_DIRECTORY"], filename)


@main_bp.route("/documentChat")
def document_chat() -> str:
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
