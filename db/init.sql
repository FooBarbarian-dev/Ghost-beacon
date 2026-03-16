CREATE TABLE oplog_oplog (
    id serial PRIMARY KEY,
    name varchar(255) NOT NULL,
    project_id integer,
    mute_notifications boolean DEFAULT false
);

CREATE TABLE oplog_oplogentry (
    id bigserial PRIMARY KEY,
    oplog_id_id integer NOT NULL REFERENCES oplog_oplog(id),
    start_date timestamptz,
    end_date timestamptz,
    source_ip varchar(255),
    dest_ip varchar(255),
    tool varchar(255),
    user_context varchar(255),
    command text,
    description text,
    output text,
    comments text,
    operator_name varchar(255),
    entry_identifier varchar(255),
    extra_fields jsonb DEFAULT '{}'::jsonb,
    tags jsonb DEFAULT '[]'::jsonb
);

CREATE INDEX idx_oplog_oplogentry_entry_identifier ON oplog_oplogentry(entry_identifier);

INSERT INTO oplog_oplog (name) VALUES ('CS Beacon Import - fox-it/cobaltstrike-beacon-data (2018-2022)');

-- Read-only role for LLM-generated queries (future use).
-- NEVER let LLM-generated SQL run with write permissions.
CREATE ROLE llm_readonly WITH LOGIN PASSWORD 'llmreadonly';
GRANT CONNECT ON DATABASE ghostwriter TO llm_readonly;
GRANT USAGE ON SCHEMA public TO llm_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO llm_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO llm_readonly;

-- Database for Metabase internal metadata
CREATE DATABASE metabase OWNER ghostwriter;
