"""
Module: Categorical Frequency, Cardinality & Entropy Profiler (modules/eda_engine/categorical_profiler.py)
Purpose: Profiles non-numeric/string columns using collections.Counter to compute 
         unique cardinality, Top-K modes, cardinality ratio, and Shannon Entropy H(X)
         in a single O(N) pass with bounded Top-K output space.
"""

from collections import Counter
import math
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


@auto_log_telemetry(module_name="eda_engine")
def profile_categorical_columns(
    parsed_data: List[Dict[str, Any]],
    top_k: int = 5
) -> Dict[str, Dict[str, Any]]:
    """
    Profiles string/categorical columns for frequency, cardinality, and entropy.
    """
    if not parsed_data:
        return {}

    columns = list(parsed_data[0].keys())
    cat_stats: Dict[str, Dict[str, Any]] = {}

    for col in columns:
        counter: Counter = Counter()
        count = 0
        null_count = 0
        is_categorical = False

        for row in parsed_data:
            val = row.get(col)
            if val is None or val == "":
                null_count += 1
                continue
            if isinstance(val, (str, bool)):
                is_categorical = True
                counter[str(val)] += 1
                count += 1

        if not is_categorical or count == 0:
            continue

        unique_count = len(counter)
        cardinality_ratio = round(unique_count / count, 4)

        # Compute Shannon Information Entropy H(X) = -sum(p * log2(p))
        entropy = 0.0
        for freq in counter.values():
            p = freq / count
            if p > 0:
                entropy -= p * math.log2(p)

        top_values = [
            {"value": k, "count": v, "percentage": round((v / count) * 100, 2)}
            for k, v in counter.most_common(top_k)
        ]

        cat_stats[col] = {
            "count": count,
            "null_count": null_count,
            "unique_count": unique_count,
            "cardinality_ratio": cardinality_ratio,
            "is_likely_id": cardinality_ratio == 1.0 and count > 1,
            "shannon_entropy": round(entropy, 4),
            "mode": top_values[0]["value"] if top_values else None,
            "top_values": top_values
        }

    return cat_stats


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 22 Verification Gate (Categorical & Entropy Profiler)...\n")

    sample_rows = [
        {"sku": "S1", "category": "Electronics", "price": 500.0},
        {"sku": "S2", "category": "Electronics", "price": 300.0},
        {"sku": "S3", "category": "Books", "price": 25.0},
        {"sku": "S4", "category": "Books", "price": 30.0},
    ]

    res, rep = profile_categorical_columns(sample_rows, top_k=3)
    print(f"Categorical Columns : {list(res.keys())} in {rep['execution_time_ms']} ms")
    print(f"Category Profile    : {res['category']}")
    print(f"SKU ID Detection    : is_likely_id={res['sku']['is_likely_id']} (Entropy={res['sku']['shannon_entropy']})")

    assert "price" not in res, "❌ FAIL: Numeric column should not be in categorical profile!"
    assert res["category"]["shannon_entropy"] == 1.0, "❌ FAIL: 50/50 split must have 1.0 bit entropy!"
    assert res["sku"]["is_likely_id"] is True, "❌ FAIL: Unique SKU column should be flagged as ID!"

    print("\n✅ STEP 22 PASSED: Categorical Frequency, Cardinality & Entropy Profiler is verified!")
