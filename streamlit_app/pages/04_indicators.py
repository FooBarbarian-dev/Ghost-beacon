import streamlit as st
import plotly.express as px
from lib.db import run_query
from lib.queries import (
    TLS_CERTIFICATE_USAGE,
    TOP_TLS_SUBJECTS,
    XOR_ENCODING_OVER_TIME,
    FILESIZE_DISTRIBUTION_RAW,
    FILESIZE_BY_VERSION
)

st.title("🔍 Indicator Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("TLS Certificate Usage")
    df_tls = run_query(TLS_CERTIFICATE_USAGE)
    if not df_tls.empty:
        fig_tls = px.pie(df_tls, values='count', names='tls_status', hole=0.3)
        st.plotly_chart(fig_tls, use_container_width=True)
    else:
        st.info("No TLS data available.")

with col2:
    st.subheader("Top Custom TLS Subjects")
    df_tls_subs = run_query(TOP_TLS_SUBJECTS)
    if not df_tls_subs.empty:
        st.dataframe(df_tls_subs, use_container_width=True, hide_index=True)
    else:
        st.info("No TLS subject data available.")

st.divider()

st.subheader("XOR Encoding Over Time")
df_xor = run_query(XOR_ENCODING_OVER_TIME)
if not df_xor.empty:
    df_xor['xor_encoded'] = df_xor['xor_encoded'].map({1: 'Encoded', 0: 'Not Encoded', None: 'Unknown'})
    fig_xor = px.bar(
        df_xor,
        x='quarter',
        y='count',
        color='xor_encoded',
        labels={'quarter': 'Quarter', 'count': 'Beacon Count', 'xor_encoded': 'Status'}
    )
    st.plotly_chart(fig_xor, use_container_width=True)
else:
    st.info("No XOR encoding data available.")

st.divider()

st.subheader("Filesize Distribution")
df_size_raw = run_query(FILESIZE_DISTRIBUTION_RAW)
if not df_size_raw.empty:
    fig_hist = px.histogram(
        df_size_raw,
        x="filesize",
        nbins=50,
        labels={'filesize': 'Payload Size (Bytes)'}
    )
    st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.info("No filesize data available.")

st.subheader("Filesize by Version (Top 10)")
df_size_v = run_query(FILESIZE_BY_VERSION)
if not df_size_v.empty:
    fig_box = px.box(
        df_size_v,
        x='filesize',
        y='tool',
        labels={'filesize': 'Payload Size (Bytes)', 'tool': 'CS Version'}
    )
    fig_box.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_box, use_container_width=True)
else:
    st.info("No filesize by version data available.")
