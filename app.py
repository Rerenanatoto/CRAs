import streamlit as st

st.set_page_config(page_title="Sovereign Rating Toolkit", layout="wide")

# ────────────────────────────────────────────────
# CSS unificado
# ────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #F0EDE8; color: #1a1a1a; }

    header[data-testid="stHeader"] { background-color: #F0EDE8 !important; border-bottom: none !important; }
    .stApp > header { background-color: #F0EDE8 !important; }
    header[data-testid="stHeader"] [data-testid="stToolbar"] { background-color: #F0EDE8 !important; }

    section[data-testid="stSidebar"] { background-color: #E4E0Da; }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span { color: #1a1a1a !important; }

    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1a1a1a !important; }

    label, .stSelectbox label, .stNumberInput label,
    .stSlider label, .stRadio label, p, span, div { color: #1a1a1a !important; }

    .stNumberInput input,
    .stNumberInput [data-testid="stNumberInput"] input {
        background-color: #FFFFFF !important; color: #1a1a1a !important;
        -webkit-text-fill-color: #1a1a1a !important;
    }
    .stSelectbox > div > div, .stSelectbox > div > div > div,
    [data-baseweb="select"] { background-color: #FFFFFF !important; color: #1a1a1a !important; }
    [data-baseweb="select"] * { color: #1a1a1a !important; -webkit-text-fill-color: #1a1a1a !important; }
    [data-baseweb="select"] > div { background-color: #FFFFFF !important; }
    [data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="popover"] li,
    [data-baseweb="menu"], [data-baseweb="menu"] ul, [data-baseweb="menu"] li {
        background-color: #FFFFFF !important; color: #1a1a1a !important;
    }
    [data-baseweb="menu"] li:hover { background-color: #E3F2FD !important; }

    .stSlider [data-testid="stTickBarMin"],
    .stSlider [data-testid="stTickBarMax"],
    .stSlider [data-baseweb="slider"] div { color: #1a1a1a !important; }

    .stNumberInput button { background-color: #FFFFFF !important; color: #1a1a1a !important; border-color: #ccc !important; }

    [data-testid="stMetricValue"] { color: #0D47A1 !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; }
    .stDataFrame { border: 1px solid #ccc; border-radius: 8px; }
    hr { border-color: #ccc !important; }

    .stDownloadButton > button { background-color: #0D47A1; color: white; border: none; border-radius: 6px; }
    .stDownloadButton > button:hover { background-color: #1565C0; color: white; }

    .field-pending { background-color: rgba(229,57,53,0.10); padding: 10px 12px 4px 12px; margin-bottom: 8px; border-radius: 8px; }
    .field-done { background-color: rgba(67,160,71,0.10); padding: 10px 12px 4px 12px; margin-bottom: 8px; border-radius: 8px; }
    .field-legend { font-size: 0.78rem; margin-bottom: 14px; }
    .legend-red  { color: #E53935; font-weight: 600; }
    .legend-green { color: #43A047; font-weight: 600; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button { color: #1a1a1a !important; }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] { border-bottom-color: #0D47A1 !important; color: #0D47A1 !important; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# Seleção de agência
# ────────────────────────────────────────────────
st.title("\U0001F4CA Sovereign Rating Toolkit")

agency = st.selectbox(
    "Agência",
    ["Moody's", "Fitch", "S&P"],
    key="agency_select",
    label_visibility="collapsed",
)

st.divider()

# ────────────────────────────────────────────────
# Roteamento
# ────────────────────────────────────────────────
if agency == "Moody's":
    from moody import render_moody
    render_moody()
elif agency == "Fitch":
    from fitch import render_fitch
    render_fitch()
else:
    from sp import render_sp
    render_sp()
