import typing
import threading

from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from backend.text_extraction import process_pdfs  # type: ignore[import-not-found]

app = Flask(__name__)
CORS(app)  # IS IT NEEDED


stop_flag = threading.Event()


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_text() -> Response:
    try:
        prompt = request.form["input"]
        if not prompt:
            response = jsonify({"error": "No input provided"})
            response.status_code = 400
            return response

        stop_flag.clear()

        # a generator function to stream results back
        def generate_results() -> typing.Generator:
            pdfs_to_process = process_pdfs(prompt)

            for result in pdfs_to_process:
                if stop_flag.is_set():
                    break
                yield (
                    "<div><p><strong>Response for:</strong> "
                    + f"<em>{result['pdf_name']}</em><br>{result['content']}<br><br></p></div>"
                )

        return Response(generate_results(), mimetype="text/html")

    except Exception as e:
        response = jsonify({"error": str(e)})
        response.status_code = 500
        return response


@app.route("/clear_output", methods=["GET"])
def clear_output() -> str:
    return ""

@app.route("/stop_processing", methods=["GET"])
def stop_processing() -> str:
    stop_flag.set() 
    return "<div><p><strong>Processing stopped. Displaying partial results...</strong></p></div>"

if __name__ == "__main__":
    app.run(debug=True)
