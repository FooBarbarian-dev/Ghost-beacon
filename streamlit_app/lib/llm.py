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
import re
import logging
import httpx
import psycopg2
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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
    retries_used: int = 0
    validation_error: str | None = None
    execution_tested: bool = False
    model_used: str | None = None

MAX_RETRIES: int = 2
REQUEST_TIMEOUT: int = 120
TEST_QUERY_TIMEOUT: int = 10

WRITE_KEYWORDS: str = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXECUTE|COPY)\b'

SYSTEM_PROMPT: str = f"""{DB_SCHEMA_CONTEXT}

You are a PostgreSQL SQL expert. Given a natural language question about the Cobalt Strike beacon dataset described above, generate a single PostgreSQL query that answers the question.

Rules:
- Output ONLY a SQL query wrapped in ```sql ... ``` code fences. No explanation before or after.
- Use only SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or CREATE.
- Use the exact column names and table name from the schema above.
- For JSONB fields, use ->> for text extraction and cast explicitly: (extra_fields->>'field')::int
- To unnest the domains array: jsonb_array_elements_text(extra_fields->'domains')
- Always add WHERE clauses to handle NULL values in JSONB fields.
- Use date_trunc() for time-based aggregations.
- Limit results to 100 rows unless the question specifically asks for all results or an aggregate.
- If the question is ambiguous, make a reasonable assumption and note it in a SQL comment.
- If the question cannot be answered with the available data, respond with: ```sql
SELECT 'This question cannot be answered with the available data.' AS error;
```
"""


def get_llm_endpoint() -> str | None:
    """Returns the LLM endpoint URL, or None if in stub mode."""
    endpoint = os.environ.get("LLM_ENDPOINT", "").strip()
    return endpoint if endpoint else None


def is_llm_available() -> bool:
    """Check if an LLM backend is configured and reachable."""
    return get_llm_endpoint() is not None


def get_llm_model() -> str:
    """Returns the LLM model to use, defaults to claydog."""
    return os.environ.get("LLM_MODEL", "claydog")


def _get_headers() -> dict[str, str]:
    """Build request headers. Supports optional API key for future use."""
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _build_messages(question: str, history: list[dict] | None = None) -> list[dict]:
    """Builds the messages payload for the OpenAI-compatible API."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    if history:
        for msg in history:
            messages.append(msg)
    else:
        messages.append({"role": "user", "content": question})

    return messages


def _call_vllm(messages: list[dict]) -> str:
    """Calls the vLLM OpenAI-compatible endpoint."""
    endpoint = get_llm_endpoint()
    if not endpoint:
        raise ValueError("LLM_ENDPOINT is not set")

    url = f"{endpoint}/chat/completions"
    model = get_llm_model()

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 1024,
        "stream": False,
    }

    try:
        response = httpx.post(
            url,
            json=payload,
            headers=_get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]
    except httpx.ConnectError as e:
        raise Exception(f"Could not connect to LLM at {endpoint}. Is the vLLM server running?") from e
    except httpx.HTTPStatusError as e:
        raise Exception(f"HTTP Error {e.response.status_code}: {e.response.text}") from e
    except httpx.TimeoutException as e:
        raise Exception("LLM request timed out after 120 seconds") from e
    except (KeyError, IndexError) as e:
        raise Exception("Unexpected response format from LLM") from e


def extract_sql(response_text: str) -> str | None:
    """
    Extract SQL from the model's response.

    Tries in order:
    1. Content between ```sql and ``` markers
    2. Content between ``` and ``` markers (no language specified)
    3. If the entire response looks like SQL (starts with SELECT/WITH after
       stripping whitespace), use it directly
    4. Return None if no SQL found
    """
    if not response_text:
        return None

    # 1. ```sql ... ```
    sql_match = re.search(r"```sql\n(.*?)\n```", response_text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        sql = sql_match.group(1).strip()
        return sql.rstrip(';')

    # 2. ``` ... ```
    code_match = re.search(r"```\n(.*?)\n```", response_text, re.DOTALL)
    if code_match:
        sql = code_match.group(1).strip()
        return sql.rstrip(';')

    # 3. Whole string looks like SQL
    stripped_text = response_text.strip()
    if stripped_text.lower().startswith(("select", "with")):
        return stripped_text.rstrip(';')

    return None


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate that the SQL is safe to execute.

    Returns (is_valid, reason).
    """
    if not sql:
        return False, "No SQL found."

    if re.search(WRITE_KEYWORDS, sql, re.IGNORECASE):
        return False, "Query contains disallowed write keywords."

    if not sql.lower().startswith(("select", "with")):
         return False, "Query must be a SELECT statement."

    return True, ""


def _get_readonly_connection_params() -> dict:
    """Connection params using the llm_readonly role."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "postgres"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "ghostwriter"),
        "user": os.environ.get("POSTGRES_READONLY_USER", "llm_readonly"),
        "password": os.environ.get("POSTGRES_READONLY_PASSWORD", "llmreadonly"),
    }


def _test_execute(sql: str) -> tuple[bool, str]:
    """
    Test-execute SQL using the llm_readonly role.

    Returns (success, error_message).
    Uses a short statement_timeout to kill runaway queries.
    """
    params = _get_readonly_connection_params()
    try:
        conn = psycopg2.connect(**params)
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = '{TEST_QUERY_TIMEOUT}s';")
            cur.execute(sql)
        conn.close()
        return True, ""
    except Exception as e:
        error_msg = str(e).strip()
        if "canceling statement due to statement timeout" in error_msg:
             return False, "Query timed out after 10 seconds. Simplify the query or add more specific filters."
        return False, error_msg


def ask(question: str) -> LLMResponse:
    """
    Full text-to-SQL pipeline with self-correction.
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

    model = get_llm_model()
    retries = 0
    history = [{"role": "user", "content": question}]

    while retries <= MAX_RETRIES:
        try:
            messages = _build_messages(question, history)
            response_text = _call_vllm(messages)

            sql = extract_sql(response_text)

            if not sql:
                return LLMResponse(
                    generated_sql=None,
                    explanation=f"The model failed to generate a valid SQL query. Raw response:\n{response_text}",
                    is_stub=False,
                    retries_used=retries,
                    model_used=model,
                )

            is_valid, validation_msg = validate_sql(sql)
            if not is_valid:
                return LLMResponse(
                    generated_sql=sql,
                    explanation="The generated query failed security validation.",
                    is_stub=False,
                    retries_used=retries,
                    validation_error=validation_msg,
                    model_used=model,
                )

            is_executable, exec_error = _test_execute(sql)

            if is_executable:
                return LLMResponse(
                    generated_sql=sql,
                    explanation=f"Generated query for: {question}",
                    is_stub=False,
                    retries_used=retries,
                    execution_tested=True,
                    model_used=model,
                )
            else:
                if retries < MAX_RETRIES:
                    history.append({"role": "assistant", "content": f"```sql\n{sql}\n```"})
                    history.append({
                        "role": "user",
                        "content": f"The previous query failed with this error:\n\n{exec_error}\n\nFix the query. Output ONLY the corrected SQL wrapped in ```sql ... ``` code fences."
                    })
                    retries += 1
                else:
                    return LLMResponse(
                        generated_sql=sql,
                        explanation=f"The generated query failed to execute and could not be corrected.\nError: {exec_error}",
                        is_stub=False,
                        retries_used=retries,
                        execution_tested=False,
                        model_used=model,
                    )

        except Exception as e:
            logger.exception("LLM generation failed")
            return LLMResponse(
                generated_sql=None,
                explanation=f"An error occurred while generating the query: {str(e)}",
                is_stub=False,
                retries_used=retries,
                model_used=model,
            )

    # Fallback if loop ends unexpectedly
    return LLMResponse(
        generated_sql=None,
        explanation="Pipeline failed to generate query.",
        is_stub=False,
        retries_used=retries,
        model_used=model,
    )
