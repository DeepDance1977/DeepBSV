import React, { useEffect, useState } from 'react';

export function App() {
  const [status, setStatus] = useState<string>('Verbinde mit DeepBSV Mining Core...');
  const [metrics, setMetrics] = useState<{ hashrate: number; blocks: number }>({ hashrate: 0, blocks: 0 });

  useEffect(() => {
    // Beispiel für WebSocket- oder API-Anbindung an das FastAPI Backend
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setStatus('Verbunden mit DeepBSV Core (Live)');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMetrics({
          hashrate: data.hashrate || 0,
          blocks: data.blocks || 0,
        });
      } catch (e) {
        console.error('Fehler beim Parsen der WebSocket-Daten', e);
      }
    };

    ws.onerror = () => {
      setStatus('Verbindungsfehler zum Mining-Backend');
    };

    ws.onclose = () => {
      setStatus('Verbindung getrennt. Reconnect läuft...');
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-4">
      <div className="max-w-xl w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
        <div className="flex items-center space-x-4 mb-6">
          <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-lg">
            BSV
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">DeepBSV Dashboard</h1>
            <p className="text-sm text-slate-400">Professional Solo-Mining on Raspberry Pi 5</p>
          </div>
        </div>

        <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 mb-6">
          <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Status</div>
          <div className="text-sm font-medium text-indigo-400">{status}</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-950 rounded-xl p-4 border border-slate-800">
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Hashrate</div>
            <div className="text-xl font-bold text-slate-100">{metrics.hashrate} <span className="text-xs font-normal text-slate-400">H/s</span></div>
          </div>
          <div className="bg-slate-950 rounded-xl p-4 border border-slate-800">
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Gefundene Blöcke</div>
            <div className="text-xl font-bold text-emerald-400">{metrics.blocks}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
