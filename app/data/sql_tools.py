"""
SQL Tools - Query validation and execution utilities.

## SQL Query Clause Order (Writing Order):
SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT

## SQL Execution Order (How database processes it):
1. FROM      - Identify the source table(s)
2. WHERE     - Filter rows before grouping
3. GROUP BY  - Group rows by specified columns
4. HAVING    - Filter groups after aggregation
5. SELECT    - Choose columns and compute expressions
6. DISTINCT  - Remove duplicate rows
7. ORDER BY  - Sort the result set
8. LIMIT     - Restrict number of rows returned

## Example Query Structure:
SELECT column1, COUNT(*) as cnt     -- Step 5: Select columns
FROM table_name                      -- Step 1: Source table
WHERE condition                      -- Step 2: Filter rows
GROUP BY column1                     -- Step 3: Group rows
HAVING COUNT(*) > 5                  -- Step 4: Filter groups
ORDER BY cnt DESC                    -- Step 7: Sort results
LIMIT 10                             -- Step 8: Limit rows

## Common Mistakes:
WRONG:  SELECT ... FROM ... LIMIT 10 GROUP BY ...
RIGHT:  SELECT ... FROM ... GROUP BY ... LIMIT 10
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from app.orchestrator.safety import assert_safe_sql

@dataclass(frozen=True)
class SQLResult:
    columns: list[str]
    rows: list[list]


def validate_sql_query(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Validate SQL query for correctness and potential issues.
    
    Args:
        sql: SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    sql_lower = sql.lower().strip()
    
    # Check for empty query
    if not sql:
        return False, "Empty SQL query"
    
    # Must be a SELECT query
    if not sql_lower.startswith("select"):
        return False, "Only SELECT queries are allowed"
    
    # Check for required FROM clause
    if "from" not in sql_lower:
        return False, "Query must include a FROM clause"
    
    # Check table names
    if "holdings" not in sql_lower and "trades" not in sql_lower:
        return False, "Query must reference 'holdings' or 'trades' table"
    
    # Check for invalid date columns
    if "tradedate" in sql_lower or "settledate" in sql_lower:
        return False, "TradeDate and SettleDate columns have invalid data. Avoid using them."
    
    # Basic syntax checks
    open_parens = sql.count("(")
    close_parens = sql.count(")")
    if open_parens != close_parens:
        return False, "Unmatched parentheses in query"
    
    # Check SQL clause ordering (LIMIT must come after GROUP BY)
    limit_pos = sql_lower.find(" limit ")
    group_by_pos = sql_lower.find(" group by ")
    order_by_pos = sql_lower.find(" order by ")
    
    if limit_pos != -1 and group_by_pos != -1 and limit_pos < group_by_pos:
        return False, "Invalid SQL: LIMIT must come after GROUP BY. Correct order: SELECT → FROM → WHERE → GROUP BY → ORDER BY → LIMIT"
    
    if limit_pos != -1 and order_by_pos != -1 and limit_pos < order_by_pos:
        return False, "Invalid SQL: LIMIT must come after ORDER BY. Correct order: SELECT → FROM → WHERE → GROUP BY → ORDER BY → LIMIT"
    
    return True, None


def run_sql(client, sql: str, limit: int = 200, max_retries: int = 3) -> SQLResult:
    """
    Execute SQL query with validation, safety checks, and automatic retry/fix.
    
    Args:
        client: DuckDB client
        sql: SQL query to execute
        limit: Maximum rows to return
        max_retries: Maximum retry attempts with automatic fixes
        
    Returns:
        SQLResult with columns and rows
        
    Raises:
        ValueError: If query validation fails after all retries
        Exception: If query execution fails after all retries
    """
    last_error = None
    current_sql = sql
    
    for attempt in range(1, max_retries + 1):
        try:
            # Validate query first
            is_valid, error_msg = validate_sql_query(current_sql)
            if not is_valid:
                raise ValueError(f"SQL Validation Error: {error_msg}")
            
            # Safety check (blocks dangerous queries)
            assert_safe_sql(current_sql)
            
            # Add limit if not present
            query_to_run = current_sql
            if "limit" not in current_sql.lower():
                query_to_run = current_sql.rstrip(";") + f" LIMIT {limit}"
            
            # Execute query
            df = client.query_df(query_to_run)
            
            if attempt > 1:
                print(f"Query succeeded on attempt {attempt}/{max_retries}")
            
            return SQLResult(columns=list(df.columns), rows=df.values.tolist())
            
        except Exception as e:
            last_error = str(e)
            error_lower = last_error.lower()
            
            # Check if it's a fixable error
            if attempt < max_retries:
                # Fix 1: CAST to TRY_CAST for conversion errors
                if "conversion error" in error_lower and "could not convert" in error_lower:
                    print(f"Attempt {attempt}/{max_retries} failed: Conversion error")
                    print(f"Fixing: Replacing CAST with TRY_CAST...")
                    current_sql = current_sql.replace("CAST(", "TRY_CAST(")
                    continue
                
                # Fix 2: Missing TRY_CAST
                elif "binder error" in error_lower and "varchar" in error_lower:
                    print(f"Attempt {attempt}/{max_retries} failed: Type mismatch")
                    print(f"Fixing: Adding TRY_CAST for text columns...")
                    # Replace common patterns
                    for col in ["MV_Base", "MV_Local", "PL_YTD", "PL_MTD", "PL_DTD"]:
                        # Fix SUM(column) -> SUM(TRY_CAST(column AS DOUBLE))
                        current_sql = current_sql.replace(f"SUM({col})", f"SUM(TRY_CAST({col} AS DOUBLE))")
                        current_sql = current_sql.replace(f"AVG({col})", f"AVG(TRY_CAST({col} AS DOUBLE))")
                        current_sql = current_sql.replace(f"MIN({col})", f"MIN(TRY_CAST({col} AS DOUBLE))")
                        current_sql = current_sql.replace(f"MAX({col})", f"MAX(TRY_CAST({col} AS DOUBLE))")
                        # Fix ORDER BY column -> ORDER BY TRY_CAST(column AS DOUBLE)
                        current_sql = current_sql.replace(f"ORDER BY {col}", f"ORDER BY TRY_CAST({col} AS DOUBLE)")
                    continue
                
                else:
                    # Unknown error, can't auto-fix - let caller retry with new SQL
                    print(f"Attempt {attempt}/{max_retries} failed: {last_error}")
                    print(f"Cannot auto-fix this error type, needs new SQL generation")
            else:
                # Last attempt failed
                print(f"All {max_retries} attempts failed. Last error: {last_error}")
                raise
    
    # Should never reach here
    raise Exception(f"Query execution failed after {max_retries} attempts: {last_error}")

