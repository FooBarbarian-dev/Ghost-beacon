# Project: beacon-ghostwriter

Proof-of-concept: loads public Cobalt Strike beacon metadata into a standalone
Ghostwriter-compatible oplog database via GraphQL.

## What this combines
- fox-it/cobaltstrike-beacon-data — source data (128k+ beacon configs as JSONL)
- GhostManager/cobalt_sync v2 — Redis dedup pattern, Docker topology (~50 lines adapted)
- SpecterOps/ghostwriter-oplog-populate — gql client setup, insert mutations (~35 lines adapted)
- GhostManager/Ghostwriter hasura-docker/metadata — schema reference
- ~90% of code is net-new glue for this specific PoC

## Structure
- db/init.sql — Ghostwriter oplog tables as standalone SQL (extracted from Django models)
- hasura/metadata/ — Hasura v2 config tracking the two oplog tables
- beacon_loader/loader.py — JSONL reader → field mapper → Redis dedup → GraphQL batch insert
- data/ — Mount point for beacons-*.jsonl.gz (not committed, download separately)

## Code Lineage (marked in loader.py comments)
- "Pattern from cobalt_sync": Redis SISMEMBER/SADD dedup
- "Pattern from ghostwriter-oplog-populate": gql client, auth, insert mutations
- "Net-new": JSONL parsing, field mapping, batch accumulation, health checks

## Key Design Decisions
- entry_identifier = beacon sha256 digest (dedup key, same strategy as cobalt_sync)
- extra_fields stores full beacon JSON minus config_block (queryable via Hasura JSONB operators)
- config_block excluded from storage (large base64), only digest reference kept
- Batch inserts of 100 (cobalt_sync does one-at-a-time; we optimize for bulk load)
- No Django auth webhook — standalone Hasura with admin secret only

## Testing
- docker compose up — initializes DB, applies Hasura metadata, runs loader
- Hasura console at http://localhost:8080/console
- Re-running loader is idempotent (Redis dedup persists via Docker volume)

## Visualization Layer (added in second task)

### Metabase (localhost:3000)
- Zero-code BI dashboards
- Connects directly to PostgreSQL (not Hasura)
- Starter SQL queries documented in README
- User creates dashboards via browser — no code in this repo

### Streamlit (localhost:8501)
- Python-based exploration UI
- Pre-built analysis pages: overview, versions, infrastructure, indicators
- Chat interface for future LLM integration (currently a stub)
- lib/llm.py contains DB_SCHEMA_CONTEXT — the prompt that will be sent to the LLM
- lib/db.py provides run_query() for all PostgreSQL access
- lib/queries.py stores all SQL as named constants

### Future LLM Integration
- Set LLM_ENDPOINT env var to local model URL (e.g., http://ollama:11434)
- Implement ask() in lib/llm.py
- Use llm_readonly PostgreSQL role for LLM-generated queries
- DB_SCHEMA_CONTEXT is the system prompt — modify it if schema changes