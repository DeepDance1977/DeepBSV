import { useEffect, useState } from 'react';

type Metrics = {
  hashrate: number;
  blocks: number;
  activeMiners: number;
  currentHeight: number;
};

type StatusResponse = {
  status: string;
  node_connected: boolean;
  active_miners: number;
  current_height: number;
  hashrate: number;
};

export function App() {
  const [status, setStatus] = useState<string>(
    'Verbinde mit DeepBSV Mining Core...'
  );

  const [metrics, setMetrics] = useState<Metrics>({
    hashrate: 0,
    blocks: 0,
    activeMiners: 0,
    currentHeight: 0,
  });

  useEffect(() => {
    let active = true;

    const loadStatus = async () => {
      try {
        const response = await fetch('/api/status', {
          cache: 'no-store',
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data: StatusResponse = await response.json();

        if (!active) {
          return;
        }

        setMetrics({
          hashrate: Number(data.hashrate) || 0,
          blocks: 0,
          activeMiners: Number(data.active_miners) || 0,
          currentHeight: Number(data.current_height) || 0,
        });

        if (data.node_connected) {
          setStatus('Verbunden mit DeepBSV Core');
        } else {
          setStatus('BSV-Node nicht verbunden');
        }
      } catch (error) {
        console.error(
          'Fehler beim Abrufen des DeepBSV-Status:',
          error
        );

        if (active) {
          setStatus('Verbindungsfehler zum Mining-Backend');
        }
      }
    };

    loadStatus();

    const interval = window.setInterval(loadStatus, 2000);

    return () => {
      active = false;
      window.clearInterval(interval);
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
            <h1 className="text-2xl font-bold tracking-tight">
              DeepBSV Dashboard
            </h1>

            <p className="text-sm text-slate-400">
              Professional Solo-Mining on Raspberry Pi 5
            </p>
          </div>
        </div>

        <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 mb-6">
          <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
            Status
          </div>

          <div className="text-sm font-medium text-indigo-400">
            {status}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-slate-950 rounded-xl p-4 border border-slate-800">
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
              Hashrate
            </div>

            <div className="text-xl font-bold text-slate-100">
              {metrics.hashrate}{' '}
              <span className="text-xs font-normal text-slate-400">
                H/s
              </span>
            </div>
          </div>

          <div className="bg-slate-950 rounded-xl p-4 border border-slate-800">
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
              Gefundene Blöcke
            </div>

            <div className="text-xl font-bold text-emerald-400">
              {metrics.blocks}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-950 rounded-xl p-4 border border-slate-800">
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
              Aktive Miner
            </div>

            <div className="text-xl font-bold text-slate-100">
              {metrics.activeMiners}
            </div>
          </div>

          <div className="bg-slate-950 rounded-xl p-4 border border-slate-800">
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
              Blockhöhe
            </div>

            <div className="text-xl font-bold text-slate-100">
              {metrics.currentHeight}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
