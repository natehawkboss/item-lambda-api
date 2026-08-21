# item-lambda-api

Asset reporting API over two entities: **sites** (locations) and **items** (name,
model number, type). FastAPI + SQLAlchemy, SQLite locally, Postgres in production.

**Running live:** https://am222hrzk4.execute-api.us-east-1.amazonaws.com
· [Swagger UI](https://am222hrzk4.execute-api.us-east-1.amazonaws.com/docs)
· [items-by-site report](https://am222hrzk4.execute-api.us-east-1.amazonaws.com/reports/items-by-site)

API Gateway → Lambda (arm64, Python 3.12) → RDS Postgres in a private subnet.
No auth, deliberately — see [Auth](#auth) below.

Built as a working version of an interview exercise — the point it makes is that
storage and hosting are one decision, and the code is arranged so you can see it:
`DATABASE_URL` is the only thing that changes between keeping the data on the
machine that runs the app and keeping it in a database the app connects to. The
second one is what lets you throw the machine away and start another.

## Run it

```bash
uv sync
uv run python -m scripts.seed          # load data/*.csv into the database
uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
```

```bash
uv run pytest
```

## Endpoints

| Method | Path                     | Notes                                        |
|--------|--------------------------|----------------------------------------------|
| GET    | `/health`                | No auth, no DB — load-balancer target        |
| GET    | `/sites`                 | All sites                                    |
| GET    | `/sites/{id}`            | 404 when missing                             |
| GET    | `/items`                 | Filters: `site_id`, `type`, `q`; paginated   |
| POST   | `/items`                 | The write path                               |
| GET    | `/items/{id}`            |                                              |
| GET    | `/reports/items-by-site` | Counts per site per type, one `GROUP BY`     |

Interactive docs at `/docs`, machine-readable schema at `/openapi.json`.

## Deploy

API Gateway HTTP API → Lambda (arm64) → private RDS Postgres. No Docker
required — `uv` cross-resolves Linux wheels from macOS.

```bash
./scripts/build_lambda.sh                    # -> build/lambda.zip

cd infra
cp terraform.tfvars.example terraform.tfvars # set your AWS profile
terraform init
terraform apply

# create tables and load the CSVs (runs inside the VPC)
aws lambda invoke --function-name "$(terraform output -raw seed_function_name)" \
  --profile <profile> /dev/stdout

curl "$(terraform output -raw api_url)health"
```

Re-running the seeder with `--payload '{"reset":true}'` clears items and
restores the dataset to what `data/items.csv` describes.

`terraform destroy` removes everything.

### What the infrastructure says

- **RDS, not a file on disk.** Nothing is saved on the Lambda itself, so AWS can
  destroy and recreate it at any time, and run as many copies at once as the
  traffic needs, without anything being lost. There is nothing on it to back up.
- **The database has no public endpoint.** Its security group accepts traffic
  from the Lambda's security group, not from a CIDR range.
- **Seeding is a separate one-off function**, not startup code, so concurrent
  cold starts can't race each other creating schema. It runs inside the VPC,
  which is what lets the database stay private with no bastion.
- **Function URL, not API Gateway** — no per-request gateway cost and no
  29-second integration ceiling.
- **Auth is written but switched off** (`app/security.py`), so the endpoints
  stay open to try. Production settings are noted at each call site.

## Auth

`POST /items` is wired to `require_api_key` from `app/security.py` — it is live
code, not a commented-out example. Enforcement is driven by configuration
rather than by editing source: set `API_KEY` in the environment and writes
require a matching `X-API-Key` header.

**This deployment leaves `API_KEY` unset, so the write path is open** and anyone
can try it. That's a deliberate demo choice; the tests cover both postures.

For a real deployment a shared secret is the fallback, not the first choice.
Preferred, in order: a Lambda Function URL with `AWS_IAM` (callers sign requests
with SigV4; the service stores no credential at all), then API Gateway usage
plans (issuance, rotation and throttling handled outside the app), then this.

### Input handling

No string sanitizing anywhere, on purpose. Injection is prevented structurally:
every value goes to Postgres as a bound parameter, so `'; DROP TABLE items; --`
is stored and matched as ordinary text. Pydantic rejects malformed requests at
the boundary with a `422` before any query runs, and responses are JSON, so
there is no markup context to escape into. `tests/test_api.py` asserts it.

## Notes from deploying it

Two things that only show up when you actually ship:

**Cross-building the package without Docker.** `uv` resolves wheels for a target
platform via `--python-platform`, which is what makes a Docker-free Lambda build
possible from macOS. Two traps: `manylinux2014` has no aarch64 `greenlet` wheel
(use `manylinux_2_28`, which matches the Amazon Linux 2023 runtime), and
stripping `*.dist-info` to shrink the zip breaks `psycopg` — it reads its own
version through `importlib.metadata`, so without it SQLAlchemy rejects the
driver with "psycopg version 3.0.2 or higher is required."

**Lambda Function URLs need more than `authorization_type = "NONE"`.** That only
disables IAM *authentication*; Lambda still authorizes against the resource
policy, so without an explicit `lambda:InvokeFunctionUrl` permission the URL
answers 403 to everyone. Even with the policy correct it stayed 403 in this
account, so the public entrypoint is an API Gateway HTTP API instead. The
tradeoff is a 29-second integration ceiling — irrelevant here, where every
endpoint is a small indexed query, but exactly what would rule it out for heavy
report generation.

## Why the CSVs are not the datastore

`data/*.csv` is seed data. It describes the world as of checkout. `POST /items`
means the database diverges from those files immediately — so the files are a
fixture, and the database is the truth.

## Directory Map

- `app/` — the application (`config`, `db`, `models`, `schemas`, `routers/`)
- `data/` — seed CSVs (sites, items)
- `scripts/seed.py` — loads the CSVs; idempotent on sites
- `tests/` — pytest, in-memory SQLite per test
- `ROADMAP.md` — state file: what's in flight, what's next
