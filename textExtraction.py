from PyPDF2 import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv

import pathlib
import os


load_dotenv()


def extract(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    with open(pdf_path, 'rb') as f:
        pdf = PdfReader(f)

        numPages = len(pdf.pages)
        print(f"Number of pages: {numPages}")

        text = ''

        try:    
            for i in range (numPages):
                page = pdf.pages[i]
                text += page.extract_text()
            return text
        
        except IndexError:
            print(f"Something went wrong with {pdf_path}")

#pdf_path = r"C:\Users\Andrzej T (Standard)\Desktop\Projects\KNF_Tool\pdfs\knf_123958_RekomendacjaF_39880.pdf"

files = [f for f in pathlib.Path().glob("pdfs/*.pdf")]

for file in files:
    extract(file)


genai.configure(api_key=f"{os.getenv.GEMINI_API_KEY}")