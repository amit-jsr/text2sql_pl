"""
Retrieval system for RAG.
Queries ChromaDB for relevant document chunks and formats citations.
"""
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

from app.rag.config import config
from app.rag.ingest import get_embedding_function


class DocumentRetriever:
    """Retrieves relevant document chunks for questions."""
    
    def __init__(self):
        """Initialize retriever with ChromaDB collection."""
        self.chroma_client = chromadb.PersistentClient(
            path=config.chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.chroma_client.get_collection(
                name="dataset_docs",
                embedding_function=get_embedding_function()
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load collection. Run 'python -m app.rag.ingest' first. Error: {e}"
            )
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: User question
            top_k: Number of chunks to return (defaults to config.top_k)
        
        Returns:
            List of dicts with 'content', 'source', 'distance'
        """
        if top_k is None:
            top_k = config.top_k
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        # Format results
        chunks = []
        for i in range(len(results["documents"][0])):
            chunks.append({
                "content": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "distance": results["distances"][0][i] if "distances" in results else None,
                "chunk_id": results["metadatas"][0][i]["chunk_id"]
            })
        
        return chunks
    
    def format_context(self, chunks: List[Dict]) -> str:
        """Format retrieved chunks as context for LLM."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Source: {chunk['source']}]\n{chunk['content']}\n")
        
        return "\n---\n\n".join(context_parts)
    
    def format_citations(self, chunks: List[Dict]) -> List[str]:
        """Format citations for response."""
        sources = set()
        for chunk in chunks:
            sources.add(chunk["source"])
        
        return sorted(list(sources))


# Singleton retriever instance
_retriever: Optional[DocumentRetriever] = None


def get_retriever() -> DocumentRetriever:
    """Get or create retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = DocumentRetriever()
    return _retriever


def retrieve_for_question(question: str, top_k: Optional[int] = None) -> Dict:
    """
    Convenience function to retrieve context for a question.
    
    Returns:
        Dict with 'context', 'chunks', 'sources'
    """
    retriever = get_retriever()
    chunks = retriever.retrieve(question, top_k)
    
    return {
        "context": retriever.format_context(chunks),
        "chunks": chunks,
        "sources": retriever.format_citations(chunks)
    }


if __name__ == "__main__":
    """Test retrieval."""
    test_questions = [
        "What does MV_Base mean?",
        "How are trades and holdings related?",
        "What's wrong with the trade dates?",
    ]
    
    retriever = get_retriever()
    
    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print('='*60)
        
        result = retrieve_for_question(question, top_k=2)
        
        print(f"\nSources: {', '.join(result['sources'])}")
        print(f"\nContext preview:")
        print(result['context'][:500] + "...")
