import re
import logging
import os

import google.generativeai as genai
from chromadb import Documents, EmbeddingFunction, Embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from extract_text import extract_text_from_pdf

log = logging.getLogger("__name__")


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")


def clean_extracted_text (text: str):
    cleaned_text = ""

    for i, line in enumerate(text.split('\n')):
        if len(line) > 10 and i > 70:
            cleaned_text += line + '\n'

    for char in ['~', '©', '_']:
        cleaned_text = cleaned_text.replace(char, '')

    return cleaned_text


def split_text(text: str):
    """
    Splits a text string into a list of non-empty substrings based on the specified pattern.
    The "\n \n" pattern will split the document paragraph by paragraph.

    Args:
        text (str): The input text to be split.

    Returns:
        List[str]: A list containing non-empty substrings obtained by splitting the input text.
    """
    split_text = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=100,
                    length_function=len,
                    add_start_index=True,
                )
    return split_text


class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Custom embedding funtion with gemini developer API for document retrieval.

    Class is based on the EmbeddingFunction of chromadb. Implements the __call__ method to generate embeddings.
    
    Args:
        input (Documents): A collection of documents embedded.

    Returns:
        Embeddings.
    """

    def __call__(self, input: Documents) -> Embeddings:
        genai.configure(api_key=GEMINI_API_KEY)
        model = "models/text-embedding-004"
        title = "custom query"
        return genai.embed_content(
                                    model=model,
                                    content=input,
                                    task_type="retrieval_document",
                                    title=title)["embedding"]
    

pdf_path = "scraped_files/2025-01-17_Rekomendacja A - dotycząca zarządzania przez banki ryzykiem związanym z działalnością na instrumentach pochodnych.pdf"

pdf_text = extract_text_from_pdf(pdf_path=pdf_path, language="polish")

cleanded_text  = clean_extracted_text(pdf_text)

print(cleanded_text)

text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=100,
                    length_function=len,
                    add_start_index=True,
                )

splited_text = text_splitter.create_documents([cleanded_text])

#print(splited_text[0].page_content)