"""
Data Assistant - Text-to-SQL Chat Interface
A natural language interface for querying holdings and trades datasets.
Single-channel architecture: All queries → SQL generation → Results
"""
import os
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import chainlit as cl
from typing import Dict, Any, List
import uuid
from datetime import datetime
import pandas as pd

# Import request handler
from app.orchestrator.request_handler import process_query_stream, is_greeting
from app.data.duckdb_client import DuckDBClient, DuckDBConfig


# Initialize DuckDB
base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
duck = DuckDBClient(DuckDBConfig())
duck.init_views(
    trades_csv_path=os.path.join(base_dir, "data/dataset/trades.csv"),
    holdings_csv_path=os.path.join(base_dir, "data/dataset/holdings.csv"),
)


# Conversation history helper
def add_to_history(question: str, answer: str, sql: str = None):
    """Add exchange to conversation history."""
    history = cl.user_session.get("history", [])
    history.append({
        "question": question,
        "answer": answer,
        "sql": sql
    })
    # Keep last 10 exchanges
    cl.user_session.set("history", history[-10:])


def format_table_html(columns: list, rows: list, max_height: int = 400) -> str:
    """Format query results as a scrollable HTML table.
    
    Args:
        columns: Column headers
        rows: Data rows
        max_height: Max height in pixels before scrolling (default 400px ~15 rows)
    """
    if not rows:
        return "*No results found*"
    
    # Format cell values
    def format_val(val):
        if isinstance(val, float):
            return f"{val:,.2f}"
        elif isinstance(val, int):
            return f"{val:,}"
        elif val is None:
            return "NULL"
        else:
            str_val = str(val)
            if len(str_val) > 50:
                return str_val[:47] + "..."
            return str_val
    
    # Build HTML table with inline styles for scrolling
    html = f'''<div style="max-height: {max_height}px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
<table style="width: 100%; border-collapse: collapse; font-size: 13px;">
<thead style="position: sticky; top: 0; background: #f5f5f5;">
<tr>'''
    
    # Headers
    for col in columns:
        html += f'<th style="padding: 8px 12px; text-align: left; border-bottom: 2px solid #ddd;">{col}</th>'
    html += '</tr></thead><tbody>'
    
    # Rows
    for i, row in enumerate(rows):
        bg = '#fff' if i % 2 == 0 else '#fafafa'
        html += f'<tr style="background: {bg};">'
        for val in row:
            html += f'<td style="padding: 6px 12px; border-bottom: 1px solid #eee;">{format_val(val)}</td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    html += f'\n\n*{len(rows)} rows*'
    
    return html


def format_table(columns: list, rows: list) -> str:
    """Format query results as a markdown table with all rows."""
    if not rows:
        return "*No results found*"
    
    # Create header
    header = "| " + " | ".join(str(col) for col in columns) + " |"
    separator = "| " + " | ".join(":---" for _ in columns) + " |"
    
    # Create all rows
    table_rows = []
    for row in rows:
        formatted_row = []
        for val in row:
            if isinstance(val, float):
                formatted_row.append(f"{val:,.2f}")
            elif isinstance(val, int):
                formatted_row.append(f"{val:,}")
            else:
                str_val = str(val) if val is not None else "NULL"
                if len(str_val) > 40:
                    str_val = str_val[:37] + "..."
                formatted_row.append(str_val)
        table_rows.append("| " + " | ".join(formatted_row) + " |")
    
    table = "\n".join([header, separator] + table_rows)
    table += f"\n\n*{len(rows)} rows*"
    
    return table


@cl.on_chat_start
async def start():
    """Called when a new chat session starts."""
    session_id = str(uuid.uuid4())[:8]
    
    cl.user_session.set("history", [])
    cl.user_session.set("session_id", session_id)
    
    welcome = """Welcome to **Data Assistant** 📊

I convert your questions into SQL queries to analyze Holdings and Trades data.

**Try asking:**
- "Top 10 holdings by market value"
- "How many trades per portfolio?"
- "Show holdings for Garfield"
- "Total P&L by security type"

💡 *I remember our conversation for follow-up questions!*
"""
    
    await cl.Message(content=welcome, author="Assistant").send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages - single channel to SQL."""
    question = message.content.strip()
    
    if not question:
        await cl.Message(content="Please ask a question!").send()
        return
    
    q_lower = question.lower().strip()
    
    # Handle special commands
    if q_lower in ["clear", "reset", "clear history"]:
        cl.user_session.set("history", [])
        await cl.Message(content="🔄 History cleared. Ask me a new question!", author="Assistant").send()
        return
    
    if q_lower in ["help", "commands", "?"]:
        await cl.Message(content="""**Commands:** `clear`, `help`

**Example queries:**
- "Top 10 holdings by market value"
- "How many trades per portfolio?"
- "Show holdings for Garfield"
- "Total market value by portfolio"
""", author="Assistant").send()
        return
    
    # Process through unified agent
    msg = cl.Message(content="", author="Assistant")
    await msg.send()
    
    history = cl.user_session.get("history", [])
    sql_used = None
    
    for event in process_query_stream(question, duck, conversation_history=history):
        event_type = event.get("type")
        content = event.get("content", "")

        if event_type == "status":
            msg.content = f"⏳ {content}"
            await msg.update()

        elif event_type == "answer":
            msg.content = content
            await msg.update()

        elif event_type == "sql":
            sql_used = content

        elif event_type == "result":
            sql_used = event.get("sql")
            columns = event.get("columns", [])
            rows = event.get("rows", [])

            # Build text response
            parts = [f"**{content}**\n"]

            if sql_used:
                parts.append(f"```sql\n{sql_used}\n```")

            if rows:
                parts.append(f"*{len(rows)} rows returned*")
            
            msg.content = "\n".join(parts)
            await msg.update()
            
            # Send scrollable dataframe with download options
            if rows:
                df = pd.DataFrame(rows, columns=columns)
                
                # Create CSV for download
                csv_data = df.to_csv(index=False).encode('utf-8')
                
                elements = [
                    cl.Dataframe(data=df, display="inline", name="Results"),
                    cl.File(name="results.csv", content=csv_data),
                ]
                
                if sql_used:
                    sql_data = sql_used.encode('utf-8')
                    elements.append(cl.File(name="query.sql", content=sql_data))
                
                await cl.Message(
                    content="", 
                    elements=elements, 
                    author="Assistant"
                ).send()

        elif event_type == "error":
            error_sql = event.get("sql")
            msg.content = f"❌ {content}"
            if error_sql:
                msg.content += f"\n\n```sql\n{error_sql}\n```"
            await msg.update()

        elif event_type == "blocked":
            msg.content = f"🚫 {content}"
            await msg.update()
            # Stop processing further events
            break
    
    # Save to history
    add_to_history(question, msg.content, sql_used)


if __name__ == "__main__":
    print("To start: chainlit run run.py -w")
