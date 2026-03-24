import { useEffect } from 'react';
import { io } from 'socket.io-client';
import { useStore } from '../store';
import { showToast } from '../lib/toastBus';

/**
 * URL del servidor Socket.IO (misma API FastAPI).
 * Debe coincidir con api/websocket_contract.py (eventos SERVER_EVENTS / CLIENT_EVENTS).
 */
const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000';

export function useWebSocket() {
  const {
    addEvent,
    addEventBatch,
    addAlert,
    addHoneypotHit,
    addProposal,
    updateIdentity,
    updateStats,
    setInitialState,
    setHealthReport,
    setHealthThroughput,
    setWsConnected,
  } = useStore();

  useEffect(() => {
    const socket = io(WS_URL, {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: Infinity,
      transports: ['websocket', 'polling'],
    });

    socket.on('connect', () => {
      setWsConnected(true);
    });

    socket.on('disconnect', () => {
      setWsConnected(false);
    });

    socket.on('initial_state', (payload) => {
      setInitialState(payload);
    });

    socket.on('new_event', (event) => {
      addEvent(event);
    });

    socket.on('new_event_batch', (payload) => {
      if (payload?.events) {
        addEventBatch(payload.events);
      }
    });

    socket.on('new_alert', (alert) => {
      addAlert(alert);
    });

    socket.on('honeypot_hit', (hit) => {
      addHoneypotHit(hit);
    });

    socket.on('identity_update', (update) => {
      updateIdentity({ ...update, id: update.identidad_id });
    });

    socket.on('ai_memo', (payload) => {
      const memo =
        payload &&
        typeof payload === 'object' &&
        payload.data &&
        typeof payload.data === 'object' &&
        !payload.id
          ? payload.data
          : payload;
      if (!memo || typeof memo !== 'object') return;
      useStore.getState().addAiMemo(memo);
      const prioridad = String(memo.prioridad || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/\p{M}/gu, '');
      const esAlta = prioridad === 'alta' || prioridad === 'critica' || prioridad.includes('crit');
      if (esAlta) {
        const raw = memo.titulo || memo.contenido || '';
        const message =
          typeof raw === 'string' && raw.length > 80 ? `${raw.slice(0, 80)}...` : raw || '(sin texto)';
        showToast({
          type: 'warning',
          title: 'Nuevo análisis IA',
          message,
        });
      }
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

    socket.on('response_proposal', () => {
      addProposal();
    });

    socket.on('pong', () => {});

    return () => {
      socket.removeAllListeners();
      socket.disconnect();
    };
  }, []);
}
