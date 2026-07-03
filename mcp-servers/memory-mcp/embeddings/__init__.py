"""
Embedding utilities for Memory MCP Server.

- embedder: Sentence-transformers wrapper with lazy model loading
"""

from .embedder import Embedder

__all__ = ["Embedder"]
