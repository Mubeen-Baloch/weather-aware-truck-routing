import type { RouteResult } from '../api/routeAnalysis';

interface Props {
  routes: RouteResult[];
  selectedIndex: number;
  recommendedIndex: number | null;
  onSelect: (index: number) => void;
}

const miles = (meters: number) => `${(meters / 1609.344).toFixed(0)} mi`;
const duration = (seconds: number) => `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
const riskCategories = [
  ['Low', 'low'], ['Moderate', 'moderate'], ['High', 'high'], ['Severe', 'severe'], ['No Travel', 'noTravel'], ['Unavailable', 'unavailable'],
] as const;

export function RouteCards({ routes, selectedIndex, recommendedIndex, onSelect }: Props) {
  return (
    <section className="route-cards" aria-label="Route options">
      {routes.map((route) => (
        <button
          className={`route-card ${route.index === selectedIndex ? 'route-card--selected' : ''}`}
          key={route.index}
          onClick={() => onSelect(route.index)}
          type="button"
        >
          <span className="route-card__topline">Route {route.index + 1}{route.index === recommendedIndex && <strong> Recommended</strong>}</span>
          <span>{miles(route.distanceMeters)} · {duration(route.durationSeconds)}</span>
          <span className="route-card__risk">
            {riskCategories.map(([label, key]) => <span key={key}>{label} {route.summary.riskMiles[key].toFixed(1)} mi</span>)}
          </span>
          <span className={route.summary.eligible ? 'status status--safe' : 'status status--warning'}>
            {route.summary.eligible ? `Average risk ${route.summary.averageRisk?.toFixed(2)}` : 'Not eligible for recommendation'}
          </span>
        </button>
      ))}
    </section>
  );
}
