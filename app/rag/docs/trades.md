# Trades Dataset Documentation

## Overview
The **Trades** dataset represents **transaction events** - individual buy and sell orders with their allocations to portfolios. It is an **event-based** dataset showing trading activity.

## Key Columns

### Trade Identifiers
- **id**: Unique trade ID
- **RevisionId**: Version number if trade was amended (higher = more recent)
- **AllocationId**: Unique allocation record ID (one trade can have multiple allocations)

### Trade Type
- **TradeTypeName**: "Buy" or "Sell"

### Security Details
- **SecurityId**: Internal security identifier (links to holdings)
- **SecurityType**: Type of security (Equity, Bond, Option, AssetBacked, etc.)
- **Name**: Security description
- **Ticker**: Stock ticker (may be NULL for bonds)
- **CUSIP**: CUSIP identifier (may be NULL)
- **ISIN**: ISIN identifier (may be NULL)

### Trade Dates
- **TradeDate**: Date trade was executed
- **SettleDate**: Settlement date

**⚠️ CRITICAL CAVEAT**: In this extract, `TradeDate` and `SettleDate` appear as `00:00.0` for ALL rows. This is a data extraction issue. These are not actual dates and cannot be used for time-series analysis.

### Trade Economics
- **Quantity**: Total quantity traded at parent trade level
- **Price**: Execution price
- **TradeFXRate**: FX rate for currency conversion (may be NULL if base currency)
- **Principal**: Gross amount = `Quantity * Price`
- **Interest**: Accrued interest (relevant for bonds)
- **TotalCash**: Total cash exchanged = `Principal + Interest + Fees`

### Allocation (Portfolio Assignment)
Each trade is allocated to one or more portfolios:

- **AllocationQTY**: Quantity allocated to this portfolio
- **AllocationPrincipal**: Principal allocated to this portfolio
- **AllocationInterest**: Interest allocated to this portfolio
- **AllocationFees**: Fees allocated to this portfolio
- **AllocationCash**: Total cash for this allocation = `AllocationPrincipal + AllocationInterest + AllocationFees`

### Allocation Details
- **PortfolioName**: Portfolio receiving this allocation (e.g., "HoldCo 1", "Redfield Accu-Fund")
- **CustodianName**: Custodian for this allocation (e.g., "JP MORGAN SECURITIES LLC", "Goldman Sachs International")
- **StrategyName**: Top-level strategy (usually "Default")
- **Strategy1Name**: Level 1 strategy (e.g., "Asset", "ClientA")
- **Strategy2Name**: Level 2 strategy (e.g., "DefaultS2")
- **Counterparty**: Trading counterparty (often "ABGS", "JPHQ", "Internal")

### Allocation Rules
- **AllocationRule**: Rule used to split trade across portfolios (e.g., "Single Fund Rule - HoldCo 1", "STANDARD PERCENTAGE")
- **IsCustomAllocation**: Boolean flag (0 = standard rule, 1 = custom allocation)

## Important Caveats

### Date Limitations
**Do NOT rely on TradeDate or SettleDate** in this extract - they are placeholder values (`00:00.0`) and do not represent actual dates.

### Multiple Allocations
A single trade (same `id`) can have **multiple rows** if allocated to multiple portfolios:
- Sum of `AllocationQTY` across rows with same `id` = `Quantity`
- Sum of `AllocationCash` across rows with same `id` ≈ `TotalCash` (minor rounding)

### Revisions
Trades can be amended (cancellations, corrections):
- Higher `RevisionId` = more recent version
- For accurate analysis, filter to latest revision per trade ID

### Fees vs Principal
- **AllocationFees** can be positive (you pay) or negative (you receive rebate)
- For Buys: `AllocationCash` > 0 (cash outflow)
- For Sells: `AllocationCash` may be negative in some systems (cash inflow)

## Common Queries

### Count Trades by Portfolio
```sql
SELECT PortfolioName, COUNT(DISTINCT id) as NumTrades, SUM(AllocationQTY) as TotalQty
FROM trades
GROUP BY PortfolioName
ORDER BY NumTrades DESC
```

### Net Traded Quantity by Security
To see net buy/sell activity:
```sql
SELECT SecurityId, Name, 
  SUM(CASE WHEN TradeTypeName = 'Buy' THEN AllocationQTY ELSE -AllocationQTY END) as NetQty
FROM trades
GROUP BY SecurityId, Name
ORDER BY ABS(NetQty) DESC
```

### Largest Trades
To find biggest transactions:
```sql
SELECT id, TradeTypeName, Name, Quantity, Principal, TotalCash
FROM trades
GROUP BY id, TradeTypeName, Name, Quantity, Principal, TotalCash
ORDER BY ABS(Principal) DESC
LIMIT 20
```

### Allocation Summary
To understand how trades are split:
```sql
SELECT AllocationRule, COUNT(*) as NumAllocations, SUM(AllocationCash) as TotalCash
FROM trades
GROUP BY AllocationRule
ORDER BY TotalCash DESC
```

## Relationship to Holdings
Trades are the **inputs** that create holdings. Multiple trades over time accumulate into a holding position.

- A **Buy trade** increases `Qty` in holdings
- A **Sell trade** decreases `Qty` in holdings
- Net of all trades = current holding (approximately, excluding corporate actions)

**Key**: Cannot directly join on simple keys - see `relationship.md` for reconciliation logic.
