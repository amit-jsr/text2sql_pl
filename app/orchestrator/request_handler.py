"""
Request Handler - Single channel text-to-SQL request processing.

This handler:
1. Handles greetings with simple responses
2. Routes ALL other questions to SQL generation
3. Executes SQL and returns formatted results
"""
import os
from typing import Optional, Dict, Any, Tuple, Generator
from dataclasses import dataclass


@dataclass
class QueryResponse:
    """Response from the unified agent."""
    answer: str
    sql: Optional[str] = None
    columns: Optional[list] = None
    rows: Optional[list] = None
    error: Optional[str] = None
    is_greeting: bool = False


# Simple greeting patterns
GREETINGS = {
    "hello", "hi", "hey", "good morning", "good afternoon", 
    "good evening", "thanks", "thank you", "bye", "goodbye"
}

GREETING_RESPONSES = {
    "hello": "Hello! Ask me anything about your Holdings and Trades data.",
    "hi": "Hi! What would you like to know about your data?",
    "hey": "Hey! Ready to help with your data queries.",
    "good morning": "Good morning! How can I help with your data today?",
    "good afternoon": "Good afternoon! What data would you like to explore?",
    "good evening": "Good evening! Ready to answer your data questions.",
    "thanks": "You're welcome! Let me know if you have more questions.",
    "thank you": "You're welcome! Feel free to ask more questions.",
    "bye": "Goodbye! Come back anytime you need data insights.",
    "goodbye": "Goodbye! Happy to help again anytime.",
}


def is_greeting(question: str) -> Tuple[bool, str]:
    """
    Check if the question is a simple greeting.
    
    Returns:
        Tuple of (is_greeting, response)
    """
    q_lower = question.lower().strip().rstrip("!.?")
    
    # Exact match
    if q_lower in GREETINGS:
        return True, GREETING_RESPONSES.get(q_lower, "Hello! How can I help with your data?")
    
    # Starts with greeting
    for greeting in GREETINGS:
        if q_lower.startswith(greeting):
            return True, GREETING_RESPONSES.get(greeting, "Hello! How can I help with your data?")
    
    return False, ""


def process_query(
    question: str,
    duck_client,
    conversation_history: Optional[list] = None
) -> QueryResponse:
    """
    Process a user query through the unified agent.
    
    Flow: Guardrails → Greeting Check → SQL Generation → Execution
    
    Args:
        question: User's question
        duck_client: DuckDB client instance
        conversation_history: Previous conversation for context
        
    Returns:
        QueryResponse with answer and optional SQL results
    """
    # Step 1: Check guardrails for harmful content
    from app.orchestrator.guardrail import check_input_guardrails
    
    guardrail_result = check_input_guardrails(question)
    if not guardrail_result.is_safe:
        return QueryResponse(
            answer=guardrail_result.reason,
            error=f"blocked:{guardrail_result.category}"
        )
    
    # Step 2: Check for greetings
    greeting, response = is_greeting(question)
    if greeting:
        return QueryResponse(answer=response, is_greeting=True)
    
    # Step 3: Everything else goes to SQL generation
    try:
        from app.data.query_planner import plan_query
        from app.data.sql_tools import run_sql
        
        # Generate SQL
        query_plan = plan_query(question, conversation_history=conversation_history)
        
        if not query_plan:
            return QueryResponse(
                answer="I couldn't understand that question. Please try rephrasing it as a data query.\n\n**Examples:**\n- \"Top 10 holdings by market value\"\n- \"How many trades per portfolio?\"\n- \"Show holdings for Garfield\"",
                error="No SQL generated"
            )
        
        sql, metadata = query_plan
        
        # Execute SQL
        try:
            result = run_sql(duck_client, sql)
            
            # Format answer based on results
            row_count = len(result.rows)
            if row_count == 0:
                answer = "No data found matching your query."
            elif row_count == 1 and len(result.columns) == 1:
                # Single value result
                answer = f"**Result:** {result.rows[0][0]}"
            else:
                answer = f"Found {row_count} result(s)."
            
            return QueryResponse(
                answer=answer,
                sql=sql,
                columns=result.columns,
                rows=result.rows
            )
            
        except ValueError as e:
            return QueryResponse(
                answer=f"Query validation failed: {str(e)}",
                sql=sql,
                error=str(e)
            )
        except Exception as e:
            return QueryResponse(
                answer=f"Query execution failed: {str(e)}",
                sql=sql,
                error=str(e)
            )
            
    except Exception as e:
        return QueryResponse(
            answer=f"An error occurred: {str(e)}",
            error=str(e)
        )


def process_query_stream(
    question: str,
    duck_client,
    conversation_history: Optional[list] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Process a query with streaming output.
    
    Flow: Guardrails → Greeting Check → SQL Generation → Execution
    
    Args:
        question: User's question
        duck_client: DuckDB client instance
        conversation_history: Previous conversation for context
        
    Yields:
        Dict with 'type' and 'content' keys
    """
    # Step 1: Check guardrails for harmful content
    from app.orchestrator.guardrail import check_input_guardrails
    
    guardrail_result = check_input_guardrails(question)
    if not guardrail_result.is_safe:
        yield {"type": "blocked", "content": guardrail_result.reason}
        return
    
    # Step 2: Check for greetings
    greeting, response = is_greeting(question)
    if greeting:
        yield {"type": "answer", "content": response, "is_greeting": True}
        return
    
    # Step 3: Generate and execute SQL
    yield {"type": "status", "content": "Generating SQL query..."}
    
    try:
        from app.data.query_planner import plan_query
        from app.data.sql_tools import run_sql
        
        # Generate SQL
        query_plan = plan_query(question, conversation_history=conversation_history)
        
        if not query_plan:
            yield {
                "type": "error",
                "content": "I couldn't understand that question. Please try rephrasing it as a data query.\n\n**Examples:**\n- \"Top 10 holdings by market value\"\n- \"How many trades per portfolio?\"\n- \"Show holdings for Garfield\""
            }
            return
        
        sql, metadata = query_plan
        
        # Status: executing
        yield {"type": "status", "content": "Executing query..."}
        yield {"type": "sql", "content": sql}
        
        # Execute SQL
        try:
            result = run_sql(duck_client, sql)
            
            row_count = len(result.rows)
            if row_count == 0:
                yield {"type": "answer", "content": "No data found matching your query."}
            else:
                yield {
                    "type": "result",
                    "content": f"Found {row_count} result(s).",
                    "columns": result.columns,
                    "rows": result.rows,
                    "sql": sql
                }
                
        except Exception as e:
            yield {"type": "error", "content": f"Query failed: {str(e)}", "sql": sql}
            
    except Exception as e:
        yield {"type": "error", "content": f"An error occurred: {str(e)}"}
