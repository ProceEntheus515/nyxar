import { useEffect } from 'react';
import { io } from 'socket.io-client';
import { useStore } from '../store';

const SOCKET_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000';

export function useWebSocket() {
  const { 
    addEvent, addEventBatch, addAlert, updateIdentity, 
    addAiMemo, updateStats, setInitialState,
    setHealthReport, setHealthThroughput,
    setWsConnected,
  } = useStore();

  useEffect(() => {
    const socket = io(SOCKET_URL, {
      reconnectionDelayMax: 10000,
      reconnection: true,
      transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
      setWsConnected(true);
    });

    socket.on('initial_state', (payload) => {
      setInitialState(payload);
    });

    socket.on('new_event', (event) => {
      addEvent(event);
    });

    socket.on('new_event_batch', (payload) => {
      if (payload.events) {
        addEventBatch(payload.events);
      }
    });

    socket.on('new_alert', (alert) => {
      addAlert(alert);
    });

    socket.on('honeypot_hit', (hit) => {
      addAlert(hit);
    });

    socket.on('identity_update', (update) => {
      updateIdentity({ ...update, id: update.identidad_id });
    });

    socket.on('ai_memo', (memo) => {
      addAiMemo(memo);
    });

    socket.on('stats_update', (stats) => {
      updateStats(stats);
    });

    socket.on('health_update', (payload) => {
      setHealthReport(payload);
    });

    socket.on('health_throughput', (payload) => {
      setHealthThroughput(payload?.points);
    });

    socket.on('disconnect', () => {
      setWsConnected(false);
    });

    return () => {
      socket.disconnect();
    };
  }, []); // Run exclusively on mount
}
