import logging
from typing import Any

import chromadb

log = logging.getLogger("__name__")


def get_chroma_client(path: str) -> Any:
    """Returns a ChromaDB client instance.

    This function initializes and returns a ChromaDB client instance.
    The client is used to interact with the ChromaDB database for storing and retrieving data.

    Returns:
        chromadb.PersistentClient: An instance of the ChromaDB client.
    """
    return chromadb.PersistentClient(path=path)
