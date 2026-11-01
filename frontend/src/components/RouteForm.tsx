import { FormEvent, useState } from 'react';

import type { RouteRequest } from '../api/routeAnalysis';

interface Props {
  busy: boolean;
  onSubmit: (request: RouteRequest) => void;
}

function defaultDeparture(): string {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset() + 60);
  return date.toISOString().slice(0, 16);
}

export function RouteForm({ busy, onSubmit }: Props) {
  const [origin, setOrigin] = useState('Austin, TX');
  const [destination, setDestination] = useState('Dallas, TX');
  const [departure, setDeparture] = useState(defaultDeparture);
  const [load, setLoad] = useState('25000');
  const [interval, setInterval] = useState('25');

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const localDate = new Date(departure);
    onSubmit({
      origin,
      destination,
      departureTime: localDate.toISOString(),
      loadWeightLbs: Number(load),
      checkpointIntervalMiles: Number(interval),
    });
  }

  return (
    <form className="route-form" onSubmit={submit}>
      <label>Origin<input required value={origin} onChange={(event) => setOrigin(event.target.value)} /></label>
      <label>Destination<input required value={destination} onChange={(event) => setDestination(event.target.value)} /></label>
      <label>Departure<input required type="datetime-local" value={departure} onChange={(event) => setDeparture(event.target.value)} /></label>
      <label>Load weight (lb)<input required min="0" type="number" value={load} onChange={(event) => setLoad(event.target.value)} /></label>
      <label>Checkpoint interval
        <select value={interval} onChange={(event) => setInterval(event.target.value)}>
          <option value="10">Every 10 miles</option>
          <option value="25">Every 25 miles</option>
          <option value="50">Every 50 miles</option>
        </select>
      </label>
      <button type="submit" disabled={busy}>{busy ? 'Analyzing…' : 'Analyze routes'}</button>
    </form>
  );
}
