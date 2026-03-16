# beacon-ghostwriter

A proof of concept combining three GhostManager/SpecterOps projects to demonstrate loading Cobalt Strike beacon data into a Ghostwriter-compatible oplog database. This is not production software.

## Why it exists

To validate the end-to-end pipeline (data → transform → dedup → GraphQL → Ghostwriter schema) before real team server data is available. When real data arrives, the schema, mutations, and dedup patterns are already proven.

## What it combines

- **fox-it/cobaltstrike-beacon-data** — The source data (128k+ real beacon configs as JSONL, collected 2018–2022).
- **GhostManager/cobalt_sync v2** — The Redis dedup pattern and Docker topology shape (~40-50 lines adapted).
- **SpecterOps/ghostwriter-oplog-populate** — The `gql` GraphQL client patterns and insert mutations (~35 lines adapted).
- **GhostManager/Ghostwriter** (`hasura-docker/metadata`) — The extracted PostgreSQL schema and Hasura configuration.
- **~90% of the code** is net-new glue specific to this PoC.

## Prerequisites

- Docker
- Docker Compose

## Getting the Data

Use the provided download script to fetch the public data files directly into the `data` directory:

```bash
./download_data.sh
```

## Running

```bash
docker compose up --build
# The loader will wait for services, process all data files, and exit cleanly.
# The Hasura console is available at http://localhost:8080/console
```

## Example Queries

Once the loader has processed data, you can run these queries via the Hasura console:

### Count imported entries
```graphql
query {
  oplog_oplogentry_aggregate {
    aggregate { count }
  }
}
```

### Filter by Cobalt Strike version
```graphql
query {
  oplog_oplogentry(
    where: { tool: { _ilike: "%4.0%" } }
    limit: 5
  ) {
    id
    start_date
    source_ip
    dest_ip
    tool
    entry_identifier
  }
}
```

### Query beacon metadata via JSONB
```graphql
query {
  oplog_oplogentry(
    where: { extra_fields: { _contains: { collected_from_port: 443 } } }
    limit: 5
  ) {
    source_ip
    tool
    extra_fields
  }
}
```

### Verify Deduplication

Re-run the loader:
```bash
docker compose run beacon_loader
# Should report 0 inserted, all skipped, as they already exist in Redis
```

## Future Direction

Replace `beacon_loader` with actual `cobalt_sync` pointed at a live team server. Replace the standalone Postgres/Hasura instances with a real Ghostwriter instance. The oplog schema and GraphQL mutation interface will remain exactly the same.
