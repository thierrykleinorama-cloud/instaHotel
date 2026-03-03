"""
Persistent cost logging for all paid API calls.
Every API call writes to the cost_log table for tracking and dashboards.
"""
from datetime import datetime, timezone
from typing import Optional

from src.database import get_supabase, TABLE_COST_LOG


def log_cost(
    tool: str,
    operation: str,
    cost_usd: float,
    model: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    params: Optional[dict] = None,
) -> None:
    """Log an API cost to the database. Fire-and-forget (never raises)."""
    try:
        row = {
            "tool": tool,
            "operation": operation,
            "cost_usd": round(cost_usd, 6),
        }
        if model:
            row["model"] = model
        if input_tokens is not None:
            row["input_tokens"] = input_tokens
        if output_tokens is not None:
            row["output_tokens"] = output_tokens
        if params:
            row["params"] = params
        get_supabase().table(TABLE_COST_LOG).insert(row).execute()
    except Exception:
        pass  # never block the main flow


def fetch_costs(
    days: int = 30,
    tool: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """Fetch recent cost log entries."""
    client = get_supabase()
    cutoff = datetime.now(timezone.utc).isoformat()
    query = (
        client.table(TABLE_COST_LOG)
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if tool:
        query = query.eq("tool", tool)
    return query.execute().data


def fetch_cost_summary(days: int = 30) -> dict:
    """Fetch aggregated cost summary grouped by tool.

    Returns: {total_usd, by_tool: {tool: {count, total_usd}}, recent: [...top 20]}
    """
    rows = fetch_costs(days=days, limit=1000)

    total = 0.0
    by_tool: dict[str, dict] = {}
    for r in rows:
        cost = float(r.get("cost_usd", 0))
        total += cost
        tool = r.get("tool", "unknown")
        if tool not in by_tool:
            by_tool[tool] = {"count": 0, "total_usd": 0.0}
        by_tool[tool]["count"] += 1
        by_tool[tool]["total_usd"] += cost

    return {
        "total_usd": round(total, 4),
        "by_tool": {k: {"count": v["count"], "total_usd": round(v["total_usd"], 4)} for k, v in by_tool.items()},
        "recent": rows[:20],
    }
