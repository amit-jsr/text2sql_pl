"""
Safety & Guardrails - Input validation and SQL safety checks.

This module provides:
1. Input guardrails - LLM-based content moderation for harmful requests
2. SQL safety - Prevent destructive SQL operations
"""

import os
import re
from pathlib import Path
from typing import Tuple
from dataclasses import dataclass

# Load .env file from project root
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    load_dotenv(env_file)
except ImportError:
    pass


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    is_safe: bool
    reason: str = ""
    category: str = ""


# =============================================================================
# INPUT GUARDRAILS - LLM-based content moderation
# =============================================================================

MODERATION_PROMPT = """You are a strict content moderation system for a financial data query assistant that ONLY handles questions about holdings, trades, portfolios, and market data.

Analyze the user's message and determine if it should be processed.

BLOCK (respond "BLOCKED") if the message:
- Is about sex, dating, relationships, or explicit content
- Contains hate speech, discrimination, slurs, or offensive language
- Asks about violence, weapons, bombs, or how to harm people
- Requests illegal activities (hacking, drugs, fraud)
- Is completely unrelated to financial data queries

ALLOW (respond "SAFE") ONLY if the message:
- Is a legitimate question about holdings, trades, portfolios, P&L, market value, securities
- Is a simple greeting (hi, hello, thanks)
- Asks about the system's data capabilities

User message: "{message}"

Remember: This is a financial data system. Any non-financial, inappropriate, or harmful request should be BLOCKED.

Respond with exactly one word - either "SAFE" or "BLOCKED":"""


def check_input_guardrails(text: str) -> GuardrailResult:
    """
    Check user input for harmful content using LLM.
    
    Args:
        text: User input to check
        
    Returns:
        GuardrailResult with is_safe=True if content is acceptable
    """
    if not text or not text.strip():
        return GuardrailResult(is_safe=True)
    
    # Skip moderation for very short inputs (likely greetings)
    if len(text.strip()) < 5:
        return GuardrailResult(is_safe=True)
    
    try:
        from openai import OpenAI
        
        # Get API configuration
        backend = os.getenv("LLM_BACKEND", "openai").lower()
        
        if backend == "groq":
            api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("GROQ_BASE_URL") or os.getenv("OPENAI_BASE_URL")
            model = os.getenv("GROQ_MODEL") or os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        if not api_key:
            # No API key - skip moderation (allow all)
            return GuardrailResult(is_safe=True)
        
        # Initialize client
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)
        
        # Call LLM for moderation
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": MODERATION_PROMPT.format(message=text)}
            ],
            temperature=0.0,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        
        if "BLOCKED" in result:
            return GuardrailResult(
                is_safe=False,
                reason="I can't help with that type of request. Please ask questions about your holdings and trades data.",
                category="llm_moderation"
            )
        
        return GuardrailResult(is_safe=True)
        
    except Exception as e:
        # On error, allow the request (fail open for better UX)
        # Log the error in production
        print(f"Guardrail check error: {e}")
        return GuardrailResult(is_safe=True)


# =============================================================================
# SQL SAFETY - Prevent destructive operations
# =============================================================================

BLOCKED_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b", re.IGNORECASE)


def assert_safe_sql(sql: str) -> None:
    """
    Validate SQL is read-only (SELECT only).
    
    Args:
        sql: SQL query to validate
        
    Raises:
        ValueError: If SQL contains destructive operations
    """
    if BLOCKED_SQL.search(sql):
        raise ValueError("Unsafe SQL detected - only SELECT queries are allowed")
