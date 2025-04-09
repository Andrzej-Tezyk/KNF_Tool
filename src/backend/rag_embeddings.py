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


def split_text(text: str):
    """
    Splits a text string into a list of non-empty substrings based on the specified pattern.
    The "\n \n" pattern will split the document paragraph by paragraph.

    Args:
        text (str): The input text to be split.

    Returns:
        List[str]: A list containing non-empty substrings obtained by splitting the input text.
    """
    split_text = re.split('\n \n', text)
    return [i for i in split_text if i != ""]


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
    