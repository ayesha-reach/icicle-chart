import streamlit as st
from upstream_icicle_chart import render_upstream_chart_page
from hop_level_customers import render_hop_level_page

st.set_page_config(page_title="Reach Partner View (Beta)", layout="wide")
st.title("Reach Partner View (Beta)")

tab1, tab2 = st.tabs(["🔁 Partner Flow", "📊 Hop-Level Analysis"])

with tab1:
    render_upstream_chart_page()

with tab2:
    render_hop_level_page()
