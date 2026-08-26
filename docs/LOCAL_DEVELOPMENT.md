# Local Development Guide

This guide takes a clean checkout to a working DocEdge development environment with PostgreSQL, Redis, the FastAPI backend, Next.js web app, Expo mobile app, and the optional MedMCQA Pathology dataset.

## 1. Prerequisites

Install:

- Git
- Docker Desktop (Docker Engine with Compose also works on Linux)
- Python 3.11 or 3.12
- Bun 1.4 or newer
- Optional for native development: Android Studio and/or Xcode on macOS

Check the tools:

```bash
git --version
docker --version
docker compose version
python3 --version
bun --version
```

On Windows, use `py -3.11` instead of `python3` where necessary. Commands below assume macOS/Linux and are run from the repository root.

## 2. Clone and configure

```bash
git clone <repository-url>
cd Medical-learning-intelligence
cp .env.example .env
```

The checked-in development database credentials are only for local Docker. Do not reuse them in a shared or production environment.

For the web app, create `apps/web/.env.local` when Google sign-in or a non-default API URL is needed:

```dotenv
API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
```

Without a Google client ID, use email/password development flows.

## 3. Python environment

Create an isolated virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell activation:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Keep the environment activated whenever running backend, ingestion, or Python tests.

## 4. JavaScript dependencies

Install all Bun workspace dependencies once from the repository root:

```bash
bun install --frozen-lockfile
```

If the lockfile was intentionally changed, run `bun install`, inspect `bun.lock`, and commit it with the dependency change.

## 5. Start PostgreSQL and Redis

```bash
docker compose -f infrastructure/docker-compose.yml up -d
docker compose -f infrastructure/docker-compose.yml ps
```

Local services:

| Service | Address | Purpose |
|---|---|---|
| PostgreSQL + pgvector | `localhost:5432` | Canonical application database |
| Redis | `localhost:6379` | Rate limiting, future cache/background work |

Inspect logs when a container is unhealthy:

```bash
docker compose -f infrastructure/docker-compose.yml logs postgres
docker compose -f infrastructure/docker-compose.yml logs redis
```

Stop services without deleting data:

```bash
docker compose -f infrastructure/docker-compose.yml down
```

`docker compose ... down -v` deletes the local database and Redis volumes. Use it only when you intentionally want a clean database.

## 6. Initialize the application database

For the current pre-M9 schema:

```bash
python -m scripts.seed_curriculum
```

This creates the existing tables through the current initialization layer and seeds courses, curriculum nodes, and development records. Milestone 9 replaces production schema synchronization with Alembic migrations; after that change, the standard command will be:

```bash
alembic upgrade head
python -m scripts.seed_curriculum
```

Confirm database connectivity:

```bash
docker compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U medadmin -d medical_exam_ai -c "select count(*) from courses;"
```

## 7. Load the MedMCQA Pathology question bank

The application can start without the full dataset, but exams require questions. Raw and generated datasets are intentionally excluded from Git.

### Reproduce the complete dataset

The following downloads the official MedMCQA Parquet splits, extracts Pathology, normalizes records, annotates duplicates, and writes JSONL outputs:

```bash
python scripts/run_pipeline.py
```

Expected principal output:

```text
data/processed/pathology/pathology_all.jsonl
data/processed/pathology/pathology_labeled.jsonl
data/processed/pathology/summary_report.json
```

The download is large and requires network access. The raw files are treated as immutable inputs. Do not edit the MedMCQA clone or generated Parquet files.

### Import processed questions into PostgreSQL

```bash
python scripts/import_to_db.py
```

The importer skips existing external source IDs by default, so normal reruns do not duplicate MedMCQA questions.

Verify the import:

```bash
docker compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U medadmin -d medical_exam_ai -c "select count(*) from questions;"
```

Do not use `--force-recreate` against a database containing work you need; it drops all tables.

## 8. Run the applications

### Recommended: separate terminals

Terminal 1 — backend:

```bash
source .venv/bin/activate
python -m uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — web:

```bash
bun run dev:web
```

Terminal 3 — mobile when required:

```bash
bun run dev:mobile
```

Addresses:

- Web: `http://localhost:3000`
- API health: `http://127.0.0.1:8000/api/health`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Expo developer server: shown in the Expo terminal

### Convenience launcher

After Python and Bun dependencies are installed:

```bash
python dev.py
```

It starts Docker, initializes/seeds the current database when needed, then launches backend and web. Separate terminals are easier to debug, so use the convenience launcher only after the manual setup works.

## 9. Mobile networking

`127.0.0.1` inside a physical phone or Android emulator is not always the development computer.

- iOS Simulator can usually reach `http://127.0.0.1:8000`.
- Android Emulator commonly uses `http://10.0.2.2:8000`.
- A physical device must use the computer's LAN address, such as `http://192.168.1.20:8000`.

Set the API base URL for the mobile environment and ensure the device and computer are on the same network. Never put production secrets in `EXPO_PUBLIC_*` variables because they are bundled into the client.

## 10. Verification before opening a pull request

```bash
python -m unittest discover tests
bun run typecheck
bun run build
```

Useful targeted checks:

```bash
python -m unittest tests.test_pipeline
python -m unittest tests.test_database
bun --filter web typecheck
bun --filter mobile typecheck
```

The full web build needs the JavaScript dependencies installed and may require the expected environment variables.

## 11. Common problems

### `ModuleNotFoundError: sqlalchemy` or `pandas`

The virtual environment is not active or requirements were not installed:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### `bun: command not found`

Install Bun, restart the terminal, verify `bun --version`, and run `bun install --frozen-lockfile`.

### PostgreSQL connection refused

```bash
docker info
docker compose -f infrastructure/docker-compose.yml ps
docker compose -f infrastructure/docker-compose.yml logs postgres
```

Confirm `.env` uses port `5432` unless the Compose port was deliberately changed.

### `docker-credential-desktop` executable not found on macOS

Docker Desktop may be installed while its credential helper directory is missing from the shell `PATH`. Confirm the helper exists:

```bash
ls -l /Applications/Docker.app/Contents/Resources/bin/docker-credential-desktop
```

Fix the current terminal session:

```bash
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
docker compose -f infrastructure/docker-compose.yml up -d
```

If that works, make it permanent for zsh:

```bash
echo 'export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Alternatively, Docker Desktop can install its command-line tools from **Settings → Advanced → CLI tools installation**. Do not remove `"credsStore": "desktop"` from `~/.docker/config.json` merely to bypass this error; the credential helper is installed and adding its directory to `PATH` preserves secure credential storage.

### Port already in use

Stop the existing service or change the local port. Keep `API_URL`, `NEXT_PUBLIC_API_URL`, and mobile configuration consistent with the new backend port.

### Web loads but API calls fail

Verify the backend health endpoint, `apps/web/.env.local`, and the rewrite in `apps/web/next.config.mjs`. Restart Next.js after changing environment variables.

### No questions are available

Run the data pipeline and database importer, then query the `questions` count as shown above.

## 12. Data and safety rules

- Do not commit `.env`, raw MedMCQA Parquet files, processed JSONL datasets, local databases, or copyrighted textbook files.
- Never invent textbook references for MedMCQA questions.
- Treat imported answers as source data, not automatically verified medical truth.
- Use only legitimately obtained knowledge documents.
- The product is for education and exam preparation, not autonomous clinical diagnosis.
