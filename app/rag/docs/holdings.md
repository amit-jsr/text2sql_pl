# Holdings Dataset Documentation

## Overview
The **Holdings** dataset represents a **snapshot view** of portfolio positions at a specific point in time (`AsOfDate`). It is a **state-based** dataset showing what securities each portfolio holds.

## Key Columns

### Dates
- **AsOfDate**: The snapshot date for this holdings extract (format: DD/MM/YY)
- **OpenDate**: When the position was first opened (format: DD/MM/YY)
- **CloseDate**: When the position was closed, or `NULL` if still open

### Identifiers
- **ShortName**: Portfolio short name (e.g., "Garfield", "Heather")
- **PortfolioName**: Full portfolio name
- **SecurityId**: Unique security identifier (internal ID)
- **SecurityTypeName**: Type of security (Bond, Equity, AssetBacked, Option, etc.)
- **SecName**: Security name or identifier (CUSIP, ticker, or description)

### Strategy Hierarchy
- **StrategyRefShortName**: Top-level strategy (usually "Default")
- **Strategy1RefShortName**: Level 1 strategy classification (e.g., "Asset", "ClientA")
- **Strategy2RefShortName**: Level 2 strategy classification (e.g., "DefaultS2")

### Custodian
- **CustodianName**: Prime broker or custodian holding the securities (e.g., "Well Prime", "CS Prime", "JP MORGAN SECURITIES LLC")

### Position Details
- **DirectionName**: Position direction - typically "Long"
- **StartQty**: Quantity at start of period
- **Qty**: Current quantity held
- **StartPrice**: Price at start of period
- **Price**: Current price

### Currency & Valuation
- **StartFXRate**: FX rate at start of period (for non-base currency securities)
- **FXRate**: Current FX rate to convert to base currency
- **MV_Local**: Market Value in local (security) currency = `Qty * Price`
- **MV_Base**: Market Value in base currency = `MV_Local * FXRate`

### P&L (Profit & Loss)
- **PL_DTD**: Day-to-date P&L
- **PL_QTD**: Quarter-to-date P&L
- **PL_MTD**: Month-to-date P&L
- **PL_YTD**: Year-to-date P&L

**Note**: P&L figures reflect unrealized gains/losses on open positions.

## Important Caveats

### NULL Values
- **CloseDate = NULL**: Position is still open as of AsOfDate
- **MV_Local = 0 or Price = 0**: Some securities (especially new positions or expired options) may have zero valuations in the extract

### Duplicate Rows
Multiple rows can exist for the same portfolio + security combination if:
- Different custodians hold parts of the position
- Different strategy allocations exist
- Historical splits or transfers created separate sub-positions

### Data Quality Notes
- Some dates appear as truncated timestamps (e.g., "00:00.0") - these are data extraction artifacts
- AsOfDate in sample: 01/08/23 (August 1, 2023)
- Some FX rates = 1 (indicates base currency securities)

## Common Queries

### Top Holdings by Market Value
To find largest positions:
```sql
SELECT PortfolioName, SecName, SecurityTypeName, SUM(MV_Base) as TotalMV
FROM holdings
WHERE CloseDate IS NULL
GROUP BY PortfolioName, SecName, SecurityTypeName
ORDER BY TotalMV DESC
LIMIT 10
```

### Portfolio Summary
To get total exposure per portfolio:
```sql
SELECT PortfolioName, COUNT(*) as NumPositions, SUM(MV_Base) as TotalMV
FROM holdings
WHERE CloseDate IS NULL
GROUP BY PortfolioName
ORDER BY TotalMV DESC
```

### P&L Analysis
To see YTD performance:
```sql
SELECT PortfolioName, SecurityTypeName, SUM(PL_YTD) as YTD_PL
FROM holdings
WHERE CloseDate IS NULL
GROUP BY PortfolioName, SecurityTypeName
ORDER BY YTD_PL DESC
```

## Relationship to Trades
Holdings represent the **cumulative result** of trades over time. A single holding row's `Qty` is the net result of all buy/sell trades for that portfolio + security combination, plus any corporate actions.

**Key**: Holdings cannot be directly joined to Trades on a simple key. See `relationship.md` for details.
