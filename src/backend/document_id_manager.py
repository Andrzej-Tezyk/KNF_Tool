import json
from pathlib import Path
from threading import Lock
import time
from typing import cast
from typing import TypedDict

MAPPING_PATH = Path(__file__).parent.parent.parent / "document_id_map.json"
_lock = Lock()


class Entry(TypedDict):
    id: str
    timestamp: int
    title: str


def _load_mapping() -> dict[str, Entry]:
    if MAPPING_PATH.exists():
        with open(MAPPING_PATH, encoding="utf-8") as f:
            return cast(dict[str, Entry], json.load(f))
    return {}


def _save_mapping(mapping: dict) -> None:
    with open(MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def get_or_assign_id(title: str) -> Entry:
    """Assigns a new ID and timestamp if not present, else returns existing."""
    with _lock:  # secures that only one thread can have access to the file
        mapping = _load_mapping()  # should be: dict[str, Entry]
        if title in mapping:
            return cast(Entry, mapping[title])
        # Assign new ID (incremental)
        next_id = str(len(mapping) + 1)
        timestamp = int(time.time())
        entry: Entry = {"id": next_id, "timestamp": timestamp, "title": title}
        mapping[title] = entry
        _save_mapping(mapping)
        return entry


# def get_title_by_id(doc_id: str) -> None:
#     mapping = _load_mapping()
#     for entry in mapping.values():
#         if entry["id"] == doc_id:
#             return entry["title"]
#     return None
