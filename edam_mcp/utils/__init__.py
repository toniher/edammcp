"""Utility functions for text processing and similarity calculations."""

from .similarity import calculate_jaccard_similarity, calculate_similarity
from .text_processing import normalize_text, preprocess_text

__all__ = [
    "preprocess_text",
    "normalize_text",
    "calculate_similarity",
    "calculate_jaccard_similarity",
]
