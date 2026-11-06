"""
Module: Sector-Aware Executive KPI Synthesizer (modules/eda_engine/kpi_synthesizer.py)
"""

import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry

PRIORITY_VALUE_KEYWORDS = (
    "revenue", "sales", "amount", "price", "total", "balance", "mrr", "cost", "profit"
)


@auto_log_telemetry(module_name="eda_engine")
def synthesize_executive_kpis(
    total_rows: int,
    numeric_stats: Dict[str, Dict[str, Any]],
    categorical_stats: Dict[str, Dict[str, Any]],
    sector_info: Dict[str, Any]
) -> Dict[str, Any]:
    primary_metric_col = None
    for kw in PRIORITY_VALUE_KEYWORDS:
        for col in numeric_stats.keys():
            if kw in col.lower() and "id" not in col.lower():
                primary_metric_col = col
                break
        if primary_metric_col:
            break

    if primary_metric_col is None:
        non_id_cols = [c for c in numeric_stats.keys() if "id" not in c.lower()]
        primary_metric_col = non_id_cols[0] if non_id_cols else (next(iter(numeric_stats.keys()), None))

    kpi_cards: List[Dict[str, Any]] = [
        {"label": "Total Records", "value": total_rows, "unit": "rows"},
        {
            "label": "Detected Sector",
            "value": sector_info.get("primary_sector", "GENERAL_TABULAR"),
            "unit": f"{int(sector_info.get('confidence', 0.0) * 100)}% conf"
        }
    ]

    if primary_metric_col and primary_metric_col in numeric_stats:
        st = numeric_stats[primary_metric_col]
        kpi_cards.append({"label": f"Total {primary_metric_col.title()}", "value": st["sum"], "unit": "sum"})
        kpi_cards.append({"label": f"Average {primary_metric_col.title()}", "value": st["mean"], "unit": "mean"})

    dominant_segment = None
    for col, cst in categorical_stats.items():
        if not cst.get("is_likely_id", False) and cst.get("top_values"):
            top_item = cst["top_values"][0]
            dominant_segment = {"column": col, "top_value": top_item["value"], "share_pct": top_item["percentage"]}
            kpi_cards.append({"label": f"Top {col.title()}", "value": top_item["value"], "unit": f"{top_item['percentage']}%"})
            break

    return {
        "sector": sector_info.get("primary_sector", "GENERAL_TABULAR"),
        "primary_metric_column": primary_metric_col,
        "dominant_segment": dominant_segment,
        "kpi_cards": kpi_cards
    }


if __name__ == "__main__":
    mock_num = {"order_id": {"sum": 15, "mean": 3.0}, "revenue": {"sum": 1250.5, "mean": 250.1}}
    mock_cat = {"category": {"is_likely_id": False, "top_values": [{"value": "Electronics", "percentage": 60.0}]}}
    mock_sector = {"primary_sector": "E_COMMERCE_RETAIL", "confidence": 0.85}
    kpis, _ = synthesize_executive_kpis(5, mock_num, mock_cat, mock_sector)
    assert kpis["primary_metric_column"] == "revenue" and len(kpis["kpi_cards"]) == 5
    print("✅ STEP 28 PASSED: Executive KPI Synthesizer verified!")
