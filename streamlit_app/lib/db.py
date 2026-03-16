"""
Database helper module.
Provides connection strings and a helper function to run queries and return pandas DataFrames.
"""
import os
import psycopg2
import pandas as pd
import streamlit as st
from typing import Optional, Any, Dict, List, Tuple

def get_connection_string() -> str:
    """Returns the PostgreSQL connection string."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "ghostwriter")
    user = os.environ.get("POSTGRES_USER", "ghostwriter")
    password = os.environ.get("POSTGRES_PASSWORD", "ghostwriter")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

@st.cache_data(ttl=300)
def run_query(sql: str, params: Optional[Tuple] = None) -> pd.DataFrame:
    """
    Connects to the database, runs a SQL query, and returns a pandas DataFrame.
    DataFrames are cached using Streamlit's cache_data functionality.
    """
    conn = None
    try:
        conn_string = get_connection_string()
        conn = psycopg2.connect(conn_string)
        if params:
            df = pd.read_sql_query(sql, conn, params=params)
        else:
            df = pd.read_sql_query(sql, conn)
        return df
    except Exception as e:
        st.error(f"Database query error: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()
