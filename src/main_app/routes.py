from pathlib import Path

from flask import Blueprint, render_template, request, send_from_directory, current_app
from werkzeug.wrappers import Response

from backend.rag.vector_db_name_generation import extract_title_from_filename
from . import log

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
    """Serves the base HTML for the document chat view."""
    content_id = request.args.get("contentId")
    return render_template("documentChat.html", content_id=content_id)
