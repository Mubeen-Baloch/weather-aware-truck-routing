import type { Checkpoint } from '../api/routeAnalysis';

export function CheckpointDetails({ checkpoint }: { checkpoint: Checkpoint | null }) {
  if (!checkpoint) return <aside className="checkpoint-details">Select a checkpoint on the map to inspect its ETA and weather risk.</aside>;
  const weather = checkpoint.weather;
  return (
    <aside className="checkpoint-details">
      <p className="eyebrow">Checkpoint</p>
      <h3>{(checkpoint.distanceMeters / 1609.344).toFixed(1)} miles from origin</h3>
      <p>ETA: {new Date(checkpoint.etaUtc).toLocaleString()}</p>
      {weather.available ? <>
        <p>Wind {weather.windMph?.toFixed(1)} mph · Rain {weather.rainInchesPerHour?.toFixed(2)} in/hr · Snow {weather.snowInchesPerHour?.toFixed(2)} in/hr</p>
        <p className={`risk-label risk-label--${checkpoint.risk.level}`}>Risk: {checkpoint.risk.level?.replace('-', ' ')}</p>
      </> : <p className="status status--warning">Weather unavailable — this checkpoint cannot support a safety recommendation.</p>}
    </aside>
  );
}
