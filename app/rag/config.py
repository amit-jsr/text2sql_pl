"""
Configuration for RAG system supporting multiple backends.
"""
import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Load .env file from project root
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    load_dotenv(env_file)
except ImportError:
    pass

class RAGBackend(str, Enum):
    LOCAL = "local"
    OPENAI = "openai"
    BEDROCK = "bedrock"

@dataclass(frozen=True)
class RAGConfig:
    """Configuration for RAG system."""
    
    backend: RAGBackend
    embedding_model: str
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 3
    
    # OpenAI specific
    openai_api_key: Optional[str] = None
    
    # Bedrock specific
    aws_region: Optional[str] = None
    
    # Paths
    docs_path: str = "app/rag/docs"
    chroma_db_path: str = "app/rag/chroma_db"
    
    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Load configuration from environment variables."""
        backend_str = os.getenv("RAG_BACKEND", "local").lower()
        backend = RAGBackend(backend_str)
        
        # Default embedding models per backend
        default_models = {
            RAGBackend.LOCAL: "all-MiniLM-L6-v2",
            RAGBackend.OPENAI: "text-embedding-3-small",
            RAGBackend.BEDROCK: "amazon.titan-embed-text-v1"
        }
        
        embedding_model = os.getenv("EMBEDDING_MODEL", default_models[backend])
        
        return cls(
            backend=backend,
            embedding_model=embedding_model,
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            top_k=int(os.getenv("TOP_K", "3")),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
        )

# Global config instance
config = RAGConfig.from_env()
