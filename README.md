# OneDegree

Interactive Thai degree-plan map. One project, one Docker container: a **FastAPI**
backend (curriculum API, seeded from `Server/curriculum_database.json` into SQLite)
that also serves the **Next.js** frontend as a static build.

```
OneDegree/
├── Dockerfile            # multi-stage: build Web (static export) → Python runtime serves API + UI
├── docker-compose.yml    # single service
├── Server/               # FastAPI backend source (app/, requirements.txt, curriculum_database.json)
└── Web/                  # Next.js frontend source (static-exported at build time)
```

The frontend calls the API same-origin at `/api/v1`, so no separate host or CORS
config is needed. Both UI and API are served by one process on container port `8000`.

## Run

```bash
docker compose up --build
```

Then open http://localhost:6729 (host `6729` → container `8000`).

- UI: `/`
- API: `/api/v1/degree-plan`, `/api/v1/health`, `/api/v1/metadata`
- Docs: `/docs`

## Local dev (without Docker)

Backend (also serves the built frontend if `Server/static/` exists; otherwise API only):

```bash
cd Server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend, against a running backend:

```bash
cd Web
npm install
npm run dev          # http://localhost:3000, proxies to API_BASE
```

By default the frontend uses `/api/v1` (same origin). For a split deployment set
`NEXT_PUBLIC_API_BASE` at build time, e.g. `NEXT_PUBLIC_API_BASE=https://bu.need.cat/api/v1 npm run build`.

> The per-folder `Server/Dockerfile`, `Web/Dockerfile`, and their `docker-compose.yml`
> files are superseded by the root `Dockerfile` / `docker-compose.yml`.
