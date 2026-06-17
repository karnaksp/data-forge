# LifeHub Telegram Data Capture

Telegram is the fastest local input surface for LifeHub. Commands capture small events that can later feed Postgres, ClickHouse, lakehouse exports and the daily context profile.

## Commands

| Command | Purpose | Example |
| --- | --- | --- |
| `/log` | Detailed activity session | `/log skate 7 8 4 good dry session` |
| `/sleep` | Sleep/recovery quick capture | `/sleep 7.5h quality=82 recovery=76` |
| `/mood` | Mood score | `/mood 8 calm focus` |
| `/pain` | Pain signal | `/pain 2 wrist after moto` |
| `/plan` | Daily planning intent | `/plan gym then project work` |
| `/moto` | Moto lesson shorthand | `/moto 6 ok cones and slow turns` |
| `/trade` | Trading context note | `/trade watchlist risk low` |
| `/note` | General private context note | `/note remember recovery bias` |
| `/sources` | Capture/source help | `/sources` |
| `/data_gaps` | Missing data and confidence | `/data_gaps` |

## Storage Behavior

- `/log` writes structured activity fields and can sync to Postgres/ClickHouse.
- `/moto` can become a `moto_lesson` activity log.
- Quick capture commands can append local JSONL through the CLI `capture` command.
- Raw sensitive text is not intended for public fixtures or evidence; future ingestion should convert it to summaries, tags, hashes or metrics before lake landing.

## CLI Equivalents

```bash
PYTHONPATH=infra/lifehub python -m lifehub.cli capture '/mood 8 calm_focus'
PYTHONPATH=infra/lifehub python -m lifehub.cli sources
PYTHONPATH=infra/lifehub python -m lifehub.cli data-gaps \
  --fixture fixtures/lifehub/open_meteo_clear_day.json \
  --summary-fixture fixtures/lifehub/week_summary.json \
  --metrics-fixture fixtures/lifehub/decision_metrics.json \
  --signal-fixture fixtures/lifehub/context_signals.json \
  --sleep-fixture fixtures/lifehub/sleep_quality.json
```
