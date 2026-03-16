import streamlit as st
import datetime
from lib.db import run_query
from lib.report_utils import render_report_header, csv_download_button, paginate_dataframe
from lib.queries import IOC_DOMAINS, IOC_INFRASTRUCTURE, IOC_HASHES, IOC_TLS, IOC_SUMMARY

render_report_header(
    title="Indicators of Compromise",
    cs_report_name="Indicators of Compromise Report",
    disclaimer="This report approximates the Cobalt Strike IOC report using beacon metadata collected from team servers in the wild (2018–2022). Unlike the real CS report, this does not include Malleable C2 traffic samples or uploaded file hashes. Indicators shown are derived from beacon configuration extraction.",
)

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    start_date = st.date_input("Start Date", datetime.date(2018, 1, 1))
with col2:
    end_date = st.date_input("End Date", datetime.date(2023, 1, 1))
with col3:
    ip_filter = st.text_input("Team Server IP (optional)", "")

params = {
    "start_date": start_date,
    "end_date": end_date,
    "ip_filter": ip_filter,
}

# Summary Statistics
df_summary = run_query(IOC_SUMMARY, params)
if not df_summary.empty:
    st.subheader("Summary Statistics")
    summary = df_summary.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Unique SHA256", f"{summary['total_hashes']:,}")
    m2.metric("Total C2 Domains", f"{summary['total_domains']:,}")
    m3.metric("Total Team Server IPs", f"{summary['total_ips']:,}")
    m4.metric("Total TLS Subjects", f"{summary['total_tls']:,}")
    st.divider()

# Domains
st.subheader("Network Indicators — C2 Domains")
df_domains = run_query(IOC_DOMAINS, params)
if not df_domains.empty:
    st.dataframe(df_domains, use_container_width=True)
else:
    st.info("No domain indicators found.")

# Infrastructure
st.subheader("Network Indicators — Team Server Infrastructure")
df_infra = run_query(IOC_INFRASTRUCTURE, params)
if not df_infra.empty:
    st.dataframe(df_infra, use_container_width=True)
else:
    st.info("No infrastructure indicators found.")

# Hashes
st.subheader("File Indicators — Beacon Hashes")
df_hashes = run_query(IOC_HASHES, params)
if not df_hashes.empty:
    csv_download_button(df_hashes, "ioc_hashes.csv", "Download Hash List (CSV)")
    df_hashes_page = paginate_dataframe(df_hashes, page_size=50, key="ioc_hashes_page")
    st.dataframe(df_hashes_page, use_container_width=True)
else:
    st.info("No hash indicators found.")

# TLS
st.subheader("TLS Certificate Indicators")
df_tls = run_query(IOC_TLS, params)
if not df_tls.empty:
    st.dataframe(df_tls, use_container_width=True)
else:
    st.info("No TLS certificate indicators found.")
