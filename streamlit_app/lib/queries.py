"""
SQL queries as named constants for the Streamlit app.
"""

# -----------------
# 01_overview.py
# -----------------
OVERVIEW_METRICS = """
SELECT
    COUNT(*) AS total_beacons,
    COUNT(DISTINCT source_ip) AS unique_ips,
    COUNT(DISTINCT tool) AS unique_versions,
    MIN(start_date) AS min_date,
    MAX(start_date) AS max_date
FROM oplog_oplogentry
WHERE start_date IS NOT NULL;
"""

BEACON_COLLECTION_TIMELINE = """
SELECT
  date_trunc('month', start_date) AS month,
  COUNT(*) AS beacon_count
FROM oplog_oplogentry
WHERE start_date IS NOT NULL
GROUP BY month
ORDER BY month;
"""

# -----------------
# 02_versions.py
# -----------------
COBALT_STRIKE_VERSION_DISTRIBUTION = """
SELECT
  tool AS cs_version,
  COUNT(*) AS count
FROM oplog_oplogentry
WHERE tool IS NOT NULL
GROUP BY tool
ORDER BY count DESC
LIMIT 20;
"""

VERSION_ADOPTION_OVER_TIME = """
WITH TopVersions AS (
    SELECT tool
    FROM oplog_oplogentry
    WHERE tool IS NOT NULL
    GROUP BY tool
    ORDER BY COUNT(*) DESC
    LIMIT 10
),
MonthlyCounts AS (
    SELECT
      date_trunc('month', start_date) AS month,
      CASE
        WHEN tool IN (SELECT tool FROM TopVersions) THEN tool
        ELSE 'Other'
      END AS version_group,
      COUNT(*) as count
    FROM oplog_oplogentry
    WHERE start_date IS NOT NULL AND tool IS NOT NULL
    GROUP BY month, version_group
)
SELECT month, version_group, count
FROM MonthlyCounts
ORDER BY month, count DESC;
"""

VERSION_FILTER_METRICS = """
SELECT
    COUNT(*) AS beacon_count,
    COUNT(DISTINCT source_ip) AS unique_ips,
    MIN(start_date) AS min_date,
    MAX(start_date) AS max_date
FROM oplog_oplogentry
WHERE tool = :selected_version;
"""

VERSION_PORTS = """
SELECT
    (extra_fields->>'collected_from_port')::int AS port,
    COUNT(*) as count
FROM oplog_oplogentry
WHERE tool = :selected_version AND extra_fields->>'collected_from_port' IS NOT NULL
GROUP BY port
ORDER BY count DESC
LIMIT 10;
"""

VERSION_DOMAINS = """
SELECT
    domain,
    COUNT(*) as count
FROM oplog_oplogentry,
  jsonb_array_elements_text(extra_fields->'domains') AS domain
WHERE tool = :selected_version
GROUP BY domain
ORDER BY count DESC
LIMIT 10;
"""

# -----------------
# 03_infrastructure.py
# -----------------
TOP_TEAM_SERVERS = """
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
"""

LISTENING_PORT_DISTRIBUTION = """
SELECT
  (extra_fields->>'collected_from_port')::int AS port,
  COUNT(*) AS count
FROM oplog_oplogentry
WHERE extra_fields->>'collected_from_port' IS NOT NULL
GROUP BY port
ORDER BY count DESC
LIMIT 20;
"""

C2_DOMAIN_FREQUENCY = """
SELECT
  domain,
  COUNT(*) AS beacon_count
FROM oplog_oplogentry,
  jsonb_array_elements_text(extra_fields->'domains') AS domain
GROUP BY domain
ORDER BY beacon_count DESC
LIMIT 30;
"""

IP_SEARCH = """
SELECT
    start_date,
    tool,
    dest_ip,
    extra_fields->>'collected_from_port' as port,
    extra_fields->>'tls_subject' as tls_subject
FROM oplog_oplogentry
WHERE source_ip = :search_ip
ORDER BY start_date DESC;
"""

# -----------------
# 04_indicators.py
# -----------------
TLS_CERTIFICATE_USAGE = """
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
"""

TOP_TLS_SUBJECTS = """
SELECT
    extra_fields->>'tls_subject' AS tls_subject,
    COUNT(*) as count
FROM oplog_oplogentry
WHERE extra_fields->>'tls_subject' IS NOT NULL
      AND extra_fields->>'tls_subject' != 'null'
GROUP BY tls_subject
ORDER BY count DESC
LIMIT 20;
"""

XOR_ENCODING_OVER_TIME = """
SELECT
  date_trunc('quarter', start_date) AS quarter,
  (extra_fields->>'xorencoded')::int AS xor_encoded,
  COUNT(*) AS count
FROM oplog_oplogentry
WHERE start_date IS NOT NULL
  AND extra_fields->>'xorencoded' IS NOT NULL
GROUP BY quarter, xor_encoded
ORDER BY quarter;
"""

FILESIZE_DISTRIBUTION_RAW = """
SELECT
    (extra_fields->>'filesize')::int AS filesize
FROM oplog_oplogentry
WHERE extra_fields->>'filesize' IS NOT NULL;
"""

FILESIZE_BY_VERSION = """
WITH TopVersions AS (
    SELECT tool
    FROM oplog_oplogentry
    WHERE tool IS NOT NULL
    GROUP BY tool
    ORDER BY COUNT(*) DESC
    LIMIT 10
)
SELECT
    tool,
    (extra_fields->>'filesize')::int AS filesize
FROM oplog_oplogentry
WHERE tool IN (SELECT tool FROM TopVersions)
      AND extra_fields->>'filesize' IS NOT NULL;
"""