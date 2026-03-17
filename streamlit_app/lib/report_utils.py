import streamlit as st
import pandas as pd

def render_report_header(
    title: str,
    cs_report_name: str,
    disclaimer: str,
    date_range: tuple[str, str] | None = None,
    scope_description: str | None = None,
) -> None:
    """Render a standardized report header with disclaimer."""
    st.title(f"📋 {title}")
    st.caption(f"Approximation of the Cobalt Strike {cs_report_name}")

    if date_range:
        st.markdown(f"**Date Range:** {date_range[0]} — {date_range[1]}")
    if scope_description:
        st.markdown(f"**Scope:** {scope_description}")

    with st.expander("⚠️ About this report", expanded=False):
        st.warning(disclaimer)

    st.divider()

def csv_download_button(df: pd.DataFrame, filename: str, label: str = "Download CSV") -> None:
    """Render a download button for a DataFrame as CSV."""
    csv = df.to_csv(index=False)
    st.download_button(label=label, data=csv, file_name=filename, mime="text/csv")

def paginate_dataframe(
    df: pd.DataFrame,
    page_size: int = 50,
    key: str = "page",
) -> pd.DataFrame:
    """Paginate a DataFrame with st.number_input for page selection. Returns the current page slice."""
    if df.empty:
        return df

    total_pages = max(1, (len(df) + page_size - 1) // page_size)
    page = st.number_input(f"Page (1–{total_pages})", min_value=1, max_value=total_pages, value=1, key=key)
    start = (page - 1) * page_size
    end = start + page_size
    st.caption(f"Showing {start + 1}–{min(end, len(df))} of {len(df)}")
    return df.iloc[start:end]
