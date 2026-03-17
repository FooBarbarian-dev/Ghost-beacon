import streamlit as st
import datetime
import plotly.express as px
import plotly.graph_objects as go
from lib.db import run_query
from lib.report_utils import render_report_header, csv_download_button, paginate_dataframe
from lib.queries import SESSIONS_UNIQUE_IPS, SESSIONS_UNIQUE_VERSIONS, SESSIONS_LIST, SESSIONS_COMM_PATHS

st.set_page_config(layout="wide")

render_report_header(
    title="Sessions",
    cs_report_name="Sessions Report",
    disclaimer="This report approximates the Cobalt Strike Sessions Report. Each beacon configuration is treated as a 'session.' Communication paths show the team server and configured C2 domains, not observed network traffic. Activity timelines show collection dates, not operator command sequences.",
)

# Load IPs and Versions for filters
df_ips = run_query(SESSIONS_UNIQUE_IPS)
ip_list = ["All"] + df_ips['source_ip'].tolist() if not df_ips.empty else ["All"]

df_versions = run_query(SESSIONS_UNIQUE_VERSIONS)
version_list = df_versions['tool'].tolist() if not df_versions.empty else []

# Filters
col1, col2, col3, col4 = st.columns(4)
with col1:
    selected_ip = st.selectbox("Team Server IP", ip_list)
with col2:
    selected_versions = st.multiselect("CS Version", version_list, default=[])
with col3:
    start_date = st.date_input("Start Date", datetime.date(2018, 1, 1))
with col4:
    end_date = st.date_input("End Date", datetime.date(2023, 1, 1))

# Convert empty versions to None or array_length check in postgres
versions_filter = selected_versions if selected_versions else None

params = {
    "ip_filter": selected_ip,
    "versions_filter": versions_filter,
    "start_date": start_date,
    "end_date": end_date,
}

df_sessions = run_query(SESSIONS_LIST, params)

if not df_sessions.empty:
    st.subheader(f"Session List ({len(df_sessions)} found)")
    csv_download_button(df_sessions, "sessions.csv", "Download Sessions CSV")

    # Add index for session numbers
    df_sessions = df_sessions.reset_index()
    df_sessions['Session #'] = df_sessions.index + 1

    # Format Comm Path
    def format_comm_path(row):
        ip = row['source_ip']
        port = row['port']
        domains = row['domains'] if row['domains'] else []
        return f"{ip}:{port} → {', '.join(domains) if domains else 'None'}"

    df_sessions['Communication Path'] = df_sessions.apply(format_comm_path, axis=1)

    display_cols = ['Session #', 'collection_date', 'source_ip', 'port', 'cs_version', 'Communication Path', 'sha256']

    page_df = paginate_dataframe(df_sessions, page_size=25, key="sessions_page")

    st.dataframe(page_df[display_cols], use_container_width=True)

    # Session Details
    st.subheader("Session Details")
    for _, row in page_df.iterrows():
        sha = row['sha256']
        sha_short = sha[:12] if sha else "None"
        with st.expander(f"SESSION: {sha_short}... | {row['source_ip']}:{row['port']} | {row['collection_date']}"):
            domains_str = "\n  ".join(row['domains']) if row['domains'] else "None"
            st.code(f"""
SESSION: {sha_short}...
Collected: {row['collection_date']}
Source: {row['source_ip']}:{row['port']}

COMMUNICATION PATH:
  Team Server: {row['source_ip']}:{row['port']}
  Configured Domains:
  {domains_str}

FILE INDICATORS:
  SHA256: {row['sha256']}
  MD5:    {row['md5']}
  SHA1:   {row['sha1']}
  Size:   {row['filesize']} bytes

ADDITIONAL INDICATORS:
  CS Version:   {row['cs_version']}
  XOR Encoded:  {'Yes' if row['xorencoded'] else 'No'}
  TLS Subject:  {row['tls_subject'] or 'Default/None'}
  TLS Issuer:   {row['tls_issuer'] or 'Default/None'}
  TLS Fingerprint SHA256: {row['tls_fingerprint_sha256'] or 'None'}
            """)

    # Visualization
    st.subheader("Communication Path Summary")
    df_comm = run_query(SESSIONS_COMM_PATHS, params)

    if not df_comm.empty:
        # Grouped bar chart instead of Sankey for simplicity and readability
        fig = px.bar(
            df_comm.head(50),
            x='domain',
            y='beacon_count',
            color='source_ip',
            title="Top Communication Paths (Domain by Team Server)",
            labels={'domain': 'C2 Domain', 'beacon_count': 'Beacon Count', 'source_ip': 'Team Server IP'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No communication path data available.")

else:
    st.info("No sessions found for the given criteria.")
