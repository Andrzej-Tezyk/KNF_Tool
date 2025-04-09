import chromadb
import time
import logging
from typing import List

from rag_embeddings import GeminiEmbeddingFunction


log = logging.getLogger("__name__")


def create_chroma_db(documents:List, path:str, name:str):
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
    db = chroma_client.create_collection(name=name, embedding_function=GeminiEmbeddingFunction())

    for index, document in enumerate(documents):
        db.add(documents=document, ids=str(index))
        time.sleep(5)
        log.debug(f"Chunk {index} of {document} was vectorized.")

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
    db = chroma_client.get_collection(name=name, embedding_function=GeminiEmbeddingFunction())
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

    """
    passage = db.query(query_texts=[query], n_results=n_results)['documents'][0]
    log.debug("Passage sent.")
    return passage