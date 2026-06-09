# Deployment guide

The web app (Spring Boot API + React frontend) is packaged as a single Docker
image by the root [`Dockerfile`](./Dockerfile). The frontend is built and copied
into the backend's static resources, and the backend serves both the SPA and the
`/api/v1/**` endpoints on one port. It needs one thing at runtime: a PostgreSQL
database.

## Runtime configuration

All configuration is via environment variables (see
[`application.properties`](./backend/src/main/resources/application.properties)):

| Variable | Required | Default | Notes |
|---|---|---|---|
| `PORT` | no | `8080` | Port the server listens on. Most platforms set this for you. |
| `ADDRESS` | no | `0.0.0.0` | Bind address. |
| `DB_CONNECTION_STRING` | one of these | – | Full JDBC URL, e.g. `jdbc:postgresql://host:5432/db`. |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | one of these | port `5432` | Used to build the JDBC URL if `DB_CONNECTION_STRING` is not set. |
| `DB_USERNAME` | yes | – | Database user. |
| `DB_PASSWORD` | yes | – | Database password. |
| `DDL_AUTO` | no | `validate` | Set to `update` on first deploy so the schema is created automatically. |
| `SENTRY_DSN` | no | empty (disabled) | Optional error reporting. |
| `JPA_SHOW_SQL` | no | `false` | Set `true` to log SQL. |

Health check endpoint: `GET /actuator/health` (returns `200 {"status":"UP"}`).

## Option A — Render (recommended, one repo, free)

Render can build the Docker image and provision a free PostgreSQL database from
the included [`render.yaml`](./render.yaml) blueprint.

1. Push this repository to GitHub.
2. In the [Render dashboard](https://dashboard.render.com), click
   **New + → Blueprint** and select this repo.
3. Render reads `render.yaml`, creates the web service + a free Postgres
   instance, and wires the `DB_*` variables automatically. Click **Apply**.
4. First boot creates the schema (`DDL_AUTO=update`). The app comes up at
   `https://<your-service>.onrender.com`.

Notes:
- Free web services sleep after ~15 min of inactivity and cold-start on the next
  request (~30–60 s for a JVM app).
- Render's **free** Postgres is deleted after 30 days. For a permanent free
  database, use Neon (Option C) and set the `DB_*` variables on the web service.

## Option B — Fly.io (free allowance, stays warm)

```bash
fly launch --no-deploy            # generates fly.toml from the Dockerfile
fly postgres create               # creates a managed Postgres app
fly postgres attach <pg-app>      # sets DATABASE_URL on the app
# Map Fly's DATABASE_URL to the app's variables (or set DB_* directly):
fly secrets set DDL_AUTO=update DB_USERNAME=... DB_PASSWORD=... \
  DB_CONNECTION_STRING="jdbc:postgresql://<host>:5432/<db>"
fly deploy
```
Set the app's internal port to `8080` in `fly.toml` (`[http_service] internal_port = 8080`).

## Option C — Any container host + Neon Postgres (permanent free DB)

1. Create a free Postgres at [neon.tech](https://neon.tech) and copy the host,
   database, user and password.
2. Deploy the Docker image to any free container host (Koyeb, Railway, etc.).
3. Set: `DDL_AUTO=update`, `DB_HOST`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`
   (Neon requires SSL, so append `?sslmode=require` if you use
   `DB_CONNECTION_STRING`).

## Getting data into the app

A fresh deployment starts with an empty database, so the UI shows no reports
until data is ingested. There are two ways to populate it.

### Live data (production) — requires a residential proxy

The scrapers in [`data/`](./data) pull contest submissions from LeetCode, run
`copydetect`, and POST the results to the API. LeetCode's contest endpoints are
behind **Cloudflare bot protection**, which blocks datacenter/cloud IPs, so the
scrapers must route through a residential proxy. The code already supports this
via the `OXYLABS_CREDENTIALS` environment variable (any Oxylabs-compatible
residential proxy works).

```bash
cd data
pip install -r requirements.txt
export API_BASE_URL=https://<your-app-url>
export OXYLABS_CREDENTIALS="<user>:<pass>"   # residential proxy
CONTEST_SLUG=weekly-contest-507 python -c "import scraping.submissions.run as r; r.handler({},None)"
CONTEST_SLUG=weekly-contest-507 python -c "import processing.copydetect.run as r; r.handler({},None)"
```

Run this per contest (e.g. on a weekly schedule) to keep the app up to date.

### Demo data (no proxy needed)

To see the app working immediately without scraping, seed a realistic dataset.
[`data/seed_demo.py`](./data/seed_demo.py) ingests a contest, two questions and a
mix of submissions through the real API, then runs the real `copydetect`
pipeline so genuine plagiarism groups appear in the UI.

```bash
cd data
pip install -r requirements.txt
API_BASE_URL=https://<your-app-url> python seed_demo.py
```

## Run locally with Docker

```bash
docker run -d --name lpd-pg -e POSTGRES_USER=lpd -e POSTGRES_PASSWORD=lpdpass \
  -e POSTGRES_DB=lpd -p 5432:5432 postgres:16

docker build -t lpd .
docker run --rm --network host \
  -e PORT=8080 -e DDL_AUTO=update \
  -e DB_CONNECTION_STRING="jdbc:postgresql://localhost:5432/lpd" \
  -e DB_USERNAME=lpd -e DB_PASSWORD=lpdpass \
  lpd
# open http://localhost:8080
```
