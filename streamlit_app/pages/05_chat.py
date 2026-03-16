import streamlit as st
from lib.llm import ask, is_llm_available, DB_SCHEMA_CONTEXT
from lib.db import run_query

st.title("💬 Ask the Data")

# Show LLM status
if is_llm_available():
    st.success("LLM backend connected.")
else:
    st.info(
        "No LLM backend configured. Set `LLM_ENDPOINT` to enable "
        "natural-language querying. The chat interface below shows "
        "how it will work when connected."
    )

# Display schema context in an expander (useful for understanding what the LLM sees)
with st.expander("Database schema (sent to LLM as context)"):
    st.code(DB_SCHEMA_CONTEXT, language="sql")

# Chat history in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sql"):
            st.code(msg["sql"], language="sql")
        if msg.get("dataframe") is not None:
            st.dataframe(msg["dataframe"])

# Chat input
if prompt := st.chat_input("Ask a question about the beacon data..."):
    # Display user message
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get LLM response
    response = ask(prompt)

    with st.chat_message("assistant"):
        st.markdown(response.explanation)

        if response.generated_sql:
            st.code(response.generated_sql, language="sql")
            try:
                df = run_query(response.generated_sql)
                st.dataframe(df)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response.explanation,
                    "sql": response.generated_sql,
                    "dataframe": df,
                })
            except Exception as e:
                st.error(f"Query execution failed: {e}")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"{response.explanation}\n\n⚠️ Query failed: {e}",
                    "sql": response.generated_sql,
                })
        else:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response.explanation,
            })

# Suggested questions (always visible)
st.divider()
st.subheader("Suggested questions")
suggestions = [
    "How many beacons were collected each year?",
    "Which team server IPs served the most unique Cobalt Strike versions?",
    "What are the most common C2 domains configured in beacons?",
    "Show me beacons using port 50050 — what versions do they run?",
    "Which beacons have custom TLS certificates?",
    "What's the average filesize by Cobalt Strike version?",
]
for s in suggestions:
    if st.button(s, key=f"suggest_{s}"):
        st.session_state.chat_input_value = s
        st.rerun()
