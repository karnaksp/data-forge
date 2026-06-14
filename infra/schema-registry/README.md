# 🧩 Schema Registry

Why: Manage Avro/JSON schemas and compatibility for Kafka topics.

## ⚙️ Profile

- `core`

## 🔗 Dependencies

- Kafka

## 🚀 How

- Start service:
  - `docker compose --profile core up -d schema-registry`

- API: `http://localhost:8081`

## 📝 Notes

- The image is pinned to `confluentinc/cp-schema-registry:8.1.0`; avoid floating `latest` tags so local smoke runs do not break when upstream base images change.
- Client URL is set via `SCHEMA_REGISTRY_*` envs in compose.
- Used by data generator and Spark structured streaming.
