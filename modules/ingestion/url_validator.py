"""
Module: URL Sanitizer, SSRF Guard & Stream Normalizer (modules/ingestion/url_validator.py)
Purpose: Validates incoming data URLs, blocks dangerous protocols or private 
         local network addresses (SSRF protection), and normalizes GitHub blob 
         links into direct raw data streams before network I/O begins.
Why we use standard libraries (urllib.parse, ipaddress):
         Zero external dependencies; parses URLs and IP ranges in O(1) time 
         and O(1) space while integrating directly with Phase 1 telemetry.
"""

import ipaddress
import os
import sys
from typing import Dict, Any
from urllib.parse import urlparse

# Ensure project root is on sys.path when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


# -----------------------------------------------------------------------------
# BLOCK 1: CUSTOM INGESTION SECURITY EXCEPTION
# Why this block started: Gives the UI a distinct error class when a URL is 
# malformed or blocked by the SSRF security filter.
# -----------------------------------------------------------------------------
class UnsafeURLError(Exception):
    """Raised when a URL fails protocol validation or triggers SSRF guards."""
    pass


# -----------------------------------------------------------------------------
# BLOCK 2: SSRF HOST & PRIVATE IP INSPECTOR
# Why this block started: Prevents Server-Side Request Forgery (SSRF) by 
# blocking localhost and private LAN IP ranges (127.0.0.1, 10.x.x.x, 192.168.x.x).
# Time Complexity: O(1) | Space Complexity: O(1)
# -----------------------------------------------------------------------------
def _verify_safe_host(hostname: str) -> None:
    if not hostname:
        raise UnsafeURLError("URL is missing a valid hostname.")

    clean_host = hostname.strip().lower()
    blocked_Hostnames = {"localhost", "0.0.0.0", "::1"}
    if clean_host in blocked_Hostnames or clean_host.endswith(".local"):
        raise UnsafeURLError(f"SSRF Guard Tripped: Localhost target '{clean_host}' is blocked.")

    # Check if hostname is a literal IP address in a private/loopback range
    try:
        ip_obj = ipaddress.ip_address(clean_host)
        if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_reserved:
            raise UnsafeURLError(
                f"SSRF Guard Tripped: Private or loopback IP '{clean_host}' is blocked."
            )
    except ValueError:
        # Hostname is a standard domain name (e.g., raw.githubusercontent.com), not an IP literal
        if "." not in clean_host:
            raise UnsafeURLError(f"Invalid domain format: '{clean_host}'.")


# -----------------------------------------------------------------------------
# BLOCK 3: DIRECT-STREAM NORMALIZER & TELEMETRY-LOGGED VALIDATOR
# Why this block started: Rewrites webpage wrapper URLs (like GitHub /blob/ links)
# into raw data streams and logs the check into GLOBAL_TELEMETRY_LOGGER.
# -----------------------------------------------------------------------------
@auto_log_telemetry(module_name="ingestion")
def validate_and_normalize_url(raw_url: str) -> Dict[str, Any]:
    """
    Validates a URL for safe HTTP/HTTPS streaming and normalizes known wrapper links.

    Returns:
        dict: Normalized URL metadata (normalized_url, domain, was_rewritten, scheme).
    """
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise UnsafeURLError("URL cannot be empty.")

    cleaned_url = raw_url.strip()
    parsed = urlparse(cleaned_url)

    # 1. Enforce strict HTTP / HTTPS scheme whitelist
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise UnsafeURLError(
            f"Unsupported protocol '{scheme}://'. Only http:// and https:// are allowed."
        )

    # 2. Verify host against SSRF loopback/private network rules
    _verify_safe_host(parsed.hostname or "")

    # 3. Auto-normalize GitHub '/blob/' links into direct raw streams
    normalized_url = cleaned_url
    was_rewritten = False

    if parsed.hostname and parsed.hostname.lower() == "github.com" and "/blob/" in parsed.path:
        raw_path = parsed.path.replace("/blob/", "/", 1)
        normalized_url = f"https://raw.githubusercontent.com{raw_path}"
        if parsed.query:
            normalized_url += f"?{parsed.query}"
        was_rewritten = True

    final_parsed = urlparse(normalized_url)

    return {
        "original_url": cleaned_url,
        "normalized_url": normalized_url,
        "domain": final_parsed.hostname,
        "scheme": final_parsed.scheme.lower(),
        "was_rewritten": was_rewritten,
        "status": "VALIDATED"
    }


# =============================================================================
# BLOCK 4: ISOLATED SANDBOX & VERIFICATION GATE
# Why this block started: Tests GitHub raw stream rewriting, SSRF localhost 
# blocking, and local file:/// exploit blocking, while verifying Phase 1 telemetry.
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 11 Verification Gate (URL Sanitizer & SSRF Guard)...\n")

    from modules.telemetry import GLOBAL_TELEMETRY_LOGGER
    GLOBAL_TELEMETRY_LOGGER.clear()

    # Test 1: GitHub '/blob/' URL auto-rewriting to raw stream
    gh_blob = "https://github.com/mwaskom/seaborn-data/blob/master/iris.csv"
    res_1, rep_1 = validate_and_normalize_url(gh_blob)
    print(f"[Test 1 - GitHub Normalize] -> {res_1['normalized_url']} (Rewritten: {res_1['was_rewritten']})")
    assert res_1["was_rewritten"] is True, "❌ FAIL: GitHub blob URL was not rewritten!"
    assert "raw.githubusercontent.com" in res_1["normalized_url"], "❌ FAIL: Wrong raw host!"

    # Test 2: Block file:/// local disk exploit
    file_blocked = False
    try:
        validate_and_normalize_url("file:///C:/Windows/System32/drivers/etc/hosts")
    except UnsafeURLError as err:
        file_blocked = True
        print(f"[Test 2 - Protocol Guard]   -> Blocked cleanly! ({err})")
    assert file_blocked, "❌ FAIL: file:/// scheme was not blocked!"

    # Test 3: Block SSRF private loopback IP (127.0.0.1)
    ssrf_blocked = False
    try:
        validate_and_normalize_url("http://127.0.0.1:8000/admin/secrets.csv")
    except UnsafeURLError as err:
        ssrf_blocked = True
        print(f"[Test 3 - SSRF IP Guard]    -> Blocked cleanly! ({err})")
    assert ssrf_blocked, "❌ FAIL: Loopback IP 127.0.0.1 was not blocked!"

    # Verify automatic integration with Phase 1 Telemetry Ring Logger
    summary = GLOBAL_TELEMETRY_LOGGER.get_summary()
    print(f"\nPhase 1 Telemetry Integration : {summary['active_logs']} event(s) auto-logged ({rep_1['execution_time_ms']} ms)")
    assert summary["active_logs"] == 1, "❌ FAIL: Telemetry decorator did not log validation!"

    print("\n✅ STEP 11 PASSED: URL Validator, SSRF Guard & Stream Normalizer is verified!")
