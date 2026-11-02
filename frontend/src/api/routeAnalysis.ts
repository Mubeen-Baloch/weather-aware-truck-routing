export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe' | 'no-travel' | null;

export interface Checkpoint {
  coordinate: [number, number];
  distanceMeters: number;
  followingSegmentMeters: number;
  etaUtc: string;
  weather: {
    available: boolean;
    timestampUtc: string | null;
    windMph: number | null;
    rainInchesPerHour: number | null;
    snowInchesPerHour: number | null;
  };
  risk: { available: boolean; level: RiskLevel; ordinal: number | null };
}

export interface RouteResult {
  index: number;
  geometry: { type: 'LineString'; coordinates: [number, number][] };
  distanceMeters: number;
  durationSeconds: number;
  checkpoints: Checkpoint[];
  heatmapFrames: HeatmapFrame[];
  summary: {
    eligible: boolean;
    riskMiles: Record<'low' | 'moderate' | 'high' | 'severe' | 'noTravel' | 'unavailable', number>;
    averageRisk: number | null;
  };
}

export interface HeatmapFrame {
  offsetHours: number;
  timeUtc: string;
  available: boolean;
  segments: Array<{
    followingSegmentMeters: number;
    risk: { available: boolean; level: RiskLevel; ordinal: number | null };
  }>;
}

export interface AnalysisResult {
  origin: { label: string; coordinate: [number, number] };
  destination: { label: string; coordinate: [number, number] };
  departureTimeUtc: string;
  loadWeightLbs: number;
  checkpointIntervalMiles: number;
  routes: RouteResult[];
  recommendation: {
    status: 'recommended' | 'no-safe-route' | 'weather-unavailable';
    routeIndex: number | null;
    criteria: RecommendationCriterion[];
  };
}

export type RecommendationCriterion =
  | 'fewest-severe-miles'
  | 'fewest-high-miles'
  | 'lowest-average-risk'
  | 'shortest-duration';

export interface RouteRequest {
  origin: string;
  destination: string;
  departureTime: string;
  loadWeightLbs: number;
  checkpointIntervalMiles: number;
}

export interface ProviderStatus {
  mode: 'fixture' | 'live';
  fixtureScenario: string | null;
  providers: { mapbox: 'fixture' | 'live'; weather: 'fixture' | 'live' };
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

export async function getProviderStatus(signal?: AbortSignal): Promise<ProviderStatus> {
  const response = await fetch(`${apiBaseUrl}/api/providers/status`, { signal });
  if (!response.ok) throw new Error('Provider status is unavailable.');
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Provider status returned malformed JSON.');
  }
  if (
    typeof payload !== 'object' || payload === null || !('mode' in payload)
    || !('fixtureScenario' in payload) || !('providers' in payload)
    || (payload.mode !== 'fixture' && payload.mode !== 'live')
    || (typeof payload.fixtureScenario !== 'string' && payload.fixtureScenario !== null)
    || typeof payload.providers !== 'object' || payload.providers === null
    || !('mapbox' in payload.providers) || !('weather' in payload.providers)
    || (payload.providers.mapbox !== 'fixture' && payload.providers.mapbox !== 'live')
    || (payload.providers.weather !== 'fixture' && payload.providers.weather !== 'live')
  ) {
    throw new Error('Provider status has an unexpected shape.');
  }
  return payload as ProviderStatus;
}

export async function analyzeRoutes(request: RouteRequest, signal?: AbortSignal): Promise<AnalysisResult> {
  const response = await fetch(`${apiBaseUrl}/api/routes/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });
  const body = await response.text();
  let payload: unknown = null;
  try {
    payload = body ? JSON.parse(body) : null;
  } catch {
    if (!response.ok) {
      throw new Error(`Route analysis failed (${response.status}). The server returned an unexpected response.`);
    }
    throw new Error('Route analysis returned an unexpected response.');
  }
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload ? payload.detail : null;
    throw new Error(typeof detail === 'string' ? detail : `Route analysis failed (${response.status}).`);
  }
  return payload as AnalysisResult;
}
