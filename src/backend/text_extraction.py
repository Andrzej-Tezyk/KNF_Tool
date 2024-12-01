import os
import time
import traceback
from pathlib import Path
import typing

import google.generativeai as genai  # type: ignore[import-untyped]
from dotenv import load_dotenv
from PyPDF2 import PdfReader

load_dotenv()


OUTPUT_DIR = Path("output")
SYSTEM_PROMPT = (
    "Do generowania odpowiedzi wykorzystaj tylko"
    + "to co jest zawarte w udostępnionych dokumentach."
)


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    "gemini-1.5-flash-8b", system_instruction=SYSTEM_PROMPT
)  # another model to be used: "gemini-1.5-flash"


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file.
    """
    try:
        with open(pdf_path, "rb") as file:
            pdf = PdfReader(file)
            print(f"Number of pages: {len(pdf.pages)}")

            text = ""
            try:
                for page in pdf.pages:  # loop through all pages
                    text += page.extract_text()
            except Exception as e:
                print(f"Something went wrong with {pdf_path}. Error messange: {e}")
                traceback.print_exc()
        return text
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        traceback.print_exc()
        return ""


def process_pdfs(prompt: str, pdfs_to_scan: typing.Generator) -> typing.Generator:
    """
    Process all PDFs in the scraped files directory, analyze them with the model,
    and save results to an output file.
    """

    if not prompt:
        yield {"error": "No prompt provided"}
        return

    try:
        for count, pdf in enumerate(pdfs_to_scan, 1):
            try:
                print(f"{count}/{len(pdfs_to_scan)}")
                print(f"Document: {pdf.stem} is beeing analyzed.")
                text = extract_text_from_pdf(pdf)
                if len(text) > 10:  # random small number
                    response = model.generate_content(f"{prompt} {text}")

                    # replace -> sometimes double space between words occure; most likely reason: pdf formating
                    response_text = response.text.replace("  ", " ")

                else:
                    file_to_send = genai.upload_file(pdf)
                    print(f"PDF uploaded successfully. File metadata: {file_to_send}\n")
                    response = model.generate_content(
                        [
                            prompt,
                            file_to_send,
                        ]
                    )

                    # replace -> sometimes double space between words occure; most likely reason: pdf formating
                    response_text = response.text.replace("  ", " ")

                yield {"pdf_name": pdf.stem, "content": response_text}
                print(f"Response for: {pdf.stem} was saved!\n")

            except Exception as e:
                print(f"There is a problem with {pdf.stem}. \n Error messange: {e}\n")
                traceback.print_exc()

            time.sleep(1)  # to lower number api requests to model per sec

    except Exception as e:
        yield {"error": str(e)}
