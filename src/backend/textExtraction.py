from PyPDF2 import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv

import pathlib
import os
import traceback
from datetime import datetime
import time

#file naming
run_time = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
#another model to be used: "gemini-1.5-flash"
model = genai.GenerativeModel("gemini-1.5-flash-8b")


# folder for downloaded pdfs
output = 'C:/Users/Andrzej T (Standard)/Desktop/Projects/KNF_Tool/output'
if not os.path.exists(output):
    os.makedirs(output)


def extract(pdf_path):
    '''
        text extraction from pdfs;
        pdf_path: path to .pdf files
    '''
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    with open(pdf_path, 'rb') as f:
        pdf = PdfReader(f)

        numPages = len(pdf.pages)
        print(f"Number of pages: {numPages}")

        text = ''

        try:    
            for i in range (numPages): #loop through all pages
                page = pdf.pages[i]
                text += page.extract_text()
            return text
        
        except Exception as e:
            print(f"Something went wrong with {pdf_path}. Error messange: {e}")
            traceback.print_exc()


files = [f for f in pathlib.Path().glob("pdfs/*.pdf")]
num_files = len(files)

count = 1
for file in files:
    try:
        print(f"{count}/{num_files}")
        print(f"Document: {file} is beeing analyzed.")
        text = extract(file)
        response = model.generate_content(f"Czy ten dokument zawiera cokolwiek na temat Sztucznej Inteligencji? Jeżeli tak, to posumuj to co jest napisane na temat Sztucznej Inteligencji. {text}")

        #replace -> sometimes double space between words occure; most likely reason: pdf formating
        output_path = os.path.join(output, f"{run_time}.txt")
        with open(output_path, "a", encoding="cp1250", errors="replace") as f:
            f.write(f"Podsumowanie dla: {file.stem}\n\n{response.text.replace('  ', ' ')} \n\n\n\n\n")

        print(f"Response for: {file} was saved!")
        print("")

    except Exception as e:
        print(f"There is a problem with {file}. \n Error messange: {e}")
        print("")
        traceback.print_exc()
    
    count += 1
    time.sleep(1) #to lower number api requests per sec