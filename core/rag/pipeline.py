"""
FinSight — RAG Pipeline (LangChain-free)
==========================================
Retrieval-Augmented Generation using only:
  - pypdf       → text extraction
  - faiss-cpu   → vector similarity search
  - tiktoken    → token-aware chunking
  - Hash embeddings → deterministic 768-dim vectors (no API key)

Design decisions:
- No LangChain — avoids pydantic-v1 / Python 3.14 incompatibility.
- Paragraph-aware chunking — honours financial document structure.
- FAISS index persisted to /tmp so documents survive page navigation.
- Graceful fallback to keyword search when faiss-cpu is unavailable.

Usage::

    from core.rag.pipeline import RAGPipeline
    pipe = RAGPipeline()
    n    = pipe.ingest("AAPL_10K_2024.pdf")
    ctx  = pipe.retrieve("What are Apple's main revenue segments?")
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

# ── Optional FAISS ────────────────────────────────────────────
try:
    import faiss as _faiss
    _FAISS = True
except ImportError:
    _faiss = None   # type: ignore[assignment]
    _FAISS = False
    log.warning("faiss-cpu not installed — falling back to keyword retrieval")

# ── Optional tiktoken ─────────────────────────────────────────
try:
    import tiktoken as _tiktoken
    _ENC = _tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None


def _token_count(text: str) -> int:
    """Estimate token count for *text*.

    Args:
        text: Input string.

    Returns:
        Token count via tiktoken, or word-count × 1.3 as fallback.
    """
    if _ENC:
        return len(_ENC.encode(text))
    return int(len(text.split()) * 1.3)


# ── Chunker ───────────────────────────────────────────────────

class _ParagraphChunker:
    """Split document text into token-bounded, paragraph-aware chunks.

    Financial documents have natural paragraph breaks that should be
    honoured to keep related information together within a chunk.

    Args:
        chunk_size: Maximum tokens per chunk.
        overlap:    Tokens of overlap between consecutive chunks to
                    preserve cross-boundary context.
    """

    def __init__(self, chunk_size: int = 800, overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.overlap    = overlap

    def split(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Split *text* into overlapping chunks.

        Args:
            text:     Raw page/section text.
            metadata: Attached to every chunk (``{"source": ..., "page": ...}``).

        Returns:
            List of ``{"text": str, "metadata": dict}`` dicts.
        """
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        if not paragraphs:
            return []

        chunks:   list[dict[str, Any]] = []
        current:  list[str]            = []
        cur_tok = 0

        for para in paragraphs:
            pt = _token_count(para)
            if current and cur_tok + pt > self.chunk_size:
                chunks.append({"text": "\n\n".join(current), "metadata": metadata})
                # Retain overlap from tail of current buffer
                buf, btok = [], 0
                for p in reversed(current):
                    t = _token_count(p)
                    if btok + t > self.overlap:
                        break
                    buf.insert(0, p)
                    btok += t
                current, cur_tok = buf, btok

            current.append(para)
            cur_tok += pt

        if current:
            chunks.append({"text": "\n\n".join(current), "metadata": metadata})

        return chunks


# ── Embedder ──────────────────────────────────────────────────

class _HashEmbedder:
    """Deterministic 768-dim hash embeddings (no API key required).

    Each word is hashed to a dimension; the weight is position-decayed.
    Vectors are L2-normalised so cosine similarity == dot product.

    Trade-off: weaker synonym/semantic matching than learned embeddings.
    Replace with ``voyage-finance-2`` or ``text-embedding-3-small`` for
    production-grade recall.

    Class Attributes:
        DIM: Embedding dimensionality (768, same as BERT-base).
    """

    DIM: int = 768

    def embed_one(self, text: str) -> np.ndarray:
        """Embed a single string to a (DIM,) float32 vector.

        Args:
            text: Input text.

        Returns:
            L2-normalised float32 ndarray of shape ``(DIM,)``.
        """
        vec = np.zeros(self.DIM, dtype=np.float32)
        for i, word in enumerate(text.lower().split()[:512]):
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.DIM  # noqa: S324
            vec[idx] += 1.0 / (i + 1)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed a list of strings.

        Args:
            texts: Input strings.

        Returns:
            float32 ndarray of shape ``(len(texts), DIM)``.
        """
        return np.stack([self.embed_one(t) for t in texts])


# ── Pipeline ──────────────────────────────────────────────────

class RAGPipeline:
    """End-to-end RAG pipeline: PDF → chunks → embeddings → FAISS → retrieval.

    The FAISS index is persisted to ``settings.faiss_index_path`` so
    uploaded documents survive Streamlit page navigation without
    re-ingestion.

    Args:
        index_path: Override FAISS persistence directory.
    """

    _IDX_FILE    = "index.faiss"
    _CHUNKS_FILE = "chunks.pkl"

    def __init__(self, index_path: str | None = None) -> None:
        self._root     = Path(index_path or settings.faiss_index_path)
        self._chunker  = _ParagraphChunker(settings.chunk_size, settings.chunk_overlap)
        self._embedder = _HashEmbedder()
        self._index: Any               = None
        self._chunks: list[dict[str, Any]] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────

    def _load(self) -> None:
        """Load persisted FAISS index from disk if present."""
        if not _FAISS:
            return
        idx    = self._root / self._IDX_FILE
        chunks = self._root / self._CHUNKS_FILE
        if not (idx.exists() and chunks.exists()):
            return
        try:
            self._index = _faiss.read_index(str(idx))
            with open(chunks, "rb") as fh:
                self._chunks = pickle.load(fh)  # noqa: S301
            log.info("faiss_loaded path=%s n=%d", self._root, len(self._chunks))
        except Exception as exc:
            log.warning("faiss_load_failed err=%s — starting fresh", exc)
            self._index = None
            self._chunks = []

    def _save(self) -> None:
        """Persist current FAISS index to disk."""
        if not (_FAISS and self._index is not None):
            return
        self._root.mkdir(parents=True, exist_ok=True)
        _faiss.write_index(self._index, str(self._root / self._IDX_FILE))
        with open(self._root / self._CHUNKS_FILE, "wb") as fh:
            pickle.dump(self._chunks, fh)

    # ── Indexing ──────────────────────────────────────────────

    def _index_chunks(self, new_chunks: list[dict[str, Any]]) -> None:
        """Embed and add *new_chunks* to the FAISS index.

        Args:
            new_chunks: Chunks from :class:`_ParagraphChunker`.

        Raises:
            RAGError: If FAISS add operation fails.
        """
        if not _FAISS:
            self._chunks.extend(new_chunks)
            return

        vecs = self._embedder.embed_batch([c["text"] for c in new_chunks]).astype(np.float32)
        _faiss.normalize_L2(vecs)

        if self._index is None:
            self._index = _faiss.IndexFlatIP(vecs.shape[1])

        try:
            self._index.add(vecs)
        except Exception as exc:
            raise RAGError(f"FAISS add failed: {exc}") from exc

        self._chunks.extend(new_chunks)

    # ── Public API ────────────────────────────────────────────

    def ingest(self, file_path: str | Path) -> int:
        """Extract, chunk, and index a PDF document.

        Args:
            file_path: Path to a ``.pdf`` file.

        Returns:
            Number of chunks added to the index.

        Raises:
            DocumentLoadError:  File not found, unreadable, or wrong format.
            DocumentParseError: pypdf extracted zero text (image-only PDF).
            RAGError:           FAISS indexing failure.
        """
        path = Path(file_path)
        if not path.exists():
            raise DocumentLoadError(str(path), "File not found")
        if path.suffix.lower() != ".pdf":
            raise DocumentLoadError(str(path), f"Unsupported format '{path.suffix}'")

        log.info("ingest_start source=%s", path.name)

        try:
            reader = pypdf.PdfReader(str(path))
            pages: list[tuple[int, str]] = [
                (i + 1, page.extract_text() or "")
                for i, page in enumerate(reader.pages)
                if (page.extract_text() or "").strip()
            ]
        except pypdf.errors.PdfReadError as exc:
            raise DocumentLoadError(str(path), f"Corrupt or encrypted PDF: {exc}") from exc
        except Exception as exc:
            raise DocumentLoadError(str(path), str(exc)) from exc

        if not pages:
            raise DocumentParseError(str(path), len(reader.pages))

        chunks: list[dict[str, Any]] = []
        for page_num, text in pages:
            chunks.extend(self._chunker.split(text, {"source": path.name, "page": page_num}))

        if not chunks:
            raise DocumentParseError(str(path), len(pages))

        self._index_chunks(chunks)
        self._save()
        log.info("ingest_done source=%s n_chunks=%d total=%d", path.name, len(chunks), len(self._chunks))
        return len(chunks)

    def retrieve(self, query: str, k: int | None = None) -> str:
        """Search the index and return concatenated context excerpts.

        Args:
            query: Natural-language question.
            k:     Chunks to retrieve.  Defaults to ``settings.top_k_results``.

        Returns:
            Formatted context string ready for Claude prompt injection.

        Raises:
            IndexNotFoundError: No documents have been ingested yet.
        """
        if not self._chunks:
            raise IndexNotFoundError()

        k = k or settings.top_k_results
        log.info("retrieve query=%r k=%d", query[:80], k)

        if _FAISS and self._index is not None:
            q = self._embedder.embed_one(query).reshape(1, -1).astype(np.float32)
            _faiss.normalize_L2(q)
            _, idxs = self._index.search(q, min(k, len(self._chunks)))
            results = [self._chunks[i] for i in idxs[0] if 0 <= i < len(self._chunks)]
        else:
            qtok = set(query.lower().split())
            results = sorted(
                self._chunks,
                key=lambda c: len(qtok & set(c["text"].lower().split())),
                reverse=True,
            )[:k]

        if not results:
            return "No relevant context found in the indexed documents."

        parts = [
            f"[Excerpt {i} — {c['metadata'].get('source','?')}, "
            f"p.{c['metadata'].get('page','?')}]\n{c['text']}"
            for i, c in enumerate(results, 1)
        ]
        return "\n\n---\n\n".join(parts)

    def list_documents(self) -> list[str]:
        """Return sorted unique source filenames in the index.

        Returns:
            List of filenames (no full paths).
        """
        return sorted({
            c["metadata"]["source"]
            for c in self._chunks
            if c.get("metadata", {}).get("source")
        })

    def clear(self) -> None:
        """Wipe in-memory index and delete persisted files."""
        self._index  = None
        self._chunks = []
        import shutil
        if self._root.exists():
            shutil.rmtree(self._root, ignore_errors=True)
        log.info("rag_cleared")
