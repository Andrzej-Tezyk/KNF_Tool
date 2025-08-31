ARG PYTHON_VERSION=3.11.9
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Install system dependencies; for installing python packages which require low level like pandas
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-privileged user that the app will run under.
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser


# Install uv for dependency management
RUN pip install uv
# Copy dependency files
COPY uv.lock pyproject.toml ./
# Install dependencies
RUN uv sync --frozen --no-dev




# Development stage
FROM base as development
RUN uv sync --frozen
COPY . .
RUN mkdir -p scraped_files cache chroma_vector_db
# Set ownership
RUN chown -R appuser:appuser /app
# Switch to non-privileged user
USER appuser
EXPOSE 8000
# Development command (Flask development server)
CMD ["uv", "run", "python", "src/main.py"]




# Production stage
FROM base as production
RUN uv sync --frozen --no-dev
COPY . .
RUN mkdir -p scraped_files cache chroma_vector_db
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["uv", "run", "gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
     "--timeout", "120", \
     "--keep-alive", "2", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--preload", \
     "src.main:app"]
