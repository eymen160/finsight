"""
FinSight — RAG Pipeline (LangChain-free)
==========================================
Retrieval-Augmented Generation pipeline built on:

- **pypdf**     — PDF text extraction
- **faiss-cpu** — approximate nearest-neighbour vector search
- **tiktoken**  — token-aware text chunking
- **Hash embeddings** — deterministic 768-dim vectors (no API key required)

Design decisions:
- No LangChain: avoids pydantic-v1 / Python 3.14 incompatibility.
- Chunking is paragraph-aware: financial documents have natural section
  breaks that should not be split mid-sentence.
- Hash embeddings trade recall quality for zero cost and offline operation.
  Replace :class:`_HashEmbedder` with an API-based embedder for production.
- The FAISS index is persisted to ``/tmp`` between Streamlit reruns so that
  uploaded documents survive page navigation without re-ingestion.

Usage::

    from core.rag.pipeline import RAGPipeline
    pipe = RAGPipeline()
    chunks_added = pipe.ingest("reports/AAPL_10K_2024.pdf")
    context = pipe.retrieve("What are Apple's main revenue segments?")
"""

from __future__ import annotations

import hashlib
import logging
import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
import pypdf

from config.settings import settings
from core.exceptions import (
    DocumentLoadError,
    DocumentParseError,
    IndexNotFoundError,
    RAGError,
)

log = logging.getLogger(__name__)

# ── Optional dependencies (graceful degradation) ──────────────

try:
    import faiss as _faiss_lib
    _FAISS_AVAILABLE = True
except ImportError:
    _faiss_lib = None  # type: ignore[assignment]
    _FAISS_AVAILABLE = False
    log.warning("faiss-cpu not installed — falling back to keyword search")

try:
    import tiktoken as _tiktoken_lib
    _TIKTOKEN_ENC = _tiktoken_lib.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENC = None


# ── Token counter ─────────────────────────────────────────────

def _count_tokens(text: str) -> int:
    """Return the approximate token count for *text*.

    Uses tiktoken (cl100k_base) when available; falls back to word count
    with a 1.3× multiplier as a conservative estimate.

    Args:
        text: Input string.

    Returns:
        Approximate token count as an integer.
    """
    if _TIKTOKEN_ENC is not None:
        return len(_TIKTOKEN_ENC.encode(text))
    # Fallback: words × 1.3 ≈ tokens for English prose
    return int(len(text.split()) * 1.3)


# ── Document chunker ──────────────────────────────────────────

class _ParagraphChunker:
    """Split document text into token-bounded, paragraph-aware chunks.

    Financial documents have natural paragraph breaks (double newlines,
    item headers) that should be honoured during chunking to keep related
    information together.

    Args:
        chunk_size: Maximum tokens per chunk.
        overlap:    Tokens of overlap between consecutive chunks to
                    preserve context across chunk boundaries.
    """

    def __init__(self, chunk_size: int = 800, overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.overlap    = overlap

    def split(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Split *text* into overlapping chunks with attached metadata.

        Args:
            text:     Raw extracted text from a single document page or section.
            metadata: Dict attached to each chunk (e.g. ``{"source": "file.pdf", "page": 3}``).

        Returns:
            A list of chunk dicts, each with keys ``"text"`` and ``"metadata"``.
        """
        # Split on paragraph boundaries; filter blank strings
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        if not paragraphs:
            return []

        chunks: list[dict[str, Any]] = []
        current_paras: list[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = _count_tokens(para)

            # Flush when adding this paragraph would exceed the limit
            if current_paras and current_tokens + para_tokens > self.chunk_size:
                chunks.append({"text": "\n\n".join(current_paras), "metadata": metadata})

                # Retain overlap: keep trailing paragraphs that fit within overlap budget
                overlap_buf: list[str] = []
                overlap_tok = 0
                for p in reversed(current_paras):
                    t = _count_tokens(p)
                    if overlap_tok + t > self.overlap:
                        break
                    overlap_buf.insert(0, p)
                    overlap_tok += t
                current_paras  = overlap_buf
                current_tokens = overlap_tok

            current_paras.append(para)
            current_tokens += para_tokens

        if current_paras:
            chunks.append({"text": "\n\n".join(current_paras), "metadata": metadata})

        return chunks


# ── Hash-based embedder ───────────────────────────────────────

class _HashEmbedder:
    """Deterministic 768-dimensional hash embeddings.

    Each word is hashed to a dimension index; the value at that index
    is incremented by a position-decayed weight.  The resulting vector
    is L2-normalised.

    This approach is fast, free, and offline.  Cosine similarity finds
    topically related chunks reliably for financial Q&A.

    Trade-off: Synonym matching and semantic reasoning are weaker than
    learned embeddings.  Replace with ``voyage-finance-2`` or
    ``text-embedding-3-small`` for production-grade recall.

    Class Attributes:
        DIM: Embedding dimensionality (768 — same as BERT-base).
    """

    DIM: int = 768

    def embed_one(self, text: str) -> np.ndarray:
        """Embed a single text string.

        Args:
            text: Input text (will be lowercased and split on whitespace).

        Returns:
            A float32 numpy array of shape ``(DIM,)``, L2-normalised.
        """
        vec = np.zeros(self.DIM, dtype=np.float32)
        words = text.lower().split()
        for i, word in enumerate(words[:512]):
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.DIM  # noqa: S324
            vec[idx] += 1.0 / (i + 1)  # position-weighted

        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts.

        Args:
            texts: Input strings.

        Returns:
            A float32 numpy array of shape ``(len(texts), DIM)``.
        """
        return np.stack([self.embed_one(t) for t in texts])


# ── RAG Pipeline ──────────────────────────────────────────────

class RAGPipeline:
    """End-to-end RAG pipeline: ingest → embed → index → retrieve.

    The FAISS index and chunk store are persisted to disk between Streamlit
    reruns so that uploaded documents survive page navigation.

    The pipeline degrades gracefully when FAISS is unavailable: retrieval
    falls back to TF-style keyword matching.

    Args:
        index_path: Override the default FAISS persistence directory.
                    Defaults to ``settings.faiss_index_path``.
    """

    _INDEX_FILE  = "index.faiss"
    _CHUNKS_FILE = "chunks.pkl"

    def __init__(self, index_path: str | None = None) -> None:
        self._root     = Path(index_path or settings.faiss_index_path)
        self._chunker  = _ParagraphChunker(
            chunk_size=settings.chunk_size,
            overlap   =settings.chunk_overlap,
        )
        self._embedder = _HashEmbedder()
        self._index: Any = None        # faiss.IndexFlatIP | None
        self._chunks: list[dict[str, Any]] = []
        self._load_persisted_index()

    # ── Persistence ───────────────────────────────────────────

    def _load_persisted_index(self) -> None:
        """Load a previously persisted FAISS index from disk, if present."""
        if not _FAISS_AVAILABLE:
            return

        idx_path    = self._root / self._INDEX_FILE
        chunks_path = self._root / self._CHUNKS_FILE

        if not (idx_path.exists() and chunks_path.exists()):
            return

        try:
            self._index = _faiss_lib.read_index(str(idx_path))
            with open(chunks_path, "rb") as fh:
                self._chunks = pickle.load(fh)  # noqa: S301
            log.info("faiss_index_loaded path=%s n_chunks=%d", self._root, len(self._chunks))
        except Exception as exc:
            log.warning("faiss_load_failed error=%s — starting fresh", exc)
            self._index  = None
            self._chunks = []

    def _persist_index(self) -> None:
        """Write the current FAISS index and chunk store to disk."""
        if not _FAISS_AVAILABLE or self._index is None:
            return
        self._root.mkdir(parents=True, exist_ok=True)
        _faiss_lib.write_index(self._index, str(self._root / self._INDEX_FILE))
        with open(self._root / self._CHUNKS_FILE, "wb") as fh:
            pickle.dump(self._chunks, fh)
        log.debug("faiss_index_persisted path=%s", self._root)

    # ── Index building ────────────────────────────────────────

    def _add_chunks_to_index(self, new_chunks: list[dict[str, Any]]) -> None:
        """Embed *new_chunks* and add them to the FAISS index.

        Args:
            new_chunks: Chunk dicts from :class:`_ParagraphChunker`.

        Raises:
            RAGError: If FAISS operations fail unexpectedly.
        """
        if not _FAISS_AVAILABLE:
            self._chunks.extend(new_chunks)
            return

        texts = [c["text"] for c in new_chunks]
        vecs  = self._embedder.embed_batch(texts).astype(np.float32)
        _faiss_lib.normalize_L2(vecs)

        if self._index is None:
            dim = vecs.shape[1]
            # IndexFlatIP + pre-normalised vectors == cosine similarity
            self._index = _faiss_lib.IndexFlatIP(dim)

        try:
            self._index.add(vecs)
        except Exception as exc:
            raise RAGError(f"FAISS add failed: {exc}") from exc

        self._chunks.extend(new_chunks)

    # ── Public API ────────────────────────────────────────────

    def ingest(self, file_path: str | Path) -> int:
        """Extract, chunk, and index a PDF document.

        Args:
            file_path: Path to a ``.pdf`` file on disk.

        Returns:
            The number of chunks added to the index.

        Raises:
            DocumentLoadError:  If the file does not exist or cannot be opened.
            DocumentParseError: If pypdf extracts zero text (image-only PDF).
            RAGError:           On FAISS indexing failures.
        """
        path = Path(file_path)

        if not path.exists():
            raise DocumentLoadError(str(path), "File not found")
        if path.suffix.lower() != ".pdf":
            raise DocumentLoadError(str(path), f"Unsupported format '{path.suffix}' — only PDF")

        log.info("ingest_start source=%s", path.name)

        # ── Extract text ──────────────────────────────────────
        try:
            reader = pypdf.PdfReader(str(path))
            pages: list[tuple[int, str]] = []
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append((i, text))
        except pypdf.errors.PdfReadError as exc:
            raise DocumentLoadError(str(path), f"Corrupt or encrypted PDF: {exc}") from exc
        except Exception as exc:
            raise DocumentLoadError(str(path), str(exc)) from exc

        if not pages:
            raise DocumentParseError(str(path), len(reader.pages))

        # ── Chunk ─────────────────────────────────────────────
        chunks: list[dict[str, Any]] = []
        for page_num, text in pages:
            meta = {"source": path.name, "page": page_num}
            chunks.extend(self._chunker.split(text, meta))

        if not chunks:
            raise DocumentParseError(str(path), len(pages))

        log.info("ingest_chunked source=%s n_chunks=%d", path.name, len(chunks))

        # ── Index ─────────────────────────────────────────────
        self._add_chunks_to_index(chunks)
        self._persist_index()

        log.info("ingest_done source=%s total_chunks=%d", path.name, len(self._chunks))
        return len(chunks)

    def retrieve(self, query: str, k: int | None = None) -> str:
        """Search the index and return concatenated context chunks.

        Args:
            query: Natural-language question from the user.
            k:     Number of top chunks to retrieve.
                   Defaults to ``settings.top_k_results``.

        Returns:
            A formatted string with chunk excerpts, suitable for injection
            into a Claude prompt as RAG context.

        Raises:
            IndexNotFoundError: If no documents have been ingested yet.
        """
        if not self._chunks:
            raise IndexNotFoundError()

        k = k or settings.top_k_results
        log.info("retrieve query=%r k=%d", query[:80], k)

        # ── FAISS similarity search ───────────────────────────
        if _FAISS_AVAILABLE and self._index is not None:
            q_vec = self._embedder.embed_one(query).reshape(1, -1).astype(np.float32)
            _faiss_lib.normalize_L2(q_vec)
            n_results = min(k, len(self._chunks))
            _, indices = self._index.search(q_vec, n_results)
            results = [
                self._chunks[i]
                for i in indices[0]
                if 0 <= i < len(self._chunks)
            ]
        else:
            # ── Keyword fallback ─────────────────────────────
            query_tokens = set(query.lower().split())
            scored = sorted(
                self._chunks,
                key=lambda c: len(query_tokens & set(c["text"].lower().split())),
                reverse=True,
            )
            results = scored[:k]

        if not results:
            return "No relevant context found in the indexed documents."

        parts = [
            f"[Excerpt {i} — {c['metadata'].get('source', '?')}, "
            f"p.{c['metadata'].get('page', '?')}]\n{c['text']}"
            for i, c in enumerate(results, start=1)
        ]
        return "\n\n---\n\n".join(parts)

    def list_documents(self) -> list[str]:
        """Return sorted unique source filenames in the index.

        Returns:
            A list of filenames (not full paths) currently indexed.
        """
        return sorted({
            c.get("metadata", {}).get("source", "")
            for c in self._chunks
            if c.get("metadata", {}).get("source")
        })

    def clear(self) -> None:
        """Wipe the in-memory index and delete persisted files.

        After calling this, :meth:`retrieve` will raise
        :class:`~core.exceptions.IndexNotFoundError` until new documents
        are ingested.
        """
        self._index  = None
        self._chunks = []

        import shutil
        if self._root.exists():
            shutil.rmtree(self._root, ignore_errors=True)

        log.info("rag_index_cleared")
