"""
Module: Automated Industry & Sector Classifier (modules/eda_engine/sector_classifier.py)
Purpose: Classifies a dataset's business domain (E-Commerce, FinTech, Healthcare,
         Logistics, SaaS, or General Tabular) in O(C) time by matching normalized 
         column tokens against weighted domain lexicons.
"""

import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry

SECTOR_LEXICONS: Dict[str, List[str]] = {
    "E_COMMERCE_RETAIL": [
        "sku", "order", "cart", "product", "item", "price", "discount",
        "revenue", "customer", "quantity", "qty", "category", "merchant"
    ],
    "FINTECH_BANKING": [
        "transaction", "account", "balance", "credit", "debit", "iban",
        "currency", "interest", "loan", "fraud", "ledger", "payment", "kyc"
    ],
    "HEALTHCARE_CLINICAL": [
        "patient", "diagnosis", "symptom", "dosage", "clinic", "hospital",
        "bp", "glucose", "heart", "medical", "icd", "treatment", "ward"
    ],
    "LOGISTICS_SUPPLY_CHAIN": [
        "shipment", "warehouse", "carrier", "tracking", "freight", "origin",
        "destination", "eta", "route", "inventory", "pallet", "dispatch"
    ],
    "SAAS_TELEMETRY": [
        "user_id", "session", "churn", "mrr", "arr", "subscription",
        "latency", "plan", "signup", "retention", "active_users"
    ]
}


@auto_log_telemetry(module_name="eda_engine")
def classify_dataset_sector(columns: List[str]) -> Dict[str, Any]:
    """
    Classifies the business domain of a dataset from its column names in O(C) time.
    """
    if not columns:
        return {
            "primary_sector": "GENERAL_TABULAR",
            "confidence": 0.0,
            "matched_keywords": [],
            "sector_scores": {}
        }

    norm_cols = [c.lower().strip() for c in columns]
    scores: Dict[str, int] = {}
    matched_by_sector: Dict[str, List[str]] = {}

    for sector, keywords in SECTOR_LEXICONS.items():
        hits: List[str] = []
        for col in norm_cols:
            for kw in keywords:
                if kw in col:
                    hits.append(f"{col}->{kw}")
                    break
        scores[sector] = len(hits)
        matched_by_sector[sector] = hits

    best_sector = max(scores, key=lambda k: scores[k])
    best_score = scores[best_sector]

    if best_score == 0:
        primary_sector = "GENERAL_TABULAR"
        confidence = 0.0
        matched = []
    else:
        primary_sector = best_sector
        confidence = round(min(1.0, best_score / max(1, len(norm_cols))), 2)
        matched = matched_by_sector[best_sector]

    return {
        "primary_sector": primary_sector,
        "confidence": confidence,
        "matched_keywords": matched,
        "sector_scores": scores
    }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 24 Verification Gate (Industry Sector Classifier)...\n")

    ecom_cols = ["order_id", "sku", "customer_id", "unit_price", "discount_pct", "order_date"]
    fintech_cols = ["transaction_id", "account_balance", "credit_score", "debit_amount", "fraud_flag"]

    res_ecom, rep = classify_dataset_sector(ecom_cols)
    res_fin, _ = classify_dataset_sector(fintech_cols)

    print(f"[E-Commerce Test] -> {res_ecom['primary_sector']} (Confidence: {res_ecom['confidence']}) in {rep['execution_time_ms']} ms")
    print(f"[FinTech Test]    -> {res_fin['primary_sector']} (Confidence: {res_fin['confidence']})")

    assert res_ecom["primary_sector"] == "E_COMMERCE_RETAIL", "❌ FAIL: E-Commerce classification failed!"
    assert res_fin["primary_sector"] == "FINTECH_BANKING", "❌ FAIL: FinTech classification failed!"

    print("\n✅ STEP 24 PASSED: Automated Industry & Sector Classifier is verified!")
