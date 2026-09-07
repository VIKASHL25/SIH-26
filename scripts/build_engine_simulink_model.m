%% =========================================================================
% Script: build_engine_simulink_model.m
% Purpose: Programmatically builds and configures the complete MALE UAV 
%          Aero Piston Engine Digital Twin Simulink Model (.slx).
% Model:   TAPAS-BH-201 / Rotax 914/915 Turbocharged Boxer Engine
% =========================================================================

function build_engine_simulink_model()
    modelName = 'AeroPistonEngine_DigitalTwin';
    
    % Close and delete existing model if open
    if bdIsLoaded(modelName)
        close_system(modelName, 0);
    end
    if exist([modelName, '.slx'], 'file') == 4
        delete([modelName, '.slx']);
    end
    
    % Create new Simulink Model
    new_system(modelName);
    open_system(modelName);
    
    % Configure Model Solver Parameters (Continuous ODE45 for High Fidelity)
    set_param(modelName, 'Solver', 'ode45');
    set_param(modelName, 'StopTime', '1500');
    set_param(modelName, 'RelTol', '1e-4');
    set_param(modelName, 'AbsTol', '1e-6');
    set_param(modelName, 'SaveTime', 'on');
    set_param(modelName, 'SaveOutput', 'on');
    
    disp(['[SIMULINK] Creating Architecture for: ', modelName, '...']);
    
    %% ---------------------------------------------------------------------
    % 1. FUEL SYSTEM & INJECTION SUBSYSTEM
    %% ---------------------------------------------------------------------
    add_block('simulink/Sources/Constant', [modelName, '/ConstStoich'], ...
        'Value', '14.7', 'Position', [50, 80, 100, 110]);
    
    add_block('simulink/Discontinuities/Saturation', [modelName, '/SatFuelAir'], ...
        'UpperLimit', '25.0', 'LowerLimit', '8.0', 'Position', [140, 80, 180, 110]);
    
    add_block('simulink/Math Operations/Sum', [modelName, '/SumAirFuel'], ...
        'Inputs', '+-', 'Position', [220, 85, 245, 110]);
        
    add_block('simulink/User-Defined Functions/Fcn', [modelName, '/FcnAirFuel'], ...
        'Expr', 'u(1)/(u(2)+1e-6)', 'Position', [280, 80, 360, 115]);
        
    add_block('simulink/Signal Routing/Switch', [modelName, '/SwitchAirGate'], ...
        'Criteria', 'u2 > Threshold', 'Threshold', '0.5', 'Position', [400, 75, 450, 125]);
        
    add_block('simulink/Math Operations/Gain', [modelName, '/GainLambda'], ...
        'Gain', '1/14.7', 'Position', [500, 85, 550, 115]);
        
    % To Workspace Blocks for AFR & Lambda
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_afr_out'], ...
        'VariableName', 'out_afr_out', 'SaveFormat', 'Array', 'Position', [600, 45, 700, 75]);
        
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_lambda_out'], ...
        'VariableName', 'out_lambda_out', 'SaveFormat', 'Array', 'Position', [600, 95, 700, 125]);

    %% ---------------------------------------------------------------------
    % 2. COMBUSTION & HEAT PARTITIONING
    %% ---------------------------------------------------------------------
    add_block('simulink/User-Defined Functions/Fcn', [modelName, '/FcnCombustionHeat'], ...
        'Expr', 'u(1) * 44e6 * 0.32', 'Position', [280, 180, 380, 220]);
        
    add_block('simulink/Discontinuities/Saturation', [modelName, '/MinMaxCombustion'], ...
        'UpperLimit', '120000', 'LowerLimit', '5000', 'Position', [420, 180, 470, 220]);

    %% ---------------------------------------------------------------------
    % 3. 4-CYLINDER THERMAL HEAD (CHT 1..4)
    %% ---------------------------------------------------------------------
    % Cylinder 1
    add_block('simulink/Continuous/Integrator', [modelName, '/Integrator_Cht1'], ...
        'InitialCondition', '95.0', 'Position', [650, 180, 690, 220]);
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_cht1_out'], ...
        'VariableName', 'out_cht1_out', 'SaveFormat', 'Array', 'Position', [750, 185, 850, 215]);

    % Cylinder 2
    add_block('simulink/Math Operations/Gain', [modelName, '/GainCht2Rate'], ...
        'Gain', '1.02', 'Position', [550, 240, 590, 270]);
    add_block('simulink/Continuous/Integrator', [modelName, '/Integrator_Cht2'], ...
        'InitialCondition', '96.0', 'Position', [650, 240, 690, 280]);
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_cht2_out'], ...
        'VariableName', 'out_cht2_out', 'SaveFormat', 'Array', 'Position', [750, 245, 850, 275]);

    % Cylinder 3
    add_block('simulink/Math Operations/Gain', [modelName, '/GainCht3Rate'], ...
        'Gain', '0.99', 'Position', [550, 300, 590, 330]);
    add_block('simulink/Continuous/Integrator', [modelName, '/Integrator_Cht3'], ...
        'InitialCondition', '94.5', 'Position', [650, 300, 690, 340]);
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_cht3_out'], ...
        'VariableName', 'out_cht3_out', 'SaveFormat', 'Array', 'Position', [750, 305, 850, 335]);

    % Cylinder 4
    add_block('simulink/Math Operations/Gain', [modelName, '/GainCht4Rate'], ...
        'Gain', '1.03', 'Position', [550, 360, 590, 390]);
    add_block('simulink/Continuous/Integrator', [modelName, '/Integrator_Cht4'], ...
        'InitialCondition', '97.0', 'Position', [650, 360, 690, 400]);
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_cht4_out'], ...
        'VariableName', 'out_cht4_out', 'SaveFormat', 'Array', 'Position', [750, 365, 850, 395]);

    %% ---------------------------------------------------------------------
    % 4. EXHAUST GAS DYNAMICS (EGT)
    %% ---------------------------------------------------------------------
    add_block('simulink/Signal Routing/Switch', [modelName, '/SwitchEgtGate'], ...
        'Criteria', 'u2 > Threshold', 'Threshold', '0.8', 'Position', [550, 440, 600, 490]);
        
    add_block('simulink/Continuous/Integrator', [modelName, '/Integrator_Egt'], ...
        'InitialCondition', '550.0', 'Position', [650, 445, 690, 485]);
        
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_egt_out'], ...
        'VariableName', 'out_egt_out', 'SaveFormat', 'Array', 'Position', [750, 450, 850, 480]);

    %% ---------------------------------------------------------------------
    % 5. MECHANICAL POWERTRAIN, LUBRICATION & OIL DYNAMICS
    %% ---------------------------------------------------------------------
    add_block('simulink/User-Defined Functions/Fcn', [modelName, '/FcnFrict'], ...
        'Expr', '0.08 * u(1) * (u(2)/2500)^1.5', 'Position', [280, 540, 380, 575]);
        
    add_block('simulink/User-Defined Functions/Fcn', [modelName, '/FcnOilPressure'], ...
        'Expr', '4.5 * (u(1)/2400) * (85.0 / max(40.0, u(2)))', 'Position', [420, 540, 530, 575]);
        
    add_block('simulink/Discontinuities/Saturation', [modelName, '/SatOilPressure'], ...
        'UpperLimit', '7.0', 'LowerLimit', '0.5', 'Position', [570, 540, 610, 575]);
        
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_oil_pressure_out'], ...
        'VariableName', 'out_oil_pressure_out', 'SaveFormat', 'Array', 'Position', [750, 545, 850, 575]);

    add_block('simulink/User-Defined Functions/Fcn', [modelName, '/FcnOilHeatTotal'], ...
        'Expr', 'u(1) * 0.15 + u(2) * 0.05', 'Position', [420, 610, 530, 645]);
        
    add_block('simulink/Sinks/To Workspace', [modelName, '/out_q_head_out'], ...
        'VariableName', 'out_q_head_out', 'SaveFormat', 'Array', 'Position', [750, 615, 850, 645]);

    %% ---------------------------------------------------------------------
    % 6. WIRING CONNECTIONS
    %% ---------------------------------------------------------------------
    % Fuel / Air
    add_line(modelName, 'ConstStoich/1', 'SatFuelAir/1');
    add_line(modelName, 'SatFuelAir/1', 'SumAirFuel/1');
    add_line(modelName, 'SumAirFuel/1', 'FcnAirFuel/1');
    add_line(modelName, 'FcnAirFuel/1', 'SwitchAirGate/1');
    add_line(modelName, 'SwitchAirGate/1', 'GainLambda/1');
    add_line(modelName, 'SwitchAirGate/1', 'out_afr_out/1');
    add_line(modelName, 'GainLambda/1', 'out_lambda_out/1');

    % Combustion to CHTs
    add_line(modelName, 'FcnCombustionHeat/1', 'MinMaxCombustion/1');
    add_line(modelName, 'MinMaxCombustion/1', 'Integrator_Cht1/1');
    add_line(modelName, 'MinMaxCombustion/1', 'GainCht2Rate/1');
    add_line(modelName, 'MinMaxCombustion/1', 'GainCht3Rate/1');
    add_line(modelName, 'MinMaxCombustion/1', 'GainCht4Rate/1');
    
    add_line(modelName, 'GainCht2Rate/1', 'Integrator_Cht2/1');
    add_line(modelName, 'GainCht3Rate/1', 'Integrator_Cht3/1');
    add_line(modelName, 'GainCht4Rate/1', 'Integrator_Cht4/1');

    add_line(modelName, 'Integrator_Cht1/1', 'out_cht1_out/1');
    add_line(modelName, 'Integrator_Cht2/1', 'out_cht2_out/1');
    add_line(modelName, 'Integrator_Cht3/1', 'out_cht3_out/1');
    add_line(modelName, 'Integrator_Cht4/1', 'out_cht4_out/1');

    % EGT & Oil
    add_line(modelName, 'SwitchEgtGate/1', 'Integrator_Egt/1');
    add_line(modelName, 'Integrator_Egt/1', 'out_egt_out/1');

    add_line(modelName, 'FcnOilPressure/1', 'SatOilPressure/1');
    add_line(modelName, 'SatOilPressure/1', 'out_oil_pressure_out/1');
    add_line(modelName, 'FcnOilHeatTotal/1', 'out_q_head_out/1');

    %% ---------------------------------------------------------------------
    % SAVE MODEL
    %% ---------------------------------------------------------------------
    save_system(modelName);
    disp(['[SUCCESS] Successfully generated Simulink Model: ', modelName, '.slx']);
end
