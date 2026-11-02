import { useCallback, useEffect, useState } from 'react';

import { analyzeRoutes, getProviderStatus, type AnalysisResult, type Checkpoint, type ProviderStatus, type RouteRequest } from './api/routeAnalysis';
import { CheckpointDetails } from './components/CheckpointDetails';
import { HeatmapSlider } from './components/HeatmapSlider';
import { RouteCards } from './components/RouteCards';
import { RouteForm } from './components/RouteForm';
import { RouteMap } from './components/RouteMap';

export default function App() {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [selectedRoute, setSelectedRoute] = useState(0);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<Checkpoint | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [heatmapOffset, setHeatmapOffset] = useState(0);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getProviderStatus(controller.signal).then(setProviderStatus).catch(() => setProviderStatus(null));
    return () => controller.abort();
  }, []);

  const submit = useCallback(async (request: RouteRequest) => {
    setBusy(true); setError(null); setSelectedCheckpoint(null); setHeatmapOffset(0);
    try {
      const result = await analyzeRoutes(request);
      setAnalysis(result);
      setSelectedRoute(result.recommendation.routeIndex ?? result.routes[0]?.index ?? 0);
    } catch (submissionError) {
      setAnalysis(null);
      setError(submissionError instanceof Error ? submissionError.message : 'Route analysis could not be completed.');
    } finally { setBusy(false); }
  }, []);

  const selected = analysis?.routes.find((route) => route.index === selectedRoute);
  const recommendationMessage = analysis?.recommendation.status === 'weather-unavailable'
    ? 'Required forecast data is unavailable for part of this trip. No reliable safety recommendation is shown.'
    : analysis?.recommendation.status === 'no-safe-route'
      ? 'Every evaluated route includes No Travel conditions. Do not proceed.'
      : analysis ? `Route ${(analysis.recommendation.routeIndex ?? 0) + 1} is recommended by fewest Severe miles, fewest High miles, lowest weighted average risk, shortest duration, then stable route index.` : null;

  return <main className="app-shell">
    <header className="hero"><div><p className="eyebrow">Weather-Aware Truck Routing {providerStatus?.mode === 'fixture' && <span className="demo-indicator">Demo — Fixture Data</span>}</p><h1>Choose the safer route before you roll.</h1></div><p className="disclaimer">Mapbox standard driving directions are not truck-specific and do not validate commercial restrictions, truck dimensions, load limits, hazmat rules, or local road compliance.</p></header>
    <section className="planner-card"><RouteForm busy={busy} onSubmit={submit} /></section>
    {error && <p className="notice notice--error" role="alert">{error}</p>}
    {analysis && <>
      <p className={`notice ${analysis.recommendation.status === 'recommended' ? 'notice--success' : 'notice--warning'}`}>{recommendationMessage}</p>
      <section className="results-layout"><div className="results-main"><RouteMap routes={analysis.routes} origin={analysis.origin.coordinate} destination={analysis.destination.coordinate} selectedIndex={selectedRoute} heatmapOffset={heatmapOffset} onCheckpointSelect={setSelectedCheckpoint} />{selected && <HeatmapSlider route={selected} offsetHours={heatmapOffset} onChange={setHeatmapOffset} />}<CheckpointDetails checkpoint={selectedCheckpoint} /></div><RouteCards routes={analysis.routes} selectedIndex={selectedRoute} recommendedIndex={analysis.recommendation.routeIndex} onSelect={(index) => { setSelectedRoute(index); setSelectedCheckpoint(null); setHeatmapOffset(0); }} /></section>
      {selected && <p className="route-caption">Selected Route {selected.index + 1}: checkpoint dots are colored by ETA-matched weather risk. Select one for details.</p>}
    </>}
  </main>;
}
