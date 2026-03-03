"""
View 14 — Cost Dashboard
Track all API costs across the InstaHotel pipeline.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.services.cost_tracker import fetch_cost_summary, fetch_costs

sidebar_css()
page_title("Cost Dashboard", "Track API spend across all tools")

# ---------------------------------------------------------------------------
# Time range selector
# ---------------------------------------------------------------------------
days = st.selectbox("Time range", [7, 14, 30, 90], index=2, format_func=lambda d: f"Last {d} days")

summary = fetch_cost_summary(days=days)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
st.markdown("### Overview")
k1, k2, k3 = st.columns(3)

total = summary["total_usd"]
tool_count = len(summary["by_tool"])
call_count = sum(v["count"] for v in summary["by_tool"].values())

k1.metric("Total Spend", f"${total:.2f}")
k2.metric("API Calls", f"{call_count:,}")
k3.metric("Tools Used", tool_count)

# ---------------------------------------------------------------------------
# Cost by tool breakdown
# ---------------------------------------------------------------------------
st.markdown("### Cost by Tool")

if summary["by_tool"]:
    # Sort by total cost descending
    sorted_tools = sorted(summary["by_tool"].items(), key=lambda x: x[1]["total_usd"], reverse=True)

    for tool_name, data in sorted_tools:
        pct = (data["total_usd"] / total * 100) if total > 0 else 0
        col_name, col_calls, col_cost, col_bar = st.columns([2, 1, 1, 4])
        col_name.markdown(f"**{tool_name}**")
        col_calls.markdown(f"{data['count']} calls")
        col_cost.markdown(f"${data['total_usd']:.4f}")
        col_bar.progress(min(pct / 100, 1.0), text=f"{pct:.1f}%")
else:
    st.info("No cost data yet. Costs are logged automatically when you use AI tools.")

# ---------------------------------------------------------------------------
# Recent calls table
# ---------------------------------------------------------------------------
st.markdown("### Recent API Calls")

# Tool filter
all_tools = ["All"] + sorted(summary["by_tool"].keys())
tool_filter = st.selectbox("Filter by tool", all_tools)

if tool_filter == "All":
    rows = fetch_costs(days=days, limit=100)
else:
    rows = fetch_costs(days=days, tool=tool_filter, limit=100)

if rows:
    # Format for display
    display_rows = []
    for r in rows:
        params = r.get("params") or {}
        if isinstance(params, str):
            import json
            params = json.loads(params)
        source = params.get("source", "estimate")
        source_label = {"real_tokens": "Real", "real_balance": "Real",
                        "real_metrics": "Real", "estimate": "Est."}.get(source, source)
        predict_time = params.get("predict_time")
        display_rows.append({
            "Time": r.get("created_at", "")[:19].replace("T", " "),
            "Tool": r.get("tool", ""),
            "Operation": r.get("operation", ""),
            "Cost ($)": f"{float(r.get('cost_usd', 0)):.4f}",
            "Source": source_label,
            "Model": r.get("model", "—"),
            "Tokens In": r.get("input_tokens") or "—",
            "Tokens Out": r.get("output_tokens") or "—",
            "Runtime": f"{predict_time:.1f}s" if predict_time else "—",
        })
    st.dataframe(display_rows, use_container_width=True, hide_index=True)
else:
    st.info("No API calls recorded in this period.")
