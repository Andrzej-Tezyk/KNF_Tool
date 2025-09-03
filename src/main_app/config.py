import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Project Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "src" / "config" / "config.json"
CACHE_DIR = PROJECT_ROOT / "cache"
CHROMA_CLIENT_DIR = str(PROJECT_ROOT / "chroma_vector_db")
SCRAPED_FILES_DIR = PROJECT_ROOT / "scraped_files"


# --- Application Settings ---
class Config:
    with open(CONFIG_PATH) as f:
        _config_json = json.load(f)

    # --- Constants ---
    try:
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    except KeyError:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    SECRET_KEY = os.environ.get("SECRET_KEY", "a_default_secret_key")
    PDF_DIRECTORY = SCRAPED_FILES_DIR
    SYSTEM_PROMPT = _config_json["system_prompt"]
    ALLOWED_EXTENSIONS = {"pdf"}
    NUM_RETRIES = 5

    # --- Chroma Settings ---
    CHROMA_CLIENT_DIR = CHROMA_CLIENT_DIR
    CHROMADB_MAX_FILENAME_LENGTH = 60

    # --- Caching ---
    CACHE_DIR = CACHE_DIR
    CACHE_TYPE = "FileSystemCache"
    CACHE_THRESHOLD = 500

    # agents to avoid being blocked by the website
    USER_AGENT_LIST = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            + "(KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/"
            + "605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
        ),
        "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            + "(KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75"
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            + "(KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
        ),
    ]
