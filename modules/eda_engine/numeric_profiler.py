"""
Module: Welford's Single-Pass Numeric Statistical Profiler (modules/eda_engine/numeric_profiler.py)
Purpose: Computes mean, sample variance, standard deviation, min, max, null count,
         median, and IQR (Q1, Q3) for numeric columns using Welford's numerically 
         stable single-pass algorithm.
Why we use standard libraries (math, typing):
         Avoids multi-pass array allocations; Welford's accumulator updates mean 
         and variance in O(1) auxiliary space per value.
"""

import math
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


def _percentile(sorted_vals: List[float], p: float) -> float:
    """Computes linear interpolated percentile from a sorted list in O(1) time."""
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    return float(sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f))


@auto_log_telemetry(module_name="eda_engine")
def profile_numeric_columns(parsed_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Profiles all numeric (int/float) columns in parsed_data using Welford's 
    online algorithm for single-pass mean/variance stability plus exact quartiles.
    """
    if not parsed_data:
        return {}

    columns = list(parsed_data[0].keys())
    stats: Dict[str, Dict[str, Any]] = {}

    for col in columns:
        count = 0
        null_count = 0
        mean = 0.0
        m2 = 0.0
        min_val = float("inf")
        max_val = float("-inf")
        total_sum = 0.0
        clean_values: List[float] = []
        is_numeric_col = True

        for row in parsed_data:
            val = row.get(col)
            if val is None or val == "":
                null_count += 1
                continue
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                is_numeric_col = False
                break

            f_val = float(val)
            clean_values.append(f_val)
            count += 1
            total_sum += f_val
            if f_val < min_val:
                min_val = f_val
            if f_val > max_val:
                max_val = f_val

            # Welford's O(1) online mean and M2 variance recurrence
            delta = f_val - mean
            mean += delta / count
            delta2 = f_val - mean
            m2 += delta * delta2

        if not is_numeric_col or count == 0:
            continue

        variance = (m2 / (count - 1)) if count > 1 else 0.0
        std_dev = math.sqrt(variance)

        clean_values.sort()
        q1 = _percentile(clean_values, 0.25)
        median = _percentile(clean_values, 0.50)
        q3 = _percentile(clean_values, 0.75)

        stats[col] = {
            "count": count,
            "null_count": null_count,
            "min": round(min_val, 4),
            "max": round(max_val, 4),
            "sum": round(total_sum, 4),
            "mean": round(mean, 4),
            "median": round(median, 4),
            "std_dev": round(std_dev, 4),
            "variance": round(variance, 4),
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(q3 - q1, 4)
        }

    return stats


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 21 Verification Gate (Welford's Numeric Profiler)...\n")

    sample_orders = [
        {"order_id": 1, "product": "A", "revenue": 100.0},
        {"order_id": 2, "product": "B", "revenue": 200.0},
        {"order_id": 3, "product": "C", "revenue": 300.0},
        {"order_id": 4, "product": "D", "revenue": 400.0},
        {"order_id": 5, "product": "E", "revenue": 500.0},
        {"order_id": 6, "product": "F", "revenue": None}
    ]

    profile, rep = profile_numeric_columns(sample_orders)
    rev_stats = profile["revenue"]

    print(f"Numeric Columns Profiled : {list(profile.keys())} in {rep['execution_time_ms']} ms")
    print(f"Revenue Stats            : {rev_stats}")

    assert "product" not in profile, "❌ FAIL: String column should be excluded!"
    assert rev_stats["count"] == 5 and rev_stats["null_count"] == 1, "❌ FAIL: Count/null mismatch!"
    assert rev_stats["mean"] == 300.0 and rev_stats["median"] == 300.0, "❌ FAIL: Mean/median math error!"
    assert round(rev_stats["std_dev"], 2) == 158.11, "❌ FAIL: Welford std_dev math error!"
    assert rev_stats["iqr"] == 200.0, "❌ FAIL: IQR math error!"

    print("\n✅ STEP 21 PASSED: Welford's Single-Pass Numeric Statistical Profiler is verified!")
