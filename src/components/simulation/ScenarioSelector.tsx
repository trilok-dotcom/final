import React, { useState } from 'react';
import type { ScenarioType, SimulationScale, CreateSimulationRequest } from '../../types/simulation';
import { Sparkles, Cpu } from 'lucide-react';

interface ScenarioSelectorProps {
  onCreate: (req: CreateSimulationRequest) => void;
  loading?: boolean;
}

export const ScenarioSelector: React.FC<ScenarioSelectorProps> = ({ onCreate, loading }) => {
  const [scenarioType, setScenarioType] = useState<ScenarioType>('URBAN_EARTHQUAKE');
  const [scale, setScale] = useState<SimulationScale>('MEDIUM');
  const [seed, setSeed] = useState<number>(42);
  const [speed, setSpeed] = useState<number>(1);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate({
      scenario_type: scenarioType,
      scale,
      seed: Number(seed),
      speed: Number(speed),
    });
  };

  return (
    <div className="bg-slate-900/90 backdrop-blur border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-amber-500 animate-pulse" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Disaster Scenario Configuration
          </h2>
        </div>
        <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400">
          SIMULATION SETUP
        </span>
      </div>

      <form onSubmit={handleCreate} className="space-y-4">
        {/* Scenario Type Selection */}
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
            Disaster Scenario Profile
          </label>
          <select
            value={scenarioType}
            onChange={(e) => setScenarioType(e.target.value as ScenarioType)}
            className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs font-semibold rounded-lg p-2.5 focus:outline-none focus:border-amber-500"
          >
            <option value="URBAN_EARTHQUAKE">URBAN EARTHQUAKE (Structural Collapse & Gas Leaks)</option>
            <option value="URBAN_FLOOD">URBAN FLOOD (Flash Inundation & Stranded Rescues)</option>
            <option value="INDUSTRIAL_FIRE">INDUSTRIAL FIRE (Chemical Tank Farm Explosion)</option>
            <option value="MULTI_VEHICLE_ACCIDENT">MULTI-VEHICLE ACCIDENT (Mass Casualty Highway Pileup)</option>
            <option value="CUSTOM">CUSTOM DISASTER EXERCISE</option>
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Scale */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Exercise Scale
            </label>
            <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
              {(['SMALL', 'MEDIUM', 'LARGE'] as SimulationScale[]).map((sc) => (
                <button
                  key={sc}
                  type="button"
                  onClick={() => setScale(sc)}
                  className={`flex-1 py-1.5 text-[11px] font-bold rounded transition ${
                    scale === sc
                      ? 'bg-amber-500 text-slate-950 shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {sc}
                </button>
              ))}
            </div>
          </div>

          {/* Deterministic Seed */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Deterministic Seed
            </label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono font-semibold rounded-lg p-2 focus:outline-none focus:border-amber-500"
              placeholder="42"
            />
          </div>

          {/* Speed Multiplier */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Initial Speed
            </label>
            <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
              {[1, 2, 5, 10].map((sp) => (
                <button
                  key={sp}
                  type="button"
                  onClick={() => setSpeed(sp)}
                  className={`flex-1 py-1.5 text-[11px] font-bold rounded transition ${
                    speed === sp
                      ? 'bg-cyan-500 text-slate-950 shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {sp}x
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Action Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-lg transition shadow-lg flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          {loading ? 'Initializing Exercise...' : 'CREATE DISASTER SCENARIO EXERCISE'}
        </button>
      </form>
    </div>
  );
};
