# main_app/events.py
import traceback

from flask import request
from flask_socketio import emit

from . import socketio, cache, log
from .services import process_document_query, process_chat_query

session_state = {}


@socketio.on("connect")
def handle_connect() -> None:
    """
    Initializes state for a new client connection.
    This function is called automatically whenever a new user connects.
    """
    sid = request.sid  # type: ignore [attr-defined]
    session_state[sid] = {"streaming": False}
    log.info(f"Client connected: {sid}. Initialized session state.")


@socketio.on("stop_processing")
def handle_stop() -> None:
    """
    Stops the stream for the current user's session by setting their streaming flag to False.
    """
    sid = request.sid  # type: ignore [attr-defined]
    if sid in session_state:
        session_state[sid]["streaming"] = False
        log.info(f"Processing stopped by user: {sid}")


@socketio.on("clear_cache")
def handle_clear_cache() -> None:
    """
    Clears all cached chat instances (UUIDs) created by the current client's session.
    """
    sid = request.sid  # type: ignore [attr-defined]
    session_map_key = f"session_map_{sid}"
    session_content_ids = cache.get(session_map_key)

    if session_content_ids:
        log.info(f"Clear event for sid: {sid}. Clearing session's cached entries.")
        for container_id in session_content_ids:
            if cache.delete(container_id):
                log.info(f"Deleted cache for key: {container_id}")
        cache.delete(session_map_key)
        log.info(f"Deleted session map for sid: {sid}")
    else:
        log.info(f"Clear event for sid: {sid}. No session map found to clear.")


# UNUSED - keep for handling clearing chat history in future if needed
@socketio.on("reset_chat_history")
def handle_reset_chat_history(data: dict) -> None:
    """
    Finds a specific chat session by its UUID and resets its history.
    """
    content_id = data.get("contentId")
    if not content_id:
        log.warning("Received reset_chat_history event without a contentId.")
        return

    log.info(f"Resetting chat history for UUID: {content_id}")
    cached_data = cache.get(content_id)

    if cached_data and "chat_history" in cached_data:
        cached_data["chat_history"] = cached_data["chat_history"][:2]
        cache.set(content_id, cached_data, timeout=3600)
        log.info(f"Successfully reset history for UUID: {content_id}")
        emit("history_reset_success", {"contentId": content_id})
    else:
        log.warning(f"Could not find data to reset for UUID: {content_id}")


@socketio.on("start_processing")
def handle_start_processing(data: dict) -> None:
    """
    Handles the initial query for documents. It delegates the core logic
    to the service layer and streams the results back to the client.
    """
    sid = request.sid  # type: ignore [attr-defined]
    if sid not in session_state:
        handle_connect()

    session_state[sid]["streaming"] = True
    print("session state: ", session_state)
    log.info(f"Started processing for SID: {sid}")

    try:
        for result in process_document_query(data, sid):
            if not session_state.get(sid, {}).get("streaming", False):
                log.info(f"Stream manually stopped for SID: {sid}")
                break

            event = result.get("event")
            payload = result.get("payload")
            if event and payload is not None:
                emit(event, payload)

    except Exception as e:
        log.error(f"Error during start_processing for SID {sid}: {e}")
        traceback.print_exc()
        emit("error", {"message": f"An unexpected error occurred: {str(e)}"})
    finally:
        if sid in session_state:
            session_state[sid]["streaming"] = False
        emit("stream_stopped")
        log.info(f"Processing finished for SID: {sid}")


@socketio.on("send_chat_message")
def handle_chat_message(data: dict) -> None:
    """
    Handles a follow-up chat message. It delegates the core logic
    to the service layer and streams the results back to the client.
    """
    sid = request.sid  # type: ignore [attr-defined]
    if sid not in session_state:
        handle_connect()

    print("SID: ", sid)
    session_state[sid]["streaming"] = True
    print("Session state: ", session_state)
    log.info(f"Chat message received from SID: {sid}")
    try:
        for result in process_chat_query(data, sid):
            if not session_state.get(sid, {}).get("streaming", False):
                log.info(f"Chat stream manually stopped for SID: {sid}")
                break

            event = result.get("event")
            payload = result.get("payload")
            if event and payload is not None:
                emit(event, payload)

    except Exception as e:
        log.error(f"Error during send_chat_message for SID {sid}: {e}")
        traceback.print_exc()
        emit("error", {"message": f"An unexpected error occurred: {str(e)}"})
    finally:
        if sid in session_state:
            session_state[sid]["streaming"] = False
        emit("stream_stopped")
        log.info(f"Chat response finished for SID: {sid}")

@socketio.on("load_chat_history")
def handle_load_chat_history(data: dict) -> None:
    """
    Loads chat history from the cache and sends it to the client.
    """
    content_id = data.get("contentId")
    if not content_id:
        log.warning("Received load_chat_history event without a contentId.")
        return

    log.info(f"Loading chat history for contentId: {content_id}")
    cached_data = cache.get(content_id)

    if cached_data:
        # Send the raw data (title and history) back to the client
        emit(
            "chat_history_loaded",
            {
                "title": cached_data.get("title", "Unknown Title"),
                "chat_history": cached_data.get("chat_history", []),
            },
        )
    else:
        log.warning(f"No cache found for contentId: {content_id}")
        emit("error", {"message": f"Could not load chat history for ID: {content_id}"})

@socketio.on("disconnect")
def handle_disconnect() -> None:
    """
    Cleans up session state and the user's cached data when they disconnect.
    """
    sid = request.sid  # type: ignore [attr-defined]
    log.info(f"Client disconnected: {sid}. Cleaning up...")

    session_state.pop(sid, None)

    session_map_key = f"session_map_{sid}"
    session_content_ids = cache.get(session_map_key)

    if session_content_ids:
        log.info(f"Cleaning up cached entries for disconnected SID: {sid}")
        for container_id in session_content_ids:
            if cache.delete(container_id):
                log.info(f"Deleted cache for key: {container_id}")
        cache.delete(session_map_key)
        log.info(f"Deleted session map for SID: {sid}")
    else:
        log.info(f"No session map found for SID: {sid}, no cache cleanup needed.")
