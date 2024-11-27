from backend.text_extraction import extract_text_from_pdf, process_pdfs
import os
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import google.generativeai as genai


SCRAPED_FILES_DIR = "scraped_files"
OUTPUT_DIR = Path("output")
SYSTEM_PROMPT = (
    "Do generowania odpowiedzi wykorzystaj tylko"
    + "to co jest zawarte w udostępnionych dokumentach."
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    "gemini-1.5-flash-8b", system_instruction=SYSTEM_PROMPT
)  # another model to be used: "gemini-1.5-flash"

load_dotenv()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_text():
    try:
        input_text = request.form.get('input')
        processed_text = process_pdfs(input_text)
        return processed_text

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True)