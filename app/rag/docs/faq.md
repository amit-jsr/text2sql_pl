# Frequently Asked Questions (FAQ)

## Data Quality & Limitations

### Q: Why are TradeDate and SettleDate showing "00:00.0"?
**A**: This is a data extraction artifact. The dates were not properly exported from the source system. **Do not use these fields for any time-based analysis.** This means you cannot:
- Calculate time-weighted returns
- Filter trades by date range
- Determine trade sequencing
- Calculate average holding periods

**Workaround**: If you need trade timing, request a corrected extract with proper date values.

---

### Q: Why do some holdings have MV_Base = 0?
**A**: This can occur when:
- **Price = 0**: Security has expired (e.g., out-of-the-money options)
- **Qty = 0**: Position was closed but row exists for historical tracking
- **Data timing**: Pricing data not available at AsOfDate

**Check**: Look at `CloseDate` - if not NULL, position is closed and zero value is expected.

---

### Q: Can I calculate P&L from trades?
**A**: Not reliably with this extract because:
- Trade dates are invalid (cannot match buy/sell pairs)
- Corporate actions aren't captured in trades
- FX rates in trades may differ from holdings

**Better approach**: Use the P&L columns in holdings (PL_YTD, PL_MTD, etc.) which are pre-calculated by the source system.

---

## Schema & Column Questions

### Q: What's the difference between Principal and TotalCash in trades?
**A**: 
- **Principal**: Base transaction amount = `Quantity × Price`
- **Interest**: Accrued interest (bonds) or dividend (equities) - typically for bond trades
- **Fees**: Commissions, exchange fees, etc.
- **TotalCash**: Full cash impact = `Principal + Interest + Fees`

**Example**: Buying a bond for $1,000,000 might have:
- Principal: $1,000,000
- Interest: $5,000 (accrued)
- Fees: $200
- TotalCash: $1,005,200 (total paid)

---

### Q: What does "AllocationQTY" mean?
**A**: When a trade is executed, it can be allocated (split) across multiple portfolios. 

**Example**: A trader executes a single 10,000 share buy order, then allocates:
- 6,000 shares → Portfolio A (AllocationQTY = 6000)
- 4,000 shares → Portfolio B (AllocationQTY = 4000)

This creates **2 rows** in the trades table with the same `id` but different `AllocationId`.

---

### Q: Why are there multiple rows for the same portfolio + security in holdings?
**A**: Holdings can be fragmented by:
- **Custodian**: Same security held at different prime brokers
- **Strategy**: Different strategy allocations within a portfolio
- **Tax lots**: Separate purchase lots (though this extract doesn't show lot detail)

**To get total position**, always `SUM(Qty)` grouped by Portfolio + Security.

---

### Q: What's the difference between Strategy1RefShortName and Strategy2RefShortName?
**A**: These represent a **hierarchy** of strategy classifications:
- **StrategyRefShortName**: Top level (often "Default")
- **Strategy1RefShortName**: Mid level (e.g., "Asset", "ClientA")
- **Strategy2RefShortName**: Granular level (e.g., "DefaultS2")

**Purpose**: Allows multi-dimensional reporting (by client, by asset class, by sub-strategy).

**Common pattern**: 
- Strategy1 = Client segment or asset type
- Strategy2 = Risk classification or sub-account

---

## Common Analysis Patterns

### Q: How do I find the top 10 holdings across all portfolios?
**A**: 
```sql
SELECT PortfolioName, SecName, SUM(MV_Base) as TotalMV
FROM holdings
WHERE CloseDate IS NULL
GROUP BY PortfolioName, SecName
ORDER BY TotalMV DESC
LIMIT 10
```

**Key**: 
- Filter `CloseDate IS NULL` to exclude closed positions
- Group by Portfolio + Security (not individual rows)
- Use `MV_Base` for consistent currency comparison

---

### Q: How do I calculate net traded quantity by security?
**A**:
```sql
SELECT SecurityId, Name,
  SUM(CASE WHEN TradeTypeName = 'Buy' THEN AllocationQTY ELSE -AllocationQTY END) as NetQty,
  COUNT(DISTINCT id) as NumTrades
FROM trades
GROUP BY SecurityId, Name
ORDER BY ABS(NetQty) DESC
```

**Key**: Buys are positive, Sells are negative. Net = Buys - Sells.

---

### Q: How do I see P&L by portfolio?
**A**:
```sql
SELECT PortfolioName,
  SUM(PL_YTD) as YTD_PL,
  SUM(PL_MTD) as MTD_PL,
  SUM(MV_Base) as CurrentMV
FROM holdings
WHERE CloseDate IS NULL
GROUP BY PortfolioName
ORDER BY YTD_PL DESC
```

**Note**: P&L in holdings is **unrealized** (mark-to-market). Realized P&L would require closed positions and sale proceeds.

---

### Q: How many unique securities are held?
**A**:
```sql
SELECT COUNT(DISTINCT SecurityId) as UniqueSecurities
FROM holdings
WHERE CloseDate IS NULL
```

---

### Q: Which portfolios traded the most?
**A**:
```sql
SELECT PortfolioName, 
  COUNT(DISTINCT id) as NumTrades,
  SUM(ABS(AllocationCash)) as TotalTradedValue
FROM trades
GROUP BY PortfolioName
ORDER BY NumTrades DESC
```

**Note**: `ABS(AllocationCash)` treats buys and sells as equivalent activity volume.

---

## Data Reconciliation

### Q: Do trades sum to holdings?
**A**: Approximately, but not exactly. Expected differences:
- **Trades before extract period**: Holdings include positions opened before this trade extract
- **Corporate actions**: Stock splits, mergers not in trades
- **Timing**: Holdings as of AsOfDate, trades may be ongoing

**Reconciliation query**: See `relationship.md` for validation SQL.

---

### Q: What if I find a discrepancy?
**A**: Check:
1. **Custodian matching**: Are you comparing the same custodian?
2. **Closed positions**: Filter holdings to `CloseDate IS NULL`
3. **Aggregation**: Sum holdings by Portfolio + Security
4. **Revisions**: Use latest `RevisionId` in trades

**If still mismatched**: Likely a data extraction issue or corporate action - escalate to data provider.

---

## Technical Questions

### Q: Can I update the data?
**A**: The SQL layer has **safety guards** that block INSERT/UPDATE/DELETE. This is read-only analytics.

**If you need to modify**: Edit the source CSV files and restart the service.

---

### Q: Why is there a LIMIT on queries?
**A**: Safety mechanism to prevent accidental massive result sets. Default LIMIT = 200 rows.

**To get more**: Explicitly add `LIMIT` to your query (e.g., `LIMIT 1000`).

---

### Q: What database is this using?
**A**: **DuckDB** - an embedded analytical database optimized for analytics on CSV/Parquet files. Fast, local, no server needed.

---

## Asking Better Questions

### ✅ Good questions (RAG can answer):
- "What does MV_Base mean?"
- "How is AllocationCash calculated?"
- "What are the limitations of TradeDate?"
- "What's the relationship between trades and holdings?"

### ✅ Good questions (SQL can answer):
- "How many trades in portfolio Garfield?"
- "Top 10 holdings by MV_Base?"
- "Total YTD P&L by strategy?"
- "Which security has the most trades?"

### ❌ Questions that can't be answered (with this data):
- "What was the average holding period?" (no valid dates)
- "Show me intraday price movements" (no intraday data)
- "What's the cost basis?" (need trade dates + lot tracking)
- "Realized P&L from closed trades?" (need sale proceeds + cost basis)

---

## Getting Help

If you need:
- **Column definitions** → Ask about specific column names
- **Numeric answers** → I'll run SQL and show evidence
- **Relationship understanding** → Ask "how are X and Y related?"
- **Data caveats** → Ask "what are the limitations of X?"

**Example good prompts**:
- "Explain MV_Base vs MV_Local"
- "Count trades by portfolio and show top 5"
- "What's wrong with the trade dates?"
- "How do I reconcile trades to holdings?"
