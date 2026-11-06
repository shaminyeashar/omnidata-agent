"""
Module: Missing Value Sparsity & Imputation Recommender (modules/eda_engine/missing_value_analyzer.py)
Purpose: Analyzes column-level and row-level missingness in a single O(N) pass and 
         recommends statistically sound imputation strategies.
"""

import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


@auto_log_telemetry(module_name="eda_engine")
def analyze_missing_values(parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes missing value density and recommends per-column imputation strategies.
    """
    if not parsed_data:
        return {"total_rows": 0, "total_missing_cells": 0, "columns": {}}

    total_rows = len(parsed_data)
    columns = list(parsed_data[0].keys())
    col_missing: Dict[str, int] = {c: 0 for c in columns}
    col_types: Dict[str, str] = {c: "unknown" for c in columns}
    rows_with_any_null = 0
    total_missing_cells = 0

    for row in parsed_data:
        row_has_null = False
        for c in columns:
            val = row.get(c)
            if val is None or val == "":
                col_missing[c] += 1
                total_missing_cells += 1
                row_has_null = True
            elif col_types[c] == "unknown":
                col_types[c] = "numeric" if (isinstance(val, (int, float)) and not isinstance(val, bool)) else "categorical"
        if row_has_null:
            rows_with_any_null += 1

    col_reports: Dict[str, Dict[str, Any]] = {}
    for c in columns:
        miss_cnt = col_missing[c]
        miss_pct = round((miss_cnt / total_rows) * 100, 2)
        dtype = col_types[c]

        if miss_cnt == 0:
            strategy = "NONE_REQUIRED"
        elif miss_pct > 50.0:
            strategy = "DROP_COLUMN_HIGH_SPARSITY"
        elif dtype == "numeric":
            strategy = "MEDIAN_IMPUTATION (ROBUST)"
        else:
            strategy = "MODE_OR_UNKNOWN_CATEGORY"

        col_reports[c] = {
            "missing_count": miss_cnt,
            "missing_percentage": miss_pct,
            "inferred_kind": dtype,
            "recommended_strategy": strategy
        }

    total_cells = total_rows * len(columns)
    overall_sparsity = round((total_missing_cells / max(1, total_cells)) * 100, 2)

    return {
        "total_rows": total_rows,
        "rows_with_nulls": rows_with_any_null,
        "total_missing_cells": total_missing_cells,
        "overall_sparsity_pct": overall_sparsity,
        "columns": col_reports
    }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 25 Verification Gate (Missing Value & Imputation Analyzer)...\n")

    rows = [
        {"id": 1, "price": 100.0, "coupon": None},
        {"id": 2, "price": None, "coupon": None},
        {"id": 3, "price": 250.0, "coupon": None},
        {"id": 4, "price": 300.0, "coupon": "SAVE10"},
    ]

    report, rep = analyze_missing_values(rows)
    print(f"Overall Sparsity : {report['overall_sparsity_pct']}% in {rep['execution_time_ms']} ms")
    for col, info in report["columns"].items():
        print(f"  Col '{col}' -> Missing: {info['missing_percentage']}% | Strategy: {info['recommended_strategy']}")

    assert report["columns"]["id"]["recommended_strategy"] == "NONE_REQUIRED"
    assert report["columns"]["price"]["recommended_strategy"] == "MEDIAN_IMPUTATION (ROBUST)"
    assert report["columns"]["coupon"]["recommended_strategy"] == "DROP_COLUMN_HIGH_SPARSITY"

    print("\n✅ STEP 25 PASSED: Missing Value Sparsity & Imputation Recommender is verified!")
