"""
Database helper module.
Provides connection strings and a helper function to run queries and return pandas DataFrames.
"""
import os
import psycopg2
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from typing import Optional, Any, Dict, List, Tuple

def get_readonly_connection_params() -> dict:
    """Connection params using the llm_readonly role. For LLM-generated queries only."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "postgres"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "ghostwriter"),
        "user": os.environ.get("POSTGRES_READONLY_USER", "llm_readonly"),
        "password": os.environ.get("POSTGRES_READONLY_PASSWORD", "llmreadonly"),
    }

def run_readonly_query(sql: str, timeout_seconds: int = 30) -> pd.DataFrame:
    """
    Execute a SQL query using the read-only role.

    Used by the chat page for LLM-generated queries.
    Sets a statement_timeout to prevent runaway queries.

    Raises psycopg2.Error on failure.
    """
    params = get_readonly_connection_params()
    conn = psycopg2.connect(**params)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = '{timeout_seconds}s';")

        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()

def get_connection_string() -> str:
    """Returns the PostgreSQL connection string."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "ghostwriter")
    user = os.environ.get("POSTGRES_USER", "ghostwriter")
    password = os.environ.get("POSTGRES_PASSWORD", "ghostwriter")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

@st.cache_data(ttl=300)
def run_query(sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
    """
    Connects to the database, runs a SQL query, and returns a pandas DataFrame.
    DataFrames are cached using Streamlit's cache_data functionality.
    """
    try:
        conn_string = get_connection_string()
        engine = create_engine(conn_string)
        with engine.connect() as conn:
            if params:
                df = pd.read_sql_query(text(sql), conn, params=params)
            else:
                df = pd.read_sql_query(text(sql), conn)
        return df
    except Exception as e:
        st.error(f"Database query error: {e}")
        return pd.DataFrame()
