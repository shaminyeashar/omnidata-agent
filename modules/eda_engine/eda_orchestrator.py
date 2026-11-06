"""
Module: Master EDA Pipeline Orchestrator (modules/eda_engine/eda_orchestrator.py)
Purpose: Unites all 13 EDA modules into a single memory-safe execution block.
"""
import os
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry, GLOBAL_TELEMETRY_LOGGER, reclaim_memory
from modules.eda_engine.numeric_profiler import profile_numeric_columns
from modules.eda_engine.categorical_profiler import profile_categorical_columns
from modules.eda_engine.outlier_detector import detect_numeric_outliers
from modules.eda_engine.sector_classifier import classify_dataset_sector
from modules.eda_engine.missing_value_analyzer import analyze_missing_values
from modules.eda_engine.correlation_matrix import compute_correlation_matrix
from modules.eda_engine.temporal_profiler import profile_temporal_columns
from modules.eda_engine.kpi_synthesizer import synthesize_executive_kpis
from modules.eda_engine.distribution_analyzer import analyze_distributions
from modules.eda_engine.data_quality_scorer import compute_data_quality_score
from modules.eda_engine.chart_recommender import recommend_visualizations
from modules.eda_engine.duplicate_detector import detect_duplicates
from modules.eda_engine.insight_narrator import generate_narrative_insights

@auto_log_telemetry(module_name="eda_engine")
def run_full_eda_pipeline(
    parsed_data: List[Dict[str, Any]],
    primary_key: Optional[str] = None
) -> Dict[str, Any]:
    
    # 1. Base Profiles
    num_stats, _ = profile_numeric_columns(parsed_data)
    cat_stats, _ = profile_categorical_columns(parsed_data)
    temp_stats, _ = profile_temporal_columns(parsed_data)
    
    # 2. Sector & Completeness
    columns = list(parsed_data[0].keys()) if parsed_data else []
    sector_info, _ = classify_dataset_sector(columns)
    missing_info, _ = analyze_missing_values(parsed_data)
    dup_info, _ = detect_duplicates(parsed_data, primary_key)
    
    # 3. Advanced Math
    outliers, _ = detect_numeric_outliers(parsed_data, numeric_stats=num_stats)
    dists, _ = analyze_distributions(parsed_data, numeric_stats=num_stats)
    correlations, _ = compute_correlation_matrix(parsed_data)
    
    # 4. Synthesized Outputs
    kpis, _ = synthesize_executive_kpis(len(parsed_data), num_stats, cat_stats, sector_info)
    health, _ = compute_data_quality_score(missing_info, outliers)
    charts, _ = recommend_visualizations(num_stats, cat_stats, dists, temp_stats, correlations)
    insights, _ = generate_narrative_insights(kpis, health, correlations)
    
    # Explicit Memory Sweep after intense profiling
    reclaim_memory(generation=2, logger=GLOBAL_TELEMETRY_LOGGER)

    return {
        "dataset_rows": len(parsed_data),
        "kpis": kpis,
        "health_score": health,
        "insights": insights,
        "charts": charts,
        "outliers": outliers,
        "duplicates": dup_info,
        "missing_data": missing_info,
        "sector_context": sector_info,
        "correlations": correlations
    }
