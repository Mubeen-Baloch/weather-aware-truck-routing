import type { RouteResult } from '../api/routeAnalysis';

interface Props {
  route: RouteResult;
  offsetHours: number;
  onChange: (offset: number) => void;
}

export function HeatmapSlider({ route, offsetHours, onChange }: Props) {
  const frame = route.heatmapFrames.find((candidate) => candidate.offsetHours === offsetHours);
  const frameTime = frame ? new Date(frame.timeUtc).toLocaleString() : 'Unavailable';

  return (
    <section className="heatmap-control" aria-label="Forecast corridor heatmap">
      <div>
        <p className="eyebrow">Trip corridor forecast</p>
        <h3>Departure +{offsetHours} hours</h3>
        <p className={frame?.available ? 'heatmap-status' : 'heatmap-status heatmap-status--unavailable'}>
          {frame?.available ? `Forecast valid at ${frameTime}` : `Forecast unavailable at ${frameTime}`}
        </p>
      </div>
      <label className="slider-label" htmlFor="forecast-offset">0 hours
        <input
          id="forecast-offset"
          type="range"
          min="0"
          max="48"
          step="1"
          value={offsetHours}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        48 hours
      </label>
      <p className="heatmap-legend"><span className="legend-low" /> Low <span className="legend-moderate" /> Moderate <span className="legend-high" /> High <span className="legend-severe" /> Severe <span className="legend-no-travel" /> No Travel <span className="legend-unavailable" /> Unavailable</p>
    </section>
  );
}
