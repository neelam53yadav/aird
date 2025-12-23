"""
Chunking utilities for AIRD preprocessing.

Ports sentence and character-based chunking from AIRD.
"""

import regex as re
from typing import List

# Sentence splitting regex
SENT_SPLIT_RE = re.compile(r"(?<!\b[A-Z])[.!?。۔؟]+(?=\s+[A-Z0-9\"'])")


def tokens_estimate(s: str) -> int:
    """Lightweight token count approximation."""
    return max(len(s) // 4, len(s.split()))


def char_chunk(text: str, max_tokens: int, overlap_chars: int) -> List[str]:
    """Character-based chunking with overlap."""
    out, start, max_chars = [], 0, max_tokens * 4
    L = len(text)
    while start < L:
        end = min(L, start + max_chars)
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        if end >= L:
            break
        start = max(end - overlap_chars, start + 1)
    return out


def sentence_chunk(body: str, max_tokens: int, overlap_sents: int, hard_overlap_chars: int) -> List[str]:
    """Sentence-based chunking with overlap, falling back to char chunking for long sentences."""
    sents = re.split(SENT_SPLIT_RE, body)
    sents = [s.strip() for s in sents if s and s.strip()]
    if not sents:
        return char_chunk(body, max_tokens, hard_overlap_chars)

    chunks, buf = [], []
    for s in sents:
        cand = " ".join(buf + [s])
        if tokens_estimate(cand) <= max_tokens:
            buf.append(s)
        else:
            if buf:
                chunks.append(" ".join(buf))
            buf = buf[-overlap_sents:] if overlap_sents > 0 else []
            buf.append(s)
    if buf:
        chunks.append(" ".join(buf))

    out: List[str] = []
    for c in chunks:
        if tokens_estimate(c) > max_tokens:
            out.extend(char_chunk(c, max_tokens, hard_overlap_chars))
        else:
            out.append(c)
    return out




