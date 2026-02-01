"""
LLM configuration with multi-backend support.
Supports: OpenAI, AWS Bedrock, or local Ollama.
"""
import os
from pathlib import Path
from typing import Optional

# Load .env file from project root
try:
    from dotenv import load_dotenv
    # Find project root (where run.py is)
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    load_dotenv(env_file)
except ImportError:
    pass


def get_llm_backend() -> str:
    """Get configured LLM backend."""
    return os.getenv("LLM_BACKEND", "openai").lower()


def generate_answer(
    question: str,
    context: str,
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate an answer using the configured LLM backend.
    
    Args:
        question: User's question
        context: Retrieved context (RAG docs or SQL results)
        system_prompt: Optional system prompt override
        
    Returns:
        Generated answer text
    """
    backend = get_llm_backend()
    
    if backend in ["openai", "groq"]:
        return _generate_openai(question, context, system_prompt)
    elif backend == "bedrock":
        return _generate_bedrock(question, context, system_prompt)
    elif backend == "ollama":
        return _generate_ollama(question, context, system_prompt)
    else:
        # Fallback: return context directly
        return f"**Context:**\n\n{context}"


def generate_answer_stream(
    question: str,
    context: str,
    system_prompt: Optional[str] = None
):
    """
    Generate an answer using the configured LLM backend with streaming.
    
    Args:
        question: User's question
        context: Retrieved context (RAG docs or SQL results)
        system_prompt: Optional system prompt override
    
    Yields:
        Chunks of the generated answer
    """
    backend = get_llm_backend()
    
    if backend in ["openai", "groq"]:
        yield from _generate_openai_stream(question, context, system_prompt)
    elif backend == "bedrock":
        # Bedrock doesn't support streaming in this implementation
        yield _generate_bedrock(question, context, system_prompt)
    elif backend == "ollama":
        # Ollama doesn't support streaming in this implementation
        yield _generate_ollama(question, context, system_prompt)
    else:
        # Fallback: just return context
        yield f"**Context:**\n\n{context}"


def _generate_openai_stream(question: str, context: str, system_prompt: Optional[str]):
    """Generate answer using OpenAI-compatible API (OpenAI or Groq) with streaming."""
    try:
        from openai import OpenAI
        
        backend = get_llm_backend()
        
        # Get API key and base URL - support both GROQ_* and OPENAI_* variables
        if backend == "groq":
            api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("GROQ_BASE_URL") or os.getenv("OPENAI_BASE_URL")
            model = os.getenv("GROQ_MODEL") or os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")
        else:  # openai
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Initialize client
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)
        
        default_system = """You are a helpful assistant for a financial data analysis system.
Answer questions based ONLY on the provided context. Be concise and accurate.
If the context doesn't contain the answer, say so clearly."""
        
        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
        
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,  # Deterministic for SQL generation
            max_tokens=1500,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
        
    except Exception as e:
        yield f"LLM error: {str(e)}\n\nFallback context:\n{context}"


def _generate_openai(question: str, context: str, system_prompt: Optional[str]) -> str:
    """Generate answer using OpenAI-compatible API (OpenAI or Groq)."""
    try:
        from openai import OpenAI
        
        backend = get_llm_backend()
        
        # Get API key and base URL - support both GROQ_* and OPENAI_* variables
        if backend == "groq":
            api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("GROQ_BASE_URL") or os.getenv("OPENAI_BASE_URL")
            model = os.getenv("GROQ_MODEL") or os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")
        else:  # openai
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Initialize client
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)
        
        default_system = """You are a helpful assistant for a financial data analysis system.
Answer questions based ONLY on the provided context. Be concise and accurate.
If the context doesn't contain the answer, say so clearly."""
        
        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,  # Deterministic for SQL generation
            max_tokens=1500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"LLM error: {str(e)}\n\nFallback context:\n{context}"


def _generate_bedrock(question: str, context: str, system_prompt: Optional[str]) -> str:
    """Generate answer using AWS Bedrock."""
    try:
        import boto3
        import json
        
        bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        default_system = """You are a helpful assistant for a financial data analysis system.
Answer questions based ONLY on the provided context. Be concise and accurate."""
        
        prompt = f"""{system_prompt or default_system}

Context:
{context}

Question: {question}

Answer:"""
        
        body = json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": 500,
            "temperature": 0.3,
            "top_p": 0.9,
        })
        
        model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
        
        response = bedrock.invoke_model(
            body=body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('completion', '').strip()
        
    except Exception as e:
        return f"Bedrock error: {str(e)}\n\nFallback context:\n{context}"


def _generate_ollama(question: str, context: str, system_prompt: Optional[str]) -> str:
    """Generate answer using local Ollama."""
    try:
        import requests
        
        default_system = """You are a helpful assistant for a financial data analysis system.
Answer questions based ONLY on the provided context. Be concise and accurate."""
        
        url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        model = os.getenv("OLLAMA_MODEL", "llama2")
        
        prompt = f"""{system_prompt or default_system}

Context:
{context}

Question: {question}

Answer:"""
        
        response = requests.post(
            url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 500
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            return f"Ollama error (status {response.status_code})\n\nFallback context:\n{context}"
            
    except Exception as e:
        return f"Ollama error: {str(e)}\n\nFallback context:\n{context}"


def is_llm_available() -> bool:
    """Check if LLM is configured and available."""
    backend = get_llm_backend()
    
    if backend == "openai":
        return os.getenv("OPENAI_API_KEY") is not None
    elif backend == "groq":
        # Check for either GROQ_API_KEY or OPENAI_API_KEY (for compatibility)
        return os.getenv("GROQ_API_KEY") is not None or os.getenv("OPENAI_API_KEY") is not None
    elif backend == "bedrock":
        # Check if AWS credentials exist
        return True  # boto3 will handle auth
    elif backend == "ollama":
        # Check if Ollama is running
        try:
            import requests
            url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/tags")
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except:
            return False
    
    return False
