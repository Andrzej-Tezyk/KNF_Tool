import time
import logging
<<<<<<< HEAD:src/backend/rag_chromadb.py
import os
from typing import Any
from dotenv import load_dotenv
=======
>>>>>>> origin/main:src/backend/rag/create_chromadb.py

import chromadb

<<<<<<< HEAD:src/backend/rag_chromadb.py
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
=======

from backend.rag.llm_embedding_function import get_gemini_ef
>>>>>>> origin/main:src/backend/rag/create_chromadb.py


log = logging.getLogger("__name__")


def create_chroma_db(documents: list, path: str, name: str, page_numbers: list = None):  # type: ignore
    """
    Creates a chroma database.

    Args:
        documents: Arr of documents to be added to a database.
        path: The path where the created database will be stored.
        name: name of the collection within the database.

    Returns:
        Tuple: A tuple containing created chroma collection and its name.
    """
    chroma_client = chromadb.PersistentClient(path=path)
    db = chroma_client.create_collection(name=name, embedding_function=get_gemini_ef())

    for index, document in enumerate(documents):

        page_num = page_numbers[index] if page_numbers else index + 1

        db.add(documents=document, ids=str(index), metadatas={"page_number": page_num})
        time.sleep(5)
        log.debug(f"Chunk {index} of {document} from page {page_num} was vectorized.")

    return db, name
