from typing import Any
import os

from dotenv import load_dotenv
import chromadb.utils.embedding_functions as embedding_functions


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

def get_gemini_ef() -> Any:
    """
    Returns a Google Gemini embedding function instance.

    This function initializes and returns an instance of the Google Gemini
    embedding function, which is used for generating embeddings for text data.

    Returns:
        embedding_functions.GoogleGenerativeAiEmbeddingFunction: An instance of the Google Gemini embedding function.
    """
    return embedding_functions.GoogleGenerativeAiEmbeddingFunction(
        api_key=GEMINI_API_KEY
    )