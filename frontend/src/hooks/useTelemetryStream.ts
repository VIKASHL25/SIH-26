import { useEffect, useRef, useCallback } from 'react';
import { useDigitalTwinStore } from '../store/useDigitalTwinStore';
import type { TelemetryFrame } from '../api/types';

export function useTelemetryStream() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const backoffRef = useRef<number>(1000);
  const isManuallyClosedRef = useRef<boolean>(false);

  const {
    currentFrame,
    frameHistory,
    wsStatus,
    pushFrame,
    setWsStatus,
  } = useDigitalTwinStore();

  const getWsUrl = useCallback(() => {
    const envUrl = import.meta.env.VITE_WS_URL;
    if (envUrl) {
      return envUrl;
    }
    const loc = window.location;
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${loc.host}/ws/telemetry`;
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setWsStatus('CONNECTING');
    const wsUrl = getWsUrl();

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('CONNECTED');
        backoffRef.current = 1000;
      };

      ws.onmessage = (event) => {
        try {
          const data: TelemetryFrame = JSON.parse(event.data);
          pushFrame(data);
        } catch (err) {
          console.error('[GCS WS] Failed to parse incoming telemetry frame:', err);
        }
      };

      ws.onerror = (event) => {
        console.warn('[GCS WS] WebSocket encountered error:', event);
        setWsStatus('ERROR');
      };

      ws.onclose = () => {
        setWsStatus('DISCONNECTED');
        wsRef.current = null;

        if (!isManuallyClosedRef.current) {
          const nextRetry = Math.min(backoffRef.current * 1.5, 10000);
          backoffRef.current = nextRetry;
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, nextRetry);
        }
      };
    } catch (err) {
      console.error('[GCS WS] Failed to establish WebSocket connection:', err);
      setWsStatus('ERROR');
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, 3000);
    }
  }, [getWsUrl, pushFrame, setWsStatus]);

  const disconnect = useCallback(() => {
    isManuallyClosedRef.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setWsStatus('DISCONNECTED');
  }, [setWsStatus]);

  const reconnect = useCallback(() => {
    disconnect();
    isManuallyClosedRef.current = false;
    connect();
  }, [disconnect, connect]);

  useEffect(() => {
    isManuallyClosedRef.current = false;
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    currentFrame,
    frameHistory,
    wsStatus,
    reconnect,
  };
}
