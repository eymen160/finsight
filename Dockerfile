FROM python:3.11-slim

# Install system deps needed by faiss/numpy in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (layer cache)
COPY backend/requirements.txt ./requirements.txt

# Install all packages — pinned exact versions for reproducibility + speed
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    # Web framework
    "fastapi==0.111.0" \
    "uvicorn[standard]==0.30.0" \
    "python-multipart==0.0.9" \
    # Config
    "pydantic==2.7.0" \
    "pydantic-settings==2.3.0" \
    "python-dotenv==1.0.0" \
    # AI
    "anthropic==0.84.0" \
    # Data — pre-built wheels, no compile
    "numpy==1.26.4" \
    "pandas==2.2.2" \
    "faiss-cpu==1.8.0" \
    # Finance
    "yfinance==0.2.40" \
    "ta==0.11.0" \
    "requests==2.32.3" \
    "requests-cache==1.2.1" \
    # RAG
    "pypdf==4.3.1" \
    "tiktoken==0.7.0" \
    # Utils
    "tenacity==8.3.0" \
    "structlog==24.2.0"

# Copy source code AFTER pip install (don't invalidate pip cache on code changes)
COPY core/    ./core/
COPY config/  ./config/
COPY backend/ ./backend/

EXPOSE 8000

# Single worker on free tier (2 workers = OOM on 512MB RAM)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "75"]
