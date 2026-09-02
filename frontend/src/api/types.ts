/**
 * ============================================================================
 * MALE UAV AERO PISTON ENGINE DIGITAL TWIN — API CONTRACT TYPES
 * Verified against Python microservice backend sources:
 * - services/api_gateway/main.py
 * - services/telemetry_service/main.py
 * - backend/simulation_engine.py
 * - explainability/xai_engine.py & explainability/shap_explainer.py
 * - services/mongodb_service/main.py
 * 
 * STEP 0 VERIFICATION NOTES:
 * 1. Physics Model: Both `cht_residual` and `cht_residual_C` (and `egt_residual`
 *    vs `egt_residual_C`) are supported to ensure resilience whether backend
 *    supplies raw simulation or formatted feature vector outputs.
 * 2. XAI Structure: Backend xai_engine produces detailed per-model dicts
 *    (fault, anomaly, degradation, rul) with `top_contributors` arrays, as well
 *    as `engineering_interpretation`, `human_summary`, and `recommendations`.
 *    The gateway also handles `top_diagnostic_drivers` if present.
 * 3. RUL Prediction: Handles both "PREDICTED" and "COLLECTING_HISTORY" states.
 * 4. Fault Classification: Predicts classes ('normal', 'overheating',
 *    'lubrication_degradation', 'injector_degradation', 'sensor_fault').
 * ============================================================================
 */

export interface TelemetryData {
  rpm: number;
  throttle_pct: number;
  load_pct: number;
  power_W?: number;
  torque_Nm?: number;
  cht_C: number;
  egt_C: number;
  oil_temperature_C: number;
  oil_pressure_bar: number;
  fuel_flow_kg_s: number;
  air_mass_flow_kg_s?: number;
  vibration_rms: number;
  battery_voltage_V: number;
  alternator_current_A: number;
  altitude_m: number;
  ambient_temp_C: number;
  injection_timing_deg?: number;
  [key: string]: number | undefined;
}

export interface PhysicsModel {
  expected_rpm: number;
  expected_cht_C: number;
  expected_egt_C: number;
  cht_residual?: number;
  cht_residual_C?: number;
  egt_residual?: number;
  egt_residual_C?: number;
  rpm_residual?: number;
  physics_residual_C?: number;
  fuel_air_ratio?: number;
}

export interface AnomalyDetection {
  is_anomaly: boolean;
  anomaly_score: number;
  decision_function: number;
}

export interface DegradationEstimation {
  degradation_index: number;
  estimated_health_pct: number;
}

export type FaultType = 
  | 'normal' 
  | 'overheating' 
  | 'lubrication_degradation' 
  | 'injector_degradation' 
  | 'sensor_fault';

export interface FaultProbabilities {
  normal: number;
  overheating: number;
  lubrication_degradation: number;
  injector_degradation: number;
  sensor_fault: number;
  [key: string]: number;
}

export interface FaultClassification {
  predicted_fault: FaultType | string;
  confidence: number;
  fault_probabilities: FaultProbabilities;
}

export interface RulPrediction {
  status: 'PREDICTED' | 'COLLECTING_HISTORY' | string;
  predicted_rul_hours: number | null;
  raw_rul_hours?: number | null;
  rul_lower_bound_p10?: number | null;
  rul_upper_bound_p90?: number | null;
  uncertainty_std_hours?: number | null;
  confidence_level?: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  records_available?: number;
  records_required?: number;
}

export interface XaiDriver {
  sensor?: string;
  feature?: string;
  display_name?: string;
  impact?: string;
  attribution_score?: number;
  shap_value?: number;
  importance?: number;
  direction?: string;
  direction_text?: string;
  unit?: string;
  value?: number;
}

export interface XaiSubModelExplanation {
  predicted_fault?: string;
  confidence?: number;
  confidence_display?: string;
  is_anomaly?: boolean;
  estimated_health_pct?: number;
  predicted_rul_hours?: number;
  top_contributors?: XaiDriver[];
  summary?: string;
}

export interface XaiPayload {
  overall_status?: string;
  top_diagnostic_drivers?: XaiDriver[];
  fault?: XaiSubModelExplanation;
  anomaly?: XaiSubModelExplanation;
  degradation?: XaiSubModelExplanation;
  rul?: XaiSubModelExplanation;
  engineering_interpretation?: string;
  human_summary?: string;
  recommendations?: string[];
}

export interface TelemetryFrame {
  timestamp_s: number;
  frame_index: number;
  total_frames: number;
  mission_id: number;
  mission_type: string;
  playback_state: 'RUNNING' | 'PAUSED' | 'STOPPED' | string;
  playback_speed: number;
  health_status: 'NOMINAL' | 'WARNING' | 'CRITICAL_FAULT' | 'FAULT' | string;
  telemetry: TelemetryData;
  physics_model: PhysicsModel;
  anomaly_detection: AnomalyDetection;
  degradation_estimation: DegradationEstimation;
  fault_classification: FaultClassification;
  rul_prediction: RulPrediction;
  xai?: XaiPayload;
  xai_explanation?: XaiPayload;
  advisories?: string[];
  model_metadata?: Record<string, any>;
}

export interface ServiceHealthStatus {
  service?: string;
  status: 'HEALTHY' | 'INITIALIZING' | 'OFFLINE' | 'UNHEALTHY' | 'ERROR';
  [key: string]: any;
}

export interface MicroservicesHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'ERROR';
  services: {
    telemetry: ServiceHealthStatus;
    ml_inference: ServiceHealthStatus;
    xai_advisory: ServiceHealthStatus;
    mongodb_atlas: ServiceHealthStatus;
  };
}

export interface MissionsResponse {
  available_mission_ids: number[];
  active_mission_id?: number;
}

export interface SavedMissionsResponse {
  recorded_missions: number[];
}

export interface MissionSummary {
  mission_id: number;
  total_frames: number;
  start_timestamp: string;
  end_timestamp: string;
  max_cht_C: number;
  max_egt_C: number;
  min_oil_pressure_bar: number;
  initial_health_pct: number;
  final_health_pct: number;
  final_rul_hours?: number | null;
  total_anomalies_detected: number;
  total_faults_classified: number;
  overall_mission_status: string;
}

export interface MissionReplayResponse {
  mission_id: number;
  total_recorded_frames: number;
  summary: MissionSummary | null;
  frames: Array<{
    mission_id: number;
    frame_index: number;
    timestamp: string;
    telemetry: TelemetryData;
    physics_residuals: PhysicsModel;
    predictions: {
      anomaly: AnomalyDetection;
      degradation: DegradationEstimation;
      fault: FaultClassification;
      rul: RulPrediction;
    };
    xai_drivers?: XaiDriver[];
    advisories?: string[];
  }>;
}

export interface AdvisoryLogItem {
  _id?: string;
  mission_id: number;
  frame_index: number;
  alert_type: 'NOMINAL' | 'WARNING_ADVISORY' | 'CRITICAL_ALERT' | 'URGENT_MAINTENANCE' | string;
  health_index_pct: number;
  predicted_rul_hours: number | null;
  message: string;
  recommended_action: string;
  timestamp?: string;
}

export interface FleetMetadataItem {
  engine_serial_number: string;
  uav_tail_number: string;
  total_operating_hours: number;
  accumulated_missions_count: number;
  current_engine_health_pct: number;
  last_depot_overhaul: string;
  status: 'AIRWORTHY' | 'DEPOT_MAINTENANCE' | 'GROUNDED' | string;
}

export interface EdgeBenchmarkResponse {
  status: string;
  onboard_edge_execution: {
    anomaly_detection: { artifact_size_kb: number; latency_ms: number; target_tier: string };
    physics_baseline_model: { latency_ms: number; target_tier: string };
  };
  ground_station_execution: {
    degradation_estimation: { latency_ms: number; target_tier: string };
    fault_classification: { latency_ms: number; target_tier: string };
    rul_prediction_131_feat: { artifact_size_kb: number; latency_ms: number; target_tier: string };
    shap_xai_explainer: { latency_ms: number; target_tier: string };
  };
  pipeline_total_latency_ms: number;
  realtime_compliant: boolean;
}

export interface FederatedLearningResponse {
  status: string;
  privacy_level: string;
  fleet_nodes: string[];
  aggregation_algorithm: string;
  metrics: {
    centralized_baseline_r2: number;
    local_only_average_r2: number;
    federated_global_model_r2: number;
    accuracy_retention_pct: number;
  };
}

export interface ScenarioRequest {
  scenario_name?: 'high_altitude' | 'hot_weather' | 'rapid_throttle' | string;
  altitude_m?: number;
  ambient_temp_C?: number;
  throttle_profile?: number[];
  duration_steps?: number;
}
