import typing
import threading
from pathlib import Path
import traceback

import markdown
from flask import Flask, request, render_template, Response, stream_with_context
from backend.text_extraction import process_pdf  # type: ignore[import-not-found]


SCRAPED_FILES_DIR = "scraped_files"


app = Flask(__name__, template_folder="templates")

stop_flag = threading.Event()


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_text() -> Response:
    try:
        prompt = request.form["input"]
        if not prompt:
            return Response(
                "<div><p><strong>Error:</strong> No input provided.</p></div>",
                status=400,
                mimetype="text/html",
            )

        stop_flag.clear()  # set flag to false

        pdf_dir = Path(SCRAPED_FILES_DIR)
        if not pdf_dir.exists():
            return Response(
                f"<div><p><strong>Error:</strong> Directory {SCRAPED_FILES_DIR} not found.</p></div>",
                status=400,
                mimetype="text/html",
            )

        pdfs_to_scan = list(pdf_dir.glob("*.pdf"))
        if not pdfs_to_scan:
            return Response(
                f"<div><p><strong>Error:</strong> No PDF files found in {SCRAPED_FILES_DIR}.</p></div>",
                status=400,
                mimetype="text/html",
            )

        def generate() -> typing.Generator:
            try:
                for pdf in pdfs_to_scan:
                    # yield f"<div><p>Processing: {pdf.name}</p></div>"

                    result = process_pdf(prompt, pdf)

                    if stop_flag.is_set():  # check is flag True or False
                        yield "<div><p><strong>Processing stopped. Partial results displayed.</strong></p></div>"
                        break

                    if "error" in result:
                        yield (
                            f"<div><p><strong>Error:</strong> {result['error']}</p></div>"
                        )
                    elif "content" in result:
                        markdown_content = markdown.markdown(result["content"])
                        yield f"""
                        <div class="output-content">
                            <h3>Result for <em>{result['pdf_name']}</em></h3>
                            <div class="markdown-body">{markdown_content}</div>
                        </div>
                        """
                    else:
                        yield "<div><p><strong>Error:</strong> Unexpected result format.</p></div>"

            except Exception as e:
                print(f"An error occurred in the generate function: {e}")
                traceback.print_exc()
                yield "<div><p><strong>Error:</strong> An unexpected error occurred.</p></div>"

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
    return "<div><p><strong>Processing stopped. Displaying partial results...</strong></p></div>"


if __name__ == "__main__":
    app.run(debug=True)
    