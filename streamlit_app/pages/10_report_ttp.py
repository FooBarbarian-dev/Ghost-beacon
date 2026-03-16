import streamlit as st
import datetime
import plotly.express as px
from lib.db import run_query
from lib.report_utils import render_report_header
from lib.queries import TTP_INFERENCES, TTP_DOMAIN_FRONTING, TTP_TECHNIQUE_SAMPLES, TTP_TECHNIQUE_TREND

st.set_page_config(layout="wide")

render_report_header(
    title="Tactics, Techniques, and Procedures",
    cs_report_name="Tactics, Techniques, and Procedures Report",
    disclaimer="This report approximates the Cobalt Strike Tactics, Techniques, and Procedures Report. The real report maps *operator actions* to MITRE ATT&CK techniques. This version infers techniques from *beacon configuration metadata only*. We can determine what the beacon was configured to do, not what the operator actually did with it. Inferences are limited and should be treated as potential capabilities, not confirmed activity.",
)

# CDN Patterns
CDN_PATTERNS = [
    "%awsstatic.com", "%cloudfront.net", "%amazonaws.com",
    "%azureedge.net", "%azure.com", "%msedge.net",
    "%googleapis.com", "%google.com", "%gstatic.com",
    "%cloudflare.com", "%fastly.net", "%akamai.net",
    "%edgecastcdn.net", "%stackpathdns.com",
    "%zendesk.com", "%jquery.com", "%bootstrap.com",
    "%tumblr.com", "%instagram.com", "%facebook.com",
]

# Hardcoded Technique Descriptions
TECHNIQUE_DESCRIPTIONS = {
    "T1071.001": ("Adversaries may communicate using application layer protocols associated with web traffic to avoid detection/network filtering by blending in with existing traffic. Commands to the remote system, and often the results of those commands, will be embedded within the protocol traffic between the client and server.", "Analyze network traffic for unusual web requests, non-standard user agents, or unexpected HTTP headers."),
    "T1071.004": ("Adversaries may communicate using the Domain Name System (DNS) application layer protocol to avoid detection/network filtering by blending in with existing traffic. Commands to the remote system, and often the results of those commands, will be embedded within the protocol traffic between the client and server.", "Analyze network traffic for unusual volume of DNS requests, large DNS TXT records, or requests to unknown/suspicious domains."),
    "T1573.002": ("Adversaries may employ a known asymmetric encryption algorithm to conceal command and control traffic rather than relying on any inherent protections provided by a communication protocol. Asymmetric cryptography, also known as public key cryptography, uses a keypair per party: one public that can be freely distributed, and one private.", "Analyze network traffic for unexpected encrypted communication channels, particularly those using self-signed or unusual TLS certificates."),
    "T1090.004": ("Adversaries may take advantage of routing schemes in Content Delivery Networks (CDNs) and other services which host multiple domains to obfuscate the intended destination of HTTPS traffic or traffic tunneled through HTTPS. Domain fronting involves using different domain names in the SNI field of the TLS connection and the Host header of the HTTP request.", "Monitor for mismatches between DNS resolution, SNI, and HTTP Host headers. Analyze traffic to known CDN providers for unusual patterns or volume."),
    "T1036.005": ("Adversaries may match or approximate the name or location of legitimate files or resources when naming/placing them. This is done for the sake of evading defenses and observation. This may be done by placing an executable in a commonly trusted directory or naming it to closely mimic the name of a legitimate, administrative system.", "Monitor for files or domains that have similar names to legitimate ones, but differ in slight ways (e.g., typosquatting) or are located in unusual paths."),
    "T1027": ("Adversaries may attempt to make an executable or file difficult to discover or analyze by encrypting, encoding, or otherwise obfuscating its contents on the system or in transit. This is common behavior that can be used across different platforms and the network to evade defenses.", "Employ antivirus and endpoint detection and response (EDR) solutions to scan for known obfuscation techniques. Monitor for execution of files with unusually high entropy."),
    "T1587.001": ("Adversaries may develop malware and malware components that can be used during targeting. This malware can take many forms, including viruses, trojans, and ransomware. Developing malware allows adversaries to have capabilities tailored to their specific objectives.", "Analyze code and behavior of unknown executables. Utilize threat intelligence feeds to identify known malware families and variants."),
    "T1583.001": ("Adversaries may buy, lease, or rent domains that can be used during targeting. These domains may be used for a variety of purposes, such as command and control (C2) or phishing.", "Monitor for newly registered domains, domains with low reputation, or domains mimicking legitimate organizations. Analyze network traffic for connections to suspicious domains."),
    "T1583.003": ("Adversaries may rent Virtual Private Servers (VPSs) that can be used during targeting. A VPS is a virtual machine sold as a service by an Internet hosting provider. VPSs can be used to host C2 infrastructure, phishing sites, or to obfuscate the origin of attacks.", "Monitor network traffic for connections to known VPS providers, particularly if the communication patterns are suspicious or the VPS is not expected to be communicating with the network."),
    "T1608.001": ("Adversaries may upload, install, or otherwise set up malware on infrastructure they control to be accessible during targeting. This malware may be hosted on a compromised website, a cloud storage service, or a VPS.", "Monitor for unusual file uploads or downloads, particularly to or from unknown or suspicious IP addresses or domains. Implement strict access controls for external-facing services."),
}

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    start_date = st.date_input("Start Date", datetime.date(2018, 1, 1))
with col2:
    end_date = st.date_input("End Date", datetime.date(2023, 1, 1))
with col3:
    confidence = st.selectbox("Minimum Confidence", ["All inferences", "Direct evidence only"])

params = {
    "start_date": start_date,
    "end_date": end_date,
    "cdn_patterns": CDN_PATTERNS,
}

# TTP Inferences
st.subheader("ATT&CK Technique Summary")
df_inferences = run_query(TTP_INFERENCES, params)

if not df_inferences.empty:
    # Filter based on confidence
    if confidence == "Direct evidence only":
        # Remove T1036.005 and T1090.004 which rely on CDN heuristics (though we add 1090.004 separately below)
        pass # The base query doesn't include the CDN ones, we add them manually

    # Manually append Domain Fronting / Masquerading based on CDN check
    df_cdn = run_query(TTP_DOMAIN_FRONTING, params)
    cdn_count = df_cdn['beacon_count'].sum() if not df_cdn.empty else 0

    if cdn_count > 0 and confidence == "All inferences":
        import pandas as pd
        new_rows = pd.DataFrame([
            {'attack_id': 'T1090.004', 'technique': 'Proxy: Domain Fronting', 'tactic': 'Command and Control', 'beacon_count': cdn_count, 'inference_basis': 'Beacons with domains matching known CDN/cloud providers'},
            {'attack_id': 'T1036.005', 'technique': 'Masquerading: Match Legitimate Name or Location', 'tactic': 'Defense Evasion', 'beacon_count': cdn_count, 'inference_basis': 'Beacons with domains impersonating legitimate services'}
        ])
        df_inferences = pd.concat([df_inferences, new_rows], ignore_index=True)

    # Add ATT&CK Links
    df_inferences['attack_id_link'] = df_inferences['attack_id'].apply(lambda x: f"[{x}](https://attack.mitre.org/techniques/{x.split('.')[0]}/)")

    # Calculate Percentage
    total_beacons = df_inferences[df_inferences['attack_id'] == 'T1608.001']['beacon_count'].sum() # Use Stage Capabilities as total since all beacons are staged
    if total_beacons > 0:
        df_inferences['percentage'] = (df_inferences['beacon_count'] / total_beacons * 100).round(2).astype(str) + "%"
    else:
        df_inferences['percentage'] = "N/A"

    display_cols = ['attack_id_link', 'technique', 'tactic', 'beacon_count', 'percentage', 'inference_basis']
    st.markdown(df_inferences[display_cols].to_markdown(index=False))

    # Detailed Expanders
    st.divider()
    st.subheader("Technique Details")

    for _, row in df_inferences.iterrows():
        attack_id = row['attack_id']
        with st.expander(f"{attack_id} - {row['technique']} ({row['beacon_count']} beacons)"):
            desc, mitigation = TECHNIQUE_DESCRIPTIONS.get(attack_id, ("Description not available.", "Guidance not available."))

            st.markdown(f"**Description:** {desc}")
            st.markdown(f"**Detection Guidance:** {mitigation}")

            st.markdown("#### Trend Over Time")
            # For CDN/Masquerading, we don't have a trend query readily available in the same format, so skip or simplify
            if attack_id not in ['T1090.004', 'T1036.005']:
                trend_params = {"start_date": start_date, "end_date": end_date, "attack_id": attack_id}
                df_trend = run_query(TTP_TECHNIQUE_TREND, trend_params)
                if not df_trend.empty:
                    fig = px.bar(df_trend, x='quarter', y='beacon_count', height=200, labels={'quarter': 'Quarter', 'beacon_count': 'Count'})
                    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Trend visualization not available for heuristic inferences.")

            st.markdown("#### Sample Beacons")
            if attack_id not in ['T1090.004', 'T1036.005']:
                sample_params = {"start_date": start_date, "end_date": end_date, "attack_id": attack_id}
                df_samples = run_query(TTP_TECHNIQUE_SAMPLES, sample_params)
                if not df_samples.empty:
                    st.dataframe(df_samples, use_container_width=True)
                else:
                    st.write("No samples available.")
            else:
                if not df_cdn.empty:
                    st.dataframe(df_cdn.head(10), use_container_width=True)
                else:
                    st.write("No samples available.")

    # ATT&CK Matrix Heatmap
    st.divider()
    st.subheader("ATT&CK Matrix (Inferred)")

    if not df_inferences.empty:
        # Create a simplified matrix
        tactics = df_inferences['tactic'].unique()
        matrix_data = []
        for tactic in tactics:
            techs = df_inferences[df_inferences['tactic'] == tactic]
            for _, tech in techs.iterrows():
                matrix_data.append({'Tactic': tactic, 'Technique': f"{tech['attack_id']} {tech['technique']}", 'Count': tech['beacon_count']})

        import pandas as pd
        df_matrix = pd.DataFrame(matrix_data)

        fig = px.treemap(
            df_matrix,
            path=['Tactic', 'Technique'],
            values='Count',
            color='Count',
            color_continuous_scale='Blues',
            title="Inferred ATT&CK Techniques Heatmap"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Note: Empty tactics are omitted as no inference is possible from beacon metadata alone.")

    # Domain Fronting Analysis
    if not df_cdn.empty and confidence == "All inferences":
        st.divider()
        st.subheader("T1090.004: Domain Fronting Analysis")
        st.markdown("The following domains match known CDN or cloud provider patterns and may be used for domain fronting.")
        st.dataframe(df_cdn, use_container_width=True)

else:
    st.info("No technique inferences available for the given criteria.")
