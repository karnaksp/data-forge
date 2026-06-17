# История изменений

## v0.1.0 - Life Data Hub

Первый продуктовый релиз после перехода от retail-first лаборатории к локальной LifeHub data platform.

### Добавлено

- LifeHub как основной продуктовый домен: спорт, outdoor readiness, восстановление и Telegram digest.
- Санкт-Петербург как базовая география для weather/readiness сценариев.
- Lakehouse flow: landing JSONL, Spark, Iceberg Bronze/Silver/Gold, Trino.
- Operational и analytical storage: Postgres и ClickHouse.
- DataOps слой: contracts, catalog, expectations, validators, lineage и evidence.
- First-class `sleep_quality` source, влияющий на рекомендации.
- Source onboarding generator для будущих источников.
- Airflow DAGs и Temporal workflows для LifeHub процессов.
- GHCR package workflow для Docker image `lifehub`.

### Сохранено

- Retail CDC/lakehouse сценарий как инженерная лаборатория для Kafka, Debezium, ClickHouse и Trino.

### Приватность

- Реальные токены, diary notes, pain text, маршруты и health/broker exports не публикуются.
- Public fixtures синтетические или redacted.
