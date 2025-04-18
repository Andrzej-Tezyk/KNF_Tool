import chromadb
import time
import logging
from typing import List
import os

import chromadb.utils.embedding_functions as embedding_functions
from backend.rag_embeddings import GeminiEmbeddingFunction


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")


log = logging.getLogger("__name__")


def get_gemini_ef():
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


def create_chroma_db(
    documents: List, path: str, name: str, page_numbers: List[int] = None
):
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


def load_chroma_collection(path, name):
    """
    Loads an existing Chroma collection from the specified path with the given name.

    Args:
        path: The path where the Chroma database is stored.
        name: The name of the collection within the Chroma database.

    Returns:
        chromadb.Collection: The loaded Chroma Collection.
    """
    chroma_client = chromadb.PersistentClient(path=path)
    db = chroma_client.get_collection(
        name=name, embedding_function=GeminiEmbeddingFunction()
    )
    log.debug("Collection loaded.")

    return db


def get_relevant_passage(query, db, n_results=1):
    """
    Get data from vector database.

    Args:
        query: Text to search.
        db: Database to query.
        n_results:

    Returns:
        A list of tuples containing (passage_text, page_number).
    """
    results = db.query(query_texts=[query], n_results=n_results)

    passages = results["documents"][0]
    metadatas = results["metadatas"][0]

    passages_with_pages = []
    for i, passage in enumerate(passages):
        page_number = metadatas[i].get("page_number", "unknown")
        passages_with_pages.append((passage, page_number))

    log.debug("Passages with page numbers sent.")
    return passages_with_pages
