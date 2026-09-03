import axios from 'axios';
import type {
  MicroservicesHealth,
  MissionsResponse,
  SavedMissionsResponse,
  MissionReplayResponse,
  AdvisoryLogItem,
  FleetMetadataItem,
  EdgeBenchmarkResponse,
  FederatedLearningResponse,
  ScenarioRequest,
  TelemetryFrame
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

export const api = {
  // Microservices & System Health
  async getHealth(): Promise<MicroservicesHealth> {
    const res = await apiClient.get<MicroservicesHealth>('/api/health');
    return res.data;
  },

  // Missions & Telemetry Simulation Controls
  async listMissions(): Promise<MissionsResponse> {
    const res = await apiClient.get<MissionsResponse>('/api/missions');
    return res.data;
  },

  async loadMission(missionId: number): Promise<{ message: string; active_mission_id: number; total_frames: number }> {
    const res = await apiClient.post('/api/simulation/load_mission', { mission_id: missionId });
    return res.data;
  },

  async startSimulation(): Promise<{ message: string; state: string }> {
    const res = await apiClient.post('/api/simulation/start');
    return res.data;
  },

  async pauseSimulation(): Promise<{ message: string; state: string }> {
    const res = await apiClient.post('/api/simulation/pause');
    return res.data;
  },

  async stepSimulation(): Promise<TelemetryFrame> {
    const res = await apiClient.post<TelemetryFrame>('/api/simulation/step');
    return res.data;
  },

  async setSpeed(speed: number): Promise<{ message: string; speed: number }> {
    const res = await apiClient.post('/api/simulation/speed', { speed });
    return res.data;
  },

  async seekFrame(frameIdx: number): Promise<{ message: string; frame_index: number }> {
    const res = await apiClient.post('/api/simulation/seek', { frame_idx: frameIdx });
    return res.data;
  },

  // Fault Injection & "What-If" Analysis
  async injectFault(overrides: Record<string, number>): Promise<{ message: string; active_overrides: Record<string, number> }> {
    const res = await apiClient.post('/api/simulation/inject_fault', { overrides });
    return res.data;
  },

  async clearFaults(): Promise<{ message: string }> {
    const res = await apiClient.post('/api/simulation/clear_faults');
    return res.data;
  },

  // Scenario Simulation
  async simulateScenario(req: ScenarioRequest): Promise<any> {
    const res = await apiClient.post('/api/simulation/scenario', req, { timeout: 35000 });
    return res.data;
  },

  // Analytics
  async getEdgeBenchmark(): Promise<EdgeBenchmarkResponse> {
    const res = await apiClient.get<EdgeBenchmarkResponse>('/api/analytics/edge_benchmark');
    return res.data;
  },

  async getFederatedLearning(): Promise<FederatedLearningResponse> {
    const res = await apiClient.get<FederatedLearningResponse>('/api/analytics/federated_learning');
    return res.data;
  },

  // MongoDB Atlas Persistence Endpoints
  async getSavedMissions(): Promise<SavedMissionsResponse> {
    const res = await apiClient.get<SavedMissionsResponse>('/api/db/saved_missions');
    return res.data;
  },

  async getMissionReplay(missionId: number): Promise<MissionReplayResponse> {
    const res = await apiClient.get<MissionReplayResponse>(`/api/db/mission/${missionId}/replay`);
    return res.data;
  },

  async getAdvisories(missionId?: number): Promise<{ advisories: AdvisoryLogItem[] }> {
    const url = missionId !== undefined ? `/api/db/advisories?mission_id=${missionId}` : '/api/db/advisories';
    const res = await apiClient.get<{ advisories: AdvisoryLogItem[] }>(url);
    return res.data;
  },

  async getFleetMetadata(): Promise<{ fleet: FleetMetadataItem[] }> {
    const res = await apiClient.get<{ fleet: FleetMetadataItem[] }>('/api/db/fleet_metadata');
    return res.data;
  },
};
