"""
Module: Zero-Payload HTTP Preflight & Change Detector (modules/ingestion/http_preflight.py)
Purpose: Performs an O(1) HTTP HEAD inspection before downloading data to:
         1. Enforce the RAM circuit breaker using remote Content-Length headers.
         2. Detect whether live e-commerce/financial feeds changed via ETag or 
            Last-Modified headers without re-downloading unchanged files.
Why we use standard libraries (urllib.request, typing):
         Zero external dependencies; inspects headers in O(1) memory without 
         allocating payload buffers.
"""

import os
import sys
import urllib.request
from typing import Dict, Any, Optional, Mapping

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry, check_and_log_ram_budget
from modules.ingestion.url_validator import validate_and_normalize_url


# -----------------------------------------------------------------------------
# BLOCK 1: PURE O(1) HEADER EVALUATION & ETAG CHANGE DETECTOR
# Why this block started: Separates header parsing from network sockets so both 
# live HTTP responses and offline unit tests can verify RAM limits and ETag diffs.
# Time Complexity: O(1) | Space Complexity: O(1)
# -----------------------------------------------------------------------------
def evaluate_preflight_headers(
    headers: Mapping[str, str],
    previous_etag: Optional[str] = None,
    previous_modified: Optional[str] = None,
    max_budget_mb: float = 50.0,
    expansion_factor: float = 4.0
) -> Dict[str, Any]:
    """
    Evaluates HTTP response headers for RAM budget compliance and content changes.
    """
    norm_headers = {k.lower(): v.strip() for k, v in headers.items() if v}

    content_type = norm_headers.get("content-type", "text/plain").split(";")[0].strip()
    etag = norm_headers.get("etag")
    last_modified = norm_headers.get("last-modified")
    raw_length = norm_headers.get("content-length")

    content_length_bytes = int(raw_length) if (raw_length and raw_length.isdigit()) else 0

    # Run Step 3 Pre-Execution RAM Circuit Breaker if Content-Length is known
    if content_length_bytes > 0:
        ram_report = check_and_log_ram_budget(
            payload_bytes=content_length_bytes,
            module_name="ingestion",
            max_budget_mb=max_budget_mb,
            expansion_factor=expansion_factor
        )
        estimated_ram_mb = ram_report["estimated_ram_mb"]
    else:
        estimated_ram_mb = 0.0

    # Determine if remote dataset is unchanged since the morning snapshot
    has_changed = True
    change_reason = "INITIAL_FETCH"

    if previous_etag and etag:
        if previous_etag == etag:
            has_changed = False
            change_reason = "ETAG_MATCH (UNCHANGED)"
        else:
            change_reason = "ETAG_UPDATED (CHANGED)"
    elif previous_modified and last_modified:
        if previous_modified == last_modified:
            has_changed = False
            change_reason = "TIMESTAMP_MATCH (UNCHANGED)"
        else:
            change_reason = "TIMESTAMP_UPDATED (CHANGED)"

    return {
        "content_type": content_type,
        "content_length_bytes": content_length_bytes,
        "estimated_ram_mb": estimated_ram_mb,
        "etag": etag,
        "last_modified": last_modified,
        "has_changed": has_changed,
        "change_reason": change_reason,
        "status": "PREFLIGHT_OK"
    }


# -----------------------------------------------------------------------------
# BLOCK 2: LIVE HTTP HEAD NETWORK INSPECTOR
# Why this block started: Sends a lightweight HTTP HEAD request (headers only, 
# zero body bytes) to inspect remote datasets safely.
# -----------------------------------------------------------------------------
@auto_log_telemetry(module_name="ingestion")
def inspect_remote_resource(
    url: str,
    previous_etag: Optional[str] = None,
    previous_modified: Optional[str] = None,
    max_budget_mb: float = 50.0,
    timeout_sec: float = 10.0
) -> Dict[str, Any]:
    """
    Validates URL, sends an HTTP HEAD request, and evaluates preflight safety.
    """
    val_result, _ = validate_and_normalize_url(url)
    target_url = val_result["normalized_url"]

    req = urllib.request.Request(
        target_url,
        method="HEAD",
        headers={"User-Agent": "OmniData-Agent/1.0 (Memory-Safe-Preflight)"}
    )

    with urllib.request.urlopen(req, timeout=timeout_sec) as response:
        header_dict = dict(response.headers.items())

    report = evaluate_preflight_headers(
        headers=header_dict,
        previous_etag=previous_etag,
        previous_modified=previous_modified,
        max_budget_mb=max_budget_mb
    )
    report["normalized_url"] = target_url
    return report


# =============================================================================
# BLOCK 3: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 12 Verification Gate (HTTP Preflight & ETag Detector)...\n")

    from modules.telemetry import MemoryBudgetExceededError

    # Test 1: Safe 2 MB CSV with initial ETag
    morning_headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Length": str(2 * 1024 * 1024),
        "ETag": '"v1-morning-batch"',
        "Last-Modified": "Fri, 06 Nov 2026 09:00:00 GMT"
    }
    res_morning = evaluate_preflight_headers(morning_headers)
    print(f"[Test 1 - Morning Fetch]    -> Changed: {res_morning['has_changed']} | Est RAM: {res_morning['estimated_ram_mb']} MB")

    # Test 2: Afternoon check with identical ETag (skips redundant download!)
    res_unchanged = evaluate_preflight_headers(morning_headers, previous_etag='"v1-morning-batch"')
    print(f"[Test 2 - Same ETag Check]  -> Changed: {res_unchanged['has_changed']} ({res_unchanged['change_reason']})")

    # Test 3: Afternoon check with updated ETag (triggers live refresh!)
    afternoon_headers = dict(morning_headers, ETag='"v2-afternoon-batch"')
    res_changed = evaluate_preflight_headers(afternoon_headers, previous_etag='"v1-morning-batch"')
    print(f"[Test 3 - New ETag Check]   -> Changed: {res_changed['has_changed']} ({res_changed['change_reason']})")

    # Test 4: Oversized 25 MB remote file (100 MB expanded > 50 MB budget)
    oversized_headers = {"Content-Length": str(25 * 1024 * 1024)}
    blocked = False
    try:
        evaluate_preflight_headers(oversized_headers, max_budget_mb=50.0)
    except MemoryBudgetExceededError:
        blocked = True
        print("[Test 4 - Oversized Header] -> Blocked BEFORE downloading a single byte!")

    assert res_morning["has_changed"] is True, "❌ FAIL: Initial fetch must be marked changed!"
    assert res_unchanged["has_changed"] is False, "❌ FAIL: Identical ETag should report unchanged!"
    assert res_changed["has_changed"] is True, "❌ FAIL: Updated ETag should report changed!"
    assert blocked is True, "❌ FAIL: Oversized Content-Length did not trip circuit breaker!"

    print("\n✅ STEP 12 PASSED: Zero-Payload HTTP Preflight & ETag Change Detector is verified!")
