import asyncio
import logging
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from chromadb import PersistentClient

from src.backend.rag.create_chromadb import create_chroma_db  # type: ignore[import-not-found]
from src.backend.utils.extract_text import extract_text_from_pdf  # type: ignore[import-not-found]
from src.backend.rag.vector_db_name_generation import replace_polish_chars, generate_vector_db_document_name  # type: ignore[import-not-found]


PDF_FILES = Path("scraped_files")
CHROMADB_MAX_FILENAME_LENGTH = 60


log = logging.getLogger("__name__")

client = PersistentClient(path="chroma_vector_db")


async def replace_polish_chars_async(text: str) -> str:
    """
    async version of function replace_polish_chars()
    """
    return await run_in_executor(replace_polish_chars, text=text)  # type: ignore[no-any-return]


async def generate_vector_db_document_name_async(
    doc_path: Path, max_length: int = 60
) -> str:
    """
    async version of function generate_vector_db_document_name
    """
    return await run_in_executor(generate_vector_db_document_name, doc_path=doc_path, max_length=max_length)  # type: ignore[no-any-return]


async def process_pdf(doc_path: Path) -> None:
    """
    Process a single PDF file asynchronously
    """
    try:
        name = await generate_vector_db_document_name_async(
            doc_path, max_length=CHROMADB_MAX_FILENAME_LENGTH
        )

        # Check if collection exists (this might be a blocking operation)
        existing_collections = await run_in_executor(client.list_collections)

        if any(collection.name == name for collection in existing_collections):
            log.info(
                f"Collection {name} already exists. Skipping processing of {doc_path}."
            )
            return

        text_list = await run_in_executor(extract_text_from_pdf, doc_path)

        await run_in_executor(create_chroma_db, text_list, "chroma_vector_db", name)

        log.info(f"{doc_path} was embedded.")

    except Exception as e:
        log.error(f"Error processing {doc_path}. Error message: {e}")
        traceback.print_exc()


async def run_in_executor(func, *args, **kwargs):  # type: ignore[no-untyped-def]
    """
    Run a blocking function in a thread pool executor
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))


async def setup_chroma_db_async(doc_paths: list, max_concurrency: int = 4) -> None:
    """
    Process multiple PDF files concurrently with limited concurrency
    """
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


if __name__ == "__main__":
    asyncio.run(main())
