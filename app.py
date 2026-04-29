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
    border-bottom: none !important;
}

/* Texto escuro na área principal */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp li, .stApp span, .stApp label,
.stApp td, .stApp th, .stApp div,
.stMarkdown, .stMarkdown * {
    color: #1a1a1a !important;
}

/* Sidebar — fundo azul escuro, texto branco */
section[data-testid="stSidebar"] {
    background-color: #1F3864 !important;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stMarkdown * {
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
    background-color: rgba(255,255,255,0.15) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    border-radius: 8px !important;
}

/* Inputs brancos com texto preto */
input, textarea, .stNumberInput input,
div[data-baseweb="select"] > div,
.stTextInput input {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
}
[data-baseweb="select"] * {
    color: #1a1a1a !important;
    -webkit-text-fill-color: #1a1a1a !important;
}
[data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="popover"] li,
[data-baseweb="menu"], [data-baseweb="menu"] ul, [data-baseweb="menu"] li {
    background-color: #FFFFFF !important;
    color: #1a1a1a !important;
}
[data-baseweb="menu"] li:hover {
    background-color: #E3F2FD !important;
}
.stNumberInput button {
    background-color: #FFFFFF !important;
    color: #1a1a1a !important;
    border-color: #ccc !important;
}

/* Métricas */
[data-testid="stMetricValue"] {
    color: #1F3864 !important;
    font-weight: 700 !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #1a1a1a !important;
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
