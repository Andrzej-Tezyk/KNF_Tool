from typing import Generator

from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from backend.text_extraction import process_pdfs  # type: ignore[import-not-found]

app = Flask(__name__)
CORS(app)  # IS IT NEEDED


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_text() -> Response:
    try:
        prompt = request.form["input"]

        # a generator function to stream results back
        def generate_results() -> Generator:
            pdfs_to_process = process_pdfs(prompt)

            for result in pdfs_to_process:
                yield (
                    "<div><p><strong>Podsumowanie dla</strong>:"
                    + f"<em>{result['pdf_name']}</em><br>{result['content']}<br><br></p></div>"
                )

        return Response(generate_results(), mimetype="text/html")

    except Exception as e:
        response = jsonify({"error": str(e)})
        response.status_code = 500
        return response


if __name__ == "__main__":
    app.run(debug=True)
