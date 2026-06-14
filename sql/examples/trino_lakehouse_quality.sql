-- Target-state lakehouse quality examples.
-- Engine: Trino.
-- Adjust catalog/schema/table names to match the Spark/Iceberg ingestion job.

select
    source_topic,
    count(*) as rows_loaded,
    count_if(event_ts is null) as missing_event_ts,
    count_if(ingested_at is null) as missing_ingested_at,
    approx_distinct(record_key) as approx_keys
from lakehouse.bronze.raw_events
group by source_topic
order by rows_loaded desc;

select
    source_topic,
    date_trunc('minute', ingested_at) as ingest_minute,
    count(*) as rows_loaded
from lakehouse.bronze.raw_events
where ingested_at >= current_timestamp - interval '1' hour
group by source_topic, date_trunc('minute', ingested_at)
order by ingest_minute desc, source_topic;

select
    source_topic,
    count(*) as duplicate_records
from (
    select
        source_topic,
        record_key,
        event_ts,
        count(*) as copies
    from lakehouse.bronze.raw_events
    group by source_topic, record_key, event_ts
    having count(*) > 1
)
group by source_topic
order by duplicate_records desc;
