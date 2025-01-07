import typing
import threading
from pathlib import Path
import traceback
import os

import markdown
from flask import Flask, request, render_template, Response, stream_with_context
import google.generativeai as genai  # type: ignore[import-untyped]
from backend.text_extraction import process_pdf  # type: ignore[import-not-found]


# directory with pdf files
SCRAPED_FILES_DIR = "scraped_files"


SYSTEM_PROMPT = (
    "Do generowania odpowiedzi wykorzystaj tylko"
    + "to co jest zawarte w udostępnionych dokumentach."
)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    "gemini-2.0-flash-exp", system_instruction=SYSTEM_PROMPT
)  # another model to be used: "gemini-1.5-flash", "gemini-1.5-flash-8b"


app = Flask(__name__, template_folder="templates", static_folder="static")

stop_flag = threading.Event()


@app.route("/")
def index() -> str:
    pdf_dir = Path(SCRAPED_FILES_DIR)
    pdf_files = [pdf.name for pdf in pdf_dir.glob("*.pdf")] if pdf_dir.exists() else []
    return render_template("index.html", pdf_files=pdf_files)


@app.route("/process", methods=["POST"])
def process_text() -> Response:
    try:
        # get the input prompt
        prompt = request.form["input"]
        if not prompt:
            return Response(
                "<div><p><strong>Error:</strong> No input provided.</p></div>",
                status=400,
                mimetype="text/html",
            )

        stop_flag.clear()  # reset stop flag

        # get selected files from the form
        selected_files = request.form.getlist("selected_files")
        if not selected_files:
            return Response(
                "<div><p><strong>Error:</strong> No files selected for processing.</p></div>",
                status=400,
                mimetype="text/html",
            )

        # get the directory of PDFs and filter only the selected files
        pdf_dir = Path(SCRAPED_FILES_DIR)
        # result: Path("scraped_files/example.pdf") -> when used with Path object
        pdfs_to_scan = [pdf_dir / file_name for file_name in selected_files]

        def generate() -> typing.Generator:
            try:
                for pdf in pdfs_to_scan:
                    if stop_flag.is_set():  # check stop flag
                        yield "<div><p><strong>Processing stopped. Partial results displayed.</strong></p></div>"
                        break

                    if not pdf.exists():
                        yield f"<div><p><strong>Error:</strong> File {pdf.name} not found.</p></div>"
                        continue

                    result = process_pdf(prompt, pdf, model)

                    if "error" in result:
                        yield f"<div><p><strong>Error:</strong> {result['error']}</p></div>"
                    elif "content" in result:
                        markdown_content = markdown.markdown(result["content"])
                        yield f"""
                        <div class="output-content">
                            <h3>
                                Result for <em>{result['pdf_name']}</em>
                                <button>
                                    <span class="arrow-icon">➤</span>
                                </button>
                            </h3>
                            <div class="markdown-body">{markdown_content}</div>
                        </div>\n\n
                        """
                    else:
                        yield "<div><p><strong>Error:</strong> Unexpected result format.</p></div>"

            except Exception as e:
                print(f"An error occurred in the generate function: {e}")
                traceback.print_exc()
                yield "<div><p><strong>Error:</strong> An unexpected error occurred.</p></div>"

            # yield "<div data-done='true'></div>"

        return Response(stream_with_context(generate()), content_type="text/html")

    except Exception as e:
        return Response(
            f"<div><p><strong>Error:</strong> {str(e)}</p></div>",
            status=500,
            mimetype="text/html",
        )


@app.route("/clear_output", methods=["GET"])
def clear_output() -> str:
    return ""


@app.route("/stop_processing", methods=["GET"])
def stop_processing() -> str:
    stop_flag.set()  # set flag to true
    print("Stop processing triggered!")
    return "<div></div>"
    # return "<div><p><strong>Processing stopped. Displaying partial results...</strong></p></div>"


if __name__ == "__main__":
    app.run(debug=True)
