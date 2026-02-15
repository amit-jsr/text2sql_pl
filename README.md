# AI Assistant — Text-to-SQL

A chatbot that converts plain-English questions into SQL and returns results from the provided CSV datasets.

## Quick start

- One-time setup:

  ```bash
  ./setup.sh
  ```

- Run the app (opens at http://localhost:8000):

  ```bash
  chainlit run run.py -w
  ```

## Core features

- Natural language → SQL
- System-generated, safe, and validated SQL queries
- Aggregations (e.g., top holdings, trades per portfolio)
- Downloadable query and results

## Configuration

- Create a .env with LLM provider and key (or copy from .env.example):

  ```bash
  cp .env.example .env
  LLM_BACKEND=openai
  OPENAI_API_KEY=your_key_here
  OPENAI_MODEL=gpt-4o
  ```

## Project Architecture

- run.py — Chainlit entrypoint  
- app/data — DuckDB client, query planner  
- app/llm — LLM adapter  
- app/orchestrator — Request handler and safety checks

Architecture: Chainlit UI  → Request handler → Input guardrails → Query planner → DuckDB (CSV views)

## Example queries

- "How many trades per portfolio?"
- "Top 10 holdings by market value"
- "Show holdings for portfolio Garfield"


## References
- docs/architecture.png (optional diagram).
- docs/questions.txt (sample prompts).

## Author
- Amit Jaiswar