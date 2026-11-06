"""
Module: Live Dataset Delta Tracker (modules/ingestion/delta_tracker.py)
Purpose: Compares morning and afternoon dataset fingerprints using Python Set 
         operations to calculate Added, Deleted, and Modified rows in O(N) time.
"""

import os
import sys
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


@auto_log_telemetry(module_name="ingestion")
def compute_dataset_delta(
    morning_fingerprint: Dict[str, Any], 
    afternoon_fingerprint: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes exact differences between two snapshot fingerprints.
    Time Complexity: O(N) | Space Complexity: O(N)
    """
    m_hashes = morning_fingerprint["row_hashes"]
    a_hashes = afternoon_fingerprint["row_hashes"]
    
    m_keys = set(m_hashes.keys())
    a_keys = set(a_hashes.keys())
    
    # O(N) Set operations
    added_keys = a_keys - m_keys
    deleted_keys = m_keys - a_keys
    common_keys = m_keys & a_keys
    
    # Check for modifications in common keys
    modified_keys = {k for k in common_keys if m_hashes[k] != a_hashes[k]}
    
    is_identical = morning_fingerprint["dataset_hash"] == afternoon_fingerprint["dataset_hash"]
    
    return {
        "is_identical": is_identical,
        "added_keys": list(added_keys),
        "deleted_keys": list(deleted_keys),
        "modified_keys": list(modified_keys),
        "total_added": len(added_keys),
        "total_deleted": len(deleted_keys),
        "total_modified": len(modified_keys)
    }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 17 Verification Gate (Delta Tracker)...\n")

    # Simulate Morning Snapshot
    morning_fp = {
        "dataset_hash": "hash_A",
        "row_hashes": {"order_1": "hash_1", "order_2": "hash_2", "order_3": "hash_3"}
    }
    
    # Simulate Afternoon Snapshot (order_1 modified, order_2 deleted, order_4 added)
    afternoon_fp = {
        "dataset_hash": "hash_B",
        "row_hashes": {"order_1": "hash_1_MODIFIED", "order_3": "hash_3", "order_4": "hash_4"}
    }
    
    delta, rep = compute_dataset_delta(morning_fp, afternoon_fp)
    
    print(f"Delta computed in {rep['execution_time_ms']} ms.")
    print(f"Added: {delta['total_added']} | Deleted: {delta['total_deleted']} | Modified: {delta['total_modified']}")
    
    assert delta["total_added"] == 1 and "order_4" in delta["added_keys"], "❌ FAIL: Addition tracking failed!"
    assert delta["total_deleted"] == 1 and "order_2" in delta["deleted_keys"], "❌ FAIL: Deletion tracking failed!"
    assert delta["total_modified"] == 1 and "order_1" in delta["modified_keys"], "❌ FAIL: Modification tracking failed!"
    
    print("\n✅ STEP 17 PASSED: Live Dataset Delta Tracker is verified!")
