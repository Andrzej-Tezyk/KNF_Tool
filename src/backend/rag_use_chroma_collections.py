from typing import Any
import logging

import chromadb
from backend.rag_embeddings import GeminiEmbeddingFunction
from dotenv import load_dotenv
import google.generativeai as genai  # type: ignore[unused-ignore]
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
import numpy as np


log = logging.getLogger("__name__")

load_dotenv()

# Autocut cosine similarity threshold
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


def autocut_gemini(
    ranked_pairs: list[tuple[tuple[str, dict], float]], n_results: int, threshold: float
) -> list[tuple[str, Any]]:
    """
    Filter and return top-ranked passages from Gemini-based retrieval above the specified similarity threshold.
    The function is applied only on Gemini-based retrieval to avoid lack of return from Chroma-based retrieval.

    Args:
        ranked_pairs: List of ((text, metadata), similarity_score) tuples.
        n_results: number of relevant results to consider.
        threshold: minimum similarity score to include a passage.

    Returns:
        A list of (text, page_number) tuples where the similarity score meets or exceeds the threshold.
    """
    return [
        (text, meta.get("page_number", "unknown"))
        for (text, meta), score in ranked_pairs[:n_results]
        if score >= threshold
    ]


def rerank_passages(
    query_embedding: list[float],
    passages_with_source: list[tuple[str, Any, str]],
    chroma_bias: float = 0.05,
) -> list[tuple[str, Any]]:
    """
    Rerank passages with source-aware scoring using Gemini semantic embeddings.

    Args:
        query_embedding: Precomputed embedding of the query
        passages_with_source: List of (text, page_number, source) tuples.
        chroma_bias: Boost for Chroma-derived (keyword-matched) passages
        that helps to prefer precision over semantic similarity.

    Returns:
        Reranked list of (passage_text, page_number) tuples.
    """
    reranked = []
    for passage, page, source in passages_with_source:
        try:
            passage_embedding = genai.embed_content(
                model="models/embedding-001",
                content=passage,
                task_type="retrieval_document",
            )["embedding"]

            similarity = cosine_similarity(
                [query_embedding], [np.array(passage_embedding)]
            )[0][0]

            if source == "chroma":
                similarity += chroma_bias

            reranked.append(((passage, page), similarity))
        except Exception as e:
            log.warning(f"Reranking failed for passage: {e}")

    reranked.sort(key=lambda x: x[1], reverse=True)
    return [(text, page) for (text, page), _ in reranked]


def get_relevant_passage(query: str, db: Any, n_results: int = 1) -> list:
    """
    Retrieve passages and their page numbers from the vector database using keyword and semantic approach.

    Args:
        query: Text to search.
        db: Database to query.
        n_results: Number of top results to return.

    Returns:
        A list of (passage_text, page_number) tuples. The number of tuples is always less or equal than 2*n_results,
        i.e. if n_results=1, maximum number of tuples is 2.
    """

    # Keyword-based ChromaDB retrieval
    results = db.query(query_texts=[query], n_results=n_results)

    passages = results["documents"][0]
    metadatas = results["metadatas"][0]

    chroma_chunks = []
    for i, passage in enumerate(passages):
        page_number = metadatas[i].get("page_number", "unknown")
        chroma_chunks.append((passage, page_number))

    # Embedding-based semantic Gemini retrieval (Hybrid Search)
    try:
        query_embedding = genai.embed_content(
            model="models/embedding-001",
            content=query,
            task_type="retrieval_query",
        )["embedding"]
        all_data = db.get(include=["documents", "metadatas"])
        all_docs = all_data["documents"]
        all_metas = all_data["metadatas"]
        doc_page_pairs = list(zip(all_docs, all_metas))
        dense_texts = [doc[0] for doc in doc_page_pairs]
        dense_embeddings = [
            np.array(
                genai.embed_content(
                    model="models/embedding-001",
                    content=txt,
                    task_type="retrieval_document",
                )["embedding"]
            )
            for txt in dense_texts
        ]
        similarities = cosine_similarity([query_embedding], dense_embeddings)[0]
        dense_ranked = sorted(
            zip(doc_page_pairs, similarities), key=lambda x: x[1], reverse=True
        )
        for (text, meta), score in dense_ranked:
            log.debug(
                f"Score: {score:.4f} | Page: {meta.get('page_number')} | Excluded: {score < similarity_threshold}"
            )
        gemini_chunks = autocut_gemini(dense_ranked, n_results, similarity_threshold)
    except Exception as e:
        log.warning(f"Gemini embedding failed: {e}")
        gemini_chunks = []

    # Merge results from both retrievals
    seen_passages = set()
    combined_passages = []

    for passage, page in chroma_chunks:
        if passage not in seen_passages:
            combined_passages.append((passage, page, "chroma"))
            seen_passages.add(passage)

    for passage, page in gemini_chunks:
        if passage not in seen_passages:
            combined_passages.append((passage, page, "gemini"))
            seen_passages.add(passage)

    # Chroma-preferred reranking
    reranked_passages = rerank_passages(
        query_embedding=query_embedding,
        passages_with_source=combined_passages,
        chroma_bias=0.05,
    )
    log.debug("Hybrid passages with page numbers sent.")
    return reranked_passages[:n_results]
