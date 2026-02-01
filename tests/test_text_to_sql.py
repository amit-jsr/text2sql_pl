"""
Test LLM-powered text-to-SQL generation.
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.text_to_sql import generate_sql_from_text
from app.llm.config import is_llm_available, get_llm_backend


def test_text_to_sql():
    """Test text-to-SQL with various questions."""
    
    backend = get_llm_backend()
    available = is_llm_available()
    
    print(f"LLM Backend: {backend}")
    print(f"Available: {available}\n")
    
    if not available:
        print("LLM not configured. Text-to-SQL requires an LLM.")
        print("\nTo enable, set one of:")
        print("  export LLM_BACKEND=openai")
        print("  export OPENAI_API_KEY=sk-...")
        print("\nOR:")
        print("  export LLM_BACKEND=ollama")
        print("  (requires Ollama running with a model)")
        return
    
    print("=" * 70)
    print("Testing LLM Text-to-SQL Generation")
    print("=" * 70)
    
    # Test questions that should work with LLM
    test_questions = [
        # Template-based (should still work)
        "How many trades per portfolio?",
        
        # New questions that templates can't handle
        "What's the total market value across all portfolios?",
        "Show me securities with negative P&L",
        "Which portfolio has the most holdings?",
        "Average market value per security in the Garfield portfolio",
        "List all portfolios sorted by total P&L descending",
        "Count how many securities are held in each portfolio",
        "Show me the top 3 securities by total quantity across all portfolios",
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {question}")
        print(f"{'='*70}")
        
        result = generate_sql_from_text(question)
        
        if result:
            sql, metadata = result
            print(f"SQL Generated:")
            print(f"\n{sql}\n")
            print(f"Method: {metadata.get('method', 'N/A')}")
        else:
            print("Failed to generate SQL")
    
    print(f"\n{'='*70}")
    print("Tip: The generated SQL can handle ANY question about the data!")
    print("   Not limited to the 10 pre-built templates.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    test_text_to_sql()
