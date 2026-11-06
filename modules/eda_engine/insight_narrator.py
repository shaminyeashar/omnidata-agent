"""
Module: Deterministic Insight Narrator (modules/eda_engine/insight_narrator.py)
Purpose: Generates human-readable, data-grounded insights without AI hallucination.
"""
import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from modules.telemetry import auto_log_telemetry

@auto_log_telemetry(module_name="eda_engine")
def generate_narrative_insights(
    kpi_report: Dict[str, Any],
    health_report: Dict[str, Any],
    corr_report: Dict[str, Any]
) -> List[str]:
    insights = []
    
    # Health Insight
    score = health_report.get("overall_health_score", 0.0)
    grade = health_report.get("grade", "UNKNOWN")
    insights.append(f"Data Readiness: The dataset scored {score}/100 ({grade}).")

    # Domain Insight
    sector = kpi_report.get("sector", "GENERAL_TABULAR")
    if sector != "GENERAL_TABULAR":
        insights.append(f"Domain Context: Automatic schema analysis classified this as a {sector.replace('_', ' ').title()} dataset.")

    # Correlation Insight
    strong_pairs = corr_report.get("strong_pairs", [])
    if strong_pairs:
        top_pair = strong_pairs[0]
        insights.append(f"Key Driver: Discovered a strong {top_pair['direction'].lower()} correlation (r={top_pair['pearson_r']}) between '{top_pair['col_a']}' and '{top_pair['col_b']}'.")

    return insights

if __name__ == "__main__":
    mock_kpi = {"sector": "E_COMMERCE_RETAIL"}
    mock_health = {"overall_health_score": 92.5, "grade": "A (PRODUCTION_READY)"}
    mock_corr = {"strong_pairs": [{"col_a": "ad_spend", "col_b": "sales", "direction": "POSITIVE", "pearson_r": 0.85}]}
    insights, _ = generate_narrative_insights(mock_kpi, mock_health, mock_corr)
    assert len(insights) == 3 and "E Commerce Retail" in insights[1]
    print("✅ STEP 33 PASSED: Deterministic Insight Narrator verified!")
