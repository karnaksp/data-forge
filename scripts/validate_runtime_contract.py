#!/usr/bin/env python3
"""Static runtime-contract checks for the retail CDC case study.

These checks intentionally avoid importing Airflow, Spark, Docker Compose, or
the generator package. They guard the portfolio demo contract against drift
between Compose envs, generator config, Kafka topics, schemas, DAG params,
Debezium config, Postgres CDC tables, and ClickHouse example sinks.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "docker-compose.yml"
GENERATOR_CONFIG_PATH = ROOT / "infra/data-generator/config.py"
DAG_PATH = ROOT / "infra/airflow/dags/bronze_events_kafka_stream_dag.py"
SCHEMA_INIT_PATH = ROOT / "infra/schema-registry/init-schemas.sh"
KAFKA_CHECKLIST_PATH = ROOT / "sql/validation/kafka_topic_inventory.md"
DEBEZIUM_CONFIG_PATH = ROOT / "infra/debezium/config/demo-postgres.json"
POSTGRES_INIT_PATH = ROOT / "infra/postgres/init-databases.sh"
CLICKHOUSE_INIT_PATH = ROOT / "infra/clickhouse/init/001_retail_event_sinks.sql"
CLICKHOUSE_EXAMPLE_PATH = ROOT / "sql/examples/clickhouse_realtime_sales.sql"

REQUIRED_GENERATOR_ENV = {
    "KAFKA_BOOTSTRAP",
    "SCHEMA_REGISTRY_URL",
    "PG_DSN",
    "TARGET_EPS",
    "WEIGHT_ORDERS",
    "WEIGHT_INTERACTIONS",
    "WEIGHT_INVENTORY_CHG",
    "SEED_USERS",
    "SEED_PRODUCTS",
    "SEED_WAREHOUSES",
    "SEED_SUPPLIERS",
    "TOPIC_ORDERS",
    "TOPIC_PAYMENTS",
    "TOPIC_SHIPMENTS",
    "TOPIC_INVENTORY_CHANGES",
    "TOPIC_CUSTOMER_INTERACTIONS",
}
OBSOLETE_GENERATOR_ENV = {
    "RATE_MPS",
    "P_CUSTOMER_INTERACTION",
    "P_INVENTORY_EVENT",
}


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def parse_python(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def literal_assignment(module: ast.Module, name: str) -> Any:
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"{name} assignment not found")


def getenv_call(node: ast.AST) -> tuple[str, str] | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    is_getenv = (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "os"
        and func.attr == "getenv"
    )
    if not is_getenv or not node.args:
        return None
    key = node.args[0]
    default = node.args[1] if len(node.args) > 1 else ast.Constant(value="")
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        if isinstance(default, ast.Constant) and isinstance(default.value, str):
            return key.value, default.value
    return None


def find_getenv(node: ast.AST) -> tuple[str, str] | None:
    direct = getenv_call(node)
    if direct:
        return direct
    for child in ast.iter_child_nodes(node):
        found = find_getenv(child)
        if found:
            return found
    return None


def config_env_defaults() -> dict[str, str]:
    module = parse_python(GENERATOR_CONFIG_PATH)
    defaults: dict[str, str] = {}
    for node in ast.walk(module):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found = find_getenv(node.value) if node.value else None
            if found:
                defaults[node.target.id] = found[1]
    return defaults


def compose_generator_env() -> dict[str, str]:
    text = COMPOSE_PATH.read_text(encoding="utf-8").splitlines()
    in_service = False
    in_environment = False
    env: dict[str, str] = {}
    for line in text:
        if re.match(r"^  [A-Za-z0-9_-]+:", line):
            in_service = line.strip() == "data-generator:"
            in_environment = False
            continue
        if not in_service:
            continue
        if re.match(r"^    environment:", line):
            in_environment = True
            continue
        if in_environment and re.match(r"^    [A-Za-z0-9_-]+:", line):
            break
        match = re.match(r"^\s{6}([A-Z0-9_]+):\s*(.+)$", line)
        if in_environment and match:
            env[match.group(1)] = match.group(2).strip()
    return env


def config_business_topics(defaults: dict[str, str]) -> set[str]:
    return {
        defaults[key]
        for key in [
            "topic_orders",
            "topic_payments",
            "topic_shipments",
            "topic_inventory_changes",
            "topic_customer_interactions",
        ]
    }


def config_cdc_topics(defaults: dict[str, str]) -> set[str]:
    return {
        value
        for key, value in defaults.items()
        if key.startswith("cdc_topic_") and value.startswith("demo.public.")
    }


def dag_topics() -> tuple[set[str], set[str]]:
    module = parse_python(DAG_PATH)
    params = literal_assignment(module, "DEFAULT_PARAMS")
    streams = literal_assignment(module, "CDC_STREAMS")
    return set(params["topics"]), {stream["topic"] for stream in streams}


def schema_registry_topics() -> set[str]:
    text = SCHEMA_INIT_PATH.read_text(encoding="utf-8")
    return set(re.findall(r'"([A-Za-z0-9._-]+\.v1)-value"', text))


def checklist_topics() -> tuple[set[str], set[str]]:
    text = KAFKA_CHECKLIST_PATH.read_text(encoding="utf-8")
    topics = re.findall(r"`([A-Za-z0-9._-]+)`", text)
    business = {topic for topic in topics if topic.endswith(".v1")}
    cdc = {topic for topic in topics if topic.startswith("demo.public.")}
    return business, cdc


def postgres_tables() -> set[str]:
    text = POSTGRES_INIT_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS ([A-Za-z_][A-Za-z0-9_]*)\(", text))


def clickhouse_init_tables() -> set[str]:
    text = CLICKHOUSE_INIT_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS analytics\.([A-Za-z_][A-Za-z0-9_]*)", text))


def clickhouse_example_tables() -> set[str]:
    text = CLICKHOUSE_EXAMPLE_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"analytics\.([A-Za-z_][A-Za-z0-9_]*)", text))


def validate_generator_env() -> list[str]:
    failures: list[str] = []
    env = compose_generator_env()
    missing = REQUIRED_GENERATOR_ENV - set(env)
    obsolete = OBSOLETE_GENERATOR_ENV & set(env)
    if missing:
        failures.append(
            f"{relative(COMPOSE_PATH)} data-generator environment is missing: {sorted(missing)}"
        )
    if obsolete:
        failures.append(
            f"{relative(COMPOSE_PATH)} data-generator uses obsolete env names: {sorted(obsolete)}"
        )

    config_env_names = {
        found[0]
        for node in ast.walk(parse_python(GENERATOR_CONFIG_PATH))
        if (found := find_getenv(node))
    }
    expected_read = REQUIRED_GENERATOR_ENV - {
        "KAFKA_BOOTSTRAP",
        "SCHEMA_REGISTRY_URL",
        "PG_DSN",
    }
    unread = expected_read - config_env_names
    if unread:
        failures.append(
            f"{relative(GENERATOR_CONFIG_PATH)} does not read expected compose "
            f"envs: {sorted(unread)}"
        )

    return failures


def validate_topic_alignment() -> list[str]:
    failures: list[str] = []
    defaults = config_env_defaults()
    business_config = config_business_topics(defaults)
    cdc_config = config_cdc_topics(defaults)
    business_dag, cdc_dag = dag_topics()
    business_schema = schema_registry_topics()
    business_checklist, cdc_checklist = checklist_topics()

    comparisons = [
        ("business topics in Config vs DAG DEFAULT_PARAMS", business_config, business_dag),
        ("business topics in Config vs Schema Registry init", business_config, business_schema),
        ("business topics in Config vs checklist", business_config, business_checklist),
        ("CDC topics in Config vs DAG CDC_STREAMS", cdc_config, cdc_dag),
        ("CDC topics in Config vs checklist", cdc_config, cdc_checklist),
    ]
    for label, left, right in comparisons:
        if left != right:
            failures.append(
                f"{label} differ: only-left={sorted(left - right)}, "
                f"only-right={sorted(right - left)}"
            )
    return failures


def validate_debezium_and_postgres() -> list[str]:
    failures: list[str] = []
    config = json.loads(DEBEZIUM_CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("topic.prefix") != "demo":
        failures.append(f"{relative(DEBEZIUM_CONFIG_PATH)} topic.prefix must be demo")
    if config.get("database.dbname") != "demo":
        failures.append(f"{relative(DEBEZIUM_CONFIG_PATH)} database.dbname must be demo")
    if config.get("publication.name") != "demo_publication":
        failures.append(
            f"{relative(DEBEZIUM_CONFIG_PATH)} publication.name must be demo_publication"
        )

    cdc_tables = {
        topic.rsplit(".", 1)[-1] for topic in config_cdc_topics(config_env_defaults())
    }
    tables = postgres_tables()
    missing = cdc_tables - tables
    if missing:
        failures.append(
            f"{relative(POSTGRES_INIT_PATH)} does not create CDC tables: {sorted(missing)}"
        )
    return failures


def validate_clickhouse_contract() -> list[str]:
    init_tables = clickhouse_init_tables()
    example_tables = clickhouse_example_tables()
    missing = example_tables - init_tables
    if missing:
        return [
            f"{relative(CLICKHOUSE_INIT_PATH)} does not create example tables: {sorted(missing)}"
        ]
    return []


def validate_runtime_contract() -> list[str]:
    failures: list[str] = []
    failures.extend(validate_generator_env())
    failures.extend(validate_topic_alignment())
    failures.extend(validate_debezium_and_postgres())
    failures.extend(validate_clickhouse_contract())
    return failures


def main() -> int:
    failures = validate_runtime_contract()
    if failures:
        print("Runtime contract validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Runtime contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
