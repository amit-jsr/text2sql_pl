"""
Test LLM integration.
Run this to verify your LLM backend is working.
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.config import generate_answer, is_llm_available, get_llm_backend


def test_llm():
    """Test LLM functionality."""
    backend = get_llm_backend()
    available = is_llm_available()
    
    print(f"LLM Backend: {backend}")
    print(f"Available: {available}")
    
    if not available:
        print("\nLLM not configured. Set one of these:")
        print("   - LLM_BACKEND=openai + OPENAI_API_KEY=sk-...")
        print("   - LLM_BACKEND=ollama (requires Ollama running)")
        print("   - LLM_BACKEND=bedrock + AWS credentials")
        print("\nWithout LLM, the system uses simple text extraction (still works!)")
        return
    
    # Test question
    context = """
    MV_Base is the market value of a position in the base currency (typically USD).
    It's calculated as: Quantity × Price × FX Rate.
    
    This is one of the most important metrics for portfolio valuation.
    """
    
    question = "What does MV_Base mean?"
    
    print(f"\nTesting with question: '{question}'")
    print(f"\nGenerating answer using {backend}...")
    
    try:
        answer = generate_answer(question, context)
        print(f"\nSuccess! Answer:\n{answer}")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    test_llm()
