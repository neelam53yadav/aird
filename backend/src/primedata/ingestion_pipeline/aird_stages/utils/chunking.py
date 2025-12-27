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
    """Sentence-based chunking with overlap, falling back to char chunking for long sentences.
    
    This preserves semantic boundaries better than character-based chunking by respecting
    sentence boundaries and maintaining context within chunks.
    """
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
            # Keep last N sentences for overlap (preserve context)
            buf = buf[-overlap_sents:] if overlap_sents > 0 else []
            buf.append(s)
    if buf:
        chunks.append(" ".join(buf))

    out: List[str] = []
    for c in chunks:
        if tokens_estimate(c) > max_tokens:
            # If chunk is still too large, split it further but preserve as much context as possible
            out.extend(char_chunk(c, max_tokens, hard_overlap_chars))
        else:
            out.append(c)
    return out


def paragraph_chunk(body: str, max_tokens: int, overlap_paras: int, hard_overlap_chars: int) -> List[str]:
    """Paragraph-based chunking with overlap for better semantic preservation.
    
    Splits on double newlines (paragraph boundaries) to preserve semantic units.
    Falls back to sentence chunking if paragraphs are too large, ensuring we never
    cut mid-sentence.
    """
    # Split on paragraph boundaries (double newlines or multiple whitespace)
    paras = re.split(r'\n\s*\n+', body)
    paras = [p.strip() for p in paras if p and p.strip()]
    
    if not paras:
        # Fallback to sentence chunking if no paragraphs found
        return sentence_chunk(body, max_tokens, max(1, overlap_paras * 2), hard_overlap_chars)
    
    chunks, buf = [], []
    for para in paras:
        cand = "\n\n".join(buf + [para]) if buf else para
        para_tokens = tokens_estimate(para)
        cand_tokens = tokens_estimate(cand)
        
        # If single paragraph exceeds max_tokens, use sentence chunking on it
        if para_tokens > max_tokens:
            # Flush buffer first if it exists
            if buf:
                chunks.append("\n\n".join(buf))
                buf = []
            # Use sentence chunking on this large paragraph to preserve sentence boundaries
            para_chunks = sentence_chunk(para, max_tokens, max(1, overlap_paras * 2), hard_overlap_chars)
            chunks.extend(para_chunks)
        elif cand_tokens <= max_tokens:
            # Can add to buffer
            buf.append(para)
        else:
            # Buffer + new para exceeds max, flush buffer
            if buf:
                chunks.append("\n\n".join(buf))
            # Keep last N paragraphs for overlap
            buf = buf[-overlap_paras:] if overlap_paras > 0 else []
            buf.append(para)
    
    if buf:
        chunks.append("\n\n".join(buf))
    
    # Final pass: ensure no chunk exceeds max_tokens (shouldn't happen, but safety check)
    out: List[str] = []
    for c in chunks:
        if tokens_estimate(c) > max_tokens:
            # Use sentence chunking for oversized chunks to preserve sentence boundaries
            out.extend(sentence_chunk(c, max_tokens, max(1, overlap_paras * 2), hard_overlap_chars))
        else:
            out.append(c)
    return out




