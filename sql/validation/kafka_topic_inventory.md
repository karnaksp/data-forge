# Kafka Topic Validation Checklist

Run after `docker compose --profile core --profile datagen up -d`.

```bash
docker compose exec kafka bash
kafka-topics.sh --bootstrap-server kafka:9092 --list
```

Expected business-event topics:

- `orders.v1`
- `payments.v1`
- `shipments.v1`
- `inventory-changes.v1`
- `customer-interactions.v1`

Expected Debezium CDC topics after connector startup:

- `demo.public.users`
- `demo.public.products`
- `demo.public.inventory`
- `demo.public.warehouse_inventory`
- `demo.public.suppliers`
- `demo.public.customer_segments`
- `demo.public.product_suppliers`
- `demo.public.warehouses`

Inspect a topic:

```bash
kafka-topics.sh --bootstrap-server kafka:9092 --describe --topic orders.v1
```

Sample a few records:

```bash
kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 \
  --topic orders.v1 \
  --from-beginning \
  --max-messages 5
```

Validation contract:

| Check | Expected result |
| --- | --- |
| Business topics exist | all five generator topics present |
| CDC topics exist | at least `demo.public.users`, `demo.public.products`, `demo.public.inventory` present |
| Messages are arriving | `orders.v1` and `customer-interactions.v1` return records within a short run |
| Keys are stable | order topic keys look like `ord_*`; inventory topic keys look like `WH*:P*` |
| Schema Registry has subjects | subjects exist for generated Avro topics |

Schema Registry check:

```bash
curl -s http://localhost:8081/subjects | jq .
```
