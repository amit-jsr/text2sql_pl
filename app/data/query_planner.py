"""
Query planner - maps natural language questions to SQL templates.
"""
import re
from typing import Dict, Any, Optional, Tuple
from app.data.query_templates import QueryTemplate, render_template


class QueryPlanner:
    """Maps natural language questions to SQL templates with parameters."""
    
    # Pattern matching for query detection
    PATTERNS = {
        QueryTemplate.COUNT_TRADES_BY_PORTFOLIO: [
            r"how many trades.*portfolio",
            r"count.*trades.*by.*portfolio",
            r"trades.*per.*portfolio",
            r"number of trades.*portfolio"
        ],
        QueryTemplate.TOP_HOLDINGS_BY_MV: [
            r"top.*holdings",
            r"largest.*holdings",
            r"biggest.*positions",
            r"holdings.*by.*(?:market value|mv)"
        ],
        QueryTemplate.PNL_BY_PORTFOLIO: [
            r"p[&]?l.*by.*portfolio",
            r"profit.*loss.*portfolio",
            r"ytd.*portfolio",
            r"performance.*portfolio"
        ],
        QueryTemplate.NET_TRADED_QTY_BY_SECURITY: [
            r"net.*trad(?:ed|ing).*(?:quantity|qty)",
            r"net.*position.*from.*trades",
            r"buy.*sell.*by.*security"
        ],
        QueryTemplate.PORTFOLIO_SUMMARY: [
            r"portfolio.*summary",
            r"overview.*portfolio",
            r"portfolio.*total"
        ],
        QueryTemplate.TRADES_FOR_SECURITY: [
            r"trades.*for.*(?:security|stock|bond)",
            r"trading.*activity.*(?:security|stock)",
            r"show.*trades.*(?:security|stock)"
        ],
        QueryTemplate.HOLDINGS_FOR_PORTFOLIO: [
            r"holdings.*for.*portfolio",
            r"what.*does.*(?:portfolio.*)?(?:hold|own)",
            r"positions.*in.*portfolio"
        ],
        QueryTemplate.LARGEST_TRADES: [
            r"largest.*trades",
            r"biggest.*trades",
            r"top.*trades.*by.*(?:size|value|principal)"
        ],
        QueryTemplate.UNIQUE_SECURITIES: [
            r"how many.*(?:unique|different).*securities",
            r"count.*securities",
            r"number of.*securities"
        ],
        QueryTemplate.ALLOCATION_SUMMARY: [
            r"allocation.*(?:summary|rules)",
            r"how.*trades.*allocated",
            r"allocation.*methods"
        ]
    }
    
    def __init__(self):
        """Initialize query planner."""
        pass
    
    def detect_template(self, question: str) -> Optional[QueryTemplate]:
        """
        Detect which template best matches the question.
        
        Returns:
            QueryTemplate or None if no match
        """
        q_lower = question.lower()
        
        for template, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    return template
        
        return None
    
    def extract_parameters(self, question: str, template: QueryTemplate) -> Dict[str, Any]:
        """
        Extract parameters from question for the template.
        
        Returns:
            Dict of parameter values
        """
        params = {}
        q_lower = question.lower()
        
        # Extract common parameters
        
        # Limit / top N
        limit_match = re.search(r"top\s+(\d+)", q_lower)
        if not limit_match:
            limit_match = re.search(r"(\d+)\s+(?:largest|biggest)", q_lower)
        
        if limit_match:
            params["limit"] = int(limit_match.group(1))
        elif "limit" in self._get_template_params(template):
            params["limit"] = 10  # default
        
        # Portfolio name
        portfolio_match = re.search(r"portfolio[:\s]+([a-z0-9\s]+?)(?:\s|$|\?)", q_lower)
        if not portfolio_match:
            portfolio_match = re.search(r"(?:for|in)\s+([a-z]+)(?:\s|$|\?)", q_lower)
        
        if portfolio_match and "portfolio_name" in self._get_template_params(template):
            # Capitalize first letter for portfolio names
            portfolio_raw = portfolio_match.group(1).strip()
            params["portfolio_name"] = portfolio_raw.title()
        
        # Security ID - extract if numeric pattern
        security_match = re.search(r"security(?:\s+id)?[:\s]+(\d+)", q_lower)
        if security_match and "security_id" in self._get_template_params(template):
            params["security_id"] = int(security_match.group(1))
        
        return params
    
    def _get_template_params(self, template: QueryTemplate) -> list:
        """Get required parameters for a template."""
        from app.data.query_templates import TEMPLATES
        return TEMPLATES[template].parameters
    
    def plan_query(self, question: str, conversation_history: Optional[list] = None) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Plan a SQL query for a natural language question.
        Uses templates first, then falls back to LLM text-to-SQL if available.
        
        Args:
            question: Natural language question
            conversation_history: List of previous exchanges for context
                Each item: {"question": str, "sql": str, "answer": str}
        
        Returns:
            Tuple of (sql_string, metadata) or None if cannot plan
        """
        # Try template-based approach first
        template = self.detect_template(question)
        
        if template is not None:
            params = self.extract_parameters(question, template)
            
            try:
                sql = render_template(template, params)
                metadata = {
                    "template": template.value,
                    "parameters": params,
                    "description": self._get_template_description(template),
                    "method": "template"
                }
                return (sql, metadata)
            
            except Exception as e:
                # Failed to render - try LLM fallback
                print(f"Template rendering failed: {e}, trying LLM...")
        
        # Fallback to LLM text-to-SQL if no template matches
        try:
            from app.llm.text_to_sql import generate_sql_from_text
            from app.llm.config import is_llm_available
            
            if is_llm_available():
                print(f"No template matched for '{question}', using LLM text-to-SQL...")
                return generate_sql_from_text(question, conversation_history=conversation_history)
        except Exception as e:
            print(f"LLM text-to-SQL error: {e}")
        
        return None
    
    def _get_template_description(self, template: QueryTemplate) -> str:
        """Get description for a template."""
        from app.data.query_templates import TEMPLATES
        return TEMPLATES[template].description


# Singleton instance
_planner: Optional[QueryPlanner] = None


def get_planner() -> QueryPlanner:
    """Get or create query planner instance."""
    global _planner
    if _planner is None:
        _planner = QueryPlanner()
    return _planner


def plan_query(question: str, conversation_history: Optional[list] = None) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Convenience function to plan a query with optional conversation history."""
    planner = get_planner()
    return planner.plan_query(question, conversation_history=conversation_history)


if __name__ == "__main__":
    """Test query planning."""
    test_questions = [
        "How many trades per portfolio?",
        "Show me the top 5 holdings by market value",
        "What's the P&L by portfolio?",
        "Holdings for portfolio Garfield",
        "Largest 20 trades",
        "Count unique securities",
    ]
    
    planner = get_planner()
    
    for question in test_questions:
        print(f"\nQ: {question}")
        result = planner.plan_query(question)
        
        if result:
            sql, metadata = result
            print(f"Template: {metadata['template']}")
            print(f"Params: {metadata['parameters']}")
            print(f"SQL preview: {sql[:100]}...")
        else:
            print("Could not plan query")
