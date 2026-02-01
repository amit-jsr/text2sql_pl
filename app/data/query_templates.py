"""
SQL query templates for common dataset questions.
Provides safe, parameterized queries with validation.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum


class QueryTemplate(str, Enum):
    """Available query templates."""
    COUNT_TRADES_BY_PORTFOLIO = "count_trades_by_portfolio"
    TOP_HOLDINGS_BY_MV = "top_holdings_by_mv"
    PNL_BY_PORTFOLIO = "pnl_by_portfolio"
    NET_TRADED_QTY_BY_SECURITY = "net_traded_qty_by_security"
    PORTFOLIO_SUMMARY = "portfolio_summary"
    TRADES_FOR_SECURITY = "trades_for_security"
    HOLDINGS_FOR_PORTFOLIO = "holdings_for_portfolio"
    LARGEST_TRADES = "largest_trades"
    UNIQUE_SECURITIES = "unique_securities"
    ALLOCATION_SUMMARY = "allocation_summary"


@dataclass(frozen=True)
class SQLTemplate:
    """SQL template with metadata."""
    template: str
    description: str
    parameters: List[str]
    example_params: Dict[str, Any]


# Template definitions
TEMPLATES: Dict[QueryTemplate, SQLTemplate] = {
    
    QueryTemplate.COUNT_TRADES_BY_PORTFOLIO: SQLTemplate(
        template="""
            SELECT PortfolioName, 
                   COUNT(DISTINCT id) as NumTrades,
                   SUM(AllocationQTY) as TotalQty,
                   SUM(ABS(AllocationCash)) as TotalValue
            FROM trades
            GROUP BY PortfolioName
            ORDER BY NumTrades DESC
        """,
        description="Count trades grouped by portfolio",
        parameters=[],
        example_params={}
    ),
    
    QueryTemplate.TOP_HOLDINGS_BY_MV: SQLTemplate(
        template="""
            SELECT PortfolioName, SecurityId,
                   Qty,
                   MV_Base
            FROM holdings
            ORDER BY MV_Base DESC
            LIMIT {limit}
        """,
        description="Top holdings by market value",
        parameters=["limit"],
        example_params={"limit": 10}
    ),
    
    QueryTemplate.PNL_BY_PORTFOLIO: SQLTemplate(
        template="""
            SELECT PortfolioName,
                   SUM(PL_YTD) as YTD_PL,
                   SUM(PL_MTD) as MTD_PL,
                   SUM(PL_DTD) as OneDayPL,
                   SUM(MV_Base) as CurrentMV
            FROM holdings
            GROUP BY PortfolioName
            ORDER BY YTD_PL DESC
        """,
        description="P&L summary by portfolio",
        parameters=[],
        example_params={}
    ),
    
    QueryTemplate.NET_TRADED_QTY_BY_SECURITY: SQLTemplate(
        template="""
            SELECT SecurityId, Name, SecurityType,
                   SUM(CASE WHEN TradeTypeName = 'Buy' THEN AllocationQTY 
                            WHEN TradeTypeName = 'Sell' THEN -AllocationQTY 
                            ELSE 0 END) as NetQty,
                   COUNT(DISTINCT id) as NumTrades
            FROM trades
            GROUP BY SecurityId, Name, SecurityType
            ORDER BY ABS(NetQty) DESC
            LIMIT {limit}
        """,
        description="Net traded quantity by security (buys - sells)",
        parameters=["limit"],
        example_params={"limit": 20}
    ),
    
    QueryTemplate.PORTFOLIO_SUMMARY: SQLTemplate(
        template="""
            SELECT PortfolioName,
                   COUNT(DISTINCT SecurityId) as NumSecurities,
                   COUNT(*) as NumPositions,
                   SUM(MV_Base) as TotalMV,
                   SUM(PL_YTD) as YTD_PL
            FROM holdings
            GROUP BY PortfolioName
            ORDER BY TotalMV DESC
        """,
        description="Portfolio summary with counts and totals",
        parameters=[],
        example_params={}
    ),
    
    QueryTemplate.TRADES_FOR_SECURITY: SQLTemplate(
        template="""
            SELECT id, TradeTypeName, PortfolioName, AllocationQTY, 
                   Price, AllocationCash, Counterparty
            FROM trades
            WHERE SecurityId = {security_id}
            ORDER BY id DESC
            LIMIT {limit}
        """,
        description="Trades for a specific security",
        parameters=["security_id", "limit"],
        example_params={"security_id": 273482, "limit": 50}
    ),
    
    QueryTemplate.HOLDINGS_FOR_PORTFOLIO: SQLTemplate(
        template="""
            SELECT SecurityId, 
                   Qty,
                   MV_Base,
                   PL_YTD as YTD_PL
            FROM holdings
            WHERE PortfolioName = '{portfolio_name}'
            ORDER BY MV_Base DESC
        """,
        description="Holdings for a specific portfolio",
        parameters=["portfolio_name"],
        example_params={"portfolio_name": "Garfield"}
    ),
    
    QueryTemplate.LARGEST_TRADES: SQLTemplate(
        template="""
            SELECT id, TradeTypeName, Name, SecurityType,
                   Quantity, Price, Principal, TotalCash, PortfolioName
            FROM trades
            ORDER BY ABS(Principal) DESC
            LIMIT {limit}
        """,
        description="Largest trades by principal amount",
        parameters=["limit"],
        example_params={"limit": 20}
    ),
    
    QueryTemplate.UNIQUE_SECURITIES: SQLTemplate(
        template="""
            SELECT COUNT(DISTINCT SecurityId) as UniqueSecurities,
                   COUNT(DISTINCT CASE WHEN CloseDate IS NULL THEN SecurityId END) as OpenSecurities,
                   SecurityTypeName
            FROM holdings
            GROUP BY SecurityTypeName
            ORDER BY UniqueSecurities DESC
        """,
        description="Count unique securities by type",
        parameters=[],
        example_params={}
    ),
    
    QueryTemplate.ALLOCATION_SUMMARY: SQLTemplate(
        template="""
            SELECT AllocationRule,
                   COUNT(*) as NumAllocations,
                   SUM(ABS(AllocationCash)) as TotalValue,
                   SUM(CASE WHEN IsCustomAllocation = 1 THEN 1 ELSE 0 END) as CustomCount
            FROM trades
            GROUP BY AllocationRule
            ORDER BY TotalValue DESC
        """,
        description="Summary of allocation rules used",
        parameters=[],
        example_params={}
    ),
}


def get_template(template_name: QueryTemplate) -> SQLTemplate:
    """Get a template by name."""
    return TEMPLATES[template_name]


def render_template(template_name: QueryTemplate, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Render a SQL template with parameters.
    
    Args:
        template_name: Template to use
        params: Parameter values (uses example values if None)
    
    Returns:
        Rendered SQL string
    """
    template_obj = TEMPLATES[template_name]
    
    if params is None:
        params = template_obj.example_params
    
    # Validate all required parameters are present
    missing = set(template_obj.parameters) - set(params.keys())
    if missing:
        raise ValueError(f"Missing required parameters: {missing}")
    
    # Render template
    sql = template_obj.template.format(**params)
    
    return sql.strip()


def list_templates() -> Dict[str, str]:
    """List all available templates with descriptions."""
    return {
        name.value: template.description
        for name, template in TEMPLATES.items()
    }


if __name__ == "__main__":
    """Test template rendering."""
    print("Available SQL Templates:")
    print("=" * 60)
    
    for name, desc in list_templates().items():
        print(f"\n{name}:")
        print(f"  {desc}")
        
        # Render with example params
        template = QueryTemplate(name)
        sql = render_template(template)
        print(f"\n  Example SQL:")
        for line in sql.split("\n")[:5]:
            print(f"    {line}")
        if sql.count("\n") > 5:
            print("    ...")
