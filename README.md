# InternFly

> Six legs. Zero years of experience. One very persistent applicant.

InternFly is an offline-first, continuously running artificial-agent simulation about a tiny fruit fly trying to become a software engineer. It lives in an interactive 3D room, wakes up, practices data structures and algorithms, searches fictional internship listings, prepares application drafts, drinks an irresponsible amount of fictional coffee, sleeps for five simulated hours, consolidates memories, dreams, and starts again.

The project combines three ideas:

- **Agent simulation:** a durable state machine coordinates bounded tasks, energy, sleep, recovery, and memory.
- **Connectome-inspired control:** connectivity from a selected Male CNS v1.0 fruit-fly subgraph can influence high-level action selection through engineered neural dynamics.
- **Scientific workplace comedy:** the fly has fictional stress, confidence, caffeine, dreams, and an entirely serious “10x drosophila” score.

InternFly does **not** claim that a fly connectome understands language, writes code, browses LinkedIn, or wants a job. Language and code behavior comes from ordinary software components; the connectome-derived controller only influences high-level choices.

## What you can watch

The dashboard presents InternFly as a small 3D story:

- The fly sleeps in a bed and wakes after exactly five simulated hours.
- It walks to a DSA workstation to generate and test Python solutions.
- It uses a separate LinkedIn-inspired workstation to evaluate fictional jobs and create drafts.
- It visits a coffee station; caffeine changes fictional agent state and engineered controller parameters.
- A window follows a simulated sunrise, daylight, sunset, and night cycle.
- The room camera can orbit and zoom, or follow the articulated fly closely.
- A neural observatory displays source neurons, connections, active regions, moving signals, and numerical population graphs.

The neural view currently expands the selected source graph into roughly **1,024 engineered visual simulation units** and more than **1,300 rendered communication paths**. This creates an observable population-scale firing display. These extra visual units inherit activity from source controller nodes and are clearly marked as an engineered numerical expansion—not additional reconstructed biological neurons.

## Scientific boundary

InternFly keeps the following layers separate throughout the code and UI:

| Provenance label | What it means |
|---|---|
| `BIOLOGICAL_CONNECTIVITY` | Neuron identities, annotations, predicted transmitters, and directed synaptic weights imported from Male CNS v1.0. |
| `SIMULATED_DYNAMICS` | Engineered numerical activity evolving over the selected graph. It is not recorded biological firing. |
| `ENGINEERED_MAPPING` | Human-designed mappings from software observations to controller input and from activity to action preferences. |
| `LLM_GENERATED` | Generated explanations, solution proposals, application wording, reflections, and dreams. |
| `DETERMINISTIC_EXECUTION` | State transitions, scoring, deduplication, policy checks, code tests, budgets, and persistence. |
| `FICTIONAL_ENTERTAINMENT` | Personality, emotions, caffeine effects, dreams, imagined rejection, and humorous statistics. |

The connectome can influence whether the agent prefers DSA practice, job search, reflection, coffee, or sleep. Deterministic policy still enforces deadlines, attempt limits, safety rules, approval requirements, and forced sleep.

## About the Male CNS brain

**Male CNS v1.0** is a structural electron-microscopy reconstruction of the adult male *Drosophila melanogaster* central nervous system published by FlyEM / HHMI Janelia and collaborators. The official release provides neuron annotations, predicted neurotransmitters, synaptic connectivity, skeletons, and neuPrint access.

InternFly uses only a selected, versioned subgraph rather than attempting to simulate the entire connectome. The importer starts from annotated seed neuron types, collects strong incoming and outgoing partners, filters edges by synapse count, and writes a reproducible manifest containing:

- exact body IDs;
- cell type, class, hemisphere, and dominant neuropil metadata;
- predicted neurotransmitter and the documented model sign derived from it;
- directed connectivity and aggregate synapse counts;
- selection parameters, retrieval date, source attribution, and a SHA-256 content hash.

The application then transforms those structural connections into a sparse recurrent rate controller. Its activity, plasticity overlay, input mapping, output mapping, node placement, glow, moving particles, and expanded visual population are engineered simulation layers.

Official resources:

- [Male CNS project](https://male-cns.janelia.org/)
- [Male CNS downloads and CC-BY license](https://male-cns.janelia.org/download/)
- [Local data-provenance documentation](docs/DATA_PROVENANCE.md)

## Architecture at a glance

```text
Environment observation
        ↓
Observation encoder
        ↓
Sparse recurrent controller
        ↓
Action preference + deterministic safety gates
        ↓
DSA / jobs / reflection / coffee / sleep specialist
        ↓
Outcome, reward, energy and memory
        ↓
Sleep replay, consolidation and next wake plan
```

The backend is a FastAPI application with a durable SQLite event store for the current prototype. The React/TypeScript dashboard receives live state through WebSockets and renders the room with Three.js. Docker Compose adds a separate restricted code-runner service.

## Quick start with Docker

This is the recommended way to run the complete project because generated code executes in the isolated runner container.

### Requirements

- Docker Desktop with Docker Compose
- Approximately 2 GB of free memory
- Ports `5173` and `8000` available

### Start

From PowerShell in the repository root (the folder containing this README):

```powershell
Copy-Item .env.example .env
docker compose -f deploy/compose/docker-compose.yml up --build
```

Open:

- Dashboard: <http://localhost:5173>
- API documentation: <http://localhost:8000/docs>
- Liveness check: <http://localhost:8000/health/live>
- Readiness check: <http://localhost:8000/health/ready>

Stop the foreground stack with `Ctrl+C`. To stop a detached stack later:

```powershell
docker compose -f deploy/compose/docker-compose.yml down
```

The named `internfly-data` Docker volume keeps the event database across normal container restarts and rebuilds.

## Development start without Docker

This mode uses the deterministic fixture runner. It is useful for UI development and offline demonstrations, but the Docker runner is the supported path for actually executing generated code in isolation.

### Requirements

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 or later
- npm

### 1. Start the API

Open PowerShell terminal 1:

```powershell
# Run from the repository root.
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --python 3.12
uv run uvicorn internfly.api:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start the dashboard

Open PowerShell terminal 2:

```powershell
# Run from the repository root.
npm --prefix apps/dashboard install
npm --prefix apps/dashboard run dev
```

Then open <http://127.0.0.1:5173>. Vite proxies `/api`, `/health`, and `/ws` requests to the backend on port `8000`.

The local event database is written to `internfly.db` in the repository root unless `INTERNFLY_DATABASE_PATH` is configured differently.

## Run with a real Male CNS-derived subgraph

The repository ships with a **synthetic development fixture** so the application runs completely offline. To create a real Male CNS v1.0 connectivity manifest, use neuPrint with your own current token.

Never put a neuPrint token in source code, screenshots, command arguments, `.env` committed to Git, application events, or dashboard state. If a token has previously been pasted into chat or another public location, revoke it and create a new one first.

From the repository root:

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --python 3.12 --extra connectome
$env:NEUPRINT_TOKEN = Read-Host "Paste your rotated neuPrint token" -MaskInput
uv run --extra connectome python scripts/fetch_malecns_subgraph.py --seed-types DNge104 --limit 512
Remove-Item Env:NEUPRINT_TOKEN
```

This produces:

```text
data/generated/malecns-subgraph.json
```

Restart the API after generation. InternFly automatically prefers this file and the dashboard changes its source label to `MALE CNS v1.0`. If the manifest is absent or invalid, the application continues with the clearly labelled development fixture.

Optional importer controls:

```text
--seed-types         One or more neuPrint neuron types; default DNge104
--limit              Maximum selected neurons; default 512
--partners-per-seed  Strong partners retained per seed; default 48
--min-synapses       Minimum aggregate edge weight; default 5
--max-edges          Maximum induced edges; default 5000
--output             Manifest destination
```

The importer does not download EM volumes or individual synapse-point tables. It stores the selected neuron metadata and aggregate graph required by the controller.

## Operating modes and safety

The default mode is `offline`:

- Job listings and companies are fictional fixtures.
- Model responses are deterministic fixtures.
- No external job application is submitted.
- Draft approval only changes a local content-hash-bound record.
- Hidden DSA tests are never exposed as memories or prompts.
- The Compose runner has no external network and runs with a read-only filesystem, dropped capabilities, memory/CPU/process limits, and a temporary workspace.

Human controls:

- **Pause:** finish the current atomic step and stop starting new work.
- **Resume:** continue from durable state.
- **Sleep now:** safely transition into the functional sleep sequence.
- **Emergency stop:** prevent new work and persist the stopped state across restarts.

InternFly never bypasses CAPTCHAs, access restrictions, platform safeguards, or application approval requirements.

## Configuration

The main environment variables are:

| Variable | Default | Purpose |
|---|---|---|
| `INTERNFLY_MODE` | `offline` | Operating mode. |
| `INTERNFLY_DATABASE_PATH` | `internfly.db` locally | Event database path. |
| `INTERNFLY_STEP_SECONDS` | `1.0` | Wall-clock delay between simulation ticks. |
| `INTERNFLY_AUTO_START` | `true` | Start the agent loop with the API. |
| `INTERNFLY_RUNNER_URL` | unset locally | Restricted runner service URL. |
| `INTERNFLY_CORS_ORIGINS` | `http://localhost:5173` | Allowed dashboard origins. |
| `INTERNFLY_SIM_MINUTES_PER_TICK` | `20` | Virtual minutes advanced per tick. |
| `INTERNFLY_SLEEP_MINUTES` | `300` | Simulated sleep duration: exactly five hours by default. |
| `INTERNFLY_DSA_SOLVE_TICKS` | `7` | Bounded DSA solving duration. |
| `INTERNFLY_JOB_SEARCH_TICKS` | `7` | Bounded job-search duration. |
| `INTERNFLY_CONNECTOME_MANIFEST` | auto-detected | Optional explicit path to a connectome manifest. |
| `NEUPRINT_TOKEN` | unset | Import-time credential only; never needed to run the app. |

See [.env.example](.env.example) for the deployment defaults.

## Project structure

```text
internfly/                    FastAPI API, orchestrator, state machine and specialists
apps/dashboard/               React, TypeScript and Three.js observatory dashboard
data/connectome/manifests/    Checked-in development connectome fixture
data/generated/               Locally generated Male CNS manifest; created on demand
scripts/                      Male CNS import and manifest utilities
deploy/compose/               Docker Compose deployment
docs/                         Scientific provenance, metrics and threat model
tests/                        Backend, durability, runner and safety tests
```

## Tests and build verification

Backend tests:

```powershell
# Run from the repository root.
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --python 3.12 --extra dev
uv run python -m pytest
```

Dashboard production build:

```powershell
npm --prefix apps/dashboard run build
```

## Troubleshooting

### Port 5173 or 8000 is already in use

Stop the existing development process with `Ctrl+C`, or identify the process before choosing a different port. If Vite selects `5174`, open the URL it prints and add that origin to `INTERNFLY_CORS_ORIGINS` when accessing the API directly.

### The dashboard says `DEVELOPMENT FIXTURE`

This is expected until `data/generated/malecns-subgraph.json` exists and the API has been restarted. Check the importer output and the API endpoint <http://localhost:8000/api/connectome/map>.

### The dashboard stays on `CONNECTING`

Confirm the API is running at port `8000`, then open <http://localhost:8000/health/ready>. In Docker, inspect service health with:

```powershell
docker compose -f deploy/compose/docker-compose.yml ps
```

### Generated code does not execute in local development

Local development deliberately uses deterministic fixture execution by default. Start the complete Docker Compose stack to use the isolated runner service.

## Attribution and license obligations

Male CNS v1.0 data is published under CC-BY 4.0. Generated manifests retain source, license, retrieval, selection, and checksum metadata. If you redistribute a generated manifest or screenshots derived from it, preserve the Male CNS attribution and make the engineered visualization and simulation layers clear.

InternFly is a software experiment and entertainment project. It is not a biological brain emulation, medical model, recruitment service, or autonomous job-submission bot.
