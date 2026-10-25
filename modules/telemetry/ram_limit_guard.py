"""
Module: Pre-Execution RAM Circuit Breaker (modules/telemetry/ram_limit_guard.py)
Purpose: Prevents Out-Of-Memory (OOM) system freezes on an 8 GB RAM machine by 
         validating payload sizes and expansion multipliers BEFORE data ingestion.
Why we use zero external libraries:
         Pure mathematical validation runs in O(1) constant time and uses O(1) 
         auxiliary space without adding background library bloat.
"""

from typing import Dict, Any


# -----------------------------------------------------------------------------
# BLOCK 1: CUSTOM EXCEPTION DEFINITION
# Why this block started: Standard Python MemoryError only triggers AFTER the 
# OS has already run out of RAM and frozen. A custom exception lets us catch 
# dangerous payloads proactively and show a clean warning in the Streamlit UI.
# -----------------------------------------------------------------------------
class MemoryBudgetExceededError(Exception):
    """Raised when an incoming dataset threatens to exceed the safe RAM budget."""
    pass


# -----------------------------------------------------------------------------
# BLOCK 2: O(1) PAYLOAD & EXPANSION CIRCUIT BREAKER
# Why this block started: Raw CSV/JSON files expand significantly when parsed 
# into Pandas DataFrames or Vector Embeddings (typically 3x to 5x raw byte size).
# Time Complexity: O(1) — Performs 4 basic floating-point arithmetic operations.
# Space Complexity: O(1) — Allocates a single small dictionary of telemetry values.
# -----------------------------------------------------------------------------
def enforce_ram_budget(
    payload_bytes: int,
    max_budget_mb: float = 50.0,
    expansion_factor: float = 4.0
) -> Dict[str, Any]:
    """
    Validates whether an incoming byte stream can safely fit within our RAM budget.

    Parameters:
        payload_bytes (int): Size of the incoming file/stream in bytes.
        max_budget_mb (float): Maximum safe RAM allocation allowed (default 50 MB).
        expansion_factor (float): Estimated in-memory multiplier (default 4.0x for Pandas).

    Returns:
        dict: Diagnostic telemetry dictionary for the 'Deep Learn' tab.

    Raises:
        ValueError: If payload_bytes is negative.
        MemoryBudgetExceededError: If estimated in-memory size exceeds max_budget_mb.
    """
    if payload_bytes < 0:
        raise ValueError("Payload size in bytes cannot be negative.")

    # Convert raw network bytes to Megabytes (1 MB = 1024 * 1024 bytes)
    raw_size_mb = round(payload_bytes / (1024 * 1024), 4)

    # Calculate estimated RAM needed once parsed into DataFrames/Embeddings
    estimated_ram_mb = round(raw_size_mb * expansion_factor, 4)

    is_safe = estimated_ram_mb <= max_budget_mb

    budget_report = {
        "raw_payload_mb": raw_size_mb,
        "expansion_factor": expansion_factor,
        "estimated_ram_mb": estimated_ram_mb,
        "max_budget_mb": max_budget_mb,
        "status": "APPROVED" if is_safe else "BLOCKED"
    }

    if not is_safe:
        raise MemoryBudgetExceededError(
            f"Circuit Breaker Tripped! Raw file is {raw_size_mb} MB, which will "
            f"expand to ~{estimated_ram_mb} MB in RAM (Limit: {max_budget_mb} MB)."
        )

    return budget_report


# =============================================================================
# BLOCK 3: ISOLATED SANDBOX & VERIFICATION GATE
# Why this block started: Rigorously tests both a safe e-commerce payload (5 MB) 
# and a dangerous payload (25 MB raw -> 100 MB expanded) to prove the breaker trips.
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 03 Verification Gate (RAM Circuit Breaker)...\n")

    # Test 1: Safe Payload (5 MB raw file -> ~20 MB in RAM, well under 50 MB limit)
    safe_bytes = 5 * 1024 * 1024
    report_1 = enforce_ram_budget(safe_bytes, max_budget_mb=50.0, expansion_factor=4.0)
    print(f"[Test 1 - Safe 5 MB File]    -> {report_1}")
    assert report_1["status"] == "APPROVED", "❌ FAIL: Safe payload was blocked!"
    assert report_1["estimated_ram_mb"] == 20.0, "❌ FAIL: Math calculation error!"

    # Test 2: Dangerous Payload (25 MB raw file -> ~100 MB in RAM, exceeds 50 MB limit)
    dangerous_bytes = 25 * 1024 * 1024
    breaker_tripped = False

    try:
        enforce_ram_budget(dangerous_bytes, max_budget_mb=50.0, expansion_factor=4.0)
    except MemoryBudgetExceededError as err:
        breaker_tripped = True
        print(f"[Test 2 - Oversized 25 MB]   -> Successfully Blocked! Reason: {err}")

    assert breaker_tripped, "❌ FAIL: Circuit breaker failed to block oversized payload!"

    print("\n✅ STEP 03 PASSED: Pre-Execution RAM Circuit Breaker is active and verified!")
