XGBoost-Based Real-Time Engine Degradation Estimation

## 1. Objective

The contribution developed for PS 26054 focuses on continuous engine degradation estimation rather than binary fault classification. The objective is to estimate a continuous degradation value from engine and environmental telemetry so that the same model can be used on sequential sensor data in a real-time digital-twin pipeline.

The central modelling principle is: infer degradation from raw sensor behaviour, deviation from expected/nominal engine behaviour, operating-condition relationships, and recent temporal behaviour.

## 2. Problem Formulation

| Item | Decision |
| --- | --- |
| Task | Continuous regression |
| Target | degradation |
| Model | XGBoost Regressor |
| Target range | 0 to 1 |
| Data type | Simulated MALE UAV aero-piston engine telemetry |
| Evaluation unit | Complete missions, not random rows |

## 3. Mission-Level Data Splitting

To avoid leakage between highly correlated consecutive observations, missions were kept completely separate across training, validation, and testing.

| Split | Missions | Samples |
| --- | --- | --- |
| Training | 58 | 58,000 |
| Validation | 21 | 21,000 |
| Test | 21 | 21,000 |

The held-out test missions were subsequently reused as a real-time replay benchmark. This means the real-time experiment does not introduce training leakage: the model is frozen before those telemetry sequences are replayed.

## 4. Feature Policy and Leakage Prevention

Several columns were deliberately excluded because they are identifiers, direct fault information, future/outcome information, or derived health information. This keeps the model focused on observable engine behaviour rather than giving it information that would not be appropriate as a sensor-derived input.

| Excluded feature | Reason |
| --- | --- |
| engine_id | Identifier; not a physical signal |
| mission_id | Mission/session identifier; used only to group temporal data |
| mission_type | Scenario/fault-context information; potential shortcut |
| fault_type | Direct fault label; unavailable to the estimator |
| fault_severity | Direct severity information; closely related to the target |
| failure_flag | Outcome/failure information |
| degradation | Regression target |
| rul_hours | Future/outcome-derived information |
| health_index | Derived health/degradation representation; potential target leakage |
| alternator_health | Constant/irrelevant feature |
| timestamp_s | Excluded from model inputs to prevent learning simulation time as a degradation shortcut |

mission_id and timestamp_s can still exist in the telemetry stream as metadata. mission_id is required internally to maintain per-mission history for causal temporal features, but neither is passed to XGBoost as a predictive feature.

## 5. Feature Engineering

### 5.1 Physics-informed residual features

Expected engine behaviour is used as a reference. Residuals measure the deviation between measured and expected values:

rpm_residual = rpm - expected_rpm

egt_residual = egt_C - expected_egt_C

The supplied physics_residual_C feature was retained. A duplicate CHT residual was not created because it would contain essentially the same information.

### 5.2 Operating-condition features

| Feature | Definition | Purpose |
| --- | --- | --- |
| fuel_air_ratio | fuel_flow / air_mass_flow | Operating mixture relationship |
| power_per_fuel | power / fuel_flow | Efficiency-like operating indicator |
| torque_per_rpm | torque / rpm | Load/engine-speed relationship |
| power_per_air | power / air_mass_flow | Power relative to inducted air |

### 5.3 Causal temporal features

Because the final system is intended for real-time inference, temporal features were constructed causally within each mission. No future sample is used to construct a current prediction.

| Temporal operation | Settings |
| --- | --- |
| Differences | Δ1, Δ5, Δ10 samples |
| Rolling mean | 5, 15, 30 samples |
| Rolling standard deviation | 5, 15, 30 samples |
| Signals | 10 selected engine/physics signals |

The temporal block contributes 90 engineered features (10 signals × 9 temporal features). Together with the base and derived features, the final model input contains 119 features.

## 6. Model Training

XGBoost was selected as the first supervised model because it handles nonlinear relationships well, works efficiently on approximately 100k rows, does not require feature scaling, and provides useful feature-importance tooling. A GPU is optional for this dataset; CPU execution is sufficient, while GPU resources become more useful if a sequence model is evaluated later.

A baseline XGBoost regressor was trained using the training missions. Validation MAE was used for early stopping. A lightweight validation-based hyperparameter search explored tree depth, learning rate, minimum child weight, row subsampling, and feature subsampling.

## 7. Evaluation Metrics

| Metric | Interpretation |
| --- | --- |
| MAE | Average absolute degradation-estimation error |
| RMSE | Penalizes larger estimation errors more strongly |
| R² | Fraction of target variation explained by the model |
| Median Absolute Error | Typical error robust to outliers |
| Maximum Absolute Error | Largest observed prediction deviation |

## 8. Final Test Performance

On the completely unseen test missions, the trained XGBoost model achieved:

| Metric | Result |
| --- | --- |
| MAE | 0.00141 |
| RMSE | 0.00525 |
| R² | 0.99963 |
| Median Absolute Error | 0.00003 |
| Maximum Absolute Error | 0.15502 |

These results are obtained on the supplied simulated dataset and should therefore be described as strong prototype results rather than field-validated UAV performance.

## 9. Model Interpretation

Native XGBoost importance, permutation importance, and SHAP analysis were included to understand which telemetry variables influence degradation estimates. The strongest observed signals included vibration rolling statistics, pressure, physics residuals, and operating conditions. This supports a dashboard presentation in which a degradation estimate can be accompanied by the main contributing indicators.

## 10. Real-Time Replay Benchmark

To test whether the trained model can operate on sequential telemetry, the 21 held-out test missions were converted into a sensor-only replay dataset. This is not a new independently generated dataset; it is the unseen test telemetry replayed one sample at a time as if sensor packets were arriving from the engine.

The real-time input contains the raw telemetry required to reconstruct the 119 model features. The degradation target and fault labels are kept in a separate ground-truth file and are never provided to the inference path.

| File | Role |
| --- | --- |
| realtime_engine_sensor_input.csv | Sensor-only input presented to the real-time inference pipeline |
| realtime_ground_truth.csv | Evaluation-only answer key containing true degradation |
| realtime_predictions.csv | Predictions produced by the replay/inference pipeline |
| realtime_prediction_template.csv | Optional output format/template; not required for evaluation |

## 11. Batch-to-Real-Time Consistency

The same held-out samples were evaluated through both the normal batch pipeline and the sequential real-time replay pipeline. The resulting predictions were effectively identical:

| Check | Observed difference |
| --- | --- |
| Maximum absolute prediction difference | 1.1102230246251565 × 10⁻¹⁶ |
| Mean absolute prediction difference | 1.1801828347854324 × 10⁻¹⁷ |

These values are at floating-point numerical precision. Therefore, the real-time feature construction and model inference reproduce the batch predictions correctly for the same telemetry samples.

## 12. Real-Time Evaluation Results

The replay predictions were matched against the separate ground-truth file using stream_row_id, mission_id, and timestamp_s. A one-to-one alignment check was used before calculating the metrics.

| Metric | Real-time replay |
| --- | --- |
| MAE | 0.001407 |
| RMSE | 0.005255 |
| R² | 0.999626 |
| Median Absolute Error | 0.000032 |
| Maximum Absolute Error | 0.155019 |

The real-time replay therefore reproduces the quality of the batch test evaluation.

## 13. Current Limitations and Next Work

The dataset is simulated because representative real UAV aero-piston engine telemetry was unavailable.

The current real-time benchmark is a replay of held-out telemetry, not a live physical engine connection.

The very high test performance should be followed by robustness testing before making strong real-world claims.

The next priority is to test noise, missing packets, sensor spikes, sensor drift, and sensor dropout.

Large-error samples should be inspected individually, especially the maximum-error cases.

Only if the XGBoost model shows a meaningful weakness on these robustness/trajectory tests should LSTM or 1D-CNN be introduced.

Future deployment should retain the exact feature-generation configuration and model artifact so training and inference remain identical.

## 14. Reproducibility / Artifacts

The trained model was saved together with the exact feature list and feature-engineering configuration. These artifacts allow the same preprocessing and feature ordering to be reconstructed for future inference.

| Artifact | Purpose |
| --- | --- |
| xgb_degradation_model.json | Trained XGBoost degradation regressor |
| feature_columns.json | Exact 119 model-input feature names/order |
| feature_config.json | Feature-engineering and temporal configuration |

## 15. Contribution Summary

The developed contribution is a physics-informed, temporally aware XGBoost regression pipeline for continuous engine degradation estimation. It combines raw telemetry with nominal-behaviour residuals, operating-condition ratios, and causal temporal statistics. Mission-level separation prevents sequence leakage, while the real-time replay benchmark verifies that sequential inference uses the same feature representation and produces effectively identical predictions to the batch pipeline. On the supplied simulated data, the approach achieves MAE ≈ 0.00141 and R² ≈ 0.99963 on unseen missions.
