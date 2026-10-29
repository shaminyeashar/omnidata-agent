"""
Module: Empirical Big-O Complexity Estimator (modules/telemetry/complexity_estimator.py)
Purpose: Computes the empirical scaling exponent (doubling ratio slope) between 
         two workload sizes (N1, N2) and their telemetry measurements (T1, T2) 
         to classify runtime/space complexity into Big-O classes for the 
         'Deep Learn' educational tab.
Why we use standard libraries (math, typing):
         Pure logarithmic arithmetic runs in O(1) time and O(1) space.
"""

import math
import os
import sys
from typing import Dict, Any

# Ensure project root is on sys.path when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


# -----------------------------------------------------------------------------
# BLOCK 1: LOGARITHMIC SCALING SLOPE & BIG-O CLASSIFIER
# Why this block started: Given two sample sizes (N1 < N2) and their measured 
# costs (cost_1, cost_2 in ms or MB), we compute slope b = log2(cost2/cost1) / log2(N2/N1)
# to mathematically prove how an algorithm scales on your hardware.
# Time Complexity: O(1) | Space Complexity: O(1)
# -----------------------------------------------------------------------------
def estimate_big_o(
    n1: int,
    cost_1: float,
    n2: int,
    cost_2: float,
    metric_type: str = "Time"
) -> Dict[str, Any]:
    """
    Estimates the Big-O complexity class from two empirical telemetry points.
    """
    if n1 <= 0 or n2 <= 0 or n2 <= n1:
        raise ValueError("Input sizes must be positive integers with n2 > n1.")
    if cost_1 < 0 or cost_2 < 0:
        raise ValueError("Telemetry costs cannot be negative.")

    # Clamp near-zero measurements to a tiny epsilon (1e-6) to prevent division by zero
    c1 = max(cost_1, 1e-6)
    c2 = max(cost_2, 1e-6)

    size_ratio = round(n2 / n1, 4)
    cost_ratio = round(c2 / c1, 4)

    # Compute logarithmic exponent b = log2(c2/c1) / log2(n2/n1)
    if cost_ratio <= 1.05:
        exponent = 0.0
    else:
        exponent = round(math.log2(cost_ratio) / math.log2(size_ratio), 3)

    # Map empirical exponent to standard Big-O complexity classes
    if exponent <= 0.15:
        big_o = "O(1) Constant"
    elif exponent <= 0.65:
        big_o = "O(log N) Logarithmic"
    elif exponent <= 1.35:
        big_o = "O(N) Linear"
    elif exponent <= 1.65:
        big_o = "O(N log N) Log-Linear"
    else:
        big_o = "O(N^2) Quadratic+"

    return {
        "metric_type": metric_type,
        "n1": n1,
        "n2": n2,
        "size_multiplier": size_ratio,
        "cost_multiplier": cost_ratio,
        "empirical_exponent": exponent,
        "estimated_complexity": big_o
    }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# Why this block started: Verifies O(1), O(N), and O(N^2) scaling proofs.
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 08 Verification Gate (Big-O Complexity Estimator)...\n")

    # Test 1: O(1) Constant scaling (N grows 10x, time stays ~2.0 ms)
    res_o1 = estimate_big_o(n1=1_000, cost_1=2.0, n2=10_000, cost_2=2.05, metric_type="Time")
    print(f"[Test 1 - Constant]  -> {res_o1['estimated_complexity']} (exponent={res_o1['empirical_exponent']})")

    # Test 2: O(N) Linear scaling (N grows 10x, RAM grows ~10x from 1.5 MB to 15.0 MB)
    res_on = estimate_big_o(n1=10_000, cost_1=1.5, n2=100_000, cost_2=15.0, metric_type="Space")
    print(f"[Test 2 - Linear]    -> {res_on['estimated_complexity']} (exponent={res_on['empirical_exponent']})")

    # Test 3: O(N^2) Quadratic scaling (N doubles 2x, time quadruples 4x from 10 ms to 40 ms)
    res_on2 = estimate_big_o(n1=1_000, cost_1=10.0, n2=2_000, cost_2=40.0, metric_type="Time")
    print(f"[Test 3 - Quadratic] -> {res_on2['estimated_complexity']} (exponent={res_on2['empirical_exponent']})")

    assert res_o1["estimated_complexity"] == "O(1) Constant", "❌ FAIL: O(1) classification failed!"
    assert res_on["estimated_complexity"] == "O(N) Linear", "❌ FAIL: O(N) classification failed!"
    assert res_on2["estimated_complexity"] == "O(N^2) Quadratic+", "❌ FAIL: O(N^2) classification failed!"

    print("\n✅ STEP 08 PASSED: Empirical Big-O Complexity Estimator is verified!")
