"""
Document ingestion for RAG system.
Loads markdown files, chunks them, and stores embeddings in ChromaDB.
"""
import os
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings

from app.rag.config import config, RAGBackend


def get_embedding_function():
    """Get embedding function based on configured backend."""
    if config.backend == RAGBackend.LOCAL:
        # Use sentence-transformers for local embeddings
        from chromadb.utils import embedding_functions
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.embedding_model
        )
    
    elif config.backend == RAGBackend.OPENAI:
        from chromadb.utils import embedding_functions
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable required for OpenAI backend")
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=config.openai_api_key,
            model_name=config.embedding_model
        )
    
    elif config.backend == RAGBackend.BEDROCK:
        # Custom Bedrock embedding function
        return BedrockEmbeddingFunction(
            model_name=config.embedding_model,
            region=config.aws_region
        )
    
    raise ValueError(f"Unsupported backend: {config.backend}")


class BedrockEmbeddingFunction:
    """Custom embedding function for AWS Bedrock."""
    
    def __init__(self, model_name: str, region: str):
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 required for Bedrock backend. Install with: pip install boto3")
        
        self.model_name = model_name
        self.client = boto3.client("bedrock-runtime", region_name=region)
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using Bedrock."""
        import json
        
        embeddings = []
        for text in texts:
            body = json.dumps({"inputText": text})
            response = self.client.invoke_model(
                modelId=self.model_name,
                body=body
            )
            result = json.loads(response["body"].read())
            embeddings.append(result["embedding"])
        
        return embeddings


def load_markdown_files(docs_path: str) -> List[Dict[str, str]]:
    """Load all markdown files from docs directory."""
    docs_dir = Path(docs_path)
    documents = []
    
    for md_file in docs_dir.glob("*.md"):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        documents.append({
            "content": content,
            "source": md_file.name,
            "path": str(md_file)
        })
    
    print(f"Loaded {len(documents)} markdown files from {docs_path}")
    return documents


def chunk_document(doc: Dict[str, str], chunk_size: int, overlap: int) -> List[Dict[str, str]]:
    """Split document into overlapping chunks."""
    content = doc["content"]
    chunks = []
    
    # Split by sections (## headers) first for better semantic chunks
    sections = content.split("\n## ")
    
    for i, section in enumerate(sections):
        if i > 0:
            section = "## " + section  # Re-add header marker
        
        # If section is larger than chunk_size, split further
        if len(section) > chunk_size:
            words = section.split()
            for j in range(0, len(words), chunk_size - overlap):
                chunk_text = " ".join(words[j:j + chunk_size])
                chunks.append({
                    "content": chunk_text,
                    "source": doc["source"],
                    "chunk_id": f"{doc['source']}_chunk_{len(chunks)}"
                })
        else:
            chunks.append({
                "content": section,
                "source": doc["source"],
                "chunk_id": f"{doc['source']}_section_{i}"
            })
    
    return chunks


def ingest_documents(force_reload: bool = False) -> chromadb.Collection:
    """
    Ingest markdown documents into ChromaDB.
    
    Args:
        force_reload: If True, delete existing collection and re-ingest
    
    Returns:
        ChromaDB collection
    """
    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(
        path=config.chroma_db_path,
        settings=Settings(anonymized_telemetry=False)
    )
    
    collection_name = "dataset_docs"
    
    # Check if collection exists
    existing_collections = [c.name for c in chroma_client.list_collections()]
    
    if collection_name in existing_collections:
        if force_reload:
            print(f"Deleting existing collection: {collection_name}")
            chroma_client.delete_collection(collection_name)
        else:
            print(f"Collection '{collection_name}' already exists. Loading...")
            collection = chroma_client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            print(f"Collection has {collection.count()} documents")
            return collection
    
    # Create collection
    print(f"Creating new collection: {collection_name}")
    collection = chroma_client.create_collection(
        name=collection_name,
        embedding_function=get_embedding_function(),
        metadata={"description": "Dataset documentation for RAG"}
    )
    
    # Load and chunk documents
    documents = load_markdown_files(config.docs_path)
    
    all_chunks = []
    for doc in documents:
        chunks = chunk_document(doc, config.chunk_size, config.chunk_overlap)
        all_chunks.extend(chunks)
    
    print(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
    
    # Add to ChromaDB in batches
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        
        collection.add(
            documents=[chunk["content"] for chunk in batch],
            metadatas=[{"source": chunk["source"], "chunk_id": chunk["chunk_id"]} for chunk in batch],
            ids=[chunk["chunk_id"] for chunk in batch]
        )
    
    print(f"Ingestion complete. Collection has {collection.count()} chunks")
    return collection


if __name__ == "__main__":
    """Run ingestion from command line."""
    import sys
    
    force = "--force" in sys.argv
    
    print(f"Starting document ingestion with backend: {config.backend}")
    print(f"Embedding model: {config.embedding_model}")
    
    collection = ingest_documents(force_reload=force)
    
    # Show sample
    results = collection.peek(5)
    print("\nSample documents:")
    for i, doc in enumerate(results["documents"][:3]):
        print(f"\n--- Document {i+1} ---")
        print(doc[:200] + "..." if len(doc) > 200 else doc)
