"""
Vector Provider System

A clean, modular vector provider system that separates concerns:
- chunking: Text splitting strategies
- embedding: Text embedding providers
- db: Vector database providers
- orchestrator: Coordinates all components based on configuration
"""

from .config import ChunkConfig, EmbeddingConfig, VectorConfig, VectorDBConfig
from .provider import VectorProvider

__all__ = ["VectorProvider", "ChunkConfig", "EmbeddingConfig", "VectorDBConfig", "VectorConfig"]
