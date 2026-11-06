"""
Module: Distribution Shape & O(N) Histogram Binner (modules/eda_engine/distribution_analyzer.py)
"""

import os
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry
from modules.eda_engine.numeric_profiler import profile_numeric_columns


@auto_log_telemetry(module_name="eda_engine")
def analyze_distributions(
    parsed_data: List[Dict[str, Any]],
    numeric_stats: Optional[Dict[str, Dict[str, Any]]] = None,
    bins: int = 10
) -> Dict[str, Dict[str, Any]]:
    if not parsed_data:
        return {}
    stats = numeric_stats if numeric_stats is not None else profile_numeric_columns(parsed_data)[0]
    dist_report: Dict[str, Dict[str, Any]] = {}
    num_bins = max(2, bins)

    for col, st in stats.items():
        n, mean, std_dev, min_v, max_v = st["count"], st["mean"], st["std_dev"], st["min"], st["max"]
        bin_counts = [0] * num_bins
        span = max_v - min_v
        bin_width = span / num_bins if span > 0 else 1.0
        m3_sum = 0.0
        m4_sum = 0.0

        for row in parsed_data:
            val = row.get(col)
            if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
                continue
            fv = float(val)
            if std_dev > 0:
                z = (fv - mean) / std_dev
                m3_sum += z ** 3
                m4_sum += z ** 4
            b_idx = 0 if span == 0 else min(num_bins - 1, int((fv - min_v) / bin_width))
            bin_counts[b_idx] += 1

        skewness = round(m3_sum / n, 4) if (n > 2 and std_dev > 0) else 0.0
        excess_kurtosis = round((m4_sum / n) - 3.0, 4) if (n > 3 and std_dev > 0) else 0.0
        shape = "SYMMETRIC_NORMAL" if abs(skewness) < 0.5 else ("RIGHT_SKEWED (POSITIVE)" if skewness >= 0.5 else "LEFT_SKEWED (NEGATIVE)")

        histogram_bins = [
            {
                "bin_index": i,
                "range": f"[{round(min_v + i * bin_width, 3)}, {round(min_v + (i + 1) * bin_width, 3)}]",
                "count": bin_counts[i]
            }
            for i in range(num_bins)
        ]

        dist_report[col] = {
            "skewness": skewness,
            "excess_kurtosis": excess_kurtosis,
            "shape_classification": shape,
            "histogram": histogram_bins
        }
    return dist_report


if __name__ == "__main__":
    skewed_rows = [{"latency_ms": 10.0}, {"latency_ms": 12.0}, {"latency_ms": 11.0}, {"latency_ms": 13.0}, {"latency_ms": 10.5}, {"latency_ms": 250.0}]
    res, _ = analyze_distributions(skewed_rows, bins=5)
    assert res["latency_ms"]["shape_classification"] == "RIGHT_SKEWED (POSITIVE)"
    print("✅ STEP 29 PASSED: Skewness, Kurtosis & Histogram Binner verified!")
