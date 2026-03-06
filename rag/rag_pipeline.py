"""
rag/rag_pipeline.py
RAG Pipeline from the paper:
  Phase 1 — Offline: PDF → chunks → embeddings → FAISS index
  Phase 2 — Online:  query + learner profile → augmented query → top-k chunks
"""

import os
import pickle
import fitz                        # PyMuPDF
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE       = 500     # tokens (approximate by words)
CHUNK_OVERLAP    = 50
TOP_K            = 5
INDEX_DIR        = "faiss_indexes"

# Load embedding model once
_embed_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


# ── PHASE 1: OFFLINE INDEXING ─────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append({"text": text, "page": page_num + 1})
    doc.close()
    return pages


def chunk_text(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Sliding window chunking with overlap."""
    chunks = []
    for page_data in pages:
        words = page_data["text"].split()
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            if chunk_text.strip():
                chunks.append({
                    "text":    chunk_text,
                    "page":    page_data["page"],
                    "start_w": start,
                    "end_w":   end
                })
            start += chunk_size - overlap
    return chunks


def build_faiss_index(subject, pdf_path):
    """
    Full pipeline: PDF → chunks → embeddings → FAISS flat L2 index.
    Saves index + chunks to disk.
    """
    os.makedirs(INDEX_DIR, exist_ok=True)
    index_path  = os.path.join(INDEX_DIR, f"{subject}_index.faiss")
    chunks_path = os.path.join(INDEX_DIR, f"{subject}_chunks.pkl")

    print(f"[RAG] Extracting text from {pdf_path} ...")
    pages  = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(pages)
    print(f"[RAG] Created {len(chunks)} chunks.")

    print("[RAG] Generating embeddings ...")
    model  = get_embed_model()
    texts  = [c["text"] for c in chunks]
    embeds = model.encode(texts, show_progress_bar=True, batch_size=32)
    embeds = np.array(embeds, dtype="float32")

    print("[RAG] Building FAISS index ...")
    dim   = embeds.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeds)

    # Persist
    faiss.write_index(index, index_path)
    with open(chunks_path, "wb") as f:
        pickle.dump(chunks, f)

    print(f"[RAG] Index saved → {index_path} ({len(chunks)} chunks)")
    return len(chunks)


def load_faiss_index(subject):
    """Load persisted FAISS index and chunks from disk."""
    index_path  = os.path.join(INDEX_DIR, f"{subject}_index.faiss")
    chunks_path = os.path.join(INDEX_DIR, f"{subject}_chunks.pkl")

    if not os.path.exists(index_path):
        return None, None

    index = faiss.read_index(index_path)
    with open(chunks_path, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks


def index_exists(subject):
    return os.path.exists(os.path.join(INDEX_DIR, f"{subject}_index.faiss"))


# ── PHASE 2: ONLINE RETRIEVAL ─────────────────────────────────────────────────

def build_retrieval_query(user_query, weak_topics, mastery_level):
    """
    Learner-conditioned query augmentation from the paper.
    Appends weak topics and mastery level to steer retrieval
    toward content matching the learner's knowledge gap.
    """
    parts = [user_query]
    if weak_topics:
        parts.append(f"Focus on: {', '.join(weak_topics)}")
    if mastery_level:
        parts.append(f"Learner level: {mastery_level}")
    return " | ".join(parts)


def retrieve_chunks(subject, user_query, weak_topics=None, mastery_level=None, k=TOP_K):
    """
    Retrieve top-k curriculum chunks for a learner-conditioned query.
    Returns list of chunk dicts with text and metadata.
    """
    index, chunks = load_faiss_index(subject)
    if index is None:
        return []

    model         = get_embed_model()
    aug_query     = build_retrieval_query(user_query, weak_topics or [], mastery_level or "")
    query_embed   = model.encode([aug_query], show_progress_bar=False)
    query_embed   = np.array(query_embed, dtype="float32")

    distances, indices = index.search(query_embed, k)
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(chunks):
            chunk = chunks[idx].copy()
            chunk["score"] = float(dist)
            results.append(chunk)
    return results


def format_context(chunks):
    """Format retrieved chunks into a single context string for the LLM prompt."""
    if not chunks:
        return "No curriculum context available."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Chunk {i} | Page {chunk.get('page', '?')}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


# ── TOPIC EXTRACTION FROM PDF ─────────────────────────────────────────────────

def extract_topics_from_pdf(pdf_path):
    """
    Auto-detect topics/chapters from PDF headings.
    Looks for: large bold text, numbered headings, chapter/unit/section markers.
    Returns a list of topic strings.
    """
    doc = fitz.open(pdf_path)
    topics = []
    seen = set()

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text  = span.get("text", "").strip()
                    size  = span.get("size", 0)
                    flags = span.get("flags", 0)
                    is_bold = bool(flags & 2**4)

                    if not text or len(text) < 3 or len(text) > 120:
                        continue

                    # Detect headings: large font OR bold OR numbered patterns
                    is_numbered = bool(
                        __import__('re').match(
                            r'^(\d+[\.\)]\s|Chapter\s|Unit\s|Section\s|Topic\s|Module\s)',
                            text, __import__('re').IGNORECASE
                        )
                    )

                    if (size >= 13 or is_bold or is_numbered):
                        # Clean up common artifacts
                        clean = text.strip("•·-–—:").strip()
                        if clean and clean.lower() not in seen and len(clean) > 3:
                            # Skip page numbers and very short labels
                            if not clean.isdigit() and not clean.lower() in [
                                'page', 'contents', 'index', 'table of contents',
                                'references', 'bibliography', 'appendix'
                            ]:
                                topics.append(clean)
                                seen.add(clean.lower())

    doc.close()
    # Deduplicate while preserving order
    return topics[:60]  # cap at 60 topics