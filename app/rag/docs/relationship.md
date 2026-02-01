# Relationship Between Trades and Holdings

## The Core Relationship

**Trades** are transaction events → **Holdings** are position snapshots

```
Buy Trade (100 shares) 
    + Buy Trade (50 shares)
    - Sell Trade (30 shares)
    = Holding (120 shares)
```

Holdings represent the **cumulative effect** of all trades (plus corporate actions, transfers, etc.).

## Why Direct Joins Are Difficult

### 1. Many-to-One Mapping
- **Many trades** → **One holding position**
- A single holding row summarizes potentially hundreds of historical trades
- Individual trade details are "lost" in the aggregated position

### 2. Different Granularity
Trades have allocations at:
- `PortfolioName` + `SecurityId` + `CustodianName` + `AllocationId` level

Holdings aggregate at:
- `PortfolioName` + `SecurityId` + `CustodianName` + `StrategyRefShortName` level (approximately)

### 3. Time Dimension Missing
- Trades show when transactions occurred (though dates are NULL in this extract!)
- Holdings show state as of `AsOfDate`
- Cannot easily answer "which trades created this holding?" without transaction history

### 4. Corporate Actions & Adjustments
Holdings may reflect:
- Stock splits
- Dividends reinvested
- Transfers between custodians
- Manual adjustments

These events don't appear in the trades dataset.

## What CAN Be Joined

### Fuzzy Reconciliation
You can attempt to join on:
```sql
SELECT h.*, t.*
FROM holdings h
LEFT JOIN trades t ON h.SecurityId = t.SecurityId 
  AND h.PortfolioName = t.PortfolioName
  AND h.CustodianName = t.CustodianName
WHERE h.CloseDate IS NULL
```

**But this will:**
- Return multiple trade rows per holding (one-to-many)
- Not prove causation (trade → holding)
- Miss trades that were later sold out (holding closed)

### Validation Check: Net Quantity
Compare net traded quantity vs current holding:
```sql
WITH net_trades AS (
  SELECT PortfolioName, SecurityId,
    SUM(CASE WHEN TradeTypeName = 'Buy' THEN AllocationQTY 
             WHEN TradeTypeName = 'Sell' THEN -AllocationQTY END) as NetQty
  FROM trades
  GROUP BY PortfolioName, SecurityId
),
holdings_qty AS (
  SELECT PortfolioName, SecurityId, SUM(Qty) as HoldingQty
  FROM holdings
  WHERE CloseDate IS NULL
  GROUP BY PortfolioName, SecurityId
)
SELECT nt.PortfolioName, nt.SecurityId, nt.NetQty, hq.HoldingQty,
  (hq.HoldingQty - nt.NetQty) as Difference
FROM net_trades nt
FULL OUTER JOIN holdings_qty hq 
  ON nt.PortfolioName = hq.PortfolioName AND nt.SecurityId = hq.SecurityId
WHERE ABS(hq.HoldingQty - nt.NetQty) > 0.01  -- Allow small rounding
```

**Expected**: Differences indicate:
- Trades before the holdings extract period
- Corporate actions
- Data extraction timing mismatches

## Common Questions & Answers

### Q: "Show me all trades for this holding"
**Answer**: Cannot definitively answer. Can show trades with matching Portfolio + Security + Custodian, but cannot prove causation without transaction dates.

### Q: "What was the average buy price for this position?"
**Answer**: Requires trade history with dates. With this extract (dates = NULL), cannot calculate accurately.

### Q: "Did portfolio X trade security Y?"
**Answer**: Yes, can answer by checking trades table:
```sql
SELECT * FROM trades 
WHERE PortfolioName = 'Garfield' AND SecurityId = 273482
```

### Q: "How much of this holding came from recent trades?"
**Answer**: Cannot answer - no valid trade dates in this extract.

## Best Practices for Analysis

### Do's
✅ Use holdings for "current state" questions (what do we own now?)
✅ Use trades for "activity" questions (how much trading happened?)
✅ Reconcile totals (net trades ≈ holdings) as a data quality check
✅ Group by Portfolio + Security for high-level comparison

### Don'ts
❌ Don't assume a trade "created" a specific holding row
❌ Don't join on dates (they're invalid in this extract)
❌ Don't expect perfect reconciliation (corporate actions exist)
❌ Don't use trades to calculate cost basis without proper dates

## Example: Portfolio Activity vs Position
**Question**: "Show me Garfield's MSFT activity and position"

**Answer**:
```sql
-- Current position
SELECT SUM(Qty) as CurrentQty, SUM(MV_Base) as CurrentMV
FROM holdings
WHERE PortfolioName = 'Garfield' AND SecurityId = 273482 AND CloseDate IS NULL;

-- Trading activity
SELECT TradeTypeName, COUNT(*) as NumTrades, SUM(AllocationQTY) as TotalQty
FROM trades
WHERE PortfolioName = 'Garfield' AND SecurityId = 273482
GROUP BY TradeTypeName;
```

**Interpretation**: 
- Position shows current state (e.g., 500 shares worth $X)
- Trades show activity (e.g., 3 buys totaling 800 shares, 2 sells totaling 300 shares → net +500)
- If net trades = current qty → clean reconciliation ✅
- If different → corporate actions or timing issues 🔍
