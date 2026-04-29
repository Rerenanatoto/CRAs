# ============================================================
# Sovereign Rating Toolkit – Unified entry point
# ============================================================
import streamlit as st

st.set_page_config(page_title="Sovereign Rating Toolkit", layout="wide")

# ── CSS leve ────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"]  {min-width:260px; max-width:320px}
.block-container           {padding-top:1.5rem}
div[data-baseweb="select"] {min-width:220px}
</style>
""", unsafe_allow_html=True)

# ── Seletor de agência ─────────────────────────────────────
agency = st.sidebar.selectbox(
    "Rating agency",
    ["Moody's", "Fitch", "S&P"],
    key="agency_selector",
)

st.sidebar.markdown("---")

if agency == "Moody's":
    from moody import render_moody
    render_moody()
elif agency == "Fitch":
    from fitch import render_fitch
    render_fitch()
else:
    from sp import render_sp
    render_sp()
