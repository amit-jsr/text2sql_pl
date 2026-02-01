# 1. Data Assistant

A text-to-SQL chatbot for querying holdings and trades data with natural language.

## Quick Start

```bash
# 1. Setup (one-time)
./setup.sh

# 2. Launch the application
chainlit run run.py -w
```

The application opens automatically at http://localhost:8000

## Features

- **Natural Language to SQL** - Ask questions in plain English, get SQL results
- **Data Analysis** - View holdings, market values, and positions
- **Trade History** - Explore transaction data and allocations
- **Conversation Memory** - Follow-up questions with context

## Example Questions

- "How many trades per portfolio?"
- "Top 10 holdings by market value"
- "Show me holdings for portfolio Garfield"
- "Total market value by security type"
- "Largest trades"

## Configuration

Configure an LLM provider in `.env` for SQL generation:

```bash
LLM_BACKEND=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
```

## Support

For questions or issues, please contact your administrator.

---

# 2. Implementation Documentation

## Overview

A single-channel text-to-SQL chatbot. All questions are converted to SQL queries.

**Architecture:** `Question → Guardrails → SQL → DuckDB → Results`

---

## Architecture

```
┌───────────────────────────────────────────────────┐
│              Chainlit UI (run.py)                 │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│              Input Guardrails                     │
│         (safety.py)                               │
│   Block: hate speech, explicit, harmful requests │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│              Request Handler                      │
│         (request_handler.py)                      │
│   Greeting Check → SQL Generation → Execution    │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│              Query Planner                        │
│   Templates (fast) → LLM Fallback (flexible)     │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│              DuckDB Engine                        │
│         CSV files loaded as views                 │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌──────────────────────┐
│  CSV Datasets        │
│  holdings.csv        │
│  trades.csv          │
└──────────────────────┘
```

---

## Project Structure

```
text2sql/
├── run.py                    # Main Chainlit app
├── setup.sh                  # Setup script
├── requirements.txt          # Dependencies
├── .env                      # Configuration (create from .env.example)
│
├── app/
│   ├── data/                 # Data layer
│   │   ├── duckdb_client.py  # Database connection
│   │   ├── query_planner.py  # NL → SQL planning
│   │   ├── query_templates.py# Pre-defined SQL templates
│   │   ├── sql_tools.py      # SQL validation & execution
│   │   └── dataset/
│   │       ├── holdings.csv
│   │       └── trades.csv
│   │
│   ├── llm/                  # LLM integration
│   │   ├── config.py         # LLM configuration
│   │   └── text_to_sql.py    # LLM SQL generation
│   │
│   ├── orchestrator/         # Request handling
│   │   ├── request_handler.py# Single-channel handler
│   │   └── safety.py         # SQL injection prevention
│   │
│   └── rag/                  # (Optional) Documentation
│       └── docs/             # Markdown docs
│
└── tests/
    ├── test_system.py
    ├── test_llm.py
    └── test_text_to_sql.py
```

---

## Core Components

### 1. Request Handler (`app/orchestrator/request_handler.py`)

Single entry point for all queries:
- Greetings → Simple response
- Everything else → SQL generation → Execution

### 2. Query Planner (`app/data/query_planner.py`)

Two-tier approach:
1. **Template Matching** - Fast regex patterns for common queries
2. **LLM Fallback** - Text-to-SQL for complex questions

### 3. DuckDB Client (`app/data/duckdb_client.py`)

```python
class DuckDBClient:
    def init_views(trades_csv, holdings_csv)  # Load CSVs as views
    def execute(sql) -> Dict                  # Run query
```

---

## Database Schema

### Holdings Table
| Column | Type | Description |
|--------|------|-------------|
| PortfolioName | TEXT | Portfolio name |
| SecurityId | INTEGER | Security ID |
| SecName | TEXT | Security name |
| SecurityTypeName | TEXT | Bond, Equity, etc. |
| Qty | DOUBLE | Quantity held |
| Price | DOUBLE | Current price |
| MV_Base | DOUBLE | Market value (USD) |
| PL_YTD | DOUBLE | Year-to-date P&L |
| PL_MTD | DOUBLE | Month-to-date P&L |
| PL_DTD | DOUBLE | Day-to-date P&L |

### Trades Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Trade ID |
| PortfolioName | TEXT | Portfolio name |
| SecurityId | INTEGER | Security ID |
| TradeTypeName | TEXT | Buy/Sell |
| Quantity | DOUBLE | Trade quantity |
| Price | DOUBLE | Trade price |
| Principal | DOUBLE | Principal amount |
| AllocationQTY | DOUBLE | Allocated quantity |

> ⚠️ `TradeDate` and `SettleDate` columns have invalid data - avoid using them.

---

## Query Templates

Pre-defined templates in `query_templates.py`:

| Template | Trigger Patterns |
|----------|-----------------|
| `COUNT_TRADES_BY_PORTFOLIO` | "how many trades per portfolio" |
| `TOP_HOLDINGS_BY_MV` | "top 10 holdings" |
| `PNL_BY_PORTFOLIO` | "p&l by portfolio" |
| `HOLDINGS_FOR_PORTFOLIO` | "holdings for Garfield" |
| `LARGEST_TRADES` | "largest trades" |

---

## Configuration

### Environment Variables (`.env`)

```bash
# LLM Configuration (OpenAI recommended)
LLM_BACKEND=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o

# Alternative: Groq (free tier)
# LLM_BACKEND=groq
# GROQ_API_KEY=your_api_key
# GROQ_MODEL=llama-3.3-70b-versatile
```
 # Data Assistant

A text-to-SQL chatbot for querying holdings and trades data with natural language.

## Quick Start

 # Data Assistant

A text-to-SQL chatbot for querying holdings and trades data with natural language.

## Quick Start

```bash
# One-time setup
./setup.sh

# Launch the application (opens at http://localhost:8000)
chainlit run run.py -w
```

## Features

- Natural language → SQL
- Data analysis: holdings, market values, positions
- Trade history and allocations
- Conversation memory for follow-ups

## Example Questions

- How many trades per portfolio?
- Top 10 holdings by market value
- Show holdings for portfolio Garfield
- Total market value by security type
- Largest trades

## Configuration

Configure an LLM provider in `.env` for SQL generation:

```bash
LLM_BACKEND=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
```

For an alternative provider (example):

```bash
# LLM_BACKEND=groq
# GROQ_API_KEY=your_key_here
# GROQ_MODEL=llama-3.3-70b-versatile
```

---

## Implementation Documentation

### Overview

Single-channel text-to-SQL chatbot: Question → Guardrails → SQL → DuckDB → Results

### Architecture

```
┌───────────────────────────────────────────────────┐
│              Chainlit UI (run.py)                 │
└─────────────────────┬─────────────────────────────┘
                 │
                 ▼
┌───────────────────────────────────────────────────┐
│              Input Guardrails (safety.py)         │
│  Blocks abusive, explicit, or harmful requests    │
└─────────────────────┬─────────────────────────────┘
                 │
                 ▼
┌───────────────────────────────────────────────────┐
│             Request Handler (request_handler.py)  │
│           Greeting check → SQL generation → exec  │
└─────────────────────┬─────────────────────────────┘
                 │
                 ▼
┌───────────────────────────────────────────────────┐
│               Query Planner                        │
│        Templates (fast) → LLM fallback (flexible) │
└─────────────────────┬─────────────────────────────┘
                 │
                 ▼
┌───────────────────────────────────────────────────┐
│                 DuckDB engine                      │
│             CSV datasets loaded as views           │
└─────────────────────┴─────────────────────────────┘
```

### Project Structure (key files)

```
text2sql/
├── run.py                    # Chainlit entrypoint
├── setup.sh                  # Setup script
├── requirements.txt
├── .env (create from .env.example)
└── app/
   ├── data/                 # DB & query planning
   │   ├── duckdb_client.py
   │   ├── query_planner.py
   │   ├── query_templates.py
   │   └── dataset/ (holdings.csv, trades.csv)
   ├── llm/                  # LLM integration
   │   ├── config.py
   │   └── text_to_sql.py
   └── orchestrator/         # Request handling & safety
      ├── request_handler.py
      └── safety.py
```

### Core components

- Request handler: greeting detection, dispatch to planner
- Query planner: template matching, then LLM fallback
- DuckDB client: loads CSVs as views and executes SQL

Example DuckDB client interface:

```python
class DuckDBClient:
   def init_views(trades_csv, holdings_csv):
      """Load CSVs as views"""

   def execute(sql) -> dict:
      """Run query and return results"""
```

### Database schema (summary)

Holdings (columns): PortfolioName, SecurityId, SecName, SecurityTypeName, Qty, Price, MV_Base, PL_YTD, PL_MTD, PL_DTD

Trades (columns): id, PortfolioName, SecurityId, TradeTypeName, Quantity, Price, Principal, AllocationQTY

Note: TradeDate and SettleDate contain invalid data and should be avoided.

### Query templates

Common templates (see `app/data/query_templates.py`):

- COUNT_TRADES_BY_PORTFOLIO — "how many trades per portfolio"
- TOP_HOLDINGS_BY_MV — "top 10 holdings"
- PNL_BY_PORTFOLIO — "p&l by portfolio"
- HOLDINGS_FOR_PORTFOLIO — "holdings for Garfield"
- LARGEST_TRADES — "largest trades"

### Request flow (single channel)

User question → greeting check → query planner (template or LLM) → sql_tools (safety checks) → duckdb_client.execute → results

### File execution order (startup)

1. `run.py` — Chainlit app
2. `app/orchestrator/request_handler.py` — processes messages
3. `app/data/duckdb_client.py` — initialize DB views

---

## Extending

To add a query template:

1. Add to `QueryTemplate` enum in `app/data/query_templates.py`.
2. Define the SQL template in the `TEMPLATES` mapping.
3. Add regex trigger patterns in `QueryPlanner.PATTERNS`.

## Testing

Run tests:

```bash
python -m pytest tests/test_text_to_sql.py tests/test_system.py
```

---

*Last Updated: January 2026*
