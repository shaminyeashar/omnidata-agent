"""
Module: Schema Drift & Column Mutation Detector (modules/ingestion/schema_validator.py)
Purpose: Extracts column schemas and data types from parsed records and detects 
         added, missing, or type-mutated columns between live data refreshes.
Why we use standard libraries (typing):
         Set and dictionary comparisons across C columns run in O(C) -> O(1) 
         bounded time and space.
"""

import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


def extract_schema(parsed_data: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Infers column names and dominant Python type names from parsed records.
    """
    if not parsed_data:
        return {}

    schema: Dict[str, str] = {}
    columns = list(parsed_data[0].keys())

    for col in columns:
        detected_type = "null"
        for row in parsed_data:
            val = row.get(col)
            if val is not None:
                detected_type = type(val).__name__
                break
        schema[col] = detected_type

    return schema


@auto_log_telemetry(module_name="ingestion")
def detect_schema_drift(
    baseline_schema: Dict[str, str],
    current_schema: Dict[str, str]
) -> Dict[str, Any]:
    """
    Compares baseline (morning) and current (afternoon) schemas in O(C) time.
    """
    base_cols = set(baseline_schema.keys())
    curr_cols = set(current_schema.keys())

    added_columns = sorted(list(curr_cols - base_cols))
    missing_columns = sorted(list(base_cols - curr_cols))
    common_columns = base_cols & curr_cols

    type_mutations: Dict[str, Dict[str, str]] = {}
    for col in sorted(common_columns):
        if baseline_schema[col] != current_schema[col]:
            type_mutations[col] = {
                "from": baseline_schema[col],
                "to": current_schema[col]
            }

    has_drift = bool(added_columns or missing_columns or type_mutations)

    return {
        "has_drift": has_drift,
        "added_columns": added_columns,
        "missing_columns": missing_columns,
        "type_mutations": type_mutations,
        "status": "DRIFT_DETECTED" if has_drift else "SCHEMA_STABLE"
    }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 18 Verification Gate (Schema Drift Detector)...\n")

    morning_rows = [{"order_id": 101, "price": 499.99, "status": "shipped"}]
    afternoon_rows = [{"order_id": 101, "price": "FREE", "discount_code": "FESTIVE"}]

    base_schema = extract_schema(morning_rows)
    curr_schema = extract_schema(afternoon_rows)

    drift_report, rep = detect_schema_drift(base_schema, curr_schema)

    print(f"Baseline Schema  : {base_schema}")
    print(f"Afternoon Schema : {curr_schema}")
    print(f"Drift Report     : {drift_report['status']} in {rep['execution_time_ms']} ms")
    print(f"  Added Columns  : {drift_report['added_columns']}")
    print(f"  Missing Columns: {drift_report['missing_columns']}")
    print(f"  Type Mutations : {drift_report['type_mutations']}")

    assert drift_report["has_drift"] is True, "❌ FAIL: Schema drift was not detected!"
    assert "discount_code" in drift_report["added_columns"], "❌ FAIL: Added column missed!"
    assert "status" in drift_report["missing_columns"], "❌ FAIL: Missing column missed!"
    assert drift_report["type_mutations"]["price"]["to"] == "str", "❌ FAIL: Type mutation missed!"

    print("\n✅ STEP 18 PASSED: Schema Drift & Column Mutation Detector is verified!")
