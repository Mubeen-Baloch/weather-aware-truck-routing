# Weather-Aware Truck Routing

Weather-Aware Truck Routing is an assessment MVP that compares up to three Mapbox driving alternatives against ETA-matched Open-Meteo hourly forecasts. It helps a driver select the safest eligible route by showing checkpoint weather risk, risk-weighted route summaries, and a 0–48 hour forecast corridor heatmap.

The application uses a React + TypeScript + Vite frontend and a stateless Django REST Framework backend. It has no database, migrations, authentication, or persisted user data.

## Prerequisites

- Node.js 22+
- Python 3.13+

## Local setup

1. Create the backend environment, install dependencies, and copy the local configuration template:

   ```powershell
   python -m venv backend\.venv
   backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
   Copy-Item backend\.env.example backend\.env
   ```

2. Copy the frontend configuration template and install dependencies:

   ```powershell
   Copy-Item frontend\.env.example frontend\.env
   npm --prefix frontend install
   ```

3. Start Django in one terminal:

   ```powershell
   backend\.venv\Scripts\python backend\manage.py runserver
   ```

4. Start Vite in a second terminal:

   ```powershell
   npm --prefix frontend run dev
   ```

Open the Vite URL, normally `http://127.0.0.1:5173`. Enter an origin, destination, timezone-aware departure time, load weight, and 10/25/50-mile checkpoint interval. The UI submits a route analysis, renders alternatives and ETA-aware checkpoint risk, recommends the best eligible route, and lets you move the forecast corridor slider from departure through +48 hours.

## Configuration

Backend configuration belongs in `backend/.env`:

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` configure local Django development.
- `ROUTING_DATA_MODE=fixture` is the default. It uses checked-in deterministic Mapbox/Open-Meteo-shaped data and needs no provider credentials.
- `ROUTING_FIXTURE_SCENARIO=standard` selects the default fixture scenario.
- `PROVIDER_REQUEST_TIMEOUT_SECONDS` and `PROVIDER_CACHE_TTL_SECONDS` control the lightweight provider client behavior.
- `MAPBOX_ACCESS_TOKEN` is required only for backend live mode.

Frontend configuration belongs in `frontend/.env`:

- `VITE_API_BASE_URL=http://127.0.0.1:8000` points the browser application at Django.
- `VITE_MAPBOX_ACCESS_TOKEN` is a public Mapbox browser token used by Mapbox GL to render the interactive map. Without it, analysis remains available but the map displays a configuration placeholder.

To explicitly use live providers for the current PowerShell session, set live mode and a backend Mapbox token before starting Django:

```powershell
$env:ROUTING_DATA_MODE = 'live'
$env:MAPBOX_ACCESS_TOKEN = 'your-server-side-mapbox-token'
backend\.venv\Scripts\python backend\manage.py runserver
```

Environment variables set in PowerShell take precedence over values in `backend/.env`. Never commit `.env` files or real provider tokens.

## API

- `GET /api/health` returns the API health status.
- `GET /api/providers/status` reports fixture/live mode and the active fixture scenario without exposing credentials.
- `POST /api/routes/analyze` accepts `origin`, `destination`, timezone-aware `departureTime`, `loadWeightLbs`, and optional `checkpointIntervalMiles` (`10`, `25`, or `50`; default `25`). It returns route geometry, checkpoints, ETA-matched weather/risk, risk-mile summaries, recommendation status, and 49 heatmap frames for departure through +48 hours.

## Deterministic fixture scenarios

Set `ROUTING_FIXTURE_SCENARIO` to one of the following while using fixture mode, then restart Django to load the new setting:

- `standard` — three complete, evaluable route alternatives with explicit 49-hour forecast coverage.
- `fewer_routes` — one returned alternative; the UI must not invent additional routes.
- `missing_weather` — incomplete required weather fields; analysis marks weather unavailable and withholds a safety recommendation.
- `unsafe_weather` — explicit 60 mph hourly wind values; routes receive No Travel risk and are ineligible.
- `tied_recommendations` — two identical alternatives with equal weather exposure, geometry, distance, duration, and risk metrics; route index `0` wins the stable final tie-break.
- `forecast_gap` — a deliberately absent hourly forecast timestamp; the affected heatmap offset is unavailable rather than fabricated.

## Routing and safety behavior

Checkpoints are placed along the route geometry at the selected interval, including a final partial segment. Their ETA is calculated from Mapbox duration annotations or per-leg step fallbacks. Open-Meteo hourly forecasts are matched in UTC to the nearest forecast time within 30 minutes; missing or invalid required weather marks that segment unavailable rather than generating a recommendation from incomplete information.

Risk uses wind, rain, and snowfall thresholds with load-based overrides. Route selection deterministically prefers fewest Severe miles, fewest High miles, lowest distance-weighted average risk, shortest duration, then route index. The forecast heatmap reuses those risk calculations for every available offset from 0 through 48 hours.

## Important limitation

Live Mapbox requests use standard driving directions. Standard Mapbox driving is **not truck-specific routing** and does not validate commercial restrictions, truck dimensions, load limits, hazmat rules, or local road compliance. It must not be used as a commercial-vehicle compliance or dispatching system.

## Verification

```powershell
npm --prefix frontend run build
backend\.venv\Scripts\python backend\manage.py test routing.tests -v 2
backend\.venv\Scripts\python backend\manage.py check
```
