# Deploy Artifact Verification

**Scope:** Four root-level Dockerfiles, four GitHub Actions workflows, `docker-compose.yml`, and `cloudbuild.yaml`. Read-only; no `gcloud`, no `docker`, no app execution.

---

## Section 1 — Dockerfile purpose

All four Dockerfiles use the `python:3.11-slim` base image.

### `Dockerfile`

- **Base:** `python:3.11-slim`
- **Entry point line:** `CMD ["/app/start.sh"]`
- **What it runs:** `start.sh`, which dispatches on `$APP_NAME`:
  - `APP_NAME=justdata` (default) → `gunicorn run_justdata:app` (unified platform)
  - otherwise → `gunicorn run_${APP_NAME}:app` (no such `run_<x>.py` modules exist at repo root — this branch is unreachable in the current tree)
- **Build arg:** `APP_NAME=` (default empty)

First 20 lines:
```
# Use Python 3.11 slim image
FROM python:3.11-slim

# Build argument to specify which app to run
# If not provided or empty, defaults to unified "justdata" app
ARG APP_NAME=
ENV APP_NAME=${APP_NAME:-justdata}

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
```

Last 20 lines:
```
# Create non-root user and give ownership of all app files
# Also fix permissions on ALL directories (OneDrive sync can set restrictive perms)
RUN useradd --create-home --shell /bin/bash app && \
    find /app -type d -exec chmod 755 {} \; && \
    find /app -type f -exec chmod 644 {} \; && \
    chmod +x /app/start.sh && \
    chown -R app:app /app
USER app

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Run the startup script which handles PORT variable correctly
CMD ["/app/start.sh"]
```

### `Dockerfile.app`

- **Base:** `python:3.11-slim`
- **Entry point line:** `CMD ["/app/start.sh"]`
- **What it runs:** same dispatch via `start.sh` → `gunicorn run_justdata:app`
- **Build arg:** `APP_NAME=` (default empty)
- Near-identical to `Dockerfile`, but omits the per-app `data/reports/*` directory creation and the OneDrive permission fixup pass. 49 lines vs 69.

First 20 lines:
```
# Use Python 3.11 slim image
FROM python:3.11-slim

# Build argument to specify which app to run
# If not provided or empty, defaults to unified "justdata" app
ARG APP_NAME=
ENV APP_NAME=${APP_NAME:-justdata}

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
```

Last 20 lines:
```
# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy and make startup script executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Run the startup script which handles PORT variable correctly
CMD ["/app/start.sh"]
```

### `Dockerfile.electwatch-job`

- **Base:** `python:3.11-slim`
- **Entry point line:** `CMD ["python", "-c", "from justdata.apps.electwatch.weekly_update import WeeklyDataUpdate; WeeklyDataUpdate(use_cache=False).run()"]`
- **What it runs:** `justdata/apps/electwatch/weekly_update.py` (inline `python -c`)
- **Port:** not exposed (batch job, not a service)

First 20 lines:
```
# Dockerfile for ElectWatch Weekly Update Job
# This runs as a Cloud Run Job triggered by Cloud Scheduler

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

Last 20 lines (file is 38 lines; showing last 18):
```
# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Run the weekly update script
CMD ["python", "-c", "from justdata.apps.electwatch.weekly_update import WeeklyDataUpdate; WeeklyDataUpdate(use_cache=False).run()"]
```

### `Dockerfile.hubspot-sync-job`

- **Base:** `python:3.11-slim`
- **Entry point line:** `CMD ["python", "-c", "from justdata.apps.hubspot.daily_sync import HubSpotDailySync; HubSpotDailySync().run()"]`
- **What it runs:** `justdata/apps/hubspot/daily_sync.py` (inline `python -c`)
- **Port:** not exposed (batch job)

First 20 lines:
```
# Dockerfile for HubSpot Daily Sync Job
# Runs as a Cloud Run Job triggered by Cloud Scheduler (daily)

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
```

Last 20 lines (file is 30 lines; showing last 12):
```
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

CMD ["python", "-c", "from justdata.apps.hubspot.daily_sync import HubSpotDailySync; HubSpotDailySync().run()"]
```

### Aside — fifth Dockerfile (not at repo root)

`scripts/slack_bot/Dockerfile` exists inside the slack bot directory and is built implicitly by `gcloud builds submit scripts/slack_bot` in `deploy-slack-bot.yml`. It is not one of the four root-level Dockerfiles enumerated by this audit, but it is the image built by the `deploy-slack-bot.yml` workflow. Entry: `gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:flask_app` → `scripts/slack_bot/app.py`.

---

## Section 2 — Workflow triggers and build targets

### `.github/workflows/ci.yml`
- **Triggers:** `pull_request` on branches `test`, `staging`, `main`
- **Dockerfile:** none (runs `pytest` on a plain `ubuntu-latest` Python 3.11 runner)
- **Cloud Run service:** none
- **GCP project:** none

### `.github/workflows/deploy-cloudrun.yml`
- **Triggers:** `push` to `main` or `staging`; `workflow_dispatch`
- **Dockerfile:** `Dockerfile.app` (built at line 78 with `docker build -f Dockerfile.app ...`)
- **Cloud Run service:** `justdata` on push to `main`; `justdata-test` on push to `staging` (decided in "Set deployment target based on branch" step)
- **GCP project:** `justdata-ncrc` (env `PROJECT_ID`)
- **Region:** `us-east1`
- **Registry:** `us-east1-docker.pkg.dev/justdata-ncrc/justdata-repo`

### `.github/workflows/deploy-electwatch-job.yml`
- **Triggers:** `push` to `main` with path filter `justdata/apps/electwatch/**`, `Dockerfile.electwatch-job`, or `.github/workflows/deploy-electwatch-job.yml`; `workflow_dispatch`
- **Dockerfile:** `Dockerfile.electwatch-job`
- **Cloud Run service:** Cloud Run **Job** `electwatch-weekly-update` (not a service — `gcloud run jobs create/update`)
- **GCP project:** `justdata-ncrc` (env `PROJECT_ID`)
- **Region:** `us-east1`
- **Image name:** `electwatch-job` (env `IMAGE_NAME`) in repo `justdata-repo`

### `.github/workflows/deploy-slack-bot.yml`
- **Triggers:** `push` to `main` with path filter `scripts/slack_bot/**`; `workflow_dispatch`
- **Dockerfile:** `scripts/slack_bot/Dockerfile` (built implicitly via `gcloud builds submit scripts/slack_bot --tag ...`)
- **Cloud Run service:** `justdata-slack-bot`
- **GCP project:** `justdata-ncrc` (env `PROJECT_ID`)
- **Region:** `us-east1`
- **Registry:** `gcr.io/justdata-ncrc/justdata-slack-bot`

### Summary table

| Workflow | Triggers | Dockerfile used | Cloud Run service | GCP project |
|---|---|---|---|---|
| `ci.yml` | PR → `test` / `staging` / `main` | none | none | none |
| `deploy-cloudrun.yml` | push → `main` or `staging`; manual | `Dockerfile.app` | `justdata` (main) / `justdata-test` (staging) | `justdata-ncrc` |
| `deploy-electwatch-job.yml` | push → `main` (paths filter); manual | `Dockerfile.electwatch-job` | Job `electwatch-weekly-update` | `justdata-ncrc` |
| `deploy-slack-bot.yml` | push → `main` (paths `scripts/slack_bot/**`); manual | `scripts/slack_bot/Dockerfile` | `justdata-slack-bot` | `justdata-ncrc` |

---

## Section 3 — Dockerfile / workflow mapping

**In use (Dockerfile + workflow pair):**
- `Dockerfile.app` ⇄ `deploy-cloudrun.yml` (builds `justdata` and `justdata-test` Cloud Run services)
- `Dockerfile.electwatch-job` ⇄ `deploy-electwatch-job.yml` (builds `electwatch-weekly-update` Cloud Run Job)
- `scripts/slack_bot/Dockerfile` ⇄ `deploy-slack-bot.yml` (builds `justdata-slack-bot` Cloud Run service)

**Orphaned Dockerfiles (exist at repo root but no `.github/workflows/*.yml` references):**
- `Dockerfile` — no workflow references it. The only build reference is `docker-compose.yml` (implicit via `build: .`).
- `Dockerfile.hubspot-sync-job` — no workflow references it. The only build reference is `scripts/deploy-hubspot-sync-job.sh` (manual deploy script at line 111).

**Broken references (workflow names a missing file):** none. Every Dockerfile named in a workflow (`Dockerfile.app`, `Dockerfile.electwatch-job`, `scripts/slack_bot/Dockerfile`) exists on disk.

---

## Section 4 — docker-compose

`docker-compose.yml` exists at the repo root and defines **five services**:

| Service | Build / Image | Command |
|---|---|---|
| `justdata-api` | `build: .` (root `Dockerfile`) | container default `CMD` (i.e. `/app/start.sh` → `gunicorn run_justdata:app`) |
| `postgres` | `image: postgres:15` | default postgres |
| `redis` | `image: redis:7-alpine` | default redis |
| `celery-worker` | `build: .` (root `Dockerfile`) | `celery -A justdata.shared.services.celery_app worker --loglevel=info` |
| `celery-beat` | `build: .` (root `Dockerfile`) | `celery -A justdata.shared.services.celery_app beat --loglevel=info` |

Two named volumes: `postgres_data`, `redis_data`. Port bindings: `8000:8000` (api), `5432:5432` (postgres), `6379:6379` (redis).

This is the sole consumer of the root-level `Dockerfile`. All three `build: .` services (api, celery-worker, celery-beat) build from the same image.

---

## Section 5 — cloudbuild.yaml

`cloudbuild.yaml` exists at the repo root. Contents:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--build-arg'
      - 'APP_NAME=${_APP_NAME}'
      - '-f'
      - 'Dockerfile.app'
      - '-t'
      - '${_IMAGE_URI}'
      - '--cache-from'
      - '${_IMAGE_URI}'
      - '.'
    timeout: '1200s'
images:
  - '${_IMAGE_URI}'
options:
  machineType: 'E2_HIGHCPU_8'
  logging: CLOUD_LOGGING_ONLY
```

- **Steps:** one — a `docker build` invocation against `Dockerfile.app` using substitutions `_APP_NAME` (default empty) and `_IMAGE_URI` for the output tag.
- **Dockerfile referenced:** `Dockerfile.app`.
- **Deploy targets:** none — this file only builds and pushes the image. It does no `gcloud run deploy`.
- **Consumer:** `scripts/deploy-cloudrun.sh` (the manual deploy script) calls `gcloud builds submit --config=cloudbuild.yaml` with `_APP_NAME=,_IMAGE_URI=...`. It is not referenced by any file under `.github/workflows/` — `deploy-cloudrun.yml` builds `Dockerfile.app` directly with `docker build` and does not invoke Cloud Build.

---

## Section 6 — Observations

Factual observations only.

1. **`Dockerfile` (root) is not referenced by any `.github/workflows/*.yml`.** Its only consumer is `docker-compose.yml` (`build: .` on three services). It is not used in CI or in any automated Cloud Run deploy path.

2. **`Dockerfile.hubspot-sync-job` is not referenced by any `.github/workflows/*.yml`.** Its only consumer is `scripts/deploy-hubspot-sync-job.sh` (manual deploy script). Despite CLAUDE.md noting that HubSpot daily sync is deployed, there is no GitHub Actions workflow that deploys this job automatically.

3. **`cloudbuild.yaml` is not referenced by any `.github/workflows/*.yml`.** Its only consumer is `scripts/deploy-cloudrun.sh` (manual deploy script). The production automated path (`deploy-cloudrun.yml`) builds `Dockerfile.app` directly with `docker build` rather than calling Cloud Build.

4. **`Dockerfile` and `Dockerfile.app` have the same entry point chain** (`/app/start.sh` → `gunicorn run_justdata:app`). The two differ primarily in: (a) `Dockerfile` pre-creates per-app `data/reports/*` directories and does a recursive chmod pass; (b) `Dockerfile.app` is leaner. Both copy the full repo and run as a non-root `app` user.

5. **The `start.sh` dispatch branch for non-`justdata` `APP_NAME` is currently unreachable.** `start.sh` falls through to `gunicorn run_${APP_NAME}:app`, but there are no `run_<x>.py` modules at the repo root other than `run_justdata.py`. The `ARG APP_NAME=` in `Dockerfile` / `Dockerfile.app` has no code path that exercises a non-default value in any workflow.

6. **`deploy-cloudrun.yml` deploys to two Cloud Run services controlled by branch:** `justdata` on `main`, `justdata-test` on `staging`. Both are in project `justdata-ncrc`, region `us-east1`.

7. **`deploy-electwatch-job.yml` deploys a Cloud Run _Job_, not a Cloud Run _service_** (`gcloud run jobs create/update electwatch-weekly-update`). It uses a different image name (`electwatch-job`) from the main app image.

8. **`deploy-slack-bot.yml` builds a fifth Dockerfile that lives at `scripts/slack_bot/Dockerfile`,** not at repo root. It is built via `gcloud builds submit scripts/slack_bot --tag ...` (not `docker build -f`), pushed to `gcr.io/justdata-ncrc/justdata-slack-bot`, and deployed as the `justdata-slack-bot` service.

9. **Branch-trigger note:** `ci.yml` fires on PRs targeting `test` / `staging` / `main`, but the branch strategy in `CLAUDE.md` describes only `staging` and `main` as long-lived. The `test` branch in the CI trigger list does not correspond to any documented branch in the current branch strategy.

10. **Two workflows use `${{ secrets.GCP_SERVICE_ACCOUNT_KEY }}`** (`deploy-cloudrun.yml`, `deploy-electwatch-job.yml`) while `deploy-slack-bot.yml` uses `${{ secrets.GCP_SA_KEY_JUSTDATA_NCRC }}`. Two different secret names for GCP service account credentials are in active use across workflows.

11. **Credential file present at repo root:** `gcp-service-account-key.json` exists at the repo root (observed in `ls` output). Flagging the presence without inspecting or reproducing any content; this is unrelated to the workflow/Dockerfile mapping but visible during this audit.

12. **`docker-compose.yml` describes a Postgres + Redis + Celery topology** that does not appear anywhere in the Cloud Run deploys or in `requirements.txt` wiring used by the Flask surfaces. The file only matters for local-compose developer workflows (if any), not for production.

13. **Dockerfiles are broadly uniform:** all four use `python:3.11-slim`, all install `gcc g++ libpq-dev curl`, all run as a non-root `app` user. The long-running service Dockerfiles (`Dockerfile`, `Dockerfile.app`) expose port 8080; the two job Dockerfiles (`Dockerfile.electwatch-job`, `Dockerfile.hubspot-sync-job`) do not expose a port.
