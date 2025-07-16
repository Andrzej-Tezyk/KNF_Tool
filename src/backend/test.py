# import chromadb
# from rag_use_chroma_collections import load_chroma_collection, get_relevant_passage  # type: ignore[import-not-found]

# client = chromadb.PersistentClient(path="chroma_vector_db")
# collections = client.list_collections()
# print(collections)


# db = load_chroma_collection(
#     path="chroma_vector_db", name="rekomendacjaa-dotyczacazarzadzaniap"
# )
# relevant_text = get_relevant_passage(query="ryzyko inwestycyjne", db=db, n_results=1)
# print(relevant_text)

from pathlib import Path
import chromadb

project_root = Path(__file__).parent.parent.parent
chroma_path = str(project_root / "chroma_vector_db")
client = chromadb.PersistentClient(path=chroma_path)
collections = client.list_collections()
print("Collections in ChromaDB:")
for c in collections:
    print(c.name)