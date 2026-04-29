import streamlit as st

st.set_page_config(page_title="Sovereign Rating App", layout="wide")

# ── CSS: fundo off-white, header escondido, inputs brancos ──
st.markdown("""
<style>
/* Fundo geral */
.stApp, [data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    background-color: #F0EDE8 !important;
}
[data-testid="stHeader"] {
    color: #F0EDE8 !important;
}
/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #1F3864 !important;
}
section[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
    background-color: rgba(255,255,255,0.15) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    border-radius: 8px !important;
}
/* Inputs brancos */
input, textarea, .stNumberInput input,
div[data-baseweb="select"] > div,
.stTextInput input {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}
/* Métricas */
[data-testid="stMetricValue"] {
    color: #1F3864 !important;
    font-weight: 700 !important;
}
/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    border-bottom: 3px solid #1F3864 !important;
    color: #1F3864 !important;
}
/* Botões download */
.stDownloadButton > button {
    background-color: #1F3864 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
}
.stDownloadButton > button:hover {
    background-color: #16304F !important;
}
</style>
""", unsafe_allow_html=True)

# ── sidebar: escolha da agência ──
st.sidebar.title("⚙️ Configurações")
agency = st.sidebar.selectbox(
    "Agência de rating",
    ["Moody's", "Fitch", "S&P"],
    key="agency_select",
)

# ── despacho ──
if agency == "Moody's":
    from moody import render_moody
    render_moody()
elif agency == "Fitch":
    from fitch import render_fitch
    render_fitch()
else:
    from sp import render_sp
    render_sp()
