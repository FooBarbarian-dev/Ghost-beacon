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

## Visualization

After data is loaded, two visualization tools are available:

**Metabase** — `http://localhost:3000`
- Full BI dashboard tool, connects to PostgreSQL directly
- First launch: create admin account, add PostgreSQL connection (host: `postgres`, port: 5432, db: `ghostwriter`, user/pass: `ghostwriter`)
- Starter SQL queries provided below for copy-paste into Native Query

### Suggested Starter Questions (for Metabase)

**1. Beacon Collection Timeline**
```sql
SELECT
  date_trunc('month', start_date) AS month,
  COUNT(*) AS beacon_count
FROM oplog_oplogentry
WHERE start_date IS NOT NULL
GROUP BY month
ORDER BY month;
```
Visualization: Line chart. X = month, Y = beacon_count.

**2. Cobalt Strike Version Distribution**
```sql
SELECT
  tool AS cs_version,
  COUNT(*) AS count
FROM oplog_oplogentry
WHERE tool IS NOT NULL
GROUP BY tool
ORDER BY count DESC
LIMIT 20;
```
Visualization: Bar chart (horizontal).

**3. Top Team Server IPs**
```sql
SELECT
  source_ip,
  COUNT(*) AS beacon_count,
  COUNT(DISTINCT (extra_fields->>'beacon_version')) AS unique_versions,
  MIN(start_date) AS first_seen,
  MAX(start_date) AS last_seen
FROM oplog_oplogentry
WHERE source_ip IS NOT NULL
GROUP BY source_ip
ORDER BY beacon_count DESC
LIMIT 50;
```
Visualization: Table.

**4. Listening Port Distribution**
```sql
SELECT
  (extra_fields->>'collected_from_port')::int AS port,
  COUNT(*) AS count
FROM oplog_oplogentry
WHERE extra_fields->>'collected_from_port' IS NOT NULL
GROUP BY port
ORDER BY count DESC;
```
Visualization: Pie chart or bar chart.

**5. C2 Domain Frequency**
```sql
SELECT
  domain,
  COUNT(*) AS beacon_count
FROM oplog_oplogentry,
  jsonb_array_elements_text(extra_fields->'domains') AS domain
GROUP BY domain
ORDER BY beacon_count DESC
LIMIT 30;
```
Visualization: Bar chart.

**6. XOR Encoding Over Time**
```sql
SELECT
  date_trunc('quarter', start_date) AS quarter,
  (extra_fields->>'xorencoded')::int AS xor_encoded,
  COUNT(*) AS count
FROM oplog_oplogentry
WHERE start_date IS NOT NULL
  AND extra_fields->>'xorencoded' IS NOT NULL
GROUP BY quarter, xor_encoded
ORDER BY quarter;
```
Visualization: Stacked bar chart.

**7. Filesize Distribution**
```sql
SELECT
  CASE
    WHEN (extra_fields->>'filesize')::int < 100000 THEN '< 100KB'
    WHEN (extra_fields->>'filesize')::int < 200000 THEN '100-200KB'
    WHEN (extra_fields->>'filesize')::int < 300000 THEN '200-300KB'
    WHEN (extra_fields->>'filesize')::int < 500000 THEN '300-500KB'
    ELSE '500KB+'
  END AS size_bucket,
  COUNT(*) AS count
FROM oplog_oplogentry
WHERE extra_fields->>'filesize' IS NOT NULL
GROUP BY size_bucket
ORDER BY MIN((extra_fields->>'filesize')::int);
```
Visualization: Bar chart.

**8. TLS Certificate Usage**
```sql
SELECT
  CASE
    WHEN extra_fields->>'tls_subject' IS NOT NULL
      AND extra_fields->>'tls_subject' != 'null'
      THEN 'Has TLS Subject'
    ELSE 'No TLS Subject'
  END AS tls_status,
  COUNT(*) AS count
FROM oplog_oplogentry
GROUP BY tls_status;
```
Visualization: Pie chart.

**Streamlit Explorer** — `http://localhost:8501`
- Pre-built analysis views for beacon version trends, infrastructure patterns, and indicator analysis
- Chat interface for future LLM-powered natural language querying
- All analysis queries visible in `streamlit_app/lib/queries.py`

## Future: LLM Integration

The Streamlit app includes a chat interface stub ready for local LLM connection. To enable:

1. Add an Ollama (or similar) service to `docker-compose.yml`
2. Set `LLM_ENDPOINT=http://ollama:11434` on the streamlit service
3. Implement the `ask()` function in `streamlit_app/lib/llm.py`
4. LLM-generated queries use the `llm_readonly` PostgreSQL role for safety

The schema context sent to the LLM is defined in `lib/llm.py` as `DB_SCHEMA_CONTEXT`. This is the most important piece to keep accurate — it determines whether the model generates correct SQL.

## Future Direction

Replace `beacon_loader` with actual `cobalt_sync` pointed at a live team server. Replace the standalone Postgres/Hasura instances with a real Ghostwriter instance. The oplog schema and GraphQL mutation interface will remain exactly the same.
