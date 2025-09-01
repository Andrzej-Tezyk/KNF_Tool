import logging
import os
from typing import Any

import chromadb

log = logging.getLogger("__name__")

os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"


def get_chroma_client(path: str) -> Any:
    """Returns a ChromaDB client instance.

    This function initializes and returns a ChromaDB client instance.
    The client is used to interact with the ChromaDB database for storing and retrieving data.

    Returns:
        chromadb.PersistentClient: An instance of the ChromaDB client.
    """
    settings = chromadb.config.Settings()
    settings.anonymized_telemetry = False

    return chromadb.PersistentClient(path=path, settings=settings)
