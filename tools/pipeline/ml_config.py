# -*- coding: utf-8 -*-
# Configuration for ML analysis components

# Thresholds for KPI extraction and analysis
kpi_thresholds = {
    "brake_pressure": 0.8,  # 80% brake pressure to detect a braking point
    "throttle_application": 0.9,  # 90% throttle to detect throttle application point
    "time_on_brake": 0.1,  # Minimum brake pressure to be considered "on brake"
}

# Impact scores for prioritization in SectionAnalyser
impact_scores = {
    "apex_speed_delta_kph": -2.0,
    "apex_speed_impact": 10,
    "braking_point_early_m": -5.0,
    "braking_point_early_impact": 8,
    "braking_point_late_m": 5.0,
    "braking_point_late_impact": 8,
    "throttle_point_late_m": 5.0,
    "throttle_point_impact": 7,
    "time_delta_multiplier": 20,
}

# Thresholds for generating recommendations in SectionAnalyser
recommendation_thresholds = {
    "braking_point_late_m": 5.0,
    "braking_point_early_m": -5.0,
    "apex_speed_slower_kph": -2.0,
    "throttle_point_late_m": 5.0,
    "time_on_throttle_less_pct": -5.0,
    "min_time_delta_for_general_rec_ms": 100,
}

# Thresholds for weather correlation analysis
weather_thresholds = {
    "significant_correlation": 0.3,
    "strong_correlation": 0.5,
}

# Consistency scores for PatternAnalyser
pattern_scores = {
    "consistency_std_multiplier": 5.0,
    "trend_improvement_threshold_s": -0.1,
    "trend_decline_threshold_s": 0.1,
    "section_consistency_high_std": 0.1,
    "section_consistency_moderate_std": 0.3,
    "consistency_trend_improving_score": 7.0,
}

# General analysis parameters
analysis_params = {
    "min_laps_for_pattern_trend": 3,
    "min_impact_score_for_recommendation": 15,
}














