from PyPDF2 import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv

import pathlib
import os
import traceback


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")



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
    try:
        print(f"{file} is analyzed")
        text = extract(file)
        response = model.generate_content(f"Czy ten dokument zawiera cokolwiek na temat Sztucznej Inteligencji? Jeżeli tak, to posumuj to co jest napisane na temat Sztucznej Inteligencji. {text}")

        with open("results.txt", "a", encoding="cp1250", errors="replace") as f:
            f.write(f"Podsumowanie dla: {file}\n{response.text} \n \n")

        print(f"Response for {file} was saved!")
        print("")

    except Exception as e:
        print(f"There is a problem with {file}. \n Error messange: {e}")
        print("")
        traceback.print_exc()