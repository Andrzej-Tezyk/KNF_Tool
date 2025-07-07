from typing import Any
import logging

import chromadb
from backend.rag_embeddings import GeminiEmbeddingFunction
from dotenv import load_dotenv
import google.generativeai as genai  # type: ignore[unused-ignore]
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


log = logging.getLogger("__name__")

load_dotenv()

#Autocut cosine similarity threshold
similarity_threshold = 0.75


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

    # Keyword-based ChromaDB retrieval
    results = db.query(query_texts=[query], n_results=n_results)

    passages = results["documents"][0]
    metadatas = results["metadatas"][0]

    chroma_chunks  = []
    for i, passage in enumerate(passages):
        page_number = metadatas[i].get("page_number", "unknown")
        chroma_chunks.append((passage, page_number))

    # Embedding-based semantic Gemini retrieval (Hybrid Search)
    try:
        hs_model = genai.GenerativeModel("embedding-001")
        query_embedding = np.array(hs_model.embed_content(content=query, task_type="retrieval_query")["embedding"])
        all_data = db.get(include=["documents", "metadatas"])
        all_docs = all_data["documents"]
        all_metas = all_data["metadatas"]
        doc_page_pairs = list(zip(all_docs, all_metas))
        dense_texts = [doc[0] for doc in doc_page_pairs]
        dense_embeddings = [np.array(hs_model.embed_content(content=txt, task_type="retrieval_document")["embedding"])
            for txt in dense_texts]
        similarities = cosine_similarity([query_embedding], dense_embeddings)[0]
        dense_ranked = sorted(zip(doc_page_pairs, similarities), key=lambda x: x[1], reverse=True)
        for (text, meta), score in dense_ranked:
            log.debug(f"Score: {score:.4f} | Page: {meta.get('page_number')} | Excluded: {score < similarity_threshold}")
        # Autocut by similarity score
        gemini_chunks = [(text, meta.get("page_number", "unknown")) for (text, meta), score in dense_ranked[:n_results] if score >= similarity_threshold]
    except Exception as e:
        log.warning(f"Gemini embedding failed: {e}")
        gemini_chunks = []

    # Merge results from both retrievals 
    seen_passages = set()
    combined_passages = []
    for passage, page in chroma_chunks + gemini_chunks:
        if passage not in seen_passages:
            combined_passages.append((passage, page))
            seen_passages.add(passage)

    log.debug("Hybrid passages with page numbers sent.")
    return combined_passages
