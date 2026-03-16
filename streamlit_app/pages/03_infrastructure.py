import streamlit as st
import plotly.express as px
from lib.db import run_query
from lib.queries import (
    TOP_TEAM_SERVERS,
    LISTENING_PORT_DISTRIBUTION,
    C2_DOMAIN_FREQUENCY,
    IP_SEARCH
)

st.title("🌐 Infrastructure Patterns")

# IP Search at top
st.subheader("IP Search")
search_ip = st.text_input("Search for a specific Team Server IP:")
if search_ip:
    df_search = run_query(IP_SEARCH, params={"search_ip": search_ip})
    if not df_search.empty:
        st.success(f"Found {len(df_search)} beacons for IP {search_ip}")
        st.dataframe(df_search, use_container_width=True, hide_index=True)
    else:
        st.warning(f"No beacons found for IP {search_ip}")

st.divider()

# Two columns for Ports and Domains
col1, col2 = st.columns(2)

with col1:
    st.subheader("Listening Ports")
    df_ports = run_query(LISTENING_PORT_DISTRIBUTION)
    if not df_ports.empty:
        fig_ports = px.pie(
            df_ports,
            values='count',
            names='port',
            hole=0.4
        )
        st.plotly_chart(fig_ports, use_container_width=True)
    else:
        st.info("No port data.")

with col2:
    st.subheader("Common C2 Domains")
    df_domains = run_query(C2_DOMAIN_FREQUENCY)
    if not df_domains.empty:
        fig_domains = px.bar(
            df_domains.head(15),
            x='count',
            y='domain',
            orientation='h',
            labels={'count': 'Count', 'domain': 'C2 Domain'}
        )
        fig_domains.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_domains, use_container_width=True)
        st.caption("*Note: Attackers configure these arbitrarily. Many impersonate legitimate CDNs.*")
    else:
        st.info("No domain data.")

st.divider()

# Top Team Servers Table
st.subheader("Top Team Servers")
df_servers = run_query(TOP_TEAM_SERVERS)
if not df_servers.empty:
    st.dataframe(df_servers, use_container_width=True, hide_index=True)
else:
    st.info("No team server data.")
