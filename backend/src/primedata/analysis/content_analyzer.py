"""
Content analysis module for intelligent chunking configuration.

This module analyzes content to automatically determine optimal chunking strategies
based on content type, structure, and complexity.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Content type enumeration."""

    LEGAL = "legal"
    CODE = "code"
    DOCUMENTATION = "documentation"
    CONVERSATION = "conversation"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    GENERAL = "general"


class ChunkingStrategy(str, Enum):
    """Chunking strategy enumeration."""

    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    SENTENCE_BOUNDARY = "sentence_boundary"
    PARAGRAPH_BOUNDARY = "paragraph_boundary"


@dataclass
class ChunkingConfig:
    """Chunking configuration data class."""

    chunk_size: int
    chunk_overlap: int
    min_chunk_size: int
    max_chunk_size: int
    strategy: ChunkingStrategy
    content_type: ContentType
    confidence: float  # 0.0 to 1.0, how confident we are in this configuration
    reasoning: str  # Human-readable explanation of why these settings were chosen


class ContentAnalyzer:
    """Analyzes content to determine optimal chunking configuration."""

    def __init__(self):
        # Content type detection patterns
        self.content_patterns = {
            ContentType.LEGAL: [
                r"\b(whereas|hereby|herein|hereinafter|pursuant to|in accordance with)\b",
                r"\b(agreement|contract|terms|conditions|clause|section)\b",
                r"\b(party|parties|plaintiff|defendant|court|legal)\b",
            ],
            ContentType.CODE: [
                r"^\s*(def|class|function|import|from|if|for|while|try|except)\s+",
                r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*[=\(]",  # Variable assignments
                r"^\s*#.*$",  # Comments
                r"^\s*//.*$",  # Comments
                r"^\s*/\*.*\*/$",  # Block comments
            ],
            ContentType.DOCUMENTATION: [
                r"^#{1,6}\s+",  # Markdown headers
                r"^\s*\*\s+",  # Bullet points
                r"^\s*\d+\.\s+",  # Numbered lists
                r"```",  # Code blocks
                r"\[.*\]\(.*\)",  # Links
            ],
            ContentType.CONVERSATION: [
                r"^\s*\d{1,2}:\d{2}\s+[AP]M\s+",  # Timestamps
                r"^\s*\[.*\]\s+",  # Speaker names
                r"^\s*<.*>\s+",  # Chat format
                r"^\s*\w+:\s+",  # Simple speaker format
            ],
            ContentType.ACADEMIC: [
                r"\b(abstract|introduction|methodology|results|conclusion|references)\b",
                r"\b(study|research|analysis|hypothesis|findings|implications)\b",
                r"^\s*\d+\.\d+\s+",  # Section numbers
                r"\[.*\]\s*\(.*\)",  # Citations
            ],
            ContentType.TECHNICAL: [
                r"\b(API|endpoint|request|response|authentication|authorization)\b",
                r"\b(database|query|table|index|schema|migration)\b",
                r"\b(algorithm|optimization|performance|scalability|architecture)\b",
                r"^\s*```\w*$",  # Code blocks
            ],
        }

        # Optimal configurations for each content type
        self.optimal_configs = {
            ContentType.LEGAL: {
                "chunk_size": 2000,
                "chunk_overlap": 400,
                "min_chunk_size": 200,
                "max_chunk_size": 3000,
                "strategy": ChunkingStrategy.SEMANTIC,
                "reasoning": "Legal documents require larger chunks to preserve context and legal meaning",
            },
            ContentType.CODE: {
                "chunk_size": 1500,
                "chunk_overlap": 300,
                "min_chunk_size": 100,
                "max_chunk_size": 2500,
                "strategy": ChunkingStrategy.RECURSIVE,
                "reasoning": "Code benefits from recursive chunking to preserve function/class boundaries",
            },
            ContentType.DOCUMENTATION: {
                "chunk_size": 1200,
                "chunk_overlap": 200,
                "min_chunk_size": 100,
                "max_chunk_size": 2000,
                "strategy": ChunkingStrategy.PARAGRAPH_BOUNDARY,
                "reasoning": "Documentation works well with paragraph-based chunking for better readability",
            },
            ContentType.CONVERSATION: {
                "chunk_size": 800,
                "chunk_overlap": 100,
                "min_chunk_size": 50,
                "max_chunk_size": 1500,
                "strategy": ChunkingStrategy.SENTENCE_BOUNDARY,
                "reasoning": "Conversations benefit from smaller chunks at sentence boundaries",
            },
            ContentType.ACADEMIC: {
                "chunk_size": 1800,
                "chunk_overlap": 350,
                "min_chunk_size": 150,
                "max_chunk_size": 2500,
                "strategy": ChunkingStrategy.SEMANTIC,
                "reasoning": "Academic papers need larger chunks to preserve argument structure",
            },
            ContentType.TECHNICAL: {
                "chunk_size": 1400,
                "chunk_overlap": 250,
                "min_chunk_size": 100,
                "max_chunk_size": 2200,
                "strategy": ChunkingStrategy.SEMANTIC,
                "reasoning": "Technical content benefits from semantic chunking to preserve concept boundaries",
            },
            ContentType.GENERAL: {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "min_chunk_size": 100,
                "max_chunk_size": 2000,
                "strategy": ChunkingStrategy.FIXED_SIZE,
                "reasoning": "General content uses balanced fixed-size chunking for optimal retrieval",
            },
        }

    def analyze_content(self, content: str, filename: Optional[str] = None) -> ChunkingConfig:
        """
        Analyze content and return optimal chunking configuration.

        Args:
            content: The text content to analyze
            filename: Optional filename for additional context

        Returns:
            ChunkingConfig with optimal settings
        """
        logger.info(f"Analyzing content: {len(content)} characters")

        # Detect content type
        content_type, confidence = self._detect_content_type(content, filename)

        # Get base configuration for detected type
        base_config = self.optimal_configs[content_type]

        # Adjust configuration based on content characteristics
        adjusted_config = self._adjust_for_content_characteristics(content, base_config, content_type)

        # Create final configuration
        config = ChunkingConfig(
            chunk_size=adjusted_config["chunk_size"],
            chunk_overlap=adjusted_config["chunk_overlap"],
            min_chunk_size=adjusted_config["min_chunk_size"],
            max_chunk_size=adjusted_config["max_chunk_size"],
            strategy=adjusted_config["strategy"],
            content_type=content_type,
            confidence=confidence,
            reasoning=adjusted_config["reasoning"],
        )

        logger.info(f"Generated chunking config: {content_type} with {confidence:.2f} confidence")
        return config

    def _detect_content_type(self, content: str, filename: Optional[str] = None) -> Tuple[ContentType, float]:
        """Detect content type based on patterns and filename."""
        scores = {}

        # Check filename extension if available
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs"]:
                scores[ContentType.CODE] = 0.8
            elif ext in [".md", ".rst", ".txt"]:
                scores[ContentType.DOCUMENTATION] = 0.6
            elif ext in [".pdf", ".doc", ".docx"]:
                scores[ContentType.GENERAL] = 0.5

        # Analyze content patterns
        for content_type, patterns in self.content_patterns.items():
            score = 0.0
            matches = 0

            for pattern in patterns:
                pattern_matches = len(re.findall(pattern, content, re.IGNORECASE | re.MULTILINE))
                if pattern_matches > 0:
                    matches += 1
                    # Normalize score based on content length
                    normalized_score = min(pattern_matches / (len(content) / 1000), 1.0)
                    score += normalized_score

            if matches > 0:
                scores[content_type] = score / len(patterns)

        # If no specific type detected, use general
        if not scores:
            return ContentType.GENERAL, 0.3

        # Return the type with highest score
        best_type = max(scores.items(), key=lambda x: x[1])
        return best_type[0], min(best_type[1], 1.0)

    def _adjust_for_content_characteristics(self, content: str, base_config: Dict, content_type: ContentType) -> Dict:
        """Adjust configuration based on specific content characteristics."""
        config = base_config.copy()

        # Analyze content complexity
        avg_sentence_length = self._calculate_avg_sentence_length(content)
        paragraph_count = len([p for p in content.split("\n\n") if p.strip()])
        word_count = len(content.split())

        # Adjust chunk size based on sentence length
        if avg_sentence_length > 30:  # Long sentences
            config["chunk_size"] = int(config["chunk_size"] * 1.2)
            config["chunk_overlap"] = int(config["chunk_overlap"] * 1.2)
            config["reasoning"] += " (adjusted for long sentences)"
        elif avg_sentence_length < 15:  # Short sentences
            config["chunk_size"] = int(config["chunk_size"] * 0.8)
            config["chunk_overlap"] = int(config["chunk_overlap"] * 0.8)
            config["reasoning"] += " (adjusted for short sentences)"

        # Adjust for very short content
        if word_count < 100:
            config["chunk_size"] = min(config["chunk_size"], word_count * 4)
            config["chunk_overlap"] = min(config["chunk_overlap"], config["chunk_size"] // 4)
            config["reasoning"] += " (adjusted for short content)"

        # Adjust for very long content
        elif word_count > 10000:
            config["chunk_size"] = int(config["chunk_size"] * 1.1)
            config["chunk_overlap"] = int(config["chunk_overlap"] * 1.1)
            config["reasoning"] += " (adjusted for long content)"

        # Ensure min/max constraints
        config["chunk_size"] = max(config["min_chunk_size"], min(config["chunk_size"], config["max_chunk_size"]))
        config["chunk_overlap"] = min(config["chunk_overlap"], config["chunk_size"] - 1)

        return config

    def _calculate_avg_sentence_length(self, content: str) -> float:
        """Calculate average sentence length in words."""
        sentences = re.split(r"[.!?]+", content)
        if not sentences:
            return 0.0

        total_words = sum(len(sentence.split()) for sentence in sentences if sentence.strip())
        return total_words / len([s for s in sentences if s.strip()])

    def preview_chunking(self, content: str, config: ChunkingConfig) -> Dict[str, Any]:
        """
        Preview how content would be chunked with given configuration.

        Args:
            content: Content to preview
            config: Chunking configuration to use

        Returns:
            Dictionary with preview information
        """
        chunks = self._simulate_chunking(content, config)

        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(len(chunk["text"]) for chunk in chunks) / len(chunks) if chunks else 0,
            "min_chunk_size": min(len(chunk["text"]) for chunk in chunks) if chunks else 0,
            "max_chunk_size": max(len(chunk["text"]) for chunk in chunks) if chunks else 0,
            "chunks": chunks[:5],  # First 5 chunks as preview
            "estimated_retrieval_quality": self._estimate_retrieval_quality(chunks, config),
        }

    def _simulate_chunking(self, content: str, config: ChunkingConfig) -> List[Dict[str, Any]]:
        """Simulate chunking process to preview results."""
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(content):
            end = min(start + config.chunk_size, len(content))
            chunk_text = content[start:end]

            if not chunk_text.strip():
                break

            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "text": chunk_text.strip(),
                    "start_char": start,
                    "end_char": end,
                    "size": len(chunk_text.strip()),
                }
            )

            chunk_index += 1
            step_size = max(1, config.chunk_size - config.chunk_overlap)
            start += step_size

            if start >= len(content):
                break

        return chunks

    def _estimate_retrieval_quality(self, chunks: List[Dict], config: ChunkingConfig) -> str:
        """Estimate retrieval quality based on chunk characteristics."""
        if not chunks:
            return "unknown"

        avg_size = sum(chunk["size"] for chunk in chunks) / len(chunks)
        size_variance = sum((chunk["size"] - avg_size) ** 2 for chunk in chunks) / len(chunks)

        # Good quality indicators
        if config.min_chunk_size <= avg_size <= config.max_chunk_size and size_variance < (avg_size * 0.3) ** 2:
            return "high"
        elif config.min_chunk_size * 0.8 <= avg_size <= config.max_chunk_size * 1.2:
            return "medium"
        else:
            return "low"


# Global instance
content_analyzer = ContentAnalyzer()
