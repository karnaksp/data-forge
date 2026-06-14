# ClickHouse Ingestion Contract

This checklist validates the Kafka-to-ClickHouse wiring for the retail CDC case study. The static contract is covered by `python scripts/validate_project.py`; the commands below are for a short local runtime proof when Docker is available.

## Static Contract

The ClickHouse init SQL defines:

- Kafka Engine source tables for `orders.v1`, `payments.v1`, and `inventory-changes.v1`.
- Materialized views into `analytics.orders`, `analytics.payments`, and `analytics.inventory_changes`.
- Dedicated consumer groups: `clickhouse_orders_sink_v1`, `clickhouse_payments_sink_v1`, and `clickhouse_inventory_changes_sink_v1`.
- Avro Confluent decoding through the local Schema Registry at `http://schema-registry:8081`.

Run:

```bash
python scripts/validate_runtime_contract.py
python scripts/validate_project.py
```

## Runtime Smoke

Use the capture script to start only the services needed for ClickHouse ingestion review, wait briefly for generator events, and write diffable evidence files under `docs/assets/`:

```bash
python scripts/capture_clickhouse_evidence.py --duration 60 --cleanup
```

The script applies `docker-compose.evidence.yml` on top of the default compose file. The override removes host port bindings so the smoke run can execute on developer machines where Postgres, Kafka, Schema Registry, or ClickHouse ports are already occupied.

The script writes:

- `docs/assets/clickhouse-show-tables.txt`
- `docs/assets/clickhouse-orders-count.txt`
- `docs/assets/clickhouse-payments-count.txt`
- `docs/assets/clickhouse-inventory-count.txt`
- `docs/assets/clickhouse-ingestion-log.txt`

Manual equivalent:

```bash
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.evidence.yml --profile core up -d postgres kafka schema-registry clickhouse
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.evidence.yml --profile datagen up -d data-generator
```

Inspect the ClickHouse tables:

```bash
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.evidence.yml exec clickhouse clickhouse-client --query "SHOW TABLES FROM analytics"
```

Check that rows arrive after the generator has produced events:

```bash
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.evidence.yml exec clickhouse clickhouse-client --query "SELECT count() FROM analytics.orders"
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.evidence.yml exec clickhouse clickhouse-client --query "SELECT count() FROM analytics.payments"
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.evidence.yml exec clickhouse clickhouse-client --query "SELECT count() FROM analytics.inventory_changes"
```

Run the example analytical queries:

```bash
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.evidence.yml exec -T clickhouse clickhouse-client --multiquery < sql/examples/clickhouse_realtime_sales.sql
```

Capture the generator log evidence:

```bash
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.evidence.yml logs --no-color --tail 200 data-generator > docs/assets/clickhouse-ingestion-log.txt
```

## Evidence to Capture

Prefer text logs for PR review because they are diffable and easy to search:

- `docs/assets/clickhouse-show-tables.txt`
- `docs/assets/clickhouse-orders-count.txt`
- `docs/assets/clickhouse-payments-count.txt`
- `docs/assets/clickhouse-inventory-count.txt`
- `docs/assets/clickhouse-ingestion-log.txt`

Static validation proves the wiring is present and aligned with repository contracts. Runtime proof requires a short local run that shows row-count files after events are produced.
