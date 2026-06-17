# Data Forge

Data Forge is a local data engineering platform for building useful personal and applied data products without sending private data to external services.

The repository now has two connected layers:

- a reusable local data platform: Postgres, ClickHouse, Kafka, MinIO, Hive Metastore, Iceberg, Spark, Trino, Airflow, Temporal, dbt-style models, data contracts, quality checks and evidence;
- an applied product domain: LifeHub, a local-only sports, recovery and decision engine for Saint Petersburg.

Retail CDC is still available as a reproducible engineering scenario, but it is no longer the main product story. The main goal is to make the repository a practical, extensible data platform that can accept new life, market, sport, project or operational sources and turn them into analytics and decisions.

## Product Value

LifeHub answers a concrete daily question:

> What should I do today, given weather, places, training history, recovery, goals and feedback?

It currently supports:

- Saint Petersburg weather readiness from Open-Meteo fixtures or API calls;
- public outdoor spots and sport locations from config or Overpass;
- Telegram-style activity diary and feedback loop;
- skate, snowboard, moto lesson, volleyball, gym, walk and recovery recommendations;
- GPX/activity file summaries;
- sleep quality as a first-class recovery source;
- daily and weekly context profiles;
- local evidence generation with privacy checks.

The important engineering point: these are not one-off scripts. Sources enter a shared lakehouse contract, flow through landing JSONL, Spark, Iceberg Bronze/Silver/Gold and Trino, and can then feed analytics or product decisions.

## Data Platform

| Layer | Tools | Purpose |
| --- | --- | --- |
| Operational storage | Postgres | Local state, diary logs, spots, preferences, recommendations |
| Analytical storage | ClickHouse | Time-series and product analytics marts |
| Data lake | MinIO | S3-compatible object storage |
| Table format | Iceberg | Bronze/Silver/Gold lakehouse tables |
| Metadata | Hive Metastore | Iceberg catalog metadata |
| Processing | Spark | Landing JSONL to Iceberg loading |
| Query/DWH | Trino | SQL access to Iceberg and analytical stores |
| Streaming/CDC | Kafka, Schema Registry, Debezium | Retail CDC and event-streaming lab |
| Orchestration | Airflow, Temporal | Scheduled and durable workflows |
| Analytics engineering | dbt-compatible SQL | Staging and mart models |
| DataOps | contracts, catalog, expectations, validators, evidence | Reproducible quality and review gates |

Detailed map: [docs/data-engineering-stack.md](docs/data-engineering-stack.md).

## LifeHub

LifeHub is the first real product built on the platform.

Core docs:

- [docs/lifehub.md](docs/lifehub.md) - product, commands, storage, Telegram behavior and source onboarding
- [infra/lifehub/README.md](infra/lifehub/README.md) - service-level notes
- [config/lifehub/source_registry.yaml](config/lifehub/source_registry.yaml) - source onboarding contract
- [contracts/lifehub/data_contract.yaml](contracts/lifehub/data_contract.yaml) - data contract
- [catalog/lifehub/datasets.yaml](catalog/lifehub/datasets.yaml) - dataset catalog

Useful commands:

```bash
make lifehub-tests
make lifehub-demo
make lifehub-lake-export-fixture
make lifehub-lakehouse-runtime-smoke
make lifehub-source-onboard-demo
make lifehub-sleep-fixture
make lifehub-evidence-flow
```

The full lakehouse smoke starts local services, exports fixture LifeHub sources, loads them with Spark into Iceberg and queries them through Trino:

```bash
make lifehub-lakehouse-runtime-smoke
```

Evidence is written to:

- [docs/evidence/lifehub-lakehouse-evidence.md](docs/evidence/lifehub-lakehouse-evidence.md)
- [docs/evidence/lifehub-lakehouse-runtime-evidence.md](docs/evidence/lifehub-lakehouse-runtime-evidence.md)

## Adding a New Source

New sources should enter through the same medallion contract instead of becoming isolated scripts.

Generate an onboarding package:

```bash
PYTHONPATH=infra/lifehub python -m lifehub.cli source-onboard sleep_quality \
  --domain recovery \
  --source-type local_json_event \
  --event-type sleep_metric \
  --required-fields occurred_at,domain,metric_name,metric_value \
  --output-dir tmp/lifehub/source_onboarding
```

The generator creates:

- a source registry entry;
- a synthetic fixture;
- a runbook with import and lakehouse smoke commands.

Then the source can be promoted into a first-class connector, like `sleep_quality`, which now:

- has its own fixture and normalizer;
- writes privacy-safe landing events;
- appears in Iceberg Bronze/Silver via Spark;
- is queryable in Trino;
- influences LifeHub recommendations by turning high-impact activities into caution when recovery is low.

## Quick Start

Requirements:

- Docker 20.10+
- Docker Compose 2+
- 8 GB RAM minimum, 16 GB recommended for the full stack
- 20 GB disk space recommended

Setup:

```bash
git clone https://github.com/karnaksp/data-forge.git
cd data-forge
cp .env.example .env
```

Core platform:

```bash
docker compose --profile core up -d
docker compose ps
```

LifeHub local profile:

```bash
docker compose --profile lifehub up -d
```

Lakehouse smoke:

```bash
make lifehub-lakehouse-runtime-smoke
```

General validation:

```bash
make validate
```

## Services

| Service | URL | Default Login |
| --- | --- | --- |
| Kafka UI | http://localhost:8082 | no auth |
| Airflow | http://localhost:8085 | `airflow` / `airflow` |
| Superset | http://localhost:8089 | `admin` / `admin` |
| MinIO Console | http://localhost:9001 | `minio` / `minio123` |
| Trino | http://localhost:8080 | no auth |
| Temporal Web | http://localhost:8233 | no auth |

Full service index: [docs/services.md](docs/services.md).

## Retail CDC Scenario

The original retail CDC/lakehouse scenario is kept as an engineering lab and regression surface.

It covers:

- Postgres retail seed tables;
- Debezium CDC topics;
- Kafka and Schema Registry contracts;
- ClickHouse ingestion;
- validation SQL and evidence.

Start here when working on the CDC lab:

- [CASE_STUDY.md](CASE_STUDY.md)
- [docs/retail-cdc-runbook.md](docs/retail-cdc-runbook.md)
- [docs/evidence/retail-cdc-evidence.md](docs/evidence/retail-cdc-evidence.md)
- [sql/validation/](sql/validation/)
- [sql/examples/](sql/examples/)

## Repository Guide

- [docs/architecture.md](docs/architecture.md) - architecture and compose profiles
- [docs/data-engineering-stack.md](docs/data-engineering-stack.md) - stack coverage and LifeHub lakehouse flow
- [docs/development.md](docs/development.md) - local development and validation
- [docs/troubleshooting.md](docs/troubleshooting.md) - common runtime issues
- [docs/guidelines.md](docs/guidelines.md) - documentation and contribution style
- [docs/learning-path.md](docs/learning-path.md) - learning path for the stack

## Privacy Policy

This repository is designed for local-first work.

- Real Telegram tokens, chat IDs, diary notes, pain text, addresses, route files, broker exports and health exports stay local.
- Public repository fixtures are synthetic or public-safe.
- Evidence files store counts and contract status, not raw private records.
- `.env.example` documents required variables; real `.env` is local only.

## License

MIT. See [LICENSE](LICENSE).
