# 🧩 Apache Kafka

Why: Event streaming backbone for real‑time data flows.

## ⚙️ Profile

- `core`

## 🔗 Dependencies

- None (Schema Registry, Debezium, and Kafka UI depend on it)

## 🚀 How

- Start service:
  - `docker compose --profile core up -d kafka`

- Broker: `localhost:9092`

## 📝 Notes

- The image is pinned to `apache/kafka:4.1.2`; avoid floating `latest` tags so local smoke runs do not break when upstream tags move.
- Listener settings come from `.env` (advertised listeners, listener protocol map, controller quorum).
- Data stored in the `kafka-data` volume mounted at `/var/lib/kafka/data`.
