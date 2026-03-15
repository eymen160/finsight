"""
FinSight — RAG Pipeline
=========================
Handles ingestion and retrieval of financial documents (10-K, 10-Q, etc.)
using LangChain + FAISS.

Architecture:
  1. Load   — PDFs are loaded via PyPDFLoader
  2. Split  — RecursiveCharacterTextSplitter chunks the text
  3. Embed  — Embeddings via LangChain (local or API-based)
  4. Index  — FAISS vector store, persisted to disk
  5. Retrieve — Similarity search returns top-K chunks

Usage:
    from core.rag.pipeline import RAGPipeline

    pipe = RAGPipeline()
    pipe.ingest("data/documents/AAPL_10K_2024.pdf")
    context = pipe.retrieve("What is Apple's revenue growth?")
"""

import os
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config.settings import settings
from core.exceptions import DocumentLoadError, IndexNotFoundError, RAGError
from core.logger import get_logger

logger = get_logger(__name__)

# Local embedding model — no API key needed, runs offline
_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class RAGPipeline:
    """
    Manages a FAISS vector store for financial document Q&A.

    The pipeline is lazy — it does not load models until first use.
    Call `ingest()` to add documents, `retrieve()` to query.
    """

    def __init__(self) -> None:
        self._index_path = Path(settings.faiss_index_path)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._embeddings: HuggingFaceEmbeddings | None = None
        self._store: FAISS | None = None

    # ── Private ───────────────────────────────────────────────

    def _get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            logger.info("loading_embedding_model", model=_EMBED_MODEL)
            self._embeddings = HuggingFaceEmbeddings(
                model_name=_EMBED_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    def _load_store(self) -> None:
        """Load an existing FAISS index from disk if available."""
        if self._store is not None:
            return
        if self._index_path.exists():
            logger.info("loading_faiss_index", path=str(self._index_path))
            self._store = FAISS.load_local(
                str(self._index_path),
                self._get_embeddings(),
                allow_dangerous_deserialization=True,
            )
        # If no index exists yet, self._store remains None

    # ── Public API ────────────────────────────────────────────

    def ingest(self, file_path: str | Path) -> int:
        """
        Load a PDF, split it into chunks, and add to the FAISS index.

        Args:
            file_path: Path to a PDF document.

        Returns:
            Number of chunks indexed.

        Raises:
            DocumentLoadError: if the file cannot be read.
            RAGError: on indexing failures.
        """
        path = Path(file_path)
        if not path.exists():
            raise DocumentLoadError(str(path), "File not found")
        if path.suffix.lower() != ".pdf":
            raise DocumentLoadError(str(path), "Only PDF files are supported")

        logger.info("ingesting_document", path=str(path))

        try:
            loader = PyPDFLoader(str(path))
            raw_docs: list[Document] = loader.load()
        except Exception as exc:
            raise DocumentLoadError(str(path), str(exc)) from exc

        chunks = self._splitter.split_documents(raw_docs)
        logger.info("document_split", n_chunks=len(chunks), source=path.name)

        try:
            embeddings = self._get_embeddings()
            if self._store is None:
                self._store = FAISS.from_documents(chunks, embeddings)
            else:
                self._store.add_documents(chunks)
            self._persist()
        except Exception as exc:
            raise RAGError(f"Failed to index '{path.name}': {exc}") from exc

        logger.info("ingestion_complete", chunks_added=len(chunks))
        return len(chunks)

    def retrieve(self, query: str, k: int | None = None) -> str:
        """
        Search the index and return concatenated context chunks.

        Args:
            query: Natural language question.
            k:     Number of chunks to retrieve (defaults to settings.top_k_results).

        Returns:
            A single string of retrieved context, ready to inject into a prompt.

        Raises:
            IndexNotFoundError: if no documents have been ingested yet.
        """
        self._load_store()
        if self._store is None:
            raise IndexNotFoundError(
                "No documents have been indexed yet. "
                "Upload a PDF via the Document Q&A page first."
            )

        k = k or settings.top_k_results
        logger.info("rag_retrieve", query=query[:80], k=k)

        docs: list[Document] = self._store.similarity_search(query, k=k)

        if not docs:
            return "No relevant context found in the indexed documents."

        parts = []
        for i, doc in enumerate(docs, start=1):
            source = doc.metadata.get("source", "Unknown")
            page   = doc.metadata.get("page", "?")
            parts.append(
                f"[Excerpt {i} — {Path(source).name}, p.{page}]\n{doc.page_content}"
            )

        return "\n\n---\n\n".join(parts)

    def list_documents(self) -> list[str]:
        """Return a list of unique source file names in the index."""
        self._load_store()
        if self._store is None:
            return []
        sources: set[str] = set()
        for doc in self._store.docstore._dict.values():
            src = doc.metadata.get("source", "")
            if src:
                sources.add(Path(src).name)
        return sorted(sources)

    def _persist(self) -> None:
        """Save the current FAISS index to disk."""
        if self._store is None:
            return
        self._index_path.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(self._index_path))
        logger.info("faiss_index_saved", path=str(self._index_path))
