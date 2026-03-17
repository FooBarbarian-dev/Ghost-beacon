import streamlit as st
import datetime
import plotly.express as px
from lib.db import run_query
from lib.report_utils import render_report_header, paginate_dataframe
from lib.queries import HOSTS_OVERVIEW, HOST_DETAIL_SERVICES, HOST_DETAIL_VERSIONS, HOST_DETAIL_DOMAINS, HOST_DETAIL_TLS, HOST_DETAIL_TIMELINE, HOST_COMPARISON

st.set_page_config(layout="wide")

render_report_header(
    title="Hosts",
    cs_report_name="Hosts Report",
    disclaimer="This report approximates the Cobalt Strike Hosts Report. In the real report, 'hosts' are compromised victim machines. Here, 'hosts' are team server IPs from which beacons were collected. This inverts the perspective: we're profiling the attacker infrastructure, not the targets.",
)

# Filters
col1, col2, col3, col4 = st.columns(4)
with col1:
    ip_search = st.text_input("Search Team Server IP", "")
with col2:
    min_beacons = st.slider("Minimum Beacon Count", 1, 100, 5)
with col3:
    start_date = st.date_input("Start Date", datetime.date(2018, 1, 1))
with col4:
    end_date = st.date_input("End Date", datetime.date(2023, 1, 1))

params = {
    "ip_search": ip_search,
    "min_beacons": min_beacons,
    "start_date": start_date,
    "end_date": end_date,
}

df_hosts = run_query(HOSTS_OVERVIEW, params)

if not df_hosts.empty:
    st.subheader(f"Hosts Overview ({len(df_hosts)} found)")

    # Calculate duration days
    df_hosts['duration_days'] = df_hosts['duration'].dt.days if 'duration' in df_hosts else 0

    page_df = paginate_dataframe(df_hosts, page_size=20, key="hosts_page")

    display_cols = ['ip_address', 'total_beacons', 'unique_cs_versions', 'ports_used', 'first_seen', 'last_seen', 'duration_days', 'has_custom_tls']
    st.dataframe(page_df[display_cols], use_container_width=True)

    # Detailed Profile
    st.divider()
    st.subheader("Host Detail View")
    selected_ip = st.selectbox("Select IP for Profile", df_hosts['ip_address'].tolist())

    if selected_ip:
        host_info = df_hosts[df_hosts['ip_address'] == selected_ip].iloc[0]

        col1, col2 = st.columns([1, 1])
        with col1:
            st.code(f"""
HOST PROFILE: {selected_ip}
First Seen: {host_info['first_seen']} | Last Seen: {host_info['last_seen']} | Active Duration: {host_info['duration_days']} days
Total Beacons: {host_info['total_beacons']}
            """)

            st.markdown("### Services (Ports)")
            df_services = run_query(HOST_DETAIL_SERVICES, {"ip_address": selected_ip})
            for _, row in df_services.iterrows():
                st.write(f"- Port **{row['port']}**: {row['count']} beacons")

            st.markdown("### Cobalt Strike Versions")
            df_versions = run_query(HOST_DETAIL_VERSIONS, {"ip_address": selected_ip})
            for _, row in df_versions.iterrows():
                st.write(f"- Version **{row['version']}**: {row['count']} beacons ({row['first_seen']} — {row['last_seen']})")

        with col2:
            st.markdown("### Configured C2 Domains")
            df_domains = run_query(HOST_DETAIL_DOMAINS, {"ip_address": selected_ip})
            for _, row in df_domains.iterrows():
                st.write(f"- Domain **{row['domain']}**: {row['count']} beacons")

            st.markdown("### TLS Certificates")
            df_tls = run_query(HOST_DETAIL_TLS, {"ip_address": selected_ip})
            if not df_tls.empty:
                for _, row in df_tls.iterrows():
                    st.write(f"- Subject: `{row['tls_subject']}` | Issuer: `{row['tls_issuer']}` | SHA256: `{row['fingerprint_sha256']}`")
            else:
                st.write("- None/Default")

        # Timeline Scatter
        st.markdown("### Beacon Timeline")
        df_timeline = run_query(HOST_DETAIL_TIMELINE, {"ip_address": selected_ip})
        if not df_timeline.empty:
            df_timeline['y'] = 1 # Jitter baseline
            fig = px.scatter(
                df_timeline,
                x="start_date",
                y="y",
                color="version",
                title="Beacon Collections Over Time",
                labels={"start_date": "Date", "version": "CS Version"}
            )
            fig.update_yaxes(showticklabels=False, title="")
            st.plotly_chart(fig, use_container_width=True)

    # Host Comparison
    st.divider()
    st.subheader("Host Comparison")
    compare_ips = st.multiselect("Select Hosts to Compare (2–5 recommended)", df_hosts['ip_address'].tolist(), max_selections=5)

    if compare_ips:
        df_compare = run_query(HOST_COMPARISON, {"ips": compare_ips})
        if not df_compare.empty:
            # Transpose for side-by-side
            df_compare = df_compare.set_index('ip_address').T
            st.dataframe(df_compare, use_container_width=True)

else:
    st.info("No hosts found matching criteria.")
