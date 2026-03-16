"""
LLM client for natural-language data exploration.

Current state: stub that returns a helpful message.
Future state: connects to a local model (Ollama, llama-cpp, vLLM)
              to generate SQL from natural language questions.

The integration pattern will be:
1. User types a question in natural language
2. LLM receives the database schema + question
3. LLM generates a SQL query
4. We execute the SQL against PostgreSQL
5. We render the results as a table/chart
6. Optionally, LLM summarizes the results in natural language

Environment variable LLM_ENDPOINT controls the backend:
- Empty string or unset: stub mode (no LLM, returns guidance message)
- URL (e.g., http://ollama:11434): connects to that endpoint
"""

import os
from dataclasses import dataclass

# The schema description that will be sent to the LLM as context.
# This is the single most important piece of prompt engineering for
# the future LLM integration — it determines whether the model
# generates correct SQL.
DB_SCHEMA_CONTEXT = """
You have access to a PostgreSQL database with Cobalt Strike beacon metadata
loaded into a Ghostwriter-compatible oplog schema.

Table: oplog_oplogentry (~128,000 rows)
Columns:
  - id: bigint (primary key)
  - start_date: timestamptz (when beacon was collected, range 2018-2022)
  - source_ip: varchar (team server IP address)
  - dest_ip: varchar (first C2 domain from beacon config, may be null)
  - tool: varchar (Cobalt Strike version string, e.g. "Cobalt Strike 4.0 (Dec 05, 2019)")
  - entry_identifier: varchar (SHA256 digest of the beacon, unique per beacon)
  - operator_name: varchar (always "beacon_import" for this dataset)
  - description: text (human-readable summary)
  - extra_fields: jsonb containing:
      - digest: {md5, sha1, sha256}
      - filesize: integer (beacon payload size in bytes)
      - tls_subject: string or null
      - tls_issuer: string or null
      - tls_fingerprint: {md5, sha1, sha256} (may be null)
      - collected_from_ip: string (same as source_ip)
      - collected_from_port: integer (typically 443, 80, 8443, 8080, 50050)
      - domains: array of strings (C2 callback domains configured in beacon)
      - max_setting_enum: integer
      - beacon_version: string (same as tool)
      - xorencoded: integer (0 or 1)
      - config_block_digest: string (SHA256 reference, actual config not stored)

JSONB access patterns:
  - extra_fields->>'key' for text values
  - (extra_fields->>'key')::int for integer values
  - extra_fields->'key' for nested JSON
  - jsonb_array_elements_text(extra_fields->'domains') to unnest the domains array

Always add appropriate WHERE clauses for NULL checks on JSONB fields.
Always use date_trunc() for time-based aggregations.
"""


@dataclass
class LLMResponse:
    """Response from the LLM integration."""
    generated_sql: str | None
    explanation: str
    is_stub: bool


def get_llm_endpoint() -> str | None:
    """Returns the LLM endpoint URL, or None if in stub mode."""
    endpoint = os.environ.get("LLM_ENDPOINT", "").strip()
    return endpoint if endpoint else None


def is_llm_available() -> bool:
    """Check if an LLM backend is configured and reachable."""
    return get_llm_endpoint() is not None


def ask(question: str) -> LLMResponse:
    """
    Send a natural-language question to the LLM and get back a SQL query.

    In stub mode, returns guidance on what this will do when connected.
    When an LLM endpoint is configured, sends the schema context + question
    and parses the response for a SQL query.
    """
    endpoint = get_llm_endpoint()

    if endpoint is None:
        return LLMResponse(
            generated_sql=None,
            explanation=(
                "LLM integration is not yet configured. "
                "To enable it, set the LLM_ENDPOINT environment variable "
                "to your local model's API URL (e.g., http://ollama:11434).\n\n"
                f"Your question: \"{question}\"\n\n"
                "When connected, the LLM will receive the database schema and "
                "generate a SQL query to answer your question. "
                "Try the pre-built analysis pages in the sidebar for now."
            ),
            is_stub=True,
        )

    # ----- FUTURE: Replace this block with actual LLM call -----
    # The integration should:
    # 1. POST to {endpoint}/api/generate (Ollama) or equivalent
    # 2. Include DB_SCHEMA_CONTEXT as system prompt
    # 3. Include the user question as the user prompt
    # 4. Instruct the model to respond with ONLY a SQL query
    #    wrapped in ```sql ... ``` markers
    # 5. Parse the SQL from the response
    # 6. Optionally do a second call asking the model to explain
    #    the results in natural language
    #
    # Example system prompt:
    #   f"{DB_SCHEMA_CONTEXT}\n\nGenerate a PostgreSQL query that answers
    #    the user's question. Respond with ONLY the SQL query wrapped in
    #    ```sql``` code fences. No explanation."
    #
    # Security note: NEVER execute LLM-generated SQL with write permissions.
    # Use a read-only PostgreSQL role for all LLM-generated queries.
    # -----------------------------------------------------------

    raise NotImplementedError(
        f"LLM endpoint configured ({endpoint}) but client not yet implemented. "
        "This is the placeholder for the future integration."
    )
