import chromadb
from rag_chromadb import load_chroma_collection, get_relevant_passage

client = chromadb.PersistentClient(path="exp_vector_db")
collections = client.list_collections()
print(collections)


db=load_chroma_collection(path="exp_vector_db", name="rekomendacjaa-dotyczacazarzadzaniap")
relevant_text = get_relevant_passage(query="ryzyko inwestycyjne",db=db,n_results=1)
print(relevant_text)