from typing import Any
import logging

import chromadb
from backend.rag_embeddings import GeminiEmbeddingFunction  # type: ignore[import-not-found]


log = logging.getLogger("__name__")


def load_chroma_collection(path: str, name: str) -> chromadb.Collection:
    """
    DO NOT USE IT FOR NOW.

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


def get_relevant_passage(query: str, db: Any, n_results: int = 1) -> list:
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
