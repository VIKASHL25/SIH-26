import { create } from 'zustand';
import type { TelemetryFrame } from '../api/types';

export type WebSocketStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR';

interface DigitalTwinState {
  currentFrame: TelemetryFrame | null;
  frameHistory: TelemetryFrame[];
  historyLimit: number;
  wsStatus: WebSocketStatus;
  playbackState: 'RUNNING' | 'PAUSED' | 'STOPPED' | string;
  playbackSpeed: number;
  selectedMissionId: number | null;
  availableMissions: number[];
  activeFaultOverrides: Record<string, number>;
  advisoryList: Array<{ id: string; text: string; timestamp: string; level: 'NOMINAL' | 'WARNING' | 'CRITICAL' }>;
  
  // Actions
  pushFrame: (frame: TelemetryFrame) => void;
  setWsStatus: (status: WebSocketStatus) => void;
  setPlaybackState: (state: string) => void;
  setPlaybackSpeed: (speed: number) => void;
  setSelectedMissionId: (id: number | null) => void;
  setAvailableMissions: (missions: number[]) => void;
  setActiveFaultOverrides: (overrides: Record<string, number>) => void;
  clearHistory: () => void;
  clearAdvisories: () => void;
}

export const useDigitalTwinStore = create<DigitalTwinState>((set) => ({
  currentFrame: null,
  frameHistory: [],
  historyLimit: 120,
  wsStatus: 'DISCONNECTED',
  playbackState: 'STOPPED',
  playbackSpeed: 1.0,
  selectedMissionId: null,
  availableMissions: [],
  activeFaultOverrides: {},
  advisoryList: [],

  pushFrame: (frame: TelemetryFrame) => {
    set((state) => {
      const updatedHistory = [...state.frameHistory, frame];
      if (updatedHistory.length > state.historyLimit) {
        updatedHistory.shift();
      }

      // Process and deduplicate advisories
      const newAdvisories = [...state.advisoryList];
      if (frame.advisories && frame.advisories.length > 0) {
        frame.advisories.forEach((adv) => {
          // Check if same advisory already in the list
          const exists = newAdvisories.some((a) => a.text === adv);
          if (!exists) {
            let level: 'NOMINAL' | 'WARNING' | 'CRITICAL' = 'NOMINAL';
            if (adv.includes('CRITICAL') || adv.includes('ALERT') || adv.includes('FAULT')) {
              level = 'CRITICAL';
            } else if (adv.includes('WARNING') || adv.includes('ADVISORY') || adv.includes('URGENT')) {
              level = 'WARNING';
            }
            newAdvisories.unshift({
              id: `${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
              text: adv,
              timestamp: new Date().toLocaleTimeString(),
              level
            });
          }
        });
      }

      // Limit advisory backlog to 50
      if (newAdvisories.length > 50) {
        newAdvisories.length = 50;
      }

      return {
        currentFrame: frame,
        frameHistory: updatedHistory,
        playbackState: frame.playback_state || state.playbackState,
        playbackSpeed: frame.playback_speed || state.playbackSpeed,
        selectedMissionId: frame.mission_id !== undefined ? frame.mission_id : state.selectedMissionId,
        advisoryList: newAdvisories
      };
    });
  },

  setWsStatus: (status) => set({ wsStatus: status }),
  setPlaybackState: (playbackState) => set({ playbackState }),
  setPlaybackSpeed: (playbackSpeed) => set({ playbackSpeed }),
  setSelectedMissionId: (selectedMissionId) => set({ selectedMissionId }),
  setAvailableMissions: (availableMissions) => set({ availableMissions }),
  setActiveFaultOverrides: (activeFaultOverrides) => set({ activeFaultOverrides }),
  clearHistory: () => set({ frameHistory: [] }),
  clearAdvisories: () => set({ advisoryList: [] }),
}));
