import streamlit as st
import plotly.express as px
from lib.db import run_query
from lib.queries import OVERVIEW_METRICS, BEACON_COLLECTION_TIMELINE

st.title("📊 Overview")

# Metrics
df_metrics = run_query(OVERVIEW_METRICS)
if not df_metrics.empty and df_metrics.iloc[0]['total_beacons'] > 0:
    metrics = df_metrics.iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Beacons", f"{metrics['total_beacons']:,}")
    col2.metric("Unique IPs", f"{metrics['unique_ips']:,}")
    col3.metric("Unique CS Versions", f"{metrics['unique_versions']:,}")

    date_range = f"{metrics['min_date'].strftime('%Y-%m') if metrics['min_date'] else 'N/A'} → {metrics['max_date'].strftime('%Y-%m') if metrics['max_date'] else 'N/A'}"
    col4.metric("Date Range", date_range)

    st.divider()

    # Timeline Chart
    st.subheader("Collection Timeline")
    df_timeline = run_query(BEACON_COLLECTION_TIMELINE)
    if not df_timeline.empty:
        fig = px.line(
            df_timeline,
            x='month',
            y='beacon_count',
            labels={'month': 'Month', 'beacon_count': 'Beacons Collected'},
            title='Beacons Collected over Time'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline data available.")
else:
    st.info("No data loaded yet. Run the beacon_loader first.")
