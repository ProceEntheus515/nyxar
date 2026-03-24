/**
 * Verificación I05: servidor WebSocket (Socket.IO) + eventos del contrato.
 * Uso (desde la raíz del repo, con dependencias del dashboard instaladas):
 *   npm install --prefix dashboard
 *   node scripts/verify_websocket.js
 *
 * Variables: WS_URL (default http://localhost:8000)
 * Requiere JWT: WS_TOKEN (mismo valor que access_token de POST /api/v1/auth/login).
 */

const path = require('path');
const { io } = require(path.join(__dirname, '..', 'dashboard', 'node_modules', 'socket.io-client'));

const WS_URL = process.env.WS_URL || 'http://localhost:8000';
const WS_TOKEN = (process.env.WS_TOKEN || '').trim();
const TIMEOUT_MS = Number(process.env.WS_VERIFY_TIMEOUT_MS || 15000);

const EXPECTED_EVENTS = ['new_event', 'stats_update'];

const received = {};

console.log('=== Verificando WebSocket Server ===\n');
console.log(`Conectando a ${WS_URL} ...\n`);

if (!WS_TOKEN) {
  console.error('[FAIL] Definí WS_TOKEN con un JWT válido (login en /api/v1/auth/login).');
  process.exit(1);
}

const socket = io(WS_URL, {
  auth: { token: WS_TOKEN },
  transports: ['websocket', 'polling'],
  reconnection: false,
});

socket.on('connect', () => {
  console.log(`[OK] Conectado. Socket ID: ${socket.id}\n`);
  console.log(`Esperando eventos (máximo ${TIMEOUT_MS / 1000} s)...\n`);
});

socket.on('connect_error', (err) => {
  console.log('[FAIL] No se pudo conectar:', err.message);
  console.log('       Levanta la API (uvicorn) y comprueba WS_URL / puerto 8000.');
});

socket.on('disconnect', () => {
  console.log('[WARN] Desconectado');
});

EXPECTED_EVENTS.forEach((eventName) => {
  socket.on(eventName, (data) => {
    if (received[eventName]) return;
    received[eventName] = data;
    console.log(`[OK] Recibido: ${eventName}`);
    if (eventName === 'new_event' && data && typeof data === 'object') {
      console.log(`  source: ${data.source}`);
      console.log(`  usuario: ${data.interno?.usuario}`);
      console.log(`  risk_score: ${data.risk_score}`);
    }
    if (eventName === 'stats_update' && data && typeof data === 'object') {
      console.log(`  eventos/min: ${data.eventos_por_min}`);
      console.log(`  identidades activas: ${data.identidades_activas}`);
    }
  });
});

setTimeout(() => {
  const missing = EXPECTED_EVENTS.filter((e) => !received[e]);

  console.log('\n=== Resultado ===');
  if (missing.length === 0) {
    console.log('[OK] Todos los eventos esperados fueron recibidos');
    console.log('[OK] WebSocket Server funcionando correctamente');
  } else {
    console.log(`[FAIL] Eventos no recibidos: ${missing.join(', ')}`);
    console.log('       Verifica pipeline (eventos en Mongo) y que stats_loop emita cada 30s.');
    process.exitCode = 1;
  }

  socket.disconnect();
  process.exit(process.exitCode || 0);
}, TIMEOUT_MS);
