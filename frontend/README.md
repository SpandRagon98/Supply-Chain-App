# Frontend

Next.js 15 / TypeScript application for the Supply Chain Disruption Autopilot.

```powershell
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`) to connect the command center. The dashboard, suppliers, inventory, shipments, and incident views consume tenant-scoped operational APIs. Their explicit unavailable state replaces data only when the API cannot be reached; they never substitute fabricated business values.
