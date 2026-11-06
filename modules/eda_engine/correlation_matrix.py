"""
Module: Pairwise Pearson Correlation Matrix Engine (modules/eda_engine/correlation_matrix.py)
Purpose: Computes the exact Pearson linear correlation coefficient r in [-1.0, 1.0]
         for all pairs of numeric columns without external matrix libraries.
"""

import math
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


def _pearson_r(x: List[float], y: List[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = 0.0
    den_x = 0.0
    den_y = 0.0
    for xi, yi in zip(x, y):
        dx = xi - mean_x
        dy = yi - mean_y
        num += dx * dy
        den_x += dx * dx
        den_y += dy * dy

    denom = math.sqrt(den_x * den_y)
    if denom == 0.0:
        return 0.0
    return round(max(-1.0, min(1.0, num / denom)), 4)


@auto_log_telemetry(module_name="eda_engine")
def compute_correlation_matrix(parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes pairwise Pearson correlation matrix and highlights strong correlations.
    """
    if not parsed_data:
        return {"matrix": {}, "strong_pairs": []}

    # Identify numeric columns
    candidate_cols = list(parsed_data[0].keys())
    num_cols: List[str] = []
    for c in candidate_cols:
        for row in parsed_data:
            v = row.get(c)
            if v is not None and v != "":
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    num_cols.append(c)
                break

    matrix: Dict[str, Dict[str, float]] = {c: {} for c in num_cols}
    strong_pairs: List[Dict[str, Any]] = []

    for i, col_a in enumerate(num_cols):
        matrix[col_a][col_a] = 1.0
        for j in range(i + 1, len(num_cols)):
            col_b = num_cols[j]
            xs: List[float] = []
            ys: List[float] = []
            for row in parsed_data:
                va, vb = row.get(col_a), row.get(col_b)
                if isinstance(va, (int, float)) and not isinstance(va, bool) and isinstance(vb, (int, float)) and not isinstance(vb, bool):
                    xs.append(float(va))
                    ys.append(float(vb))

            r_val = _pearson_r(xs, ys)
            matrix[col_a][col_b] = r_val
            matrix[col_b][col_a] = r_val

            if abs(r_val) >= 0.7:
                strong_pairs.append({
                    "col_a": col_a,
                    "col_b": col_b,
                    "pearson_r": r_val,
                    "direction": "POSITIVE" if r_val > 0 else "NEGATIVE"
                })

    return {
        "numeric_columns": num_cols,
        "matrix": matrix,
        "strong_pairs": strong_pairs
    }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 26 Verification Gate (Pearson Correlation Matrix)...\n")

    data = [
        {"ad_spend": 10.0, "sales": 100.0, "churn": 50.0},
        {"ad_spend": 20.0, "sales": 200.0, "churn": 40.0},
        {"ad_spend": 30.0, "sales": 300.0, "churn": 30.0},
        {"ad_spend": 40.0, "sales": 400.0, "churn": 20.0},
    ]

    res, rep = compute_correlation_matrix(data)
    print(f"Correlation Matrix computed in {rep['execution_time_ms']} ms:")
    for col, row_map in res["matrix"].items():
        print(f"  {col:<10} -> {row_map}")
    print(f"Strong Pairs (|r| >= 0.7) : {res['strong_pairs']}")

    assert res["matrix"]["ad_spend"]["sales"] == 1.0, "❌ FAIL: Expected +1.0 correlation!"
    assert res["matrix"]["ad_spend"]["churn"] == -1.0, "❌ FAIL: Expected -1.0 correlation!"
    assert len(res["strong_pairs"]) == 3, "❌ FAIL: Expected 3 strong pairs!"

    print("\n✅ STEP 26 PASSED: Pairwise Pearson Correlation Matrix Engine is verified!")
