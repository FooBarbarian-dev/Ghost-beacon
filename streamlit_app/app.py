"""
Beacon Ghostwriter Explorer

Streamlit app for exploring Cobalt Strike beacon metadata
loaded into a Ghostwriter-compatible oplog database.

Navigation is via Streamlit's built-in page system (pages/ directory).
"""

import streamlit as st

st.set_page_config(
    page_title="Beacon Ghostwriter Explorer",
    page_icon="👻",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("👻 Beacon Ghostwriter Explorer")
st.markdown(
    """
    Exploring **~128,000 Cobalt Strike beacon configurations** (2018–2022)
    from the [fox-it/cobaltstrike-beacon-data](https://github.com/fox-it/cobaltstrike-beacon-data)
    dataset, loaded into a Ghostwriter-compatible oplog database.

    Use the sidebar to navigate between analysis views.

    ---

    **Data sources:**
    - PostgreSQL (direct) for all queries
    - Hasura GraphQL console available at [localhost:8080/console](http://localhost:8080/console)
    - Metabase dashboards available at [localhost:3000](http://localhost:3000)
    """
)