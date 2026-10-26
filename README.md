# sonnen Homelab Power Controller

Local Python services for collecting sonnenBatterie API data into PostgreSQL and making conservative, rule-based decisions about a Talos/Kubernetes homelab.

## Architecture

- `collector`: polls the local sonnen JSON API and stores normalized fields plus raw JSON.
- `postgres`: stores append-only measurement rows and decision history.
- `decision-engine`: reads recent rolling windows from PostgreSQL and writes scale/wake/hold decisions.
- `cluster_controller`: isolates future Talos/Kubernetes actions. The first implementation only supports Wake-on-LAN for the control plane and dry-run logging for the rest.

There is no web UI. Logs, SQL, Python, and R are the intended interfaces.

## Setup

```bash
cd sonnen-homelab-power-controller
cp .env.example .env
```

Edit `.env`:

- `SONNEN_BASE_URL`: for example `http://192.168.0.67`
- `SONNEN_AUTH_TOKEN`: token for authenticated endpoints
- `DATABASE_URL`: use `postgresql://sonnen:sonnen@postgres:5432/sonnen` inside Compose
- `CONTROL_PLANE_MAC_ADDRESS`: HP laptop control-plane MAC address
- `CLUSTER_API_HOST`: Kubernetes API endpoint for reachability checks
- `EXECUTE_ACTIONS=false`: dry-run mode, recommended default

## Start With Docker Compose

```bash
docker compose up --build
```

PostgreSQL persists data in the `postgres-data` volume. The migration in `migrations/001_init.sql` is automatically applied when the database volume is first created.

Optional pgAdmin:

```bash
docker compose --profile tools up pgadmin
```

## Initialize Or Reapply Schema

For an existing database:

```bash
psql "$DATABASE_URL" -f migrations/001_init.sql
```

## Manual sonnen API Tests

Status may work without a token:

```bash
curl "$SONNEN_BASE_URL/api/v2/status"
```

Authenticated request:

```bash
curl -H "Auth-Token: $SONNEN_AUTH_TOKEN" "$SONNEN_BASE_URL/api/v2/latestdata"
```

## Run Locally Without Compose

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python scripts/run_collector.py
python scripts/run_decision_engine.py
```

## Test Wake-on-LAN

Dry-run mode does not send packets from the decision engine. To explicitly send one:

```bash
python scripts/test_wol.py
```

The module validates MAC addresses and sends a UDP magic packet to `WOL_BROADCAST_ADDRESS:WOL_PORT`.

## Dry-Run Mode

`EXECUTE_ACTIONS=false` is the default. In this mode decisions are still written to `cluster_power_decisions`, but Wake-on-LAN and future cluster actions are logged instead of executed.

Set `EXECUTE_ACTIONS=true` only after validating decisions in the database and logs.

## First Decision Policy

The first policy is rule-based:

- scale down when average RSOC is below `SOC_SCALE_DOWN_THRESHOLD`
- scale up when RSOC is above `SOC_SCALE_UP_THRESHOLD` and sustained surplus exceeds `MIN_SURPLUS_W_FOR_SCALE_UP`
- scale down when grid import is sustained and battery SOC is not high
- hold when no threshold is met or when an action cooldown is active

The engine reads 5, 15, and 30 minute rolling windows from `sonnen_status`. Every decision is persisted with the measurement context used to make it.

## Tests

```bash
pytest
```

Current tests cover the decision policy, Wake-on-LAN packet generation, and basic sonnen client behavior.

## Future Improvements

- Add real Kubernetes API or `kubectl` workload scaling.
- Add `talosctl`-based node shutdown once the desired declarative flow is clear.
- Track SOC trend explicitly instead of using only rolling averages.
- Add retention/partitioning if the measurement tables grow large.
- Add views for R and Python analysis.

## Local API Smoke Test

After editing `.env`, verify the sonnen API client without starting PostgreSQL:

```bash
python scripts/read_sonnen_once.py
```

This reads `/api/v2/status` and `/api/v2/latestdata` through the same `SonnenClient` used by the collector.
