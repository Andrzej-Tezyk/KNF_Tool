import logging
import traceback
from pathlib import Path

from rag_embeddings import clean_extracted_text
from langchain.text_splitter import RecursiveCharacterTextSplitter
from rag_chromadb import create_chroma_db, load_chroma_collection, get_relevant_passage
from extract_text import extract_text_from_pdf


PDF_FILES = Path("scraped_files")


log = logging.getLogger("__name__")

POLISH_CHARS = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"


text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=100,
                    length_function=len,
                    add_start_index=True,
                )

pdf_path = "scraped_files/2025-01-17_Rekomendacja C - dotycząca zarządzania ryzykiem koncentracji.pdf"

pdf_text = extract_text_from_pdf(pdf_path)

cleanded_text  = clean_extracted_text(pdf_text)

#print(cleanded_text)

splited_text = text_splitter.create_documents([cleanded_text])

documents = []

for chunk in splited_text:
    documents.append(chunk.page_content)

chroma_db, name = create_chroma_db(documents=documents, 
                                   path="rag",
                                   name="exp1-rekomendacja-C")

db=load_chroma_collection(path="rag", name="exp1-rekomendacja-C")
relevant_text = get_relevant_passage(query="ryzyko inwestycyjne",db=db,n_results=3)
print(relevant_text)


'''
def replace_polish_chars(text: str) -> str:
    polish_to_ascii = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ż": "z", "ź": "z",
        "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N",
        "Ó": "O", "Ś": "S", "Ż": "Z", "Ź": "Z",
    }

    return ''.join(polish_to_ascii.get(c, c) for c in text)

def setup_chroma_db (doc_path: Path) -> None:
    try:
        text = extract_text_from_pdf(doc_path)
        cleanded_text  = clean_extracted_text(text)
        splited_text = text_splitter.create_documents([cleanded_text])

        documents = []
        for chunk in splited_text:
            documents.append(chunk.page_content)

        name = str(doc_path).replace(" ", "").lower()
        name = replace_polish_chars(name)
        name = name[25:60]

        create_chroma_db(documents=documents, 
                                path="vector_db",
                                name=name)
    
    except Exception as e:
        log.error(f"Error processing {doc_path}: {str(e)}")
        traceback.print_exc()


if PDF_FILES.is_dir():
    for pdf_file in PDF_FILES.glob("*.pdf"):
        setup_chroma_db(doc_path = pdf_file)
        log.debug(f"{pdf_file} was embedded into chromadb.")
else:
    log.error(f"The path {PDF_FILES} is not a directory.")

    '''