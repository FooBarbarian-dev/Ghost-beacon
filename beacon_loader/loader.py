import os
import sys
import glob
import gzip
import json
import time
import logging
from typing import List, Dict, Any, Optional

import redis
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration from env ---
HASURA_URL = os.environ.get("HASURA_URL", "http://graphql_engine:8080/v1/graphql")
HASURA_ADMIN_SECRET = os.environ.get("HASURA_ADMIN_SECRET", "myadminsecret")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
OPLOG_ID = int(os.environ.get("OPLOG_ID", "1"))
DATA_DIR = os.environ.get("DATA_DIR", "/data")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100"))

# --- Pattern from ghostwriter-oplog-populate: insert mutation ---
# ghostwriter-oplog-populate uses insert_oplog_one for single inserts.
# We use insert_oplog_oplogentry (batch) for throughput.
INSERT_MUTATION = gql("""
mutation InsertBeaconEntries($entries: [oplog_oplogentry_insert_input!]!) {
  insert_oplog_oplogentry(objects: $entries) {
    affected_rows
    returning {
      id
      entry_identifier
    }
  }
}
""")

def wait_for_services(redis_client: redis.Redis, gql_client: Client) -> None:
    """Wait for Redis and Hasura to be ready."""
    logger.info("Waiting for dependencies...")
    max_retries = 12
    for i in range(max_retries):
        try:
            # Check Redis
            redis_client.ping()

            # Check Hasura (simple query to ensure schema is loaded and responding)
            # Actually, just making sure we can connect to Hasura via requests transport.
            # In sync context for checking we can just try connecting or assume it's up if the container healthcheck passed.
            # But we can try an introspection or dummy query. Let's just rely on the GraphQL client initialization and connection.

            # A simple way to check Hasura is up is to issue a simple query
            try:
                # Just execute a very basic query to verify connection and auth
                query = gql("""
                query CheckHealth {
                  oplog_oplog(limit: 1) { id }
                }
                """)
                gql_client.execute(query)
            except Exception as e:
                logger.warning(f"Hasura not ready yet: {e}")
                raise e

            logger.info("All dependencies are ready.")
            return
        except Exception as e:
            if i == max_retries - 1:
                logger.error(f"Failed to connect to dependencies after {max_retries} attempts.")
                sys.exit(1)
            logger.info(f"Services not ready, retrying in 5 seconds... (Attempt {i+1}/{max_retries})")
            time.sleep(5)

# --- Net-new: JSONL reader, field mapping, batch accumulation ---
def process_file(filepath: str, redis_client: redis.Redis, gql_client: Client) -> None:
    """Process a single JSONL gz file."""
    logger.info(f"Processing file: {filepath}")

    entries_processed = 0
    entries_inserted = 0
    entries_skipped = 0
    batch = []

    start_time = time.time()

    try:
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                entries_processed += 1
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON on line in {filepath}")
                    continue

                # Extract digest (dedup key)
                digest_dict = data.get("digest", {})
                sha256 = digest_dict.get("sha256")

                if not sha256:
                    logger.warning("Missing sha256 digest in entry, skipping")
                    continue

                # --- Pattern from cobalt_sync v2: Redis dedup ---
                # cobalt_sync hashes beacon events and checks Redis before posting.
                # We use digest.sha256 as the key instead of computing our own hash.
                if redis_client.sismember("beacon_digests", sha256):
                    entries_skipped += 1
                    continue

                # Transform data
                domains = data.get("domains", [])
                dest_ip = domains[0] if domains else None
                tls_subject = data.get("tls_subject")

                description = (
                    f"Beacon collected from {data.get('collected_from_ip', 'unknown')}:"
                    f"{data.get('collected_from_port', 'unknown')} on "
                    f"{data.get('collected_dt', 'unknown')}. "
                    f"Version: {data.get('beacon_version', 'unknown')}. "
                    f"Filesize: {data.get('filesize', 'unknown')}. "
                    f"XOR encoded: {data.get('xorencoded', 'unknown')}. "
                    f"Domains: {', '.join(domains) if domains else 'None'}. "
                    f"TLS Subject: {tls_subject or 'None'}."
                )

                # Prepare extra_fields
                extra_fields = data.copy()
                if "config_block" in extra_fields:
                    del extra_fields["config_block"]
                    extra_fields["config_block_digest"] = sha256

                oplog_entry = {
                    "oplog_id_id": OPLOG_ID,
                    "start_date": data.get("collected_dt"),
                    "end_date": None,
                    "source_ip": data.get("collected_from_ip"),
                    "dest_ip": dest_ip,
                    "tool": data.get("beacon_version"),
                    "user_context": None,
                    "command": None,
                    "description": description,
                    "output": None,
                    "comments": None,
                    "operator_name": "beacon_import",
                    "entry_identifier": sha256,
                    "extra_fields": extra_fields,
                    "tags": []
                }

                batch.append(oplog_entry)

                if len(batch) >= BATCH_SIZE:
                    _insert_batch(batch, gql_client, redis_client)
                    entries_inserted += len(batch)
                    batch = []

                if entries_processed % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = entries_processed / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"Progress [{filepath}]: Processed: {entries_processed}, "
                        f"Inserted: {entries_inserted}, Skipped: {entries_skipped}, "
                        f"Elapsed: {elapsed:.2f}s, Rate: {rate:.2f} entries/s"
                    )

            # Insert remaining batch
            if batch:
                _insert_batch(batch, gql_client, redis_client)
                entries_inserted += len(batch)

    except Exception as e:
        logger.error(f"Error processing file {filepath}: {e}")

    logger.info(
        f"Finished [{filepath}]: Processed: {entries_processed}, "
        f"Inserted: {entries_inserted}, Skipped: {entries_skipped}"
    )

def _insert_batch(batch: List[Dict[str, Any]], gql_client: Client, redis_client: redis.Redis) -> None:
    """Execute the GraphQL mutation to insert a batch and record success in Redis."""
    try:
        variables = {"entries": batch}
        # Execute mutation
        result = gql_client.execute(INSERT_MUTATION, variable_values=variables)

        # --- Pattern from cobalt_sync v2: Redis dedup ---
        # Mark processed: SADD beacon_digests {sha256} for each entry in the successful batch.
        returned_entries = result.get("insert_oplog_oplogentry", {}).get("returning", [])

        if returned_entries:
            identifiers = [entry.get("entry_identifier") for entry in returned_entries if entry.get("entry_identifier")]
            if identifiers:
                redis_client.sadd("beacon_digests", *identifiers)

    except Exception as e:
        logger.error(f"Failed to insert batch: {e}")
        # Could implement retry logic here if needed

def main() -> None:
    logger.info("Starting beacon loader...")

    # --- Pattern from ghostwriter-oplog-populate: gql client setup ---
    # ghostwriter-oplog-populate uses gql library with AIOHTTPTransport.
    # We simplify auth from JWT (login mutation) to x-hasura-admin-secret header.
    # Adapted to use RequestsHTTPTransport for synchronous execution.
    transport = RequestsHTTPTransport(
        url=HASURA_URL,
        headers={'x-hasura-admin-secret': HASURA_ADMIN_SECRET},
        retries=3
    )

    gql_client = Client(transport=transport, fetch_schema_from_transport=False)

    # Redis client setup
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    # Wait for dependencies
    wait_for_services(redis_client, gql_client)

    # Discover files
    files = glob.glob(os.path.join(DATA_DIR, "beacons-*.jsonl.gz"))
    if not files:
        logger.info(f"No matching files found in {DATA_DIR}. Exiting.")
        sys.exit(0)

    # Sort chronologically
    files.sort()

    logger.info(f"Found {len(files)} files to process.")

    for filepath in files:
        process_file(filepath, redis_client, gql_client)

    logger.info("Beacon loading complete.")

if __name__ == "__main__":
    main()
