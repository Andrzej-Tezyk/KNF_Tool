import typing
import threading
import markdown
from flask import Flask, request, render_template, Response, stream_with_context
from backend.text_extraction import process_pdfs  # type: ignore[import-not-found]

app = Flask(__name__)

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

        stop_flag.clear()

        def generate_results() -> typing.Generator:
            pdfs_to_process = process_pdfs(prompt)

            for result in pdfs_to_process:
                if stop_flag.is_set():
                    yield "<div><p><strong>Processing stopped. Partial results displayed.</strong></p></div>"
                    break

                if "error" in result:
                    yield (
                        f"<div><p><strong>Error:</strong> {result['error']}</p></div>"
                    )
                else:
                    markdown_content = markdown.markdown(result["content"])
                    yield f"""
                    <div style="border: 1px solid var(--border-color); padding: 1rem; margin-bottom: 1rem;">
                        <h3 style="color: var(--primary-color);">
                            Result for <em>{result['pdf_name']}</em>
                        </h3>
                        <div>{markdown_content}</div>
                    </div>
                    """

        return Response(
            stream_with_context(generate_results()), content_type="text/html"
        )

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
    stop_flag.set()
    return "<div><p><strong>Processing stopped. Displaying partial results...</strong></p></div>"


if __name__ == "__main__":
    app.run(debug=True)
