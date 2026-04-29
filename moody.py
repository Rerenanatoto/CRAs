import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
from typing import Dict, Tuple

# ============================================================
# Configuração do Streamlit
# ============================================================

st.set_page_config(page_title="Moody's Rating Methodology", layout="wide")

# ============================================================
# CSS customizado
# ============================================================

st.markdown("""
<style>
    /* ---- Fundo off-white quente ---- */
    .stApp {
        background-color: #F0EDE8;
        color: #1a1a1a;
    }

    /* ---- Barra preta do topo — mesma cor da página ---- */
    header[data-testid="stHeader"] {
        background-color: #F0EDE8 !important;
        border-bottom: none !important;
    }
    .stApp > header {
        background-color: #F0EDE8 !important;
    }
    /* Toolbar icons no topo */
    header[data-testid="stHeader"] [data-testid="stToolbar"] {
        background-color: #F0EDE8 !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #E4E0DA;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span {
        color: #1a1a1a !important;
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #1a1a1a !important;
    }

    /* Labels gerais */
    label, .stSelectbox label, .stNumberInput label,
    .stSlider label, .stRadio label, p, span, div {
        color: #1a1a1a !important;
    }

    /* ---- Inputs: fundo BRANCO, letra PRETA ---- */
    /* Number inputs */
    .stNumberInput input,
    .stNumberInput [data-testid="stNumberInput"] input {
        background-color: #FFFFFF !important;
        color: #1a1a1a !important;
        -webkit-text-fill-color: #1a1a1a !important;
    }

    /* Selectbox */
    .stSelectbox [data-testid="stMarkdownContainer"],
    .stSelectbox > div > div,
    .stSelectbox > div > div > div,
    [data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #1a1a1a !important;
    }
    [data-baseweb="select"] * {
        color: #1a1a1a !important;
        -webkit-text-fill-color: #1a1a1a !important;
    }
    [data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
    }

    /* Dropdown menu (lista aberta) */
    [data-baseweb="popover"],
    [data-baseweb="popover"] ul,
    [data-baseweb="popover"] li,
    [data-baseweb="menu"],
    [data-baseweb="menu"] ul,
    [data-baseweb="menu"] li {
        background-color: #FFFFFF !important;
        color: #1a1a1a !important;
    }
    [data-baseweb="menu"] li:hover {
        background-color: #E3F2FD !important;
    }

    /* Slider */
    .stSlider [data-testid="stTickBarMin"],
    .stSlider [data-testid="stTickBarMax"],
    .stSlider [data-baseweb="slider"] div {
        color: #1a1a1a !important;
    }

    /* Number input +/- buttons */
    .stNumberInput button {
        background-color: #FFFFFF !important;
        color: #1a1a1a !important;
        border-color: #ccc !important;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #0D47A1 !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #1a1a1a !important;
    }

    /* Dataframe */
    .stDataFrame {
        border: 1px solid #ccc;
        border-radius: 8px;
    }

    /* Divider */
    hr { border-color: #ccc !important; }

    /* Botões de download */
    .stDownloadButton > button {
        background-color: #0D47A1;
        color: white;
        border: none;
        border-radius: 6px;
    }
    .stDownloadButton > button:hover {
        background-color: #1565C0;
        color: white;
    }

    /* ---- Indicadores vermelho / verde (FUNDO) ---- */
    .field-pending {
        background-color: rgba(229, 57, 53, 0.10);
        padding: 10px 12px 4px 12px;
        margin-bottom: 8px;
        border-radius: 8px;
    }
    .field-done {
        background-color: rgba(67, 160, 71, 0.10);
        padding: 10px 12px 4px 12px;
        margin-bottom: 8px;
        border-radius: 8px;
    }
    .field-legend {
        font-size: 0.78rem;
        margin-bottom: 14px;
    }
    .legend-red  { color: #E53935; font-weight: 600; }
    .legend-green { color: #43A047; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Helper: campo com fundo vermelho/verde
# ============================================================

def _mark(key: str):
    """Callback on_change: marca campo como modificado."""
    st.session_state[f"_mod_{key}"] = True

def render_field_open(key: str):
    modified = st.session_state.get(f"_mod_{key}", False)
    css_class = "field-done" if modified else "field-pending"
    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)

def render_field_close():
    st.markdown('</div>', unsafe_allow_html=True)

def legend():
    st.markdown(
        '<p class="field-legend">'
        '<span class="legend-red">■ Valor padrão (pendente)</span> &nbsp; '
        '<span class="legend-green">■ Modificado ✓</span>'
        '</p>',
        unsafe_allow_html=True
    )


# ============================================================
# Thresholds e Constantes
# ============================================================

GDP_GROWTH_THRESHOLDS = {
    ">4.50": "aaa",
    "4.50-4.40": "aa1", "4.40-3.70": "aa2", "3.70-3.30": "aa3",
    "3.30-3.00": "a1",  "3.00-2.70": "a2",  "2.70-2.40": "a3",
    "2.40-2.10": "baa1", "2.10-1.80": "baa2", "1.80-1.60": "baa3",
    "1.60-1.30": "ba1",  "1.30-1.10": "ba2",  "1.10-0.90": "ba3",
    "0.90-0.70": "b1",   "0.70-0.50": "b2",   "0.50-0.30": "b3",
    "<0.30": "caa"
}

MAD_VOLATILITY_THRESHOLDS = {
    "<0.3": "aaa", "0.3-0.5": "aa", "0.5-0.7": "a",
    "0.7-0.9": "baa", "0.9-1.1": "ba", "1.1-1.3": "b", ">1.3": "caa"
}

SCALE_ECONOMY_THRESHOLDS = {
    ">48,000": "aaa",
    "42,000-48,000": "aa1", "37,000-42,000": "aa2", "32,000-37,000": "aa3",
    "27,500-32,000": "a1",  "24,500-27,500": "a2",  "21,000-24,500": "a3",
    "19,000-21,000": "baa1", "16,000-19,000": "baa2", "14,000-16,000": "baa3",
    "12,000-14,000": "ba1",  "10,750-12,000": "ba2",  "9,500-10,750": "ba3",
    "8,000-9,500": "b1",     "7,000-8,000": "b2",     "6,200-7,000": "b3",
    "<6,200": "caa"
}

RATING_SCALE = [
    "aaa", "aa1", "aa2", "aa3", "a1", "a2", "a3",
    "baa1", "baa2", "baa3", "ba1", "ba2", "ba3",
    "b1", "b2", "b3", "caa1", "caa2", "caa3", "ca", "c"
]

# ============================================================
# Funções auxiliares
# ============================================================

def find_rating_from_value(value: float, thresholds_ranges: Dict) -> str:
    for range_key, rating in thresholds_ranges.items():
        if "-" in range_key:
            parts = range_key.split("-")
            min_val = float(parts[0].replace(",", ""))
            max_val = float(parts[1].replace(",", ""))
            if min_val <= value < max_val:
                return rating
        elif ">" in range_key:
            min_val = float(range_key.replace(">", "").replace(",", ""))
            if value > min_val:
                return rating
        elif "<" in range_key:
            max_val = float(range_key.replace("<", "").replace(",", ""))
            if value < max_val:
                return rating
    return "b3"

def rating_to_numeric(rating: str) -> float:
    r = rating.lower()
    BASE_TO_MID = {
        "aa": "aa2", "a": "a2", "baa": "baa2",
        "ba": "ba2", "b": "b2", "caa": "caa2"
    }
    r = BASE_TO_MID.get(r, r)
    return float(RATING_SCALE.index(r))

def numeric_to_rating(numeric_val: float) -> str:
    idx = int(round(numeric_val))
    idx = max(0, min(len(RATING_SCALE) - 1, idx))
    return RATING_SCALE[idx]

def get_wgi_score_category(wgi_score: float) -> str:
    if wgi_score > 1.5:    return "aaa"
    elif wgi_score > 1.0:  return "aa"
    elif wgi_score > 0.5:  return "a"
    elif wgi_score > 0.0:  return "baa"
    elif wgi_score > -0.5: return "ba"
    elif wgi_score > -1.0: return "b"
    elif wgi_score > -1.5: return "caa"
    else:                  return "ca"

# ============================================================
# Funções de cálculo
# ============================================================

def calculate_economic_strength(gdp_growth, mad_volatility, gdp_per_capita_ppp, nominal_gdp_bn):
    scores = {}
    scores['growth'] = find_rating_from_value(gdp_growth, GDP_GROWTH_THRESHOLDS)
    scores['volatility'] = find_rating_from_value(mad_volatility, MAD_VOLATILITY_THRESHOLDS)
    scores['scale'] = find_rating_from_value(gdp_per_capita_ppp, SCALE_ECONOMY_THRESHOLDS)
    g = rating_to_numeric(scores['growth'])
    v = rating_to_numeric(scores['volatility'])
    s = rating_to_numeric(scores['scale'])
    avg = g * 0.30 + v * 0.35 + s * 0.35
    return numeric_to_rating(avg), scores

def calculate_institutions_governance(wgi_ge, wgi_rq, wgi_va, data_quality):
    scores = {}
    wgi_avg = (wgi_ge + wgi_rq) / 2
    scores['legislative'] = get_wgi_score_category(wgi_avg)
    if wgi_va > 1.0:    scores['judiciary'] = "aa"
    elif wgi_va > 0.0:  scores['judiciary'] = "a"
    else:                scores['judiciary'] = "baa"
    if data_quality >= 8:   scores['transparency'] = "aa"
    elif data_quality >= 6: scores['transparency'] = "a"
    else:                   scores['transparency'] = "baa"
    l = rating_to_numeric(scores['legislative'])
    j = rating_to_numeric(scores['judiciary'])
    t = rating_to_numeric(scores['transparency'])
    avg = l * 0.30 + j * 0.30 + t * 0.40
    return numeric_to_rating(avg), scores

def calculate_fiscal_strength(primary_balance_gdp, debt_gdp, interest_burden, revenue_gdp):
    scores = {}
    if primary_balance_gdp > 5:    scores['performance'] = "aaa"
    elif primary_balance_gdp > 2:  scores['performance'] = "aa"
    elif primary_balance_gdp > 0:  scores['performance'] = "a"
    elif primary_balance_gdp > -3: scores['performance'] = "baa"
    elif primary_balance_gdp > -6: scores['performance'] = "ba"
    else:                          scores['performance'] = "b"
    if debt_gdp < 30:   scores['burden'] = "aaa"
    elif debt_gdp < 50: scores['burden'] = "aa"
    elif debt_gdp < 70: scores['burden'] = "a"
    elif debt_gdp < 90: scores['burden'] = "baa"
    else:                scores['burden'] = "ba"
    if revenue_gdp > 25:   scores['flexibility'] = "aa"
    elif revenue_gdp > 20: scores['flexibility'] = "a"
    else:                   scores['flexibility'] = "baa"
    p = rating_to_numeric(scores['performance'])
    b = rating_to_numeric(scores['burden'])
    f = rating_to_numeric(scores['flexibility'])
    avg = p * 0.40 + b * 0.40 + f * 0.20
    return numeric_to_rating(avg), scores

def calculate_event_risk(ext, pol, bank, liq):
    risk_levels = {"low": 0, "moderate": 1, "high": 2}
    risks = {
        "external_vulnerability": risk_levels.get(ext, 0),
        "political_risk": risk_levels.get(pol, 0),
        "banking_sector_risk": risk_levels.get(bank, 0),
        "liquidity_risk": risk_levels.get(liq, 0),
    }
    level = max(risks.values())
    if level == 0:   return "Low", risks
    elif level == 1: return "Moderate", risks
    else:            return "High", risks

# ============================================================
# Título
# ============================================================

st.title("\U0001F4CA Moody's Sovereign Rating Methodology")

# ============================================================
# Seleção suspensa (dropdown) — sem label visível
# ============================================================

page = st.selectbox(
    "Selecione a seção",
    [
        "Economic Strength",
        "Institutions & Governance",
        "Fiscal Strength",
        "Event Risk",
        "Results",
        "Summary",
        "Methodology"
    ],
    key="nav_page",
    label_visibility="collapsed"
)

# ============================================================
# SEÇÃO: Economic Strength
# ============================================================
if page == "Economic Strength":
    st.header("Economic Strength Assessment")
    legend()

    col1, col2, col3 = st.columns(3)

    with col1:
        render_field_open("gdp_growth")
        gdp_growth = st.number_input(
            "Average Real GDP Growth (%)",
            value=2.5, step=0.1,
            key="gdp_growth",
            on_change=_mark, args=("gdp_growth",),
            help="Crescimento médio real do PIB em 10 anos"
        )
        render_field_close()

    with col2:
        render_field_open("mad_vol")
        mad_volatility = st.number_input(
            "MAD Volatility in Real GDP Growth (%)",
            value=0.8, step=0.1,
            key="mad_vol",
            on_change=_mark, args=("mad_vol",),
            help="Desvio Absoluto Mediano da volatilidade do PIB"
        )
        render_field_close()

    with col3:
        render_field_open("gdp_pc")
        gdp_per_capita_ppp = st.number_input(
            "GDP per Capita (PPP, USD)",
            value=25000.0, step=1000.0,
            key="gdp_pc",
            on_change=_mark, args=("gdp_pc",),
            help="PIB per capita em paridade de poder de compra"
        )
        render_field_close()

    render_field_open("nom_gdp")
    nominal_gdp = st.number_input(
        "Nominal GDP (US$ Billions)",
        value=1500.0, step=100.0,
        key="nom_gdp",
        on_change=_mark, args=("nom_gdp",),
        help="PIB nominal em bilhões USD"
    )
    render_field_close()

    econ_score, econ_details = calculate_economic_strength(
        gdp_growth, mad_volatility, gdp_per_capita_ppp, nominal_gdp
    )

    st.divider()
    st.subheader("Sub-factor Scores")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Growth Dynamics", econ_details['growth'].upper())
    c2.metric("Volatility", econ_details['volatility'].upper())
    c3.metric("Scale of Economy", econ_details['scale'].upper())
    c4.metric("**Economic Strength**", econ_score.upper())
    st.session_state['econ_score'] = econ_score

# ============================================================
# SEÇÃO: Institutions & Governance
# ============================================================
elif page == "Institutions & Governance":
    st.header("Institutions and Governance Strength Assessment")
    legend()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Worldwide Governance Indicators (WGI)")

        render_field_open("wgi_ge")
        wgi_govt_effectiveness = st.slider(
            "Government Effectiveness",
            min_value=-2.5, max_value=2.5, value=0.5, step=0.1,
            key="wgi_ge",
            on_change=_mark, args=("wgi_ge",),
            help="Range: -2.5 (weak) to 2.5 (strong)"
        )
        render_field_close()

        render_field_open("wgi_rq")
        wgi_regulatory_quality = st.slider(
            "Regulatory Quality",
            min_value=-2.5, max_value=2.5, value=0.5, step=0.1,
            key="wgi_rq",
            on_change=_mark, args=("wgi_rq",),
            help="Range: -2.5 (weak) to 2.5 (strong)"
        )
        render_field_close()

        render_field_open("wgi_va")
        wgi_voice_accountability = st.slider(
            "Voice & Accountability",
            min_value=-2.5, max_value=2.5, value=0.3, step=0.1,
            key="wgi_va",
            on_change=_mark, args=("wgi_va",),
            help="Range: -2.5 (weak) to 2.5 (strong)"
        )
        render_field_close()

    with col2:
        st.subheader("Other Governance Factors")

        render_field_open("data_q")
        data_quality = st.slider(
            "Data Quality & Transparency (1-10)",
            min_value=1, max_value=10, value=7,
            key="data_q",
            on_change=_mark, args=("data_q",),
            help="Qualidade e transparência dos dados publicados"
        )
        render_field_close()

    inst_score, inst_details = calculate_institutions_governance(
        wgi_govt_effectiveness, wgi_regulatory_quality, wgi_voice_accountability, data_quality
    )

    st.divider()
    st.subheader("Sub-factor Scores")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Legislative/Executive", inst_details['legislative'].upper())
    c2.metric("Judiciary", inst_details['judiciary'].upper())
    c3.metric("Transparency", inst_details['transparency'].upper())
    c4.metric("**Institutions**", inst_score.upper())
    st.session_state['inst_score'] = inst_score

# ============================================================
# SEÇÃO: Fiscal Strength
# ============================================================
elif page == "Fiscal Strength":
    st.header("Fiscal Strength Assessment")
    legend()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Fiscal Performance")

        render_field_open("prim_bal")
        primary_balance = st.number_input(
            "Primary Balance (% of GDP)",
            value=0.5, step=0.1,
            key="prim_bal",
            on_change=_mark, args=("prim_bal",),
            help="Superávit/déficit primário em % do PIB"
        )
        render_field_close()

        render_field_open("debt_gdp")
        debt_gdp = st.number_input(
            "General Government Debt (% of GDP)",
            value=65.0, step=1.0,
            key="debt_gdp",
            on_change=_mark, args=("debt_gdp",),
            help="Dívida bruta em % do PIB"
        )
        render_field_close()

    with col2:
        st.subheader("Fiscal Flexibility")

        render_field_open("int_bur")
        interest_burden = st.number_input(
            "Interest Burden (% of revenues)",
            value=8.0, step=0.1,
            key="int_bur",
            on_change=_mark, args=("int_bur",),
            help="Despesa com juros em % das receitas"
        )
        render_field_close()

        render_field_open("rev_gdp")
        revenue_gdp = st.number_input(
            "Government Revenue (% of GDP)",
            value=22.0, step=0.1,
            key="rev_gdp",
            on_change=_mark, args=("rev_gdp",),
            help="Receita do governo em % do PIB"
        )
        render_field_close()

    fiscal_score, fiscal_details = calculate_fiscal_strength(
        primary_balance, debt_gdp, interest_burden, revenue_gdp
    )

    st.divider()
    st.subheader("Sub-factor Scores")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Performance", fiscal_details['performance'].upper())
    c2.metric("Burden", fiscal_details['burden'].upper())
    c3.metric("Flexibility", fiscal_details['flexibility'].upper())
    c4.metric("**Fiscal Strength**", fiscal_score.upper())
    st.session_state['fiscal_score'] = fiscal_score

# ============================================================
# SEÇÃO: Event Risk
# ============================================================
elif page == "Event Risk":
    st.header("Susceptibility to Event Risk")
    legend()

    col1, col2 = st.columns(2)

    with col1:
        render_field_open("ext_vuln")
        external_vuln = st.selectbox(
            "External Vulnerability Risk",
            ["Low", "Moderate", "High"],
            key="ext_vuln",
            on_change=_mark, args=("ext_vuln",),
            help="Risco de vulnerabilidade externa"
        )
        render_field_close()

        render_field_open("bank_risk")
        banking_risk = st.selectbox(
            "Banking Sector Risk",
            ["Low", "Moderate", "High"],
            key="bank_risk",
            on_change=_mark, args=("bank_risk",),
            help="Risco do setor bancário"
        )
        render_field_close()

    with col2:
        render_field_open("pol_risk")
        political_risk = st.selectbox(
            "Political Risk",
            ["Low", "Moderate", "High"],
            key="pol_risk",
            on_change=_mark, args=("pol_risk",),
            help="Risco político"
        )
        render_field_close()

        render_field_open("liq_risk")
        liquidity_risk = st.selectbox(
            "Government Liquidity Risk",
            ["Low", "Moderate", "High"],
            key="liq_risk",
            on_change=_mark, args=("liq_risk",),
            help="Risco de liquidez do governo"
        )
        render_field_close()

    event_risk, event_details = calculate_event_risk(
        external_vuln.lower(), political_risk.lower(),
        banking_risk.lower(), liquidity_risk.lower()
    )

    st.divider()
    st.subheader("Risk Assessment")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("External Vulnerability", external_vuln)
    c2.metric("Political Risk", political_risk)
    c3.metric("Banking Sector Risk", banking_risk)
    c4.metric("Liquidity Risk", liquidity_risk)
    st.divider()
    st.metric("Overall Event Risk", event_risk)
    st.session_state['event_risk'] = event_risk

# ============================================================
# SEÇÃO: Results
# ============================================================
elif page == "Results":
    st.header("Rating Results")

    econ = st.session_state.get('econ_score', 'baa1')
    inst = st.session_state.get('inst_score', 'baa1')
    fiscal = st.session_state.get('fiscal_score', 'baa1')
    event = st.session_state.get('event_risk', 'Moderate')

    econ_numeric = rating_to_numeric(econ)
    inst_numeric = rating_to_numeric(inst)
    fiscal_numeric = rating_to_numeric(fiscal)

    economic_resiliency = numeric_to_rating((econ_numeric + inst_numeric) / 2)

    gfs_numeric = (econ_numeric + inst_numeric) / 2
    gfs = numeric_to_rating(gfs_numeric * 0.6 + fiscal_numeric * 0.4)

    if event == "High":      event_notch = -2
    elif event == "Moderate": event_notch = -1
    else:                     event_notch = 0

    gfs_numeric_final = rating_to_numeric(gfs)
    indicative_numeric = gfs_numeric_final + event_notch
    indicative_rating = numeric_to_rating(max(0, min(len(RATING_SCALE)-1, indicative_numeric)))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Economic Strength", econ.upper())
    c2.metric("Institutions", inst.upper())
    c3.metric("Fiscal Strength", fiscal.upper())
    c4.metric("Event Risk", event)

    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Economic Resiliency", economic_resiliency.upper())
    c2.metric("Government Financial Strength", gfs.upper())

    st.divider()
    st.metric("Scorecard-Indicated Rating", indicative_rating.upper(),
              help=f"Baseado em GFS ({gfs.upper()}) + Event Risk adjustment ({event_notch:+d})")

    # Radar chart
    st.subheader("Rating Profile Radar")
    factors = ['Economic', 'Institutional', 'Fiscal']
    values = [econ_numeric, inst_numeric, fiscal_numeric]

    fig = go.Figure(data=go.Scatterpolar(
        r=values, theta=factors, fill='toself',
        name='Scores', line=dict(color='#0D47A1')
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 20]), bgcolor='#FAF9F7'),
        showlegend=True,
        title="Rating Factor Profiles (lower is better)",
        height=500,
        paper_bgcolor='#FAF9F7',
        plot_bgcolor='#FAF9F7',
        font=dict(color='#1a1a1a')
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# SEÇÃO: Summary
# ============================================================
elif page == "Summary":
    st.header("Summary & Export")

    econ = st.session_state.get('econ_score', 'baa1')
    inst = st.session_state.get('inst_score', 'baa1')
    fiscal = st.session_state.get('fiscal_score', 'baa1')
    event = st.session_state.get('event_risk', 'Moderate')

    econ_numeric = rating_to_numeric(econ)
    inst_numeric = rating_to_numeric(inst)
    fiscal_numeric = rating_to_numeric(fiscal)

    economic_resiliency = numeric_to_rating((econ_numeric + inst_numeric) / 2)
    gfs_numeric = (econ_numeric + inst_numeric) / 2 * 0.6 + fiscal_numeric * 0.4
    gfs = numeric_to_rating(gfs_numeric)

    if event == "High":      event_notch = -2
    elif event == "Moderate": event_notch = -1
    else:                     event_notch = 0

    indicative_numeric = rating_to_numeric(gfs) + event_notch
    indicative_rating = numeric_to_rating(max(0, min(len(RATING_SCALE)-1, indicative_numeric)))

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Rating Summary")
        summary_data = {
            "Factor": ["Economic Strength", "Institutions & Governance", "Fiscal Strength", "Event Risk"],
            "Score": [econ.upper(), inst.upper(), fiscal.upper(), event],
            "Status": ["\u2713", "\u2713", "\u2713", "\u2713"]
        }
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Derived Ratings")
        st.metric("Economic Resiliency", economic_resiliency.upper())
        st.metric("Gov't Financial Strength", gfs.upper())
        st.metric("**Final Rating**", indicative_rating.upper(),
                  delta=f"{event_notch:+d} notch", delta_color="off")

    st.divider()
    st.subheader("Export Analysis")

    export_data = {
        "Timestamp": pd.Timestamp.now().isoformat(),
        "Economic_Strength": econ,
        "Institutions_Governance": inst,
        "Fiscal_Strength": fiscal,
        "Event_Risk": event,
        "Economic_Resiliency": economic_resiliency,
        "Government_Financial_Strength": gfs,
        "Indicative_Rating": indicative_rating,
        "Event_Risk_Adjustment": event_notch
    }

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label="\U0001F4E5 Download as JSON",
            data=json.dumps(export_data, indent=2),
            file_name="moody_rating_analysis.json",
            mime="application/json"
        )
    with c2:
        st.download_button(
            label="\U0001F4E5 Download as CSV",
            data=pd.DataFrame([export_data]).to_csv(index=False),
            file_name="moody_rating_analysis.csv",
            mime="text/csv"
        )

    st.divider()
    st.subheader("Comparison with Rating Categories")
    comparison_data = {
        "Rating": ["AAA", "AA", "A", "BAA", "BA", "B", "CAA"],
        "Category": ["Aaa/Aa1/Aa2/Aa3", "A1/A2/A3", "Baa1/Baa2/Baa3",
                      "Ba1/Ba2/Ba3", "B1/B2/B3", "Caa1/Caa2/Caa3", "Ca/C"],
        "Meaning": [
            "Highest creditworthiness", "High creditworthiness",
            "Upper-medium creditworthiness", "Medium creditworthiness",
            "Speculative", "Highly speculative", "Minimal or in default"
        ]
    }
    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

# ============================================================
# SEÇÃO: Methodology
# ============================================================
elif page == "Methodology":
    st.header("Moody's Sovereign Rating Methodology")

    st.markdown("""
    ### Overview

    Moody's sovereign rating methodology evaluates credit risk of governments globally
    through a comprehensive scorecard approach.

    ### Key Components

    #### 1. **Economic Strength** (30%)
    - **Growth Dynamics**: Average real GDP growth (weighted 30%)
    - **Volatility**: Median absolute deviation of real GDP growth (weighted 35%)
    - **Scale of Economy**: GDP per capita in PPP terms (weighted 35%)

    #### 2. **Institutions and Governance Strength** (30%)
    - **Quality of Legislative/Executive Institutions** (30%): Based on WGI indicators
    - **Quality of Judiciary** (30%): Based on voice and accountability
    - **Data Quality & Transparency** (40%): Quality of economic and fiscal data

    #### 3. **Fiscal Strength** (40%)
    - **Fiscal Performance**: Primary balance as % of GDP
    - **Fiscal Burden**: Debt and interest metrics
    - **Fiscal Flexibility**: Revenue generation capacity

    #### 4. **Susceptibility to Event Risk**
    - **External Vulnerability Risk**
    - **Political Risk**
    - **Banking Sector Risk**
    - **Government Liquidity Risk**

    ### Rating Scale
    """)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Investment Grade:**")
        for i, rating in enumerate(RATING_SCALE[:13]):
            if i % 3 == 0:
                st.write(f"- {rating.upper()}")
    with c2:
        st.markdown("**Sub-Investment Grade:**")
        for rating in RATING_SCALE[13:19]:
            st.write(f"- {rating.upper()}")
    with c3:
        st.markdown("**Speculative:**")
        for rating in RATING_SCALE[19:]:
            st.write(f"- {rating.upper()}")

    st.divider()
    st.markdown("""
    ### Calculation Framework

    1. **Economic Resiliency** = Average of Economic Strength and Institutions/Governance
    2. **Government Financial Strength** = Weighted combination of Economic Resiliency (60%)
       and Fiscal Strength (40%)
    3. **Scorecard-Indicated Rating** = GFS adjusted for Event Risk

    ### Notes

    - The scorecard provides a range of three notches, not a precise rating
    - Analysts may apply judgment adjustments based on specific circumstances
    - This is a simplified simulation for educational purposes
    """)
