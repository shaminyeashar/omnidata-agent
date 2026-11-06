"""
Module: Composite Data Quality & Readiness Scorer (modules/eda_engine/data_quality_scorer.py)
"""

import os
import sys
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


@auto_log_telemetry(module_name="eda_engine")
def compute_data_quality_score(
    missing_report: Dict[str, Any],
    outlier_report: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    sparsity_pct = float(missing_report.get("overall_sparsity_pct", 0.0))
    completeness_score = max(0.0, 100.0 - sparsity_pct)

    avg_outlier_pct = (
        sum(v.get("outlier_percentage", 0.0) for v in outlier_report.values()) / len(outlier_report)
        if outlier_report else 0.0
    )
    anomaly_stability_score = max(0.0, 100.0 - (avg_outlier_pct * 2.0))

    cols = missing_report.get("columns", {})
    if cols:
        healthy_cols = sum(1 for c in cols.values() if c.get("recommended_strategy") != "DROP_COLUMN_HIGH_SPARSITY")
        schema_consistency_score = (healthy_cols / len(cols)) * 100.0
    else:
        schema_consistency_score = 100.0

    overall_score = round((0.50 * completeness_score) + (0.30 * anomaly_stability_score) + (0.20 * schema_consistency_score), 2)
    if overall_score >= 90.0:
        grade = "A (PRODUCTION_READY)"
    elif overall_score >= 75.0:
        grade = "B (GOOD_MINOR_CLEANING)"
    elif overall_score >= 60.0:
        grade = "C (FAIR_NEEDS_IMPUTATION)"
    else:
        grade = "D (CRITICAL_DATA_QUALITY)"

    return {
        "overall_health_score": overall_score,
        "grade": grade,
        "completeness_score": round(completeness_score, 2),
        "anomaly_stability_score": round(anomaly_stability_score, 2),
        "schema_consistency_score": round(schema_consistency_score, 2)
    }


if __name__ == "__main__":
    clean_missing = {"overall_sparsity_pct": 2.0, "columns": {"id": {"recommended_strategy": "NONE_REQUIRED"}}}
    clean_outliers = {"price": {"outlier_percentage": 1.0}}
    score_res, _ = compute_data_quality_score(clean_missing, clean_outliers)
    assert score_res["grade"].startswith("A")
    print("✅ STEP 30 PASSED: Composite Data Quality Scorer verified!")
