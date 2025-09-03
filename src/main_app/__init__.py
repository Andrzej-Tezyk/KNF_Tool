import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_caching import Cache
from pathlib import Path

from backend.utils.custom_logger import CustomFormatter
from backend.rag.chroma_instance import get_chroma_client
from .config import Config

socketio = SocketIO(cors_allowed_origins="*")
cache = Cache()
chroma_client = get_chroma_client(Config.CHROMA_CLIENT_DIR)

# Setup logging
log = logging.getLogger("__name__")
log.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
log.addHandler(ch)


def create_app(config_class: type[Config] = Config) -> Flask:
    """Creates and configures the Flask application."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    # Ensure cache directory exists
    Path(app.config["CACHE_DIR"]).mkdir(parents=True, exist_ok=True)

    # Initialize extensions with the app
    socketio.init_app(app)
    cache.init_app(app)

    log.info("Vector DB initialized")

    # Register Blueprints
    from . import routes

    app.register_blueprint(routes.main_bp)

    # Import SocketIO events to register them
    from . import events  # noqa: F401

    return app
