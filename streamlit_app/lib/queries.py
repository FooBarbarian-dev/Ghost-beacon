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

# -----------------
# 06_report_ioc.py
# -----------------
IOC_DOMAINS = """
SELECT
    domain,
    COUNT(*) AS beacon_count,
    MIN(start_date) AS first_seen,
    MAX(start_date) AS last_seen,
    array_agg(DISTINCT source_ip) AS associated_ips
FROM oplog_oplogentry,
    jsonb_array_elements_text(extra_fields->'domains') AS domain
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = '' OR source_ip = :ip_filter)
GROUP BY domain
ORDER BY beacon_count DESC
LIMIT 50;
"""

IOC_INFRASTRUCTURE = """
SELECT
    source_ip AS ip_address,
    (extra_fields->>'collected_from_port')::int AS port,
    COUNT(*) AS beacon_count,
    array_agg(DISTINCT tool) AS cs_versions_observed,
    MIN(start_date) AS first_seen,
    MAX(start_date) AS last_seen,
    MAX(extra_fields->>'tls_subject') AS tls_subject
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = '' OR source_ip = :ip_filter)
GROUP BY source_ip, port
ORDER BY beacon_count DESC;
"""

IOC_HASHES = """
SELECT
    extra_fields->>'sha256' AS sha256,
    extra_fields->>'md5' AS md5,
    extra_fields->>'sha1' AS sha1,
    tool AS cs_version,
    (extra_fields->>'filesize')::int AS filesize,
    start_date AS collection_date,
    source_ip
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = '' OR source_ip = :ip_filter)
      AND extra_fields->>'sha256' IS NOT NULL
ORDER BY start_date DESC;
"""

IOC_TLS = """
SELECT
    extra_fields->>'tls_subject' AS tls_subject,
    extra_fields->>'tls_issuer' AS tls_issuer,
    extra_fields->'tls_fingerprint'->>'sha256' AS fingerprint_sha256,
    COUNT(*) AS beacon_count,
    array_agg(DISTINCT source_ip) AS associated_ips
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = '' OR source_ip = :ip_filter)
      AND extra_fields->>'tls_subject' IS NOT NULL
      AND extra_fields->>'tls_subject' != 'null'
GROUP BY tls_subject, tls_issuer, fingerprint_sha256
ORDER BY beacon_count DESC;
"""

IOC_SUMMARY = """
SELECT
    COUNT(DISTINCT extra_fields->>'sha256') AS total_hashes,
    COUNT(DISTINCT domain) AS total_domains,
    COUNT(DISTINCT source_ip) AS total_ips,
    COUNT(DISTINCT CASE WHEN extra_fields->>'tls_subject' != 'null' THEN extra_fields->>'tls_subject' END) AS total_tls
FROM oplog_oplogentry
LEFT JOIN LATERAL jsonb_array_elements_text(CASE WHEN jsonb_typeof(extra_fields->'domains') = 'array' THEN extra_fields->'domains' ELSE '[]'::jsonb END) AS domain ON true
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = '' OR source_ip = :ip_filter);
"""

# -----------------
# 07_report_sessions.py
# -----------------
SESSIONS_UNIQUE_IPS = """
SELECT DISTINCT source_ip FROM oplog_oplogentry WHERE source_ip IS NOT NULL ORDER BY source_ip;
"""

SESSIONS_UNIQUE_VERSIONS = """
SELECT DISTINCT tool FROM oplog_oplogentry WHERE tool IS NOT NULL ORDER BY tool;
"""

SESSIONS_LIST = """
SELECT
    start_date AS collection_date,
    source_ip,
    (extra_fields->>'collected_from_port')::int AS port,
    tool AS cs_version,
    extra_fields->>'sha256' AS sha256,
    extra_fields->>'md5' AS md5,
    extra_fields->>'sha1' AS sha1,
    (extra_fields->>'filesize')::int AS filesize,
    (extra_fields->>'xorencoded')::int AS xorencoded,
    extra_fields->>'tls_subject' AS tls_subject,
    extra_fields->>'tls_issuer' AS tls_issuer,
    extra_fields->'tls_fingerprint'->>'sha256' AS tls_fingerprint_sha256,
    extra_fields->'domains' AS domains
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = 'All' OR source_ip = :ip_filter)
      -- ARRAY_LENGTH Check done in pandas or by injecting versions, but we'll do it with param
      AND (array_length(:versions_filter::text[], 1) IS NULL OR tool = ANY(:versions_filter::text[]))
ORDER BY start_date DESC;
"""

SESSIONS_COMM_PATHS = """
SELECT
    source_ip,
    domain,
    COUNT(*) AS beacon_count
FROM oplog_oplogentry,
     jsonb_array_elements_text(CASE WHEN jsonb_typeof(extra_fields->'domains') = 'array' THEN extra_fields->'domains' ELSE '[]'::jsonb END) AS domain
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = 'All' OR source_ip = :ip_filter)
      AND (array_length(:versions_filter::text[], 1) IS NULL OR tool = ANY(:versions_filter::text[]))
GROUP BY source_ip, domain
ORDER BY beacon_count DESC;
"""

# -----------------
# 08_report_hosts.py
# -----------------
HOSTS_OVERVIEW = """
SELECT
    source_ip AS ip_address,
    COUNT(*) AS total_beacons,
    array_length(array_agg(DISTINCT tool), 1) AS unique_cs_versions,
    array_agg(DISTINCT (extra_fields->>'collected_from_port')::int) AS ports_used,
    MIN(start_date) AS first_seen,
    MAX(start_date) AS last_seen,
    MAX(start_date) - MIN(start_date) AS duration,
    BOOL_OR(extra_fields->>'tls_subject' IS NOT NULL AND extra_fields->>'tls_subject' != 'null' AND extra_fields->>'tls_subject' NOT ILIKE '%cobaltstrike%') AS has_custom_tls
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_search = '' OR source_ip ILIKE '%' || :ip_search || '%')
GROUP BY source_ip
HAVING COUNT(*) >= :min_beacons
ORDER BY total_beacons DESC;
"""

HOST_DETAIL_SERVICES = """
SELECT
    (extra_fields->>'collected_from_port')::int AS port,
    COUNT(*) AS count
FROM oplog_oplogentry
WHERE source_ip = :ip_address
GROUP BY port
ORDER BY count DESC;
"""

HOST_DETAIL_VERSIONS = """
SELECT
    tool AS version,
    COUNT(*) AS count,
    MIN(start_date) AS first_seen,
    MAX(start_date) AS last_seen
FROM oplog_oplogentry
WHERE source_ip = :ip_address
GROUP BY version
ORDER BY count DESC;
"""

HOST_DETAIL_DOMAINS = """
SELECT
    domain,
    COUNT(*) AS count
FROM oplog_oplogentry,
     jsonb_array_elements_text(CASE WHEN jsonb_typeof(extra_fields->'domains') = 'array' THEN extra_fields->'domains' ELSE '[]'::jsonb END) AS domain
WHERE source_ip = :ip_address
GROUP BY domain
ORDER BY count DESC;
"""

HOST_DETAIL_TLS = """
SELECT
    extra_fields->>'tls_subject' AS tls_subject,
    extra_fields->>'tls_issuer' AS tls_issuer,
    extra_fields->'tls_fingerprint'->>'sha256' AS fingerprint_sha256,
    COUNT(*) AS count
FROM oplog_oplogentry
WHERE source_ip = :ip_address
      AND extra_fields->>'tls_subject' IS NOT NULL
      AND extra_fields->>'tls_subject' != 'null'
GROUP BY tls_subject, tls_issuer, fingerprint_sha256
ORDER BY count DESC;
"""

HOST_DETAIL_TIMELINE = """
SELECT
    start_date,
    tool AS version
FROM oplog_oplogentry
WHERE source_ip = :ip_address
ORDER BY start_date;
"""

HOST_COMPARISON = """
SELECT
    source_ip AS ip_address,
    COUNT(*) AS total_beacons,
    array_agg(DISTINCT tool) AS versions,
    array_agg(DISTINCT (extra_fields->>'collected_from_port')::int) AS ports,
    array_agg(DISTINCT domain) AS domains,
    MIN(start_date) AS first_seen,
    MAX(start_date) AS last_seen
FROM oplog_oplogentry
LEFT JOIN jsonb_array_elements_text(CASE WHEN jsonb_typeof(extra_fields->'domains') = 'array' THEN extra_fields->'domains' ELSE '[]'::jsonb END) AS domain ON true
WHERE source_ip = ANY(:ips::text[])
GROUP BY source_ip;
"""

# -----------------
# 09_report_activity.py
# -----------------
ACTIVITY_TIMELINE = """
SELECT
    date_trunc(:granularity, start_date) AS period,
    tool AS cs_version,
    COUNT(*) AS beacon_count
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = '' OR source_ip = :ip_filter)
      AND (array_length(:versions_filter::text[], 1) IS NULL OR tool = ANY(:versions_filter::text[]))
GROUP BY period, cs_version
ORDER BY period, beacon_count DESC;
"""

ACTIVITY_LOG = """
SELECT
    start_date AS collection_date,
    source_ip,
    (extra_fields->>'collected_from_port')::int AS port,
    tool AS cs_version,
    extra_fields->'domains' AS domains,
    LEFT(extra_fields->>'sha256', 16) AS sha256_short
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = '' OR source_ip = :ip_filter)
      AND (array_length(:versions_filter::text[], 1) IS NULL OR tool = ANY(:versions_filter::text[]))
ORDER BY start_date DESC;
"""

ACTIVITY_HEATMAP = """
SELECT
    EXTRACT(MONTH FROM start_date) AS month,
    EXTRACT(DOW FROM start_date) AS day_of_week,
    EXTRACT(HOUR FROM start_date) AS hour_of_day,
    COUNT(*) AS beacon_count
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (:ip_filter = '' OR source_ip = :ip_filter)
      AND (array_length(:versions_filter::text[], 1) IS NULL OR tool = ANY(:versions_filter::text[]))
GROUP BY month, day_of_week, hour_of_day;
"""

ACTIVITY_NEW_INFRA_IPS = """
WITH first_seen AS (
    SELECT
        source_ip,
        MIN(start_date) AS first_appearance
    FROM oplog_oplogentry
    GROUP BY source_ip
)
SELECT
    date_trunc(:granularity, first_appearance) AS period,
    COUNT(*) AS new_ips
FROM first_seen
WHERE first_appearance >= :start_date AND first_appearance <= :end_date
GROUP BY period
ORDER BY period;
"""

ACTIVITY_NEW_INFRA_DOMAINS = """
WITH first_seen AS (
    SELECT
        domain,
        MIN(start_date) AS first_appearance
    FROM oplog_oplogentry,
         jsonb_array_elements_text(CASE WHEN jsonb_typeof(extra_fields->'domains') = 'array' THEN extra_fields->'domains' ELSE '[]'::jsonb END) AS domain
    GROUP BY domain
)
SELECT
    date_trunc(:granularity, first_appearance) AS period,
    COUNT(*) AS new_domains
FROM first_seen
WHERE first_appearance >= :start_date AND first_appearance <= :end_date
GROUP BY period
ORDER BY period;
"""

ACTIVITY_NEW_INFRA_VERSIONS = """
WITH first_seen AS (
    SELECT
        tool AS version,
        MIN(start_date) AS first_appearance
    FROM oplog_oplogentry
    WHERE tool IS NOT NULL
    GROUP BY version
)
SELECT
    date_trunc(:granularity, first_appearance) AS period,
    COUNT(*) AS new_versions
FROM first_seen
WHERE first_appearance >= :start_date AND first_appearance <= :end_date
GROUP BY period
ORDER BY period;
"""

# -----------------
# 10_report_ttp.py
# -----------------
TTP_INFERENCES = """
SELECT
    'T1071.001' AS attack_id, 'Application Layer Protocol: Web Protocols' AS technique, 'Command and Control' AS tactic,
    COUNT(*) AS beacon_count, 'Beacons communicating over HTTP/HTTPS (port 80, 443, 8080, 8443)' AS inference_basis
FROM oplog_oplogentry WHERE start_date >= :start_date AND start_date <= :end_date AND (extra_fields->>'collected_from_port')::int IN (80, 443, 8080, 8443)
UNION ALL
SELECT
    'T1071.004', 'Application Layer Protocol: DNS', 'Command and Control',
    COUNT(*), 'Beacons on port 53'
FROM oplog_oplogentry WHERE start_date >= :start_date AND start_date <= :end_date AND (extra_fields->>'collected_from_port')::int = 53
UNION ALL
SELECT
    'T1573.002', 'Encrypted Channel: Asymmetric Cryptography', 'Command and Control',
    COUNT(*), 'Beacons with HTTPS/TLS (port 443, 8443 or has TLS subject)'
FROM oplog_oplogentry WHERE start_date >= :start_date AND start_date <= :end_date AND ((extra_fields->>'collected_from_port')::int IN (443, 8443) OR (extra_fields->>'tls_subject' IS NOT NULL AND extra_fields->>'tls_subject' != 'null'))
UNION ALL
SELECT
    'T1027', 'Obfuscated Files or Information', 'Defense Evasion',
    COUNT(*), 'XOR-encoded beacons'
FROM oplog_oplogentry WHERE start_date >= :start_date AND start_date <= :end_date AND (extra_fields->>'xorencoded')::int = 1
UNION ALL
SELECT
    'T1587.001', 'Develop Capabilities: Malware', 'Resource Development',
    COUNT(DISTINCT extra_fields->>'sha256'), 'Unique beacon payloads (distinct hashes)'
FROM oplog_oplogentry WHERE start_date >= :start_date AND start_date <= :end_date
UNION ALL
SELECT
    'T1583.001', 'Acquire Infrastructure: Domains', 'Resource Development',
    (SELECT COUNT(DISTINCT domain) FROM oplog_oplogentry, jsonb_array_elements_text(CASE WHEN jsonb_typeof(extra_fields->'domains') = 'array' THEN extra_fields->'domains' ELSE '[]'::jsonb END) AS domain WHERE start_date >= :start_date AND start_date <= :end_date), 'C2 domains used across beacons'
UNION ALL
SELECT
    'T1583.003', 'Acquire Infrastructure: Virtual Private Server', 'Resource Development',
    COUNT(DISTINCT source_ip), 'Team server IPs'
FROM oplog_oplogentry WHERE start_date >= :start_date AND start_date <= :end_date
UNION ALL
SELECT
    'T1608.001', 'Stage Capabilities: Upload Malware', 'Resource Development',
    COUNT(*), 'Beacons staged on team servers'
FROM oplog_oplogentry WHERE start_date >= :start_date AND start_date <= :end_date
ORDER BY beacon_count DESC;
"""

TTP_DOMAIN_FRONTING = """
SELECT
    domain,
    COUNT(*) AS beacon_count,
    array_agg(DISTINCT source_ip) AS team_servers,
    array_agg(DISTINCT tool) AS cs_versions
FROM oplog_oplogentry,
    jsonb_array_elements_text(CASE WHEN jsonb_typeof(extra_fields->'domains') = 'array' THEN extra_fields->'domains' ELSE '[]'::jsonb END) AS domain
WHERE start_date >= :start_date AND start_date <= :end_date
AND domain LIKE ANY(:cdn_patterns::text[])
GROUP BY domain
ORDER BY beacon_count DESC;
"""

TTP_TECHNIQUE_SAMPLES = """
SELECT
    start_date AS collection_date,
    source_ip,
    tool AS cs_version,
    extra_fields->'domains' AS domains,
    LEFT(extra_fields->>'sha256', 16) AS sha256_short
FROM oplog_oplogentry
WHERE start_date >= :start_date AND start_date <= :end_date
      AND (
          (:attack_id = 'T1071.001' AND (extra_fields->>'collected_from_port')::int IN (80, 443, 8080, 8443))
          OR (:attack_id = 'T1071.004' AND (extra_fields->>'collected_from_port')::int = 53)
          OR (:attack_id = 'T1573.002' AND ((extra_fields->>'collected_from_port')::int IN (443, 8443) OR (extra_fields->>'tls_subject' IS NOT NULL AND extra_fields->>'tls_subject' != 'null')))
          OR (:attack_id = 'T1027' AND (extra_fields->>'xorencoded')::int = 1)
          OR (:attack_id IN ('T1587.001', 'T1583.001', 'T1583.003', 'T1608.001'))
      )
ORDER BY start_date DESC
LIMIT 10;
"""

TTP_TECHNIQUE_TREND = """
SELECT
    date_trunc('quarter', start_date) AS quarter,
    COUNT(*) AS beacon_count
FROM oplog_oplogentry
WHERE start_date IS NOT NULL AND start_date >= :start_date AND start_date <= :end_date
      AND (
          (:attack_id = 'T1071.001' AND (extra_fields->>'collected_from_port')::int IN (80, 443, 8080, 8443))
          OR (:attack_id = 'T1071.004' AND (extra_fields->>'collected_from_port')::int = 53)
          OR (:attack_id = 'T1573.002' AND ((extra_fields->>'collected_from_port')::int IN (443, 8443) OR (extra_fields->>'tls_subject' IS NOT NULL AND extra_fields->>'tls_subject' != 'null')))
          OR (:attack_id = 'T1027' AND (extra_fields->>'xorencoded')::int = 1)
          OR (:attack_id IN ('T1587.001', 'T1583.001', 'T1583.003', 'T1608.001'))
      )
GROUP BY quarter
ORDER BY quarter;
"""