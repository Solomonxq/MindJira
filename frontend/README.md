# MindJira Frontend

React + Vite + TypeScript + Tailwind CSS dashboard for MindJira services.

## Features

- Authentication via auth service
- Description enrichment
- Test case generation
- Sprint summary reports
- Job history and triggering

## Development

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

The dev server proxies `/api` to `http://localhost` (Traefik).

## Build

```bash
npm run build
```

## Environment Variables

Create `.env` in `frontend/`:

```env
VITE_API_BASE_URL=/api
```
