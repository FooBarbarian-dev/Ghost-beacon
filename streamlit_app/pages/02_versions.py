import streamlit as st
import plotly.express as px
from lib.db import run_query
from lib.queries import (
    COBALT_STRIKE_VERSION_DISTRIBUTION,
    VERSION_ADOPTION_OVER_TIME,
    VERSION_FILTER_METRICS,
    VERSION_PORTS,
    VERSION_DOMAINS
)

st.title("🛡️ Version Analysis")

df_versions = run_query(COBALT_STRIKE_VERSION_DISTRIBUTION)

if df_versions.empty:
    st.info("No data loaded yet.")
else:
    # Version Distribution
    st.subheader("Top Cobalt Strike Versions")
    fig_dist = px.bar(
        df_versions,
        y='cs_version',
        x='count',
        orientation='h',
        labels={'cs_version': 'CS Version', 'count': 'Beacon Count'}
    )
    fig_dist.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_dist, use_container_width=True)

    # Version Adoption Over Time
    st.subheader("Version Adoption Over Time")
    df_adoption = run_query(VERSION_ADOPTION_OVER_TIME)
    if not df_adoption.empty:
        fig_area = px.area(
            df_adoption,
            x='month',
            y='count',
            color='version_group',
            labels={'month': 'Month', 'count': 'Beacon Count', 'version_group': 'Version'}
        )
        st.plotly_chart(fig_area, use_container_width=True)

    st.divider()

    # Deep Dive
    st.subheader("Version Deep Dive")
    versions_list = df_versions['cs_version'].tolist()
    selected_version = st.selectbox("Select a version to inspect:", versions_list)

    if selected_version:
        df_v_metrics = run_query(VERSION_FILTER_METRICS, params=(selected_version,))
        if not df_v_metrics.empty:
            v_metrics = df_v_metrics.iloc[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Beacons with Version", f"{v_metrics['beacon_count']:,}")
            col2.metric("Team Server IPs Using It", f"{v_metrics['unique_ips']:,}")

            d_range = f"{v_metrics['min_date'].strftime('%Y-%m-%d') if v_metrics['min_date'] else 'N/A'} → {v_metrics['max_date'].strftime('%Y-%m-%d') if v_metrics['max_date'] else 'N/A'}"
            col3.metric("Observed Time Range", d_range)

        col_p, col_d = st.columns(2)
        with col_p:
            st.write("**Top Ports**")
            df_ports = run_query(VERSION_PORTS, params=(selected_version,))
            st.dataframe(df_ports, use_container_width=True, hide_index=True)

        with col_d:
            st.write("**Top Domains**")
            df_domains = run_query(VERSION_DOMAINS, params=(selected_version,))
            st.dataframe(df_domains, use_container_width=True, hide_index=True)
