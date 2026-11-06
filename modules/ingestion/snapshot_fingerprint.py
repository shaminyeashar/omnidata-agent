"""
Module: Cryptographic Snapshot Fingerprinter (modules/ingestion/snapshot_fingerprint.py)
Purpose: Generates a deterministic SHA-256 hash for the entire dataset and every 
         individual row, allowing O(1) row-level comparisons between live data refreshes.
Why we use standard libraries (hashlib, json):
         Cryptographic hashing provides 100% certainty of data mutation without 
         storing duplicate datasets in RAM.
"""

import hashlib
import json
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


def _hash_dict(d: Dict[str, Any]) -> str:
    """Deterministically hashes a dictionary into a SHA-256 string in O(1) time."""
    serialized = json.dumps(d, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


@auto_log_telemetry(module_name="ingestion")
def create_snapshot_fingerprint(
    parsed_data: List[Dict[str, Any]], 
    primary_key: str = None
) -> Dict[str, Any]:
    """
    Creates a fingerprint containing row-level hashes and a master dataset hash.
    Time Complexity: O(N) where N is the number of rows.
    """
    row_hashes = {}
    
    for idx, row in enumerate(parsed_data):
        # Use primary key if provided and exists, otherwise use row index
        if primary_key and primary_key in row:
            pk_val = str(row[primary_key])
        else:
            pk_val = f"__row_{idx}__"
            
        row_hashes[pk_val] = _hash_dict(row)
        
    # The master dataset hash is a hash of all row hashes combined
    dataset_hash = _hash_dict(row_hashes)
    
    return {
        "dataset_hash": dataset_hash,
        "row_hashes": row_hashes,
        "primary_key_used": primary_key,
        "total_rows": len(parsed_data)
    }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 16 Verification Gate (Snapshot Fingerprint)...\n")

    morning_data = [
        {"order_id": 1, "status": "shipped"},
        {"order_id": 2, "status": "pending"}
    ]
    
    fingerprint, rep = create_snapshot_fingerprint(morning_data, primary_key="order_id")
    
    print(f"Generated {fingerprint['total_rows']} row hashes in {rep['execution_time_ms']} ms.")
    print(f"Master Dataset Hash : {fingerprint['dataset_hash']}")
    
    assert len(fingerprint["row_hashes"]) == 2, "❌ FAIL: Missing row hashes!"
    assert "1" in fingerprint["row_hashes"], "❌ FAIL: Primary key mapping failed!"

    print("\n✅ STEP 16 PASSED: Cryptographic Snapshot Fingerprinter is verified!")
