import chromadb
from src.backend.rag.chroma_collection_manager import load_chroma_collection, get_relevant_passage  # type: ignore[import-not-found]

client = chromadb.PersistentClient(path="chroma_vector_db")
collections = client.list_collections()
print(collections)


db = load_chroma_collection(
    path="chroma_vector_db", name="rekomendacjaa-dotyczacazarzadzaniap"
)
relevant_text = get_relevant_passage(query="ryzyko inwestycyjne", db=db, n_results=1)
print(relevant_text)
