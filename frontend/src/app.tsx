import { useEffect, useState } from 'react';
import { Activity, Cpu, Server } from 'lucide-react';

interface Metrics {
  type: string;
  hashrate: number;
  active_miners: number;
  current_height: number;
}

export default function App() {
  const [metrics, setMetrics] = useState<Metrics>({
    type: 'metrics_update',
    hashrate: 0.0,
    active_miners: 0,
    current_height: 0,
  });
  const [isConnected, setIsConnected] = useState<boolean>(false);

  useEffect(() => {
    // WebSocket-Verbindung zum FastAPI-Backend aufbauen
    const ws = new WebSocket('ws://localhost:8000/ws/metrics');

    ws.onopen = () => {
      setIsConnected(true);
      ws.send('ping');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'metrics_update') {
          setMetrics(data);
        }
      } catch (err) {
        console.error('Fehler beim Parsen der WebSocket-Daten:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 font-sans">
      <div className="max-w-5xl mx-auto space-y-6">
        
        {/* Header */}
        <header className="flex justify-between items-center border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">DeepBSV Dashboard</h1>
            <p className="text-sm text-slate-400">Raspberry Pi 5 Solo-Mining Plattform</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`h-3 w-3 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
            <span className="text-xs font-medium text-slate-300">
              {isConnected ? 'Verbunden (Live)' : 'Getrennt'}
            </span>
          </div>
        </header>

        {/* Metriken Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          {/* Hashrate Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between shadow-lg">
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Hashrate</p>
              <p className="text-2xl font-bold text-white mt-1">
                {metrics.hashrate.toFixed(2)} <span className="text-sm font-normal text-slate-400">H/s</span>
              </p>
            </div>
            <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Activity className="h-6 w-6" />
            </div>
          </div>

          {/* Active Miners Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between shadow-lg">
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Aktive Miner</p>
              <p className="text-2xl font-bold text-white mt-1">{metrics.active_miners}</p>
            </div>
            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <Cpu className="h-6 w-6" />
            </div>
          </div>

          {/* Block Height Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between shadow-lg">
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Block-Höhe</p>
              <p className="text-2xl font-bold text-white mt-1">{metrics.current_height}</p>
            </div>
            <div className="p-3 bg-amber-500/10 text-amber-400 rounded-lg">
              <Server className="h-6 w-6" />
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
