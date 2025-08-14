from pathlib import Path
import chromadb

from src.backend.document_id_manager import _load_mapping



"""
File for unused functions and code snippets
"""


"""
document_id_manager.py
"""


def get_title_by_id(doc_id: str) -> str | None:
    mapping = _load_mapping()
    for entry in mapping.values():
        if entry["id"] == doc_id:
            return entry["title"]
    return None


"""
testing code
"""
project_root = Path(__file__).parent.parent.parent
chroma_path = str(project_root / "chroma_vector_db")
client = chromadb.PersistentClient(path=chroma_path)
collections = client.list_collections()
print("Collections in ChromaDB:")
for c in collections:
    print(c.name)
