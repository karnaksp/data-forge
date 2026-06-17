# LifeHub Source Onboarding Playbook

This playbook describes how to add a new personal data source without creating a one-off script or leaking private raw data.

## Flow

```text
data/private/inbox/<source>/... -> connector -> minimized event envelope -> tmp/lake/lifehub/landing/<source>/dt=... -> Iceberg/Trino/dbt -> daily context profile
```

## Steps

1. Add the source to `config/lifehub/source_registry.yaml` with tier, domain, privacy class, raw policy, local policy, landing path, tables, consumers and onboarding contract.
2. Add synthetic fixture coverage when the source is active. Planned sources may use a `planned-...` producer and no committed raw fixture.
3. Implement a connector that writes `lifehub.lake.v1` envelopes. The payload must already be minimized before landing.
4. Add a smoke path to `make lifehub-full-source-demo` when the connector becomes active.
5. Run `python scripts/validate_lifehub_dataops.py --landing-root tmp/lake` to check registry coverage, envelope shape and forbidden payload fields.
6. Add docs and tests before exposing the source in Telegram or the cockpit.

## Current Active Local File Sources

- `calendar_events`: `.ics` busy blocks with hashed/classified summaries.
- `sleep_quality`: CSV/JSON night-level recovery summaries.
- `moto_learning_log`: CSV/JSON lesson progress summaries.
- `trade_journal_summary`: CSV/JSON trading result and risk summaries with hashed instruments/setups.
- `personal_notes_summary`: Markdown/JSON note metadata, hashes, tags and word counts.

Use:

```bash
PYTHONPATH=infra/lifehub python -m lifehub.cli inbox-scan fixtures/lifehub/local_inbox --output-root tmp/lake --dt 2026-06-16
make lifehub-full-source-demo
```

## Privacy Checklist

- Do not commit real files under `data/private/`, `data/raw/` or `tmp/`.
- Do not put raw notes, pain text, private addresses, exact private GPS, account ids, message bodies, document numbers or secrets in fixtures.
- Use hashes, buckets, counts, booleans and coarse categories for sensitive data.
- Tier 4 sources are pointer-only and must not write raw records to shared Bronze.
