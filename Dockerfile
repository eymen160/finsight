FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install all deps — faiss-cpu last (needs libgomp1)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "fastapi==0.111.0" \
    "uvicorn[standard]==0.30.0" \
    "python-multipart==0.0.9" \
    "pydantic==2.7.0" \
    "pydantic-settings==2.3.0" \
    "python-dotenv==1.0.0" \
    "anthropic==0.84.0" \
    "numpy==1.26.4" \
    "pandas==2.2.2" \
    "yfinance==0.2.40" \
    "ta==0.11.0" \
    "requests==2.32.3" \
    "requests-cache==1.2.1" \
    "pypdf==4.3.1" \
    "tiktoken==0.7.0" \
    "tenacity==8.3.0" \
    "structlog==24.2.0" && \
    pip install --no-cache-dir "faiss-cpu==1.8.0" || \
    echo "faiss-cpu install failed — keyword fallback will be used"

COPY core/    ./core/
COPY config/  ./config/
COPY backend/ ./backend/

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "7860", \
     "--workers", "1", \
     "--timeout-keep-alive", "75"]
