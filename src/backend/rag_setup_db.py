from rag_embeddings import split_text
from rag_chromadb import create_chroma_db, load_chroma_collection, get_relevant_passage
from extract_text import extract_text_from_pdf

'''
pdf_path = "scraped_files/2025-01-17_Rekomendacja A - dotycząca zarządzania przez banki ryzykiem związanym z działalnością na instrumentach pochodnych.pdf"


pdf_text = extract_text_from_pdf(pdf_path)
pdf_text_split = split_text(pdf_text)


chroma_db, name = create_chroma_db(documents=pdf_text_split, 
                                   path="rag",
                                   name="exp")

'''

db=load_chroma_collection(path="rag", name="exp")

relevant_text = get_relevant_passage(query="ryzyko inwestycyjne",db=db,n_results=3)

print(relevant_text)