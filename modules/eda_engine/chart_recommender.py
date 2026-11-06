"""
Module: Memory-Safe Visualization Spec Recommender (modules/eda_engine/chart_recommender.py)
"""

import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


@auto_log_telemetry(module_name="eda_engine")
def recommend_visualizations(
    numeric_stats: Dict[str, Dict[str, Any]],
    categorical_stats: Dict[str, Dict[str, Any]],
    distribution_stats: Dict[str, Dict[str, Any]],
    temporal_stats: Dict[str, Dict[str, Any]],
    correlation_report: Dict[str, Any]
) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []

    for col, cst in categorical_stats.items():
        if not cst.get("is_likely_id", False) and cst.get("top_values"):
            specs.append({
                "chart_type": "BAR_TOP_K",
                "title": f"Top Categories in '{col}'",
                "x_column": col,
                "y_label": "Count",
                "data": cst["top_values"]
            })

    for col, dst in distribution_stats.items():
        if "id" not in col.lower():
            specs.append({
                "chart_type": "HISTOGRAM_PREBINNED",
                "title": f"Distribution of '{col}' ({dst['shape_classification']})",
                "x_column": col,
                "y_label": "Frequency",
                "skewness": dst["skewness"],
                "data": dst["histogram"]
            })

    if temporal_stats and numeric_stats:
        time_col = next(iter(temporal_stats.keys()))
        metric_cols = [c for c in numeric_stats.keys() if "id" not in c.lower()]
        if metric_cols:
            specs.append({
                "chart_type": "TIME_SERIES_TREND",
                "title": f"{metric_cols[0].title()} Trend over {time_col}",
                "x_column": time_col,
                "y_column": metric_cols[0],
                "granularity": temporal_stats[time_col]["inferred_granularity"]
            })

    num_cols = correlation_report.get("numeric_columns", [])
    if len(num_cols) >= 2:
        specs.append({
            "chart_type": "CORRELATION_HEATMAP",
            "title": "Pairwise Pearson Correlation Matrix (r)",
            "columns": num_cols,
            "matrix": correlation_report.get("matrix", {})
        })

    return specs


if __name__ == "__main__":
    mock_num = {"revenue": {"mean": 200.0}, "ad_spend": {"mean": 50.0}}
    mock_cat = {"region": {"is_likely_id": False, "top_values": [{"value": "South", "count": 10, "percentage": 50.0}]}}
    mock_dist = {"revenue": {"shape_classification": "SYMMETRIC_NORMAL", "skewness": 0.1, "histogram": [{"range": "[0,100]", "count": 5}]}}
    mock_temp = {"order_date": {"inferred_granularity": "DAILY"}}
    mock_corr = {"numeric_columns": ["revenue", "ad_spend"], "matrix": {"revenue": {"ad_spend": 0.92}}}
    charts, _ = recommend_visualizations(mock_num, mock_cat, mock_dist, mock_temp, mock_corr)
    assert len(charts) == 4
    print("✅ STEP 31 PASSED: Visualization Spec Recommender verified!")
