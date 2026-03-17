import streamlit as st
import datetime
import plotly.express as px
from lib.db import run_query
from lib.report_utils import render_report_header, paginate_dataframe
from lib.queries import ACTIVITY_TIMELINE, ACTIVITY_LOG, ACTIVITY_HEATMAP, ACTIVITY_NEW_INFRA_IPS, ACTIVITY_NEW_INFRA_DOMAINS, ACTIVITY_NEW_INFRA_VERSIONS, SESSIONS_UNIQUE_VERSIONS

st.set_page_config(layout="wide")

render_report_header(
    title="Activity",
    cs_report_name="Activity Report",
    disclaimer="This report approximates the Cobalt Strike Activity Report. The real report is a timeline of operator commands and post-exploitation activities. This version shows a timeline of beacon collection events — when beacon configurations were observed on team servers in the wild. Patterns in collection timing can reveal campaign deployment cycles and infrastructure activity.",
)

# Filters
df_versions = run_query(SESSIONS_UNIQUE_VERSIONS)
version_list = df_versions['tool'].tolist() if not df_versions.empty else []

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    granularity = st.selectbox("Time Granularity", ["day", "week", "month", "quarter"], index=2)
with col2:
    selected_versions = st.multiselect("CS Version Filter", version_list, default=[])
with col3:
    ip_filter = st.text_input("Team Server IP", "")
with col4:
    start_date = st.date_input("Start Date", datetime.date(2018, 1, 1))
with col5:
    end_date = st.date_input("End Date", datetime.date(2023, 1, 1))

versions_filter = selected_versions if selected_versions else None

params = {
    "granularity": granularity,
    "versions_filter": versions_filter,
    "ip_filter": ip_filter,
    "start_date": start_date,
    "end_date": end_date,
}

# 1. Timeline
st.subheader("Activity Timeline")
df_timeline = run_query(ACTIVITY_TIMELINE, params)

if not df_timeline.empty:
    if versions_filter:
        fig = px.area(
            df_timeline,
            x='period',
            y='beacon_count',
            color='cs_version',
            title=f"Beacon Collections Over Time (by {granularity})",
            labels={'period': 'Date', 'beacon_count': 'Count', 'cs_version': 'Version'}
        )
    else:
        # Aggregate if no version filter
        df_timeline_agg = df_timeline.groupby('period')['beacon_count'].sum().reset_index()
        fig = px.line(
            df_timeline_agg,
            x='period',
            y='beacon_count',
            title=f"Total Beacon Collections Over Time (by {granularity})",
            labels={'period': 'Date', 'beacon_count': 'Count'}
        )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No timeline data available for the given criteria.")

# 2. Activity Log
st.subheader("Activity Log")
df_log = run_query(ACTIVITY_LOG, params)

if not df_log.empty:
    page_df = paginate_dataframe(df_log, page_size=50, key="activity_log_page")
    st.dataframe(page_df, use_container_width=True)
else:
    st.info("No activity logs found.")

# 3. Heatmap
st.subheader("Activity Heatmap (Month vs Day of Week)")
df_heatmap = run_query(ACTIVITY_HEATMAP, params)

if not df_heatmap.empty:
    # Prepare pivot table for heatmap
    pivot = df_heatmap.pivot_table(index='day_of_week', columns='month', values='beacon_count', aggfunc='sum').fillna(0)

    # Map index/columns to names
    days = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
    months = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

    pivot.index = [days.get(i, i) for i in pivot.index]
    pivot.columns = [months.get(c, c) for c in pivot.columns]

    fig = px.imshow(
        pivot,
        labels=dict(x="Month", y="Day of Week", color="Collections"),
        x=pivot.columns,
        y=pivot.index,
        color_continuous_scale="Viridis",
        aspect="auto"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No heatmap data available.")

# 4. New Infrastructure
st.subheader(f"New Infrastructure Detection (by {granularity})")

df_new_ips = run_query(ACTIVITY_NEW_INFRA_IPS, params)
df_new_domains = run_query(ACTIVITY_NEW_INFRA_DOMAINS, params)
df_new_versions = run_query(ACTIVITY_NEW_INFRA_VERSIONS, params)

if not df_new_ips.empty or not df_new_domains.empty or not df_new_versions.empty:
    df_merged = df_new_ips if not df_new_ips.empty else pd.DataFrame(columns=['period', 'new_ips'])

    if not df_new_domains.empty:
        df_merged = df_merged.merge(df_new_domains, on='period', how='outer')
    else:
        df_merged['new_domains'] = 0

    if not df_new_versions.empty:
        df_merged = df_merged.merge(df_new_versions, on='period', how='outer')
    else:
        df_merged['new_versions'] = 0

    df_merged = df_merged.fillna(0).sort_values('period')

    # Format period
    if granularity == "month":
        df_merged['period'] = df_merged['period'].dt.strftime('%Y-%m')
    elif granularity == "quarter":
         df_merged['period'] = df_merged['period'].dt.to_period('Q').astype(str)

    # Display table
    st.dataframe(df_merged.rename(columns={'period': 'Period', 'new_ips': 'New IPs', 'new_domains': 'New Domains', 'new_versions': 'New CS Versions'}), use_container_width=True)
else:
    st.info("No new infrastructure detection data available.")
