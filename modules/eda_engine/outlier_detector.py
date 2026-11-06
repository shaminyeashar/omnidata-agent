"""
Module: Dual IQR & Z-Score Outlier Pinpointer (modules/eda_engine/outlier_detector.py)
Purpose: Detects numeric anomalies using both Tukey's 1.5x IQR fences and Z-Score 
         thresholds, returning exact row indices and bounded sample evidence for 
         anti-hallucination citation.
"""

import os
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry
from modules.eda_engine.numeric_profiler import profile_numeric_columns


@auto_log_telemetry(module_name="eda_engine")
def detect_numeric_outliers(
    parsed_data: List[Dict[str, Any]],
    numeric_stats: Optional[Dict[str, Dict[str, Any]]] = None,
    iqr_multiplier: float = 1.5,
    z_threshold: float = 2.5,
    max_flagged_rows: int = 25
) -> Dict[str, Dict[str, Any]]:
    """
    Pinpoints outlier rows per numeric column using IQR fences and Z-scores.
    """
    if not parsed_data:
        return {}

    stats = numeric_stats if numeric_stats is not None else profile_numeric_columns(parsed_data)[0]
    outlier_report: Dict[str, Dict[str, Any]] = {}

    for col, st in stats.items():
        q1, q3, iqr = st["q1"], st["q3"], st["iqr"]
        mean, std_dev = st["mean"], st["std_dev"]

        lower_fence = round(q1 - (iqr_multiplier * iqr), 4)
        upper_fence = round(q3 + (iqr_multiplier * iqr), 4)

        flagged_indices: List[int] = []
        flagged_samples: List[Dict[str, Any]] = []
        total_outliers = 0

        for idx, row in enumerate(parsed_data):
            val = row.get(col)
            if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
                continue

            f_val = float(val)
            is_iqr_outlier = (f_val < lower_fence) or (f_val > upper_fence)
            z_score = abs((f_val - mean) / std_dev) if std_dev > 0 else 0.0
            is_z_outlier = z_score >= z_threshold

            if is_iqr_outlier or is_z_outlier:
                total_outliers += 1
                if len(flagged_indices) < max_flagged_rows:
                    flagged_indices.append(idx)
                    flagged_samples.append({
                        "row_index": idx,
                        "value": f_val,
                        "z_score": round(z_score, 3),
                        "reason": "BOTH" if (is_iqr_outlier and is_z_outlier) else ("IQR" if is_iqr_outlier else "Z_SCORE")
                    })

        outlier_report[col] = {
            "total_outliers": total_outliers,
            "outlier_percentage": round((total_outliers / max(1, st["count"])) * 100, 2),
            "lower_fence": lower_fence,
            "upper_fence": upper_fence,
            "flagged_row_indices": flagged_indices,
            "flagged_samples": flagged_samples
        }

    return outlier_report


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 23 Verification Gate (IQR & Z-Score Outlier Detector)...\n")

    # 9 normal orders around $100-$110, plus 1 extreme anomaly at row index 9 ($9,500)
    orders = [{"amount": 100.0 + (i % 5) * 2} for i in range(9)]
    orders.append({"amount": 9500.0})

    report, rep = detect_numeric_outliers(orders)
    amt_outliers = report["amount"]

    print(f"Outliers Detected   : {amt_outliers['total_outliers']} in {rep['execution_time_ms']} ms")
    print(f"IQR Fences          : [{amt_outliers['lower_fence']}, {amt_outliers['upper_fence']}]")
    print(f"Flagged Row Indices : {amt_outliers['flagged_row_indices']}")
    print(f"Flagged Evidence    : {amt_outliers['flagged_samples']}")

    assert amt_outliers["total_outliers"] == 1, "❌ FAIL: Expected exactly 1 outlier!"
    assert amt_outliers["flagged_row_indices"] == [9], "❌ FAIL: Did not pinpoint row index 9!"

    print("\n✅ STEP 23 PASSED: Dual IQR & Z-Score Outlier Pinpointer is verified!")
