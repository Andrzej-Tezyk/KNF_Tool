import os
import time
import traceback
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv
from PyPDF2 import PdfReader

load_dotenv()


SCRAPED_FILES_DIR = "scraped_files"
OUTPUT_DIR = Path("output")
SYSTEM_PROMPT = (
    "Do generowania odpowiedzi wykorzystaj tylko"
    + "to co jest zawarte w udostępnionych dokumentach."
)


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    "gemini-1.5-flash-8b", system_instruction=SYSTEM_PROMPT
)  # another model to be used: "gemini-1.5-flash"


def extract_text_from_pdf(pdf_path):
    with open(pdf_path, "rb") as file:
        pdf = PdfReader(file)
        print(f"Number of pages: {len(pdf.pages)}")

        text = ""
        try:
            for page in pdf.pages:  # loop through all pages
                text += page.extract_text()
            return text
        except Exception as e:
            print(f"Something went wrong with {pdf_path}. Error messange: {e}")
            traceback.print_exc()


pdfs_to_scan = list(Path().glob(f"{SCRAPED_FILES_DIR}/*.pdf"))
output_path = os.path.join(
    OUTPUT_DIR, f'{datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")}.txt'
)

llm_response_output = ""
for count, pdf in enumerate(pdfs_to_scan, 1):
    try:
        print(f"{count}/{len(pdfs_to_scan)}")
        print(f"Document: {pdf.stem} is beeing analyzed.")
        text = extract_text_from_pdf(pdf)
        if len(text) > 10: # random small number
            response = model.generate_content(
                "Czy ten dokument zawiera cokolwiek na temat Sztucznej Inteligencji?"
                + f"Jeżeli tak, to posumuj to co jest napisane na temat Sztucznej Inteligencji. {text}"
            )

            # replace -> sometimes double space between words occure; most likely reason: pdf formating
            llm_response_output += f"Podsumowanie dla: {pdf.stem}\n\n{response.text.replace('  ', ' ')} \n\n\n\n\n"
            print(f"Response for: {pdf.stem} was saved!\n")
        else:
            file_to_send = genai.upload_file(pdf)
            print(f"PDF uploaded successfully. File metadata: {file_to_send}\n")
            response = model.generate_content(
                ["Czy przesłany dokument zawiera cokolwiek na temat Sztucznej Inteligencji?"
                + f"Jeżeli tak, to posumuj to co jest napisane na temat Sztucznej Inteligencji.",
                file_to_send]
            )

            # replace -> sometimes double space between words occure; most likely reason: pdf formating
            llm_response_output += f"Podsumowanie dla: {pdf.stem}\n\n{response.text.replace('  ', ' ')} \n\n\n\n\n"
            print(f"Response for: {pdf.stem} was saved!\n")

    except Exception as e:
        print(f"There is a problem with {pdf.stem}. \n Error messange: {e}\n")
        traceback.print_exc()

    time.sleep(1)  # to lower number api requests to model per sec

with open(output_path, "w", encoding="utf-8", errors="replace") as llm_output_file:
    llm_output_file.write(llm_response_output)
