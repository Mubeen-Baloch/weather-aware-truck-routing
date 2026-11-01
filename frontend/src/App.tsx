import { useEffect, useState } from 'react';

type HealthState = 'checking' | 'healthy' | 'unavailable';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

export default function App() {
  const [health, setHealth] = useState<HealthState>('checking');

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/health`, { signal: controller.signal });
        setHealth(response.ok ? 'healthy' : 'unavailable');
      } catch {
        if (!controller.signal.aborted) setHealth('unavailable');
      }
    }

    void checkHealth();
    return () => controller.abort();
  }, []);

  const message = {
    checking: 'Checking backend connection…',
    healthy: 'Backend health check connected.',
    unavailable: 'Backend health check unavailable. Start Django at the configured API URL.',
  }[health];

  return (
    <main className="app-shell">
      <section className="status-card" aria-live="polite">
        <p className="eyebrow">Weather-Aware Truck Routing</p>
        <h1>Foundation is ready.</h1>
        <p>Route planning, weather analysis, and map features will be added in later milestones.</p>
        <p className={`health health--${health}`}>{message}</p>
      </section>
    </main>
  );
}
