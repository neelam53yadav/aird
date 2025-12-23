"""
Text processing utilities for AIRD preprocessing.

Ports text normalization, PII redaction, and section detection from AIRD.
"""

import regex as re
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger

# Regex patterns for PII detection
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\s\-\.)/]*)?(?:\(?\d{3}\)?[\s\-\./]*)?\d{3}[\s\-\./]*\d{4}")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Header detection patterns
TITLECASE_RE = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$")
ALLCAPS_RE = re.compile(r"^[A-Z0-9][A-Z0-9 &'\-]{6,}$")
NUMBERED_RE = re.compile(r"^(\d+)[\.\)]\s+(.+)$")

# Sentence splitting regex
SENT_SPLIT_RE = re.compile(r"(?<!\b[A-Z])[.!?。۔؟]+(?=\s+[A-Z0-9\"'])")


def _compile_flags(flag_str: Optional[str]) -> int:
    """Compile regex flags from string (e.g., 'MULTILINE|IGNORECASE')."""
    if not flag_str:
        return 0
    flags = 0
    for f in flag_str.split("|"):
        f = f.strip().upper()
        if f == "MULTILINE":
            flags |= re.MULTILINE
        if f == "IGNORECASE":
            flags |= re.IGNORECASE
    return flags


def normalize_wrapped_lines(text: str) -> str:
    """
    Fix common PDF line-wrap artifacts:
      - join hyphenated breaks: 'inter-\nnational' -> 'international'
      - join short soft breaks within paragraphs when previous line didn't end a sentence
      - collapse 3+ blank lines to 2
    """
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)  # de-hyphenate
    t = re.sub(r"(?m)(?<![.!?]['\")\]])\n(?=[a-zA-Z0-9])", " ", t)  # soft join
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def redact_pii(text: str) -> str:
    """Redact PII (emails, phones, SSNs) from text."""
    t = EMAIL_RE.sub("[redacted_email]", text)
    t = PHONE_RE.sub("[redacted_phone]", t)
    t = SSN_RE.sub("[SSN]", t)
    return t


def apply_normalizers(text: str, steps: Optional[List[Dict[str, Any]]]) -> str:
    """Apply regex-based normalization steps from playbook."""
    out = text
    for step in steps or []:
        pat = step.get("pattern")
        if not pat:
            logger.warning(f"Normalizer step missing 'pattern' field, skipping: {step}")
            continue
        
        # Handle YAML parsing issue: sometimes patterns are parsed as lists (e.g., [\u2018\u2019])
        # Convert list to string character class pattern
        if isinstance(pat, list):
            # Convert list of characters to regex character class string
            pat = "[" + "".join(str(c) for c in pat) + "]"
            logger.debug(f"Converted list pattern to string: {pat}")
        
        if not isinstance(pat, str):
            logger.warning(f"Normalizer pattern must be string or list, got {type(pat)}: {pat}, skipping")
            continue
        
        repl = step.get("replace", "")
        flag_val = step.get("flags")
        # Handle flags: can be string, None, or other types
        if isinstance(flag_val, str):
            flags = _compile_flags(flag_val)
        elif flag_val is None:
            flags = 0
        else:
            # If flags is not a string or None, log and use 0
            logger.warning(f"Unexpected flags type in normalizer (expected str or None, got {type(flag_val)}): {flag_val}, using 0")
            flags = 0
        try:
            out = re.sub(pat, repl, out, flags=flags)
        except (re.error, TypeError) as e:
            logger.warning(f"Bad regex pattern in normalizer: {pat}, error: {e}, flags type: {type(flags)}, flags value: {flags}")
            # ignore bad regex in config; continue
            pass
    return out


def split_pages_by_config(text: str, page_fences: Optional[List[Dict[str, Any]]]) -> List[Dict[str, int]]:
    """
    If a page fence pattern is defined, split text into {page, text} blocks.
    Otherwise produce a single page.
    """
    for fence in page_fences or []:
        flags = _compile_flags(fence.get("flags"))
        lines = text.splitlines()
        pages, curr, page = [], [], 1
        for line in lines:
            if re.match(fence.get("pattern", r"^$"), line, flags=flags):
                if curr:
                    pages.append({"page": page, "text": "\n".join(curr).strip()})
                    curr = []
                m = re.search(r"PAGE\s+(\d+)", line, flags=re.IGNORECASE)
                page = int(m.group(1)) if m else (pages[-1]["page"] + 1 if pages else 1)
                continue
            curr.append(line)
        if curr:
            pages.append({"page": page, "text": "\n".join(curr).strip()})
        if len(pages) > 1:
            return pages
    return [{"page": 1, "text": text.strip()}]


def detect_sections_configured(
    text: str,
    header_specs: Optional[List[Dict[str, Any]]],
    aliases: Optional[Dict[str, str]],
) -> List[Tuple[str, str, str]]:
    """
    Use header rules from playbook to split into sections.
    Returns tuples: (title_raw, canonical_section, body_text)
    """
    lines = text.splitlines()
    sections, buf, title_raw = [], [], "Introduction"
    aliases = aliases or {}

    def flush():
        nonlocal buf, title_raw
        if buf:
            canon = aliases.get(title_raw, _canon_from_title(title_raw))
            sections.append((title_raw, canon, "\n".join(buf).strip()))
            buf = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        is_header = False
        # explicit header rules first
        for spec in header_specs or []:
            pat = spec.get("pattern")
            flags = _compile_flags(spec.get("flags"))
            if pat and re.match(pat, line, flags=flags):
                flush()
                title_raw = line
                is_header = True
                break
        if is_header:
            continue
        # fallback heuristics: numbered, TitleCase (>=2 words), ALLCAPS long
        if NUMBERED_RE.match(line) or TITLECASE_RE.match(line) or (ALLCAPS_RE.match(line) and len(line.split()) >= 2):
            flush()
            title_raw = line
            continue
        buf.append(line)

    flush()
    if not sections:
        return [("Introduction", "introduction", text.strip())]
    return sections


def _canon_from_title(title: str) -> str:
    """Convert title to canonical section name."""
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    # a small alias map inline; playbook aliases still take precedence
    ALIASES = {
        "executive summary": "executive_summary",
        "table of contents": "table_of_contents",
        "conclusions": "conclusions",
        "conclusion": "conclusions",
        "abstract": "abstract",
        "introduction": "introduction",
        "background": "background",
    }
    if t in ALIASES:
        return ALIASES[t]
    return re.sub(r"[^a-z0-9]+", "_", t)[:40] or "section"



