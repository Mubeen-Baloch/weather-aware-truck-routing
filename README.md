# Weather-Aware Truck Routing

Assessment MVP for comparing driving routes against forecast weather. Milestone 1 provides only the React/Django foundation and health check; routing, weather, and risk analysis are intentionally not implemented yet.

Milestone 2 adds provider clients and deterministic fixtures only. It does not expose route analysis yet.

## Prerequisites

- Node.js 22+
- Python 3.13+

## Local development

1. Create the backend environment and install dependencies:

   ```powershell
   python -m venv backend\\.venv
   backend\\.venv\\Scripts\\python -m pip install -r backend\\requirements.txt
   Copy-Item backend\\.env.example backend\\.env
   ```

2. Start the Django API in one terminal:

   ```powershell
   backend\\.venv\\Scripts\\python backend\\manage.py runserver
   ```

3. Configure and start the frontend in another terminal:

   ```powershell
   Copy-Item frontend\\.env.example frontend\\.env
   npm --prefix frontend install
   npm --prefix frontend run dev
   ```

Open the Vite URL (normally `http://127.0.0.1:5173`). The page calls `GET /api/health` on the Django API and reports its result.

## Configuration

- `backend/.env` is reserved for Django settings such as `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS`.
- `frontend/.env` sets `VITE_API_BASE_URL`; use `http://127.0.0.1:8000` for local development.
- Backend provider mode defaults to `fixture`, which uses checked-in deterministic Mapbox/Open-Meteo-shaped responses and needs no API credentials. Set `ROUTING_DATA_MODE=live` and a `MAPBOX_ACCESS_TOKEN` only when testing live providers.
- Live Mapbox calls use Geocoding v6 and standard driving directions. Standard driving directions are not truck-specific and must not be treated as commercial-vehicle compliance routing.

Do not commit `.env` files or provider credentials. No database, migrations, or persistent models are used in this MVP.
