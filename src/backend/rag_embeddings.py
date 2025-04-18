import logging
import os

import google.generativeai as genai
from chromadb import Documents, EmbeddingFunction, Embeddings


log = logging.getLogger("__name__")


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")


def clean_extracted_text(text: str):

    for char in ["~", "©", "_", "\n"]:
        text = text.replace(char, "")

    return text


class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Custom embedding funtion (to use other model than 001) with gemini developer API for document retrieval. NOT IN USE

    Class is based on the EmbeddingFunction of chromadb. Implements the __call__ method to generate embeddings.

    Args:
        input (Documents): A collection of documents embedded.

    Returns:
        Embeddings.
    """

    def __call__(self, input_docs: Documents) -> Embeddings:
        genai.configure(api_key=GEMINI_API_KEY)
        model = "models/text-embedding-004"
        title = "custom query"
        return genai.embed_content(
            model=model, content=input_docs, task_type="retrieval_document", title=title
        )["embedding"]
