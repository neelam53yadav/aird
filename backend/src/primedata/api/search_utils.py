"""
Search utility functions for improving RAG playground query relevance.
Includes query expansion and keyword boosting.
"""

import re
from typing import List


def expand_query_terms(query: str) -> List[str]:
    """
    Expand query with common abbreviations and synonyms to improve search relevance.
    Returns a list of query terms (original + expansions) for keyword matching.
    
    Args:
        query: Original search query
        
    Returns:
        List of query terms including original and expansions
    """
    query_lower = query.lower()
    terms = set()
    
    # Add original query
    terms.add(query_lower)
    
    # Common abbreviation expansions
    expansions = {
        r'\baws\b': ['amazon web services', 'amazon web service'],
        r'\bceo\b': ['chief executive officer', 'chief executive'],
        r'\bcto\b': ['chief technology officer', 'chief technical officer'],
        r'\bcfo\b': ['chief financial officer'],
        r'\bcio\b': ['chief information officer'],
        r'\bapi\b': ['application programming interface'],
        r'\bsdk\b': ['software development kit'],
        r'\bui\b': ['user interface'],
        r'\bux\b': ['user experience'],
        r'\bqa\b': ['quality assurance'],
        r'\bdevops\b': ['development operations'],
    }
    
    # Apply expansions
    expanded_query = query_lower
    for pattern, replacements in expansions.items():
        if re.search(pattern, query_lower):
            for replacement in replacements:
                expanded_query = re.sub(pattern, replacement, expanded_query)
                terms.add(replacement)
    
    # Extract important keywords (nouns, proper nouns, important terms)
    # Split by common separators and keep meaningful words
    words = re.findall(r'\b\w+\b', expanded_query)
    for word in words:
        if len(word) > 3:  # Skip very short words
            terms.add(word)
    
    return list(terms)


def calculate_keyword_boost(text: str, query_terms: List[str], original_query: str) -> float:
    """
    Calculate keyword boost score based on exact matches and term frequency.
    Returns a boost multiplier (0.0 to 0.15) to add to similarity score.
    
    Args:
        text: Document text to check
        query_terms: List of expanded query terms
        original_query: Original user query
        
    Returns:
        Boost value (0.0 to 0.15)
    """
    if not text or not query_terms:
        return 0.0
    
    text_lower = text.lower()
    original_query_lower = original_query.lower()
    
    boost = 0.0
    max_boost = 0.15  # Maximum boost of 15% to similarity score
    
    # 1. Exact phrase match (highest boost)
    if original_query_lower in text_lower:
        boost += 0.08
    
    # 2. All important terms present (medium boost)
    important_terms = [term for term in query_terms if len(term) > 4]  # Focus on longer terms
    if important_terms:
        matches = sum(1 for term in important_terms if term in text_lower)
        term_coverage = matches / len(important_terms) if important_terms else 0
        boost += 0.05 * term_coverage
    
    # 3. Exact keyword matches (case-insensitive)
    keyword_matches = 0
    for term in query_terms:
        # Count occurrences of the term as whole word
        pattern = r'\b' + re.escape(term) + r'\b'
        matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
        if matches > 0:
            keyword_matches += min(matches, 3)  # Cap at 3 matches per term
    
    if keyword_matches > 0:
        boost += min(0.02 * keyword_matches, 0.05)  # Up to 5% for keyword matches
    
    # 4. Entity/name matching (for queries like "CEO of AWS")
    # Check if query contains entity indicators and text contains those entities
    entity_patterns = [
        (r'\b(?:ceo|chief executive officer)\b.*?\b(?:of|for)\b.*?\b(aws|amazon web services)\b', r'\baws\b|\bamazon web services\b'),
        (r'\b(?:ceo|chief executive officer)\b.*?\b(?:of|for)\b.*?\b(amazon)\b', r'\bamazon\.com\b|\bamazon inc\b'),
    ]
    
    for query_pattern, text_pattern in entity_patterns:
        if re.search(query_pattern, original_query_lower):
            if re.search(text_pattern, text_lower):
                boost += 0.03  # Small boost for entity context match
    
    return min(boost, max_boost)
