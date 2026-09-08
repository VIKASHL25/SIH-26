function run_mission(mission_id, stop_time)
%% SIH 2026 - Simulink Mission Runner
%
% Usage:
%   run_mission(1)
%   run_mission(25)
%   run_mission(100)
%
% Optional:
%   run_mission(25, 30)
%
% This loads the selected mission from the 100k dataset,
% creates telemetry_ts, and runs the existing Simulink model.

clc;

%% Default arguments

if nargin < 1
    mission_id = 1;
end

if nargin < 2
    stop_time = 30;
end

%% Project paths

project_root = 'C:\Users\User\OneDrive\Desktop\Projects\SIH\SIH-26';

dataset_path = fullfile( ...
    project_root, ...
    'data', ...
    'MALE_UAV_aero_piston_engine_final_100k.csv');

simulink_model = fullfile( ...
    project_root, ...
    'simulink', ...
    'simulink_udp_poc');

fprintf('Dataset path:\n%s\n\n', dataset_path);

%% Validate mission

if ~isscalar(mission_id) || ...
        mission_id < 1 || ...
        mission_id > 100 || ...
        mod(mission_id, 1) ~= 0

    error('mission_id must be an integer between 1 and 100.');
end

%% Validate stop time

if stop_time <= 0
    error('stop_time must be greater than 0.');
end

%% Check dataset

if ~isfile(dataset_path)
    error('Dataset not found:\n%s', dataset_path);
end

%% Load dataset

fprintf('Loading dataset...\n');

T = readtable(dataset_path);

fprintf('Dataset loaded: %d rows\n', height(T));

%% Select mission

mission_data = T( ...
    strcmp(T.engine_id, 'ENGINE_001') & ...
    T.mission_id == mission_id, :);

if isempty(mission_data)
    error('Mission %d was not found in the dataset.', mission_id);
end

%% Sort mission by timestamp

mission_data = sortrows(mission_data, 'timestamp_s');

%% Build 20-signal telemetry matrix

telemetry_data = [
    mission_data.rpm, ...
    mission_data.throttle_pct, ...
    mission_data.load_pct, ...
    mission_data.cht_C, ...
    mission_data.egt_C, ...
    mission_data.oil_temperature_C, ...
    mission_data.oil_pressure_bar, ...
    mission_data.air_mass_flow_kg_s, ...
    mission_data.fuel_flow_kg_s, ...
    mission_data.torque_Nm, ...
    mission_data.power_W, ...
    mission_data.vibration_rms, ...
    mission_data.battery_voltage_V, ...
    mission_data.alternator_current_A, ...
    mission_data.alternator_health, ...
    mission_data.altitude_m, ...
    mission_data.ambient_temp_C, ...
    mission_data.pressure_kPa, ...
    mission_data.injection_timing_deg, ...
    mission_data.air_density_kg_m3
];

%% Create Simulink timeseries

telemetry_ts = timeseries( ...
    telemetry_data, ...
    mission_data.timestamp_s);

%% Send telemetry to MATLAB base workspace

assignin('base', 'telemetry_ts', telemetry_ts);
assignin('base', 'mission_id', mission_id);

%% Display mission information

fprintf('\n');
fprintf('========================================\n');
fprintf('       SIMULINK MISSION REPLAY\n');
fprintf('========================================\n');
fprintf('Mission ID : %d\n', mission_id);
fprintf('Engine     : %s\n', string(mission_data.engine_id(1)));
fprintf('Samples    : %d\n', height(mission_data));
fprintf('Start time : %.0f s\n', mission_data.timestamp_s(1));
fprintf('End time   : %.0f s\n', mission_data.timestamp_s(end));
fprintf('Signals    : %d\n', size(telemetry_data, 2));
fprintf('Stop time  : %.0f s\n', stop_time);
fprintf('========================================\n\n');

%% Verify telemetry variable

if ~evalin('base', 'exist(''telemetry_ts'', ''var'')')
    error('telemetry_ts was not created in the MATLAB base workspace.');
end

fprintf('telemetry_ts created successfully.\n');

%% Run Simulink

fprintf('\nStarting Simulink Mission %d...\n', mission_id);
fprintf('Stop time: %.0f seconds\n\n', stop_time);

sim(simulink_model, ...
    'StopTime', num2str(stop_time));

%% Completion

fprintf('\n');
fprintf('========================================\n');
fprintf('Mission %d replay completed successfully.\n', mission_id);
fprintf('========================================\n');

end