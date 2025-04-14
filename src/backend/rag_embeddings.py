import re
import logging
import os

import google.generativeai as genai
from chromadb import Documents, EmbeddingFunction, Embeddings
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
    