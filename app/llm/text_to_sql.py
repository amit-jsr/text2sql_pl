"""
LLM-powered text-to-SQL generation.
Converts natural language questions to SQL queries using an LLM.
"""
from typing import Optional, Dict, Any, Tuple
from app.llm.config import generate_answer, is_llm_available

# Try to import sqlparse for SQL formatting
try:
    import sqlparse
    SQLPARSE_AVAILABLE = True
except ImportError:
    SQLPARSE_AVAILABLE = False


# Schema information for the LLM
SCHEMA_INFO = """
# Database Schema

## Table: holdings
Portfolio positions snapshot (1,023 rows)

Columns:
- PortfolioName (TEXT): Name of the portfolio (e.g., 'Garfield', 'Heather', 'MNC Investment Fund')
- SecurityId (INTEGER): Unique security identifier
- SecName (TEXT): Security name/identifier string
- SecurityTypeName (TEXT): Type of security (e.g., 'Bond', 'Equity', 'AssetBacked')
- Qty (DOUBLE): Quantity held
- Price (DOUBLE): Current price
- MV_Base (DOUBLE): Market value in base currency (USD)
- MV_Local (DOUBLE): Market value in local currency
- PL_YTD (DOUBLE): Year-to-date profit/loss
- PL_MTD (DOUBLE): Month-to-date profit/loss
- PL_DTD (DOUBLE): Day-to-date profit/loss

## Table: trades
Transaction events (650 rows)

Columns:
- id (INTEGER): Unique trade identifier
- PortfolioName (TEXT): Portfolio name
- SecurityId (INTEGER): Security identifier
- SecurityType (TEXT): Type of security
- Name (TEXT): Security name
- TradeTypeName (TEXT): Type of trade (e.g., 'Buy', 'Sell')
- Quantity (DOUBLE): Trade quantity
- Price (DOUBLE): Trade price
- Principal (DOUBLE): Principal amount
- TotalCash (DOUBLE): Total cash amount
- AllocationQTY (DOUBLE): Allocated quantity
- AllocationCash (DOUBLE): Allocated cash amount
- TradeDate (TEXT): Trade date (NOTE: invalid in this dataset - shows "00:00.0")
- SettleDate (TEXT): Settlement date (NOTE: invalid in this dataset)

## Data Catalog - Column Name Mappings
Use this to understand what users mean when they ask about data:

| User Says | Actual Column | Table |
|-----------|---------------|-------|
| portfolio, fund, account | PortfolioName | both |
| security, stock, bond, asset, instrument | SecurityId, SecName, Name | both |
| security type, asset class, type | SecurityTypeName (holdings), SecurityType (trades) | both |
| quantity, shares, units, amount | Qty (holdings), Quantity (trades) | both |
| price, value per unit | Price | both |
| market value, mv, value, worth | MV_Base | holdings |
| local value, local mv | MV_Local | holdings |
| pnl, p&l, profit, loss, gain, return | PL_YTD, PL_MTD, PL_DTD | holdings |
| ytd, year to date | PL_YTD | holdings |
| mtd, month to date | PL_MTD | holdings |
| dtd, day to date, today | PL_DTD | holdings |
| trade type, buy, sell, action | TradeTypeName | trades |
| principal, notional | Principal | trades |
| cash, total cash | TotalCash | trades |
| allocation | AllocationQTY, AllocationCash | trades |

## Important Notes:
- Use DuckDB SQL syntax
- Both tables exist as views in the database
- TradeDate and SettleDate columns have invalid data - avoid using them
- Portfolio names include: Garfield, Heather, MNC Investment Fund, Opium Holdings Partners, Platpot, Ytum, NorthPoint, HoldCo 1, Redfield Accu-Fund, UNC Investment Fund, etc.
"""


def generate_sql_from_text(
    question: str, 
    max_retries: int = 3,
    conversation_history: Optional[list] = None
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Generate SQL query from natural language using LLM with retry logic.
    
    Args:
        question: Natural language question about the data
        max_retries: Maximum number of retry attempts (default: 3)
        conversation_history: List of previous exchanges for context
            Each item: {"question": str, "sql": str, "answer": str}
        
    Returns:
        Tuple of (sql_query, metadata) or None if generation fails after all retries
        
    Example:
        >>> sql, meta = generate_sql_from_text("What's the total market value by portfolio?")
        >>> print(sql)
        SELECT PortfolioName, SUM(CAST(MV_Base AS DOUBLE)) as TotalValue FROM holdings GROUP BY PortfolioName
    """
    if not is_llm_available():
        return None
    
    # Build conversation context
    conversation_context = ""
    if conversation_history:
        recent = conversation_history[-3:]  # Last 3 exchanges
        history_parts = []
        for item in recent:
            history_parts.append(f"User: {item.get('question', '')}")
            if item.get('sql'):
                history_parts.append(f"SQL: {item.get('sql', '')}")
        conversation_context = "\n".join(history_parts)
    
    system_prompt = f"""You are an expert SQL query generator. Your ONLY job is to output a valid DuckDB SQL query.

CRITICAL RULES:
1. Output ONLY the SQL query - no explanations, no markdown, no code fences
2. Use ONLY these tables: holdings, trades
3. NEVER use TradeDate or SettleDate columns (they have invalid data)
4. ALWAYS put clauses in this order: SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT
5. Only add LIMIT if the user explicitly asks for a specific number (e.g., "top 10", "first 5")

{SCHEMA_INFO}

QUERY PATTERNS:
- "how many X per Y" → SELECT Y, COUNT(*) FROM table GROUP BY Y
- "top N X by Y" → SELECT ... FROM table ORDER BY Y DESC LIMIT N  
- "total/sum of X" → SELECT SUM(X) FROM table
- "X for portfolio Y" → SELECT ... FROM table WHERE PortfolioName = 'Y'
- "list all X" → SELECT DISTINCT X FROM table

EXAMPLES:

Q: How many trades per portfolio?
SELECT PortfolioName, COUNT(*) as NumTrades FROM trades GROUP BY PortfolioName ORDER BY NumTrades DESC

Q: Top 10 holdings by market value
SELECT PortfolioName, SecName, MV_Base FROM holdings ORDER BY MV_Base DESC LIMIT 10

Q: Total market value by portfolio
SELECT PortfolioName, SUM(MV_Base) as TotalMV FROM holdings GROUP BY PortfolioName ORDER BY TotalMV DESC

Q: Holdings for Garfield portfolio
SELECT SecName, SecurityTypeName, Qty, MV_Base, PL_YTD FROM holdings WHERE PortfolioName = 'Garfield'

Q: Largest trades
SELECT PortfolioName, Name, TradeTypeName, Quantity, Principal FROM trades ORDER BY Principal DESC LIMIT 10

Q: Average P&L by security type
SELECT SecurityTypeName, AVG(PL_YTD) as AvgPnL, COUNT(*) as Count FROM holdings GROUP BY SecurityTypeName ORDER BY AvgPnL DESC

Now generate SQL for the user's question. Output ONLY the SQL query, nothing else."""
    
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            # Build context - include conversation history and error feedback
            context_parts = []
            
            if conversation_context:
                context_parts.append(f"## Previous Conversation:\n{conversation_context}")
            
            context_parts.append(f"## Current Question:\n{question}")
            
            if last_error and attempt > 1:
                context_parts.append(f"\n## Error from previous attempt:\n{last_error}\nFix the issue. Remember: LIMIT must come AFTER GROUP BY and ORDER BY.")
            
            context = "\n\n".join(context_parts)
            
            # Generate SQL using LLM
            sql_response = generate_answer(
                question=question,
                context=context,
                system_prompt=system_prompt
            )
            
            # Clean up response - remove markdown code blocks if present
            sql_query = sql_response.strip()
            
            # Remove markdown code fences
            if sql_query.startswith("```"):
                lines = sql_query.split("\n")
                # Remove first and last lines if they're code fences
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                sql_query = "\n".join(lines).strip()
            
            # Remove 'sql' language identifier
            if sql_query.lower().startswith("sql\n"):
                sql_query = sql_query[4:].strip()
            
            # Format and clean SQL using sqlparse
            if SQLPARSE_AVAILABLE:
                try:
                    # Format the SQL query
                    sql_query = sqlparse.format(
                        sql_query,
                        reindent=True,
                        keyword_case='upper',
                        strip_comments=True,
                        use_space_around_operators=True
                    )
                    # Remove extra whitespace
                    sql_query = ' '.join(sql_query.split())
                except:
                    # If formatting fails, continue with unformatted query
                    pass
            
            # Validate basic SQL structure
            if not _is_valid_sql(sql_query):
                last_error = "Generated SQL failed validation"
                if attempt < max_retries:
                    print(f"Attempt {attempt}/{max_retries} failed validation, retrying...")
                    continue
                else:
                    return None
            
            # Additional validation using the validator
            from app.data.sql_tools import validate_sql_query
            is_valid, error_msg = validate_sql_query(sql_query)
            
            if not is_valid:
                last_error = error_msg
                if attempt < max_retries:
                    print(f"Attempt {attempt}/{max_retries} failed: {error_msg}")
                    print(f"Retrying...")
                    continue
                else:
                    return None
            
            # Success!
            metadata = {
                "method": "llm_generated",
                "llm_backend": "text-to-sql",
                "question": question,
                "attempts": attempt
            }
            
            if attempt > 1:
                print(f"Success on attempt {attempt}/{max_retries}")
            
            return sql_query, metadata
            
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                print(f"Attempt {attempt}/{max_retries} error: {e}")
                print(f"Retrying...")
            continue
    
    # All retries failed
    print(f"Failed after {max_retries} attempts. Last error: {last_error}")
    return None


def _is_valid_sql(sql: str) -> bool:
    """
    Basic validation of generated SQL.
    
    Args:
        sql: SQL query string
        
    Returns:
        True if SQL looks valid, False otherwise
    """
    sql_lower = sql.lower().strip()
    
    # Must start with SELECT (read-only)
    if not sql_lower.startswith("select"):
        return False
    
    # Must reference holdings or trades
    if "holdings" not in sql_lower and "trades" not in sql_lower:
        return False
    
    # Must not contain dangerous operations
    dangerous_keywords = [
        "drop", "delete", "insert", "update", "alter", 
        "create", "truncate", "exec", "execute"
    ]
    for keyword in dangerous_keywords:
        if keyword in sql_lower:
            return False
    
    # Basic syntax check - must have FROM
    if " from " not in sql_lower:
        return False
    
    return True


def enhance_query_planner_with_llm():
    """
    This function integrates LLM text-to-SQL with the existing template-based planner.
    Call this to enable fallback to LLM when templates don't match.
    """
    from app.data.query_planner import QueryPlanner
    
    # Store original plan_query method
    original_plan_query = QueryPlanner.plan_query
    
    def plan_query_with_llm_fallback(self, question: str):
        """Enhanced plan_query that falls back to LLM if templates don't match."""
        # Try template-based approach first
        result = original_plan_query(self, question)
        
        if result is not None:
            return result
        
        # Fallback to LLM text-to-SQL
        print(f"No template matched, trying LLM text-to-SQL...")
        return generate_sql_from_text(question)
    
    # Monkey-patch the method
    QueryPlanner.plan_query = plan_query_with_llm_fallback
    print("Query planner enhanced with LLM fallback")
