import asyncio
import logging
import traceback
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

from chromadb import PersistentClient
from rag_chromadb import create_chroma_db, load_chroma_collection, get_relevant_passage
from extract_text import extract_text_from_pdf


PDF_FILES = Path("scraped_files")


log = logging.getLogger("__name__")

client = PersistentClient(path="exp_vector_db")



async def replace_polish_chars(text: str) -> str:
    """
    For documents names only.
    """
    polish_to_ascii = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ż": "z", "ź": "z",
        "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N",
        "Ó": "O", "Ś": "S", "Ż": "Z", "Ź": "Z",
    }

    return ''.join(polish_to_ascii.get(c, c) for c in text)

async def process_pdf(doc_path: Path) -> None:
    """Process a single PDF file asynchronously"""
    try:
        name = str(doc_path).replace(" ", "").lower()
        name = await replace_polish_chars(name)
        name = name[25:60]

        # Check if collection exists (this might be a blocking operation)
        existing_collections = await run_in_executor(client.list_collections)
        
        if any(collection.name == name for collection in existing_collections):
            log.info(f"Collection {name} already exists. Skipping processing of {doc_path}.")
            return

        # Extract text (potentially CPU-bound operation)
        text_list = await run_in_executor(extract_text_from_pdf, doc_path)

        # Create ChromaDB (potentially IO-bound operation)
        await run_in_executor(
            create_chroma_db,
            text_list,
            "exp_vector_db",
            name
        )

        log.info(f"{doc_path} was embedded.")

    except Exception as e:
        log.error(f"Error processing {doc_path}")
        traceback.print_exc()

async def run_in_executor(func, *args, **kwargs):
    """Run a blocking function in a thread pool executor"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(
            executor, 
            lambda: func(*args, **kwargs)
        )

async def setup_chroma_db_async(doc_paths: List[Path], max_concurrency: int = 4) -> None:
    """Process multiple PDF files concurrently with limited concurrency"""
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def process_with_semaphore(doc_path: Path) -> None:
        async with semaphore:
            await process_pdf(doc_path)
            log.debug(f"{doc_path} was embedded into chromadb.")
    
    tasks = [process_with_semaphore(pdf_file) for pdf_file in doc_paths]
    await asyncio.gather(*tasks)

async def main() -> None:
    if PDF_FILES.is_dir():
        pdf_files = list(PDF_FILES.glob("*.pdf"))
        await setup_chroma_db_async(pdf_files)
    else:
        log.error(f"The path {PDF_FILES} is not a directory.")

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())