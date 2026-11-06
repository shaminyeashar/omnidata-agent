"""
Module: O(N) Duplicate & Collision Detector (modules/eda_engine/duplicate_detector.py)
Purpose: Detects exact row duplicates and primary key collisions in O(N) time 
         using bounded HashSet lookups.
"""
import os
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from modules.telemetry import auto_log_telemetry

@auto_log_telemetry(module_name="eda_engine")
def detect_duplicates(
    parsed_data: List[Dict[str, Any]],
    primary_key: Optional[str] = None
) -> Dict[str, Any]:
    if not parsed_data:
        return {"exact_duplicates": 0, "pk_collisions": 0, "duplicate_rate_pct": 0.0}

    seen_hashes = set()
    seen_pks = set()
    exact_duplicates = 0
    pk_collisions = 0

    for row in parsed_data:
        # Hash the row deterministically
        row_tuple = tuple(sorted((k, str(v)) for k, v in row.items()))
        row_hash = hash(row_tuple)

        if row_hash in seen_hashes:
            exact_duplicates += 1
        else:
            seen_hashes.add(row_hash)

        if primary_key and primary_key in row:
            pk_val = str(row[primary_key])
            if pk_val in seen_pks:
                pk_collisions += 1
            else:
                seen_pks.add(pk_val)

    duplicate_rate = round((exact_duplicates / len(parsed_data)) * 100, 2)
    return {
        "exact_duplicates": exact_duplicates,
        "pk_collisions": pk_collisions,
        "duplicate_rate_pct": duplicate_rate
    }

if __name__ == "__main__":
    rows = [{"id": 1, "val": "A"}, {"id": 1, "val": "B"}, {"id": 2, "val": "C"}, {"id": 2, "val": "C"}]
    res, _ = detect_duplicates(rows, primary_key="id")
    assert res["exact_duplicates"] == 1 and res["pk_collisions"] == 2
    print("✅ STEP 32 PASSED: O(N) Duplicate & Collision Detector verified!")
