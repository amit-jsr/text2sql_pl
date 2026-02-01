
import duckdb
from dataclasses import dataclass

@dataclass(frozen=True)
class DuckDBConfig:
    db_path: str = ":memory:"

class DuckDBClient:
    def __init__(self, cfg: DuckDBConfig):
        self.conn = duckdb.connect(cfg.db_path)

    def init_views(self, trades_csv_path: str, holdings_csv_path: str) -> None:
        self.conn.execute(f"CREATE OR REPLACE VIEW trades AS SELECT * FROM read_csv_auto('{trades_csv_path}')")
        self.conn.execute(f"CREATE OR REPLACE VIEW holdings AS SELECT * FROM read_csv_auto('{holdings_csv_path}')")

    def query_df(self, sql: str):
        return self.conn.execute(sql).df()
    
    def execute(self, sql: str):
        """Execute SQL and return results in dict format."""
        try:
            result = self.conn.execute(sql).fetchall()
            columns = [desc[0] for desc in self.conn.description]
            return {
                'columns': columns,
                'rows': result,
                'row_count': len(result)
            }
        except Exception as e:
            return {
                'error': str(e),
                'columns': [],
                'rows': [],
                'row_count': 0
            }
