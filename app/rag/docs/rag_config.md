# RAG Configuration

## Overview
This system supports multiple embedding and LLM backends for flexibility:
- **Local (Ollama)**: Free, private, no API costs
- **OpenAI**: High quality, easy to use
- **AWS Bedrock**: Enterprise-ready, AWS-integrated

## Configuration

Set environment variables to choose your backend:

```bash
# Option 1: Local (default)
export RAG_BACKEND=local
export EMBEDDING_MODEL=all-MiniLM-L6-v2  # sentence-transformers model

# Option 2: OpenAI
export RAG_BACKEND=openai
export OPENAI_API_KEY=sk-...
export EMBEDDING_MODEL=text-embedding-3-small

# Option 3: AWS Bedrock
export RAG_BACKEND=bedrock
export AWS_REGION=us-east-1
export EMBEDDING_MODEL=amazon.titan-embed-text-v1
```

## Backends

### Local (Sentence Transformers)
- **Pros**: Free, fast, private
- **Cons**: Lower quality than GPT-4
- **Best for**: Development, demos, cost-sensitive deployments

### OpenAI
- **Pros**: High quality embeddings and chat
- **Cons**: API costs, requires internet
- **Best for**: Production with budget

### AWS Bedrock
- **Pros**: Enterprise features, AWS integration, no egress costs
- **Cons**: AWS account required, regional availability
- **Best for**: AWS-native deployments

## Vector Store
Uses **ChromaDB** for all backends:
- Embedded database (no server)
- Fast similarity search
- Persists to disk at `app/rag/chroma_db/`
