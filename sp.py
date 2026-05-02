import io
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import zipfile
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"
DATA_DIR = APP_DIR / "data"
META_COLS = ["country_name", "country_code", "lt_fc_rating"]

# ============================================================
# Helpers gerais
# ============================================================

def normalize_label(text: str) -> str:
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def slugify(text: str) -> str:
    text = normalize_label(text).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def coerce_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.replace({
        "N/A": np.nan,
        "N.M.": np.nan,
        "NM": np.nan,
        "None": np.nan,
        "nan": np.nan,
        "": np.nan,
    })
    return pd.to_numeric(s, errors="coerce")


def show_image(path: Path, caption: str | None = None):
    try:
        st.image(str(path), caption=caption, use_container_width=True)
    except TypeError:
        try:
            st.image(str(path), caption=caption, use_column_width=True)
        except TypeError:
            st.image(str(path), caption=caption)


def st_dataframe_compat(df: pd.DataFrame, **kwargs):
    try:
        st.dataframe(df, **kwargs)
    except TypeError:
        st.dataframe(df)


def st_plotly_chart_compat(fig, use_container_width: bool = True):
    try:
        st.plotly_chart(fig, use_container_width=use_container_width)
    except TypeError:
        st.plotly_chart(fig)


def clamp_score(x: float) -> int:
    return int(max(1, min(6, round(x))))


def round_to_half(x: float) -> float:
    y = round(x * 2) / 2
    return max(1.0, min(6.0, y))


def fmt_score(x: float) -> str:
    x = float(x)
    if x.is_integer():
        return f"{int(x)}"
    return f"{x:.1f}"


# ============================================================
# Constantes da metodologia
# ============================================================
GDP_PC_THRESHOLDS = [
    (53600, 1, "Mais que 53.600"),
    (38100, 2, "38.100–53.600"),
    (22600, 3, "22.600–38.100"),
    (7700, 4, "7.700–22.600"),
    (1500, 5, "1.500–7.700"),
    (0, 6, "Abaixo de 1.500"),
]

MEDIAN_GROWTH_BY_INIT = {"1-2": 1.0, "3": 1.7, "4-6": 2.7}

MONETARY_TABLE8A = [
    {"Score": 1, "Exchange-rate regime": "Reserve currency"},
    {"Score": 2, "Exchange-rate regime": "Actively traded or free-floating currency"},
    {"Score": 3, "Exchange-rate regime": "Managed float, crawling peg / crawl-like arrangement, floating with short track record, or intermittent FX intervention"},
    {"Score": 4, "Exchange-rate regime": "Conventional peg or heavy intervention in the foreign exchange market"},
    {"Score": 5, "Exchange-rate regime": "Hard peg (currency board)"},
    {"Score": 6, "Exchange-rate regime": "No local currency (uses another sovereign's currency)"},
]

MONETARY_TABLE8B = {
    1: {
        "monetary_authority_independence": "Strong and long-established track record (more than 10 years) of full independence with clear objectives",
        "monetary_policy_tools_and_effectiveness": "Wide array of monetary instruments",
        "price_stability": "CPI is low and in line with trading partners, leading to stable REER over the economic cycle; broad price stability by other measures",
        "lender_of_last_resort": "Ability to act as lender of last resort for the financial system",
        "local_financial_system_and_capital_markets": "Depository corporation claims on residents in local currency and nonsovereign local-currency bond market capitalization combined exceed 50% of GDP",
    },
    2: {
        "monetary_authority_independence": "Track record of independence",
        "monetary_policy_tools_and_effectiveness": "Market-based monetary instruments",
        "price_stability": "CPI is low and in line with trading partners, leading to fairly stable REER over the economic cycle; broad price stability by other measures",
        "lender_of_last_resort": "Ability to act as lender of last resort for the financial system",
        "local_financial_system_and_capital_markets": "Depository corporation claims on residents in local currency and nonsovereign local-currency bond market capitalization combined exceed 50% of GDP",
    },
    3: {
        "monetary_authority_independence": "Independence, although with a shorter track record or less secure",
        "monetary_policy_tools_and_effectiveness": "Market-based monetary instruments, but heavy reliance on reserve requirements",
        "price_stability": "CPI broadly in line with trading partners over the economic cycle; somewhat volatile REER over the cycle",
        "lender_of_last_resort": "Ability to act as lender of last resort for the financial system",
        "local_financial_system_and_capital_markets": "Depository corporation claims on residents in local currency plus nonsovereign local-currency bond market capitalization and equity market capitalization combined exceed 50% of GDP",
    },
    4: {
        "monetary_authority_independence": "Operational independence, but shorter or less secure than at better assessments",
        "monetary_policy_tools_and_effectiveness": "Market-based monetary instruments, but effectiveness may be untested in a downside scenario",
        "price_stability": "Annual CPI below 10%; somewhat volatile REER over the economic cycle",
        "lender_of_last_resort": "Ability to act as lender of last resort for the financial system",
        "local_financial_system_and_capital_markets": "Depository corporation claims on residents in local currency plus nonsovereign local-currency bond market capitalization and equity market capitalization combined are below 50% of GDP",
    },
    5: {
        "monetary_authority_independence": "Independence is limited by perceived political interference",
        "monetary_policy_tools_and_effectiveness": "Monetary statistics are not viewed as credible",
        "price_stability": "Average CPI typically exceeds 10%; volatile REER over the economic cycle",
        "lender_of_last_resort": "Limited ability to act as lender of last resort for the financial system",
        "local_financial_system_and_capital_markets": "Depository corporation claims on residents in local currency plus nonsovereign local-currency bond market capitalization and equity market capitalization combined are significantly below 50% of GDP",
    },
    6: {
        "monetary_authority_independence": "",
        "monetary_policy_tools_and_effectiveness": "",
        "price_stability": "Average CPI typically exceeds 20%; volatile REER over the economic cycle",
        "lender_of_last_resort": "No ability to act as lender of last resort for the financial system",
        "local_financial_system_and_capital_markets": "Depository corporation claims on residents in local currency plus nonsovereign local-currency bond market capitalization and equity market capitalization combined are significantly below 50% of GDP",
    },
}

MONETARY_TABLE8B_SUMMARY = {
    1: "1 – strongest credibility profile",
    2: "2 – very strong credibility profile",
    3: "3 – strong / intermediate credibility profile",
    4: "4 – adequate but less proven credibility profile",
    5: "5 – weak credibility profile",
    6: "6 – weakest credibility profile",
}

CONTINGENT_TABLE7 = {
    "1-5": {"<=50%": "Limited", "50-100%": "Limited", "100-250%": "Limited", "250-500%": "Limited", ">500%": "Limited/Moderate"},
    "6-7": {"<=50%": "Limited", "50-100%": "Limited", "100-250%": "Limited", "250-500%": "Limited/Moderate", ">500%": "Moderate/High"},
    "8-9": {"<=50%": "Limited", "50-100%": "Limited", "100-250%": "Limited/Moderate", "250-500%": "Moderate/High", ">500%": "High/Very High"},
    "10": {"<=50%": "Limited", "50-100%": "Limited/Moderate", "100-250%": "Moderate/High", "250-500%": "High/Very High", ">500%": "High/Very High"},
}

CONTINGENT_TO_DEBT_ADJ = {
    "Limited": 0,
    "Moderate": 1,
    "High": 2,
    "Very High": 3,
    "Limited/Moderate": None,
    "Moderate/High": None,
    "High/Very High": None,
}

INST_TABLE2 = {
    1: {
        "effectiveness": [
            "Proactive policymaking and a strong track record in managing past economic and financial crisis and delivering economic growth",
            "Ability and willingness to implement reforms to ensure sustainable public finances and economic growth over the long term",
            "Cohesive civil society, as evidenced by high social inclusion, prevalence of civic organizations, degree of social order and capacity of political institutions to respond to societal priorities",
        ],
        "transparency": [
            "Extensive checks and balances between institutions",
            "Unbiased enforcement of contracts and respect for rule of law",
            "Free flow of information throughout society, with open debate of policy decisions",
            "Timely and reliable data and statistical information",
        ],
    },
    2: {
        "effectiveness": [
            "Generally strong, but shorter, track record of policies that deliver sustainable public finances and balanced economic growth consistently over the long term",
            "Weaker ability to implement reforms because of a slow or complex decision-making process",
            "Cohesive civil society, but slightly less in degree than countries we assess '1'",
        ],
        "transparency": [
            "Generally effective checks and balances",
            "Unbiased enforcement of contracts and respect for rule of law",
            "Free flow of information throughout society, with open debate of policy decisions",
            "Timely and reliable data and statistical information",
        ],
    },
    3: {
        "effectiveness": [
            "Generally effective policymaking in recent years, promoting sustainable public finances and balanced economic growth. But policy shifts are possible because of changes in administration or the potential destabilizing influences of underlying socioeconomic or significant long-term fiscal challenges",
            "Cohesive civil society, but less in degree than countries we assess '1' or '2', either because of ethnic, racial, or class tensions or because of higher level of crime",
        ],
        "transparency": [
            "Evolving checks and balances between various institutions",
            "Generally unbiased enforcement of contracts and respect for rule of law",
            "Free flow of information throughout society, but with policy decisions not fully and openly debated",
            "Statistical information that may be less timely than for the higher categories or subject to large revisions",
        ],
    },
    4: {
        "effectiveness": [
            "Policy choices may weaken support for sustainable public finances and balanced economic growth",
            "Reduced predictability of future policy responses because of an uncertain or untested succession process or moderate risk of challenges to political institutions resulting from highly centralized decision-making and parts of the population desiring more political or economic participation",
            "Civil society with ethnic, racial, or class tensions; rising crime rates; and a reduced capacity of political institutions to respond to societal priorities. Low probability, however, of social upheaval",
        ],
        "transparency": [
            "More uncertain checks and balances between institutions, less enforcement of contracts and respect for the rule of law than in above categories",
            "Relatively weak transparency, owing to interference by political institutions in the free dissemination of information, material gaps in data, or reporting delays",
        ],
    },
    5: {
        "effectiveness": [
            "Policy choices likely weaken capability and willingness to maintain sustainable public finances and balanced economic growth, and thus, debt service",
            "High risk of challenges to political institutions, possibly involving domestic conflict, because of demands for more economic or political participation by parts of the population, or significant ethnic or religious challenges to the legitimacy of political institutions",
            "Future policy responses are difficult to predict because of a highly polarized political landscape, highly centralized decision-making or an uncertain or untested succession process",
            "Frayed civil society with difficult ethnic, racial, or class tensions; high crime; and a reduced capacity of political institutions to respond to societal priorities. Rising chance of social upheaval",
        ],
        "transparency": [
            "Unassured enforcement of contracts and respect for rule of law",
            "Impaired transparency, owing to at least one of the following factors: moderate to high levels of perceived corruption, material data gaps, or significant interference by political institutions in the free dissemination of information",
        ],
    },
    6: {
        "effectiveness": [
            "Weak political institutions, resulting in an uncertain policy environment in periods of stress, including diminished capability and willingness to maintain timely debt service",
            "Considerable risk of breakdown between political institutions, including significant risk of domestic conflict",
            "Distressed civil society; sharp ethnic, racial, or class tensions; inability or unwillingness of political institutions to respond to societal priorities; or present danger of social upheaval",
        ],
        "transparency": [
            "Unassured enforcement of contracts and respect for rule of law",
            "Impaired transparency, owing to several of the following factors: frequent and material data revisions or lack or suppression of data and information flows; or high levels of perceived corruption of political institutions",
        ],
    },
}

INST_TABLE2_LABELS = {
    1: "1 – Proactive policymaking / extensive checks & balances",
    2: "2 – Strong track record (shorter) / effective checks & balances",
    3: "3 – Effective policymaking (recent) / evolving checks & balances",
    4: "4 – Reduced predictability / weaker transparency",
    5: "5 – High challenges / impaired transparency",
    6: "6 – Weak institutions / impaired transparency",
}

INDICATIVE_MATRIX_COLS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
INDICATIVE_MATRIX = [
    ["AAA", "AAA", "AAA", "AA+", "AA", "A+", "A", "A-", "BBB+", "BB+", "BB-"],
    ["AAA", "AAA", "AA+", "AA", "AA-", "A", "A-", "BBB+", "BBB", "BB+", "BB-"],
    ["AAA", "AA+", "AA", "AA-", "A", "A-", "BBB+", "BBB", "BB+", "BB", "B+"],
    ["AA+", "AA", "AA-", "A+", "A-", "BBB", "BBB-", "BB+", "BB", "BB-", "B+"],
    ["AA", "AA-", "A+", "A", "BBB+", "BBB-", "BB+", "BB", "BB-", "B+", "B"],
    ["AA-", "A+", "A", "BBB+", "BBB", "BB+", "BB", "BB-", "B+", "B", "B"],
    ["A", "A-", "BBB+", "BBB", "BB+", "BB", "BB-", "B+", "B", "B-", "B-"],
    ["BBB", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B", "B-", "B-"],
    ["BB+", "BB+", "BB", "BB-", "B+", "B", "B", "B-", "B-", "B-", "B-"],
]

RATING_SCALE = [
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-",
    "BB+", "BB", "BB-",
    "B+", "B", "B-",
    "CCC+", "CCC", "CCC-", "CC", "C",
]

# ============================================================
# Lógica metodologia
# ============================================================


# ============================================================
# External Assessment – quantitative helpers (Table 4)
# ============================================================

EXT_LIQUIDITY_THRESHOLDS = [
    # (label, lo_pct, hi_pct)   – ratio = gross_ext_fin_needs / (CAR + usable_reserves)
    ("≤50%",    0,   50),
    ("50–100%", 50, 100),
    ("100–150%",100,150),
    (">150%",   150, 9999),
]

EXT_INDEBTEDNESS_THRESHOLDS = [
    # (label, lo_pct, hi_pct)  – narrow net ext debt / CAR (or CAP if assets > debt)
    ("< −50%",  -9999, -50),
    ("−50–0%",  -50,     0),
    ("0–50%",     0,    50),
    ("50–100%",  50,   100),
    ("100–150%",100,   150),
    ("150–200%",150,   200),
    (">200%",   200,  9999),
]

# Table 4 initial‑assessment grid
# rows = indebtedness bucket (0‑6), cols depend on currency status
# For reserve‑currency sovereigns: single column
# For actively‑traded: single column
# For others: 4 liquidity columns (≤50, 50‑100, 100‑150, >150)
_T4_RESERVE = [1, 1, 1, 2, 2, 3, 3]
_T4_ACTIVE  = [1, 1, 2, 2, 3, 4, 4]
_T4_OTHER   = [
    # ≤50  50-100  100-150  >150
    [1,    1,      1,       2],   # <-50%
    [1,    1,      2,       3],   # -50–0%
    [1,    2,      3,       4],   # 0–50%
    [2,    3,      4,       5],   # 50–100%
    [3,    4,      5,       5],   # 100–150%
    [4,    5,      5,       6],   # 150–200%
    [5,    6,      6,       6],   # >200%
]

def _bucket_idx(value, thresholds):
    """Return the bucket index for *value* given a list of (label, lo, hi) tuples."""
    for i, (_, lo, hi) in enumerate(thresholds):
        if lo <= value < hi:
            return i
    return len(thresholds) - 1

def ext_initial_assessment(currency_status: str,
                           indebtedness_pct: float,
                           liquidity_pct: float = 0.0) -> int:
    """Return initial external assessment 1‑6 per Table 4."""
    row = _bucket_idx(indebtedness_pct, EXT_INDEBTEDNESS_THRESHOLDS)
    if currency_status == "Reserve currency":
        return _T4_RESERVE[row]
    if currency_status == "Actively traded":
        return _T4_ACTIVE[row]
    col = _bucket_idx(liquidity_pct, EXT_LIQUIDITY_THRESHOLDS)
    return _T4_OTHER[row][col]


def fp_bucket_index(fp_profile: float) -> int:
    x = fp_profile
    if x <= 1.7: return 0
    if x <= 2.2: return 1
    if x <= 2.7: return 2
    if x <= 3.2: return 3
    if x <= 3.7: return 4
    if x <= 4.2: return 5
    if x <= 4.7: return 6
    if x <= 5.2: return 7
    return 8


def indicative_from_matrix(ie_profile: float, fp_profile: float) -> str:
    col_val = round_to_half(ie_profile)
    try:
        col = INDICATIVE_MATRIX_COLS.index(col_val)
    except ValueError:
        col = min(range(len(INDICATIVE_MATRIX_COLS)), key=lambda i: abs(INDICATIVE_MATRIX_COLS[i] - col_val))
    row = fp_bucket_index(fp_profile)
    return INDICATIVE_MATRIX[row][col]


def apply_notches(base_rating: str, notch_adj: int, lc_uplift: int = 0) -> str:
    r = (base_rating or "").upper().strip()
    if r not in RATING_SCALE:
        return r
    idx = RATING_SCALE.index(r)
    new_idx = idx - int(notch_adj) - int(lc_uplift)
    new_idx = max(0, min(len(RATING_SCALE) - 1, new_idx))
    return RATING_SCALE[new_idx]


def init_economic_from_gdppc(gdppc_usd: float) -> int:
    for thr, score, _label in GDP_PC_THRESHOLDS:
        if gdppc_usd >= thr:
            return score
    return 6


def pick_growth_bucket(init_score: int) -> str:
    if init_score in (1, 2):
        return "1-2"
    if init_score == 3:
        return "3"
    return "4-6"


def table5_candidates(change_net_debt_gdp: float) -> list[int]:
    x = float(change_net_debt_gdp)
    if x < 0: return [1]
    if x < 1: return [1, 2]
    if x < 2: return [2]
    if x < 3: return [2, 3]
    if x < 4: return [3, 4]
    if x < 5: return [4, 5]
    if x < 6: return [5]
    if x < 7: return [5, 6]
    return [6]


def table5_initial_from_inputs(change_net_debt_gdp: float, overlap_trend: str) -> int:
    candidates = table5_candidates(change_net_debt_gdp)
    if len(candidates) == 1:
        return candidates[0]
    if overlap_trend == "melhorando":
        return min(candidates)
    return max(candidates)


def table6_initial_from_inputs(net_debt_gdp: float, interest_to_rev: float) -> int:
    if net_debt_gdp <= 30: col = 0
    elif net_debt_gdp <= 60: col = 1
    elif net_debt_gdp <= 80: col = 2
    elif net_debt_gdp <= 100: col = 3
    else: col = 4
    if interest_to_rev <= 5: row = 0
    elif interest_to_rev <= 10: row = 1
    elif interest_to_rev <= 15: row = 2
    else: row = 3
    matrix = [
        [1, 2, 3, 4, 5],
        [2, 3, 4, 5, 6],
        [3, 4, 5, 6, 6],
        [4, 5, 6, 6, 6],
    ]
    return matrix[row][col]


def radar(scores: dict):
    cats = list(scores.keys())
    vals = [scores[c] for c in cats]
    cats2 = cats + [cats[0]]
    vals2 = vals + [vals[0]]
    fig = go.Figure(data=[go.Scatterpolar(r=vals2, theta=cats2, fill="toself", name="Scores",
                    line=dict(color="#1F3864"), fillcolor="rgba(31,56,100,0.18)")])
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[6, 1])),
        showlegend=False,
        margin=dict(l=30, r=30, t=30, b=30),
    )
    return fig


def bullets(items):
    return "".join([f"- {x}" for x in items])


def download_payload():
    payload = {
        "institutional": st.session_state.get("institutional", 4),
        "economic": st.session_state.get("economic", 4),
        "external": st.session_state.get("external", 3),
        "fiscal": st.session_state.get("fiscal", 4.0),
        "monetary": st.session_state.get("monetary", 3),
        "profiles": st.session_state.get("profiles", {}),
        "indicative": st.session_state.get("indicative", None),
        "final_rating": st.session_state.get("final_rating", None),
        "notch_adj": st.session_state.get("notch_adj", 0),
        "lc_uplift": st.session_state.get("lc_uplift", 0),
        "notes": st.session_state.get("notes", ""),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

# ============================================================
# SRI -> Excel export
# ============================================================

def _fix_strref_in_zip(buf):
    # 1) numRef->strRef in cat  2) hollow markers (match line color)
    out = io.BytesIO()
    with zipfile.ZipFile(buf, 'r') as zin, \
         zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith('xl/charts/') and item.filename.endswith('.xml'):
                xml = data.decode('utf-8')
                # Fix 1: numRef -> strRef
                def _swap(m):
                    inner = (m.group(1)
                             .replace('<c:numRef>',    '<c:strRef>')
                             .replace('</c:numRef>',   '</c:strRef>')
                             .replace('<c:numCache>',  '<c:strCache>')
                             .replace('</c:numCache>', '</c:strCache>'))
                    return '<c:cat>' + inner + '</c:cat>'
                xml = re.sub(r'<c:cat>(.*?)</c:cat>', _swap, xml, flags=re.DOTALL)
                # Fix 2: hollow markers inheriting line color
                NS_A    = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
                NOFILL  = '<a:noFill ' + NS_A + '/>'
                def _hollow_sppr(m):
                    inner = m.group(1)
                    # remove existing solidFill so border inherits series color
                    inner = re.sub(r'<a:solidFill.*?</a:solidFill>', '', inner, flags=re.DOTALL)
                    if 'noFill' not in inner:
                        inner = NOFILL + inner
                    return '<spPr>' + inner + '</spPr>'
                def _hollow_marker(m):
                    return re.sub(r'<spPr>(.*?)</spPr>', _hollow_sppr,
                                  m.group(0), flags=re.DOTALL)
                xml = re.sub(r'<marker>.*?</marker>', _hollow_marker,
                             xml, flags=re.DOTALL)
                data = xml.encode('utf-8')
            zout.writestr(item, data)
    out.seek(0)
    return out


def _sane_sheet(name, used, ml=28):
    safe = re.sub(r'[/\\?*\[\]:]+', '_', str(name)).strip()[:ml] or 'Sheet'
    base, n = safe, 2
    while safe in used:
        safe = base[:ml-2] + '_' + str(n); n += 1
    return safe


@st.cache_data(show_spinner=False)
def sri_to_excel(df: pd.DataFrame) -> bytes:
    import math
    wb = Workbook()
    wb.remove(wb.active)

    # -- SRI_Dados: styled raw data --
    ws_data  = wb.create_sheet('SRI_Dados')
    hdr_fill = PatternFill('solid', fgColor='1F4E79')
    hdr_font = Font(bold=True, color='FFFFFF')
    thin     = Side(style='thin', color='BFBFBF')
    brd      = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt      = PatternFill('solid', fgColor='D6E4F0')
    cols_export = [c for c in
                   ['sheet', 'country_name', 'country_code', 'lt_fc_rating',
                    'indicator', 'year', 'year_num', 'value', 'is_forecast']
                   if c in df.columns]
    for ci, col in enumerate(cols_export, 1):
        c = ws_data.cell(1, ci, col)
        c.font = hdr_font; c.fill = hdr_fill
        c.alignment = Alignment(horizontal='center', wrap_text=True)
        c.border = brd
    for ri, row in enumerate(df[cols_export].itertuples(index=False), 2):
        fill = alt if ri % 2 == 0 else PatternFill()
        for ci, val in enumerate(row, 1):
            v = val if not (isinstance(val, float) and math.isnan(val)) else None
            c = ws_data.cell(ri, ci, v)
            c.fill = fill; c.border = brd
            c.alignment = Alignment(horizontal='center')
    ws_data.freeze_panes = 'A2'

    # -- Graficos: one LineChart per indicator --
    ws_charts = wb.create_sheet('Graficos')
    used      = list(wb.sheetnames)
    chart_row = 1
    indicators = sorted(df['indicator'].dropna().unique()) if 'indicator' in df.columns else []
    for ind in indicators:
        df_i = (df[df['indicator'] == ind]
                .dropna(subset=['year_num', 'value'])
                .sort_values(['country_name', 'year_num']))
        if df_i.empty:
            continue
        countries = sorted(df_i['country_name'].unique().tolist())
        years     = sorted(df_i['year_num'].unique().tolist())
        n_yr = len(years); n_ct = len(countries)

        # Aux sheet: col A = str years, cols B+ = countries, one row per year
        aux_name = _sane_sheet(ind, used); used.append(aux_name)
        ws = wb.create_sheet(aux_name)
        ws.cell(1, 1, 'Ano')
        for ci, ct in enumerate(countries, 2):
            ws.cell(1, ci, ct)
        for ri, yr in enumerate(years, 2):
            ws.cell(ri, 1, str(int(yr)))  # string -> correct X axis
            for ci, ct in enumerate(countries, 2):
                m = df_i[(df_i['country_name'] == ct) & (df_i['year_num'] == yr)]['value']
                ws.cell(ri, ci, round(float(m.mean()), 4) if not m.empty else None)

        # LineChart: add_data per country column
        lc = LineChart()
        lc.title   = str(ind)[:45]
        lc.style   = 10
        lc.width   = 22
        lc.height  = 14
        lc.smooth  = False

        for ci in range(2, n_ct + 2):
            lc.add_data(Reference(ws, min_col=ci, min_row=1, max_row=n_yr + 1),
                        titles_from_data=True)
        lc.set_categories(Reference(ws, min_col=1, min_row=2, max_row=n_yr + 1))

        # Markers: symbol + size only (no graphicalProperties — corrupts XML)
        for s in lc.series:
            s.marker.symbol = 'circle'
            s.marker.size   = 8

        # X axis: years visible at bottom
        lc.x_axis.axPos          = 'b'
        lc.x_axis.delete         = False
        lc.x_axis.tickLblPos     = 'low'
        lc.x_axis.majorGridlines = None
        lc.x_axis.title          = 'Ano'

        # Y axis: values visible on left
        lc.y_axis.axPos          = 'l'
        lc.y_axis.delete         = False
        lc.y_axis.tickLblPos     = 'nextTo'
        lc.y_axis.numFmt         = 'General'
        lc.y_axis.majorGridlines = None
        lc.y_axis.title          = 'Valor'

        ws_charts.add_chart(lc, 'A' + str(chart_row))
        chart_row += 25

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf = _fix_strref_in_zip(buf)
    return buf.read()

# ============================================================
# Lógica SRI
# ============================================================

def find_local_xlsx() -> Path | None:
    preferred_names = [
        DATA_DIR / "base.xlsx",
        DATA_DIR / "report.xlsx",
        APP_DIR / "base.xlsx",
        APP_DIR / "report.xlsx",
    ]
    for candidate in preferred_names:
        if candidate.exists():
            return candidate
    for search_dir in [DATA_DIR, APP_DIR]:
        if search_dir.exists():
            files = sorted([p for p in search_dir.glob("*.xlsx") if not p.name.startswith("~$")])
            if files:
                return files[0]
    return None


def find_data_end(raw: pd.DataFrame) -> int:
    first_col = raw.iloc[:, 0].astype(str).fillna("").str.strip().str.lower()
    end_idx = len(raw)
    for idx, value in enumerate(first_col):
        if (
            value.startswith("lt fc--")
            or value.startswith("copyright")
            or value.startswith("no content")
            or value.startswith("credit-related")
            or value.startswith("to reprint")
            or value.startswith("any passwords/user ids")
        ):
            end_idx = idx
            break
    return end_idx


def parse_sheet(raw: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    raw = raw.copy().dropna(how="all", axis=1)
    if len(raw) < 6:
        return pd.DataFrame()
    end_idx = find_data_end(raw)
    raw = raw.iloc[:end_idx].reset_index(drop=True)
    if len(raw) < 6:
        return pd.DataFrame()
    indicator_row = raw.iloc[3].tolist()
    year_row = raw.iloc[4].tolist()
    records = []
    current_indicator = None
    for col_idx, cell in enumerate(indicator_row):
        if col_idx < 3:
            continue
        if pd.notna(cell):
            current_indicator = normalize_label(cell)
        year_value = year_row[col_idx] if col_idx < len(year_row) else None
        if current_indicator and pd.notna(year_value):
            records.append({
                "col_idx": col_idx,
                "indicator": current_indicator,
                "indicator_key": slugify(current_indicator),
                "year": str(year_value).strip(),
            })
    if not records:
        return pd.DataFrame()
    col_map = pd.DataFrame(records)
    data = raw.iloc[5:].copy().dropna(how="all")
    if data.empty:
        return pd.DataFrame()
    rename_map = {}
    if 0 in data.columns: rename_map[0] = "country_name"
    if 1 in data.columns: rename_map[1] = "country_code"
    if 2 in data.columns: rename_map[2] = "lt_fc_rating"
    data = data.rename(columns=rename_map)
    required_cols = ["country_name", "country_code", "lt_fc_rating"]
    if not all(col in data.columns for col in required_cols):
        return pd.DataFrame()
    usable_cols = [c for c in col_map["col_idx"].tolist() if c in data.columns]
    if not usable_cols:
        return pd.DataFrame()
    col_map = col_map[col_map["col_idx"].isin(usable_cols)].copy()
    data = data[required_cols + usable_cols].copy()
    data["country_name"] = data["country_name"].astype(str).str.strip()
    data["country_code"] = data["country_code"].astype(str).str.strip()
    data["lt_fc_rating"] = data["lt_fc_rating"].astype(str).str.strip()
    invalid_starts = ("lt fc--", "copyright", "no content")
    data = data[
        data["country_name"].ne("")
        & ~data["country_name"].str.lower().str.startswith(invalid_starts)
    ].copy()
    if data.empty:
        return pd.DataFrame()
    long_df = data.melt(
        id_vars=required_cols,
        value_vars=usable_cols,
        var_name="col_idx",
        value_name="value_raw",
    )
    long_df = long_df.merge(col_map, on="col_idx", how="left")
    long_df["sheet"] = sheet_name
    long_df["sheet_key"] = slugify(sheet_name)
    long_df["value"] = coerce_numeric(long_df["value_raw"])
    long_df["year"] = long_df["year"].astype(str).str.strip()
    long_df["year_num"] = pd.to_numeric(long_df["year"].str.extract(r"(\d{4})")[0], errors="coerce")
    long_df["is_forecast"] = long_df["year"].str.contains(r"[ef]$", case=False, na=False)
    return long_df[[
        "sheet", "sheet_key", "country_name", "country_code", "lt_fc_rating",
        "indicator", "indicator_key", "year", "year_num", "is_forecast", "value"
    ]]


@st.cache_data(show_spinner=False)
def load_workbook(file_bytes=None) -> pd.DataFrame:
    empty = pd.DataFrame(columns=[
        "sheet", "sheet_key", "country_name", "country_code", "lt_fc_rating",
        "indicator", "indicator_key", "year", "year_num", "is_forecast", "value"
    ])
    if file_bytes is not None:
        source = io.BytesIO(file_bytes)
    else:
        local_file = find_local_xlsx()
        if local_file is None:
            return empty
        source = local_file
    xls = pd.ExcelFile(source, engine="openpyxl")
    frames = []
    for sheet in xls.sheet_names:
        raw = pd.read_excel(xls, sheet_name=sheet, header=None, engine="openpyxl")
        try:
            parsed = parse_sheet(raw, sheet)
            if not parsed.empty:
                frames.append(parsed)
        except Exception:
            continue
    if not frames:
        return empty
    df = pd.concat(frames, ignore_index=True)
    return df.dropna(subset=["indicator", "year"])


def build_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("Filtros do SRI")
    all_categories = sorted(df["sheet"].dropna().unique().tolist())
    selected_categories = st.multiselect(
        "Categoria",
        options=all_categories,
        default=all_categories,
        key="f_categories",
        help="Escolha uma ou mais categorias (abas da planilha).",
    )
    df1 = df[df["sheet"].isin(selected_categories)] if selected_categories else df.copy()

    all_ratings = sorted(df1["lt_fc_rating"].dropna().unique().tolist())
    selected_ratings = st.multiselect(
        "LT FC rating",
        options=all_ratings,
        default=[],
        key="f_ratings",
        help="Deixe vazio para considerar todos os ratings.",
    )
    df2 = df1[df1["lt_fc_rating"].isin(selected_ratings)] if selected_ratings else df1.copy()

    all_countries = sorted(df2["country_name"].dropna().unique().tolist())
    selected_countries = st.multiselect(
        "País",
        options=all_countries,
        default=[],
        key="f_countries",
        help="Deixe vazio para considerar todos os países do recorte atual.",
    )

    all_indicators = sorted(df2["indicator"].dropna().unique().tolist())
    selected_indicators = st.multiselect(
        "Indicadores",
        options=all_indicators,
        default=[],
        key="f_indicators",
        help="Deixe vazio para considerar todos os indicadores do recorte atual.",
    )

    valid_years = df2["year_num"].dropna()
    year_min, year_max = (2019, 2028) if valid_years.empty else (int(valid_years.min()), int(valid_years.max()))
    selected_year_range = st.slider(
        "Faixa de anos",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
        key="f_years",
    )

    forecast_mode = st.radio(
        "Período",
        ["Todos", "Somente históricos", "Somente estimativas/projeções"],
        index=0,
        key="f_forecast",
        horizontal=True,
    )

    filtered = df2.copy()
    if selected_countries:
        filtered = filtered[filtered["country_name"].isin(selected_countries)]
    if selected_indicators:
        filtered = filtered[filtered["indicator"].isin(selected_indicators)]
    filtered = filtered[filtered["year_num"].between(selected_year_range[0], selected_year_range[1], inclusive="both")]
    if forecast_mode == "Somente históricos":
        filtered = filtered[~filtered["is_forecast"]]
    elif forecast_mode == "Somente estimativas/projeções":
        filtered = filtered[filtered["is_forecast"]]
    return filtered


def render_dashboard_tab(df: pd.DataFrame):
    st.subheader("Dashboards")
    if df.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Países", df["country_name"].nunique())
    c2.metric("Indicadores", df["indicator"].nunique())
    c3.metric("Observações", f"{len(df):,}".replace(",", "."))

    available_sheets = sorted(df["sheet"].dropna().unique().tolist())
    if not available_sheets:
        st.info("Nenhuma aba disponível para plotagem com os filtros atuais.")
        return

    if len(available_sheets) == 1:
        sheet_for_charts = available_sheets[0]
        st.caption(f"Mostrando todos os indicadores da aba: **{sheet_for_charts}**")
    else:
        sheet_for_charts = st.selectbox(
            "Aba para gerar gráficos (um gráfico por indicador)",
            available_sheets,
            index=0,
            key="sheet_for_charts",
        )

    plot_df = df[df["sheet"] == sheet_for_charts].copy().dropna(subset=["year_num", "value"])
    if plot_df.empty:
        st.info("Sem dados numéricos para gerar gráficos nesta aba com os filtros atuais.")
        return

    indicators = sorted(plot_df["indicator"].dropna().unique().tolist())
    if not indicators:
        st.info("Nenhum indicador encontrado para esta aba.")
        return

    st.markdown(f"### {sheet_for_charts} — gráficos para **{len(indicators)}** indicadores")
    cols_per_row = 2
    show_legend = plot_df["country_name"].nunique() <= 12

    for i in range(0, len(indicators), cols_per_row):
        row_inds = indicators[i : i + cols_per_row]
        row_cols = st.columns(cols_per_row)
        for col, ind in zip(row_cols, row_inds):
            with col:
                ind_df = plot_df[plot_df["indicator"] == ind].sort_values(["country_name", "year_num"])
                if ind_df.empty:
                    st.caption(f"Sem dados para: {ind}")
                    continue
                fig = px.line(
                    ind_df,
                    x="year_num",
                    y="value",
                    color="country_name",
                    markers=True,
                    hover_data=["lt_fc_rating", "year", "country_code"],
                    title=ind,
                )
                fig.update_layout(
                    height=340,
                    margin=dict(l=10, r=10, t=50, b=10),
                    legend_title_text="País",
                    showlegend=show_legend,
                )
                fig.update_xaxes(title="Ano")
                fig.update_yaxes(title="Valor")
                st_plotly_chart_compat(fig, use_container_width=True)

    st.markdown("#### Média por LT FC rating (no recorte atual)")
    rating_summary = (
        df.groupby(["lt_fc_rating", "indicator"], as_index=False)["value"]
        .mean()
        .rename(columns={"value": "media_valor"})
        .sort_values(["indicator", "lt_fc_rating"])
    )
    st_dataframe_compat(rating_summary, use_container_width=True, hide_index=True)


    st.markdown("---")
    st.download_button(
        "⬇️ Baixar Excel (.xlsx com gráficos de linha)",
        data=sri_to_excel(df),
        file_name="sri_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_sri_dash",
    )


def render_table_tab(df: pd.DataFrame):
    st.subheader("Dados em tabela")
    if df.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return
    view_mode = st.radio(
        "Visualização",
        ["Longa (recomendada)", "Pivotada"],
        horizontal=True,
        index=0,
        key="view_mode",
    )

    # FIX: long_df é sempre preservado para exportação Excel (tem year_num e value)
    long_df = df.sort_values(["sheet", "country_name", "indicator", "year_num"]).copy()

    if view_mode == "Longa (recomendada)":
        display_df = long_df
    else:
        display_df = (
            df.pivot_table(
                index=["sheet", "country_name", "country_code", "lt_fc_rating", "indicator"],
                columns="year",
                values="value",
                aggfunc="first",
            )
            .reset_index()
        )
    st_dataframe_compat(display_df, use_container_width=True, hide_index=True)
    csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
    _c1, _c2 = st.columns(2)
    with _c1:
        st.download_button("⬇️ Baixar CSV", data=csv_data,
            file_name="bda_filtrado.csv", mime="text/csv", key="dl_csv_tbl")
    with _c2:
        st.download_button("⬇️ Baixar Excel (.xlsx com gráficos)",
            data=sri_to_excel(long_df),
            file_name="sri_filtrado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_excel_tbl")

# ============================================================
# UI metodologia (agora dentro da 1ª aba)
# ============================================================

def render_methodology_tab():
    st.header("Metodologia")
    method_page = st.selectbox(
        "Seção da metodologia",
        ["Visão geral", "Economic", "Fiscal", "Monetary", "External", "Institutional", "Resultados"],
        key="method_page_select",
        label_visibility="collapsed",
    )
    st.markdown("---")

    if method_page == "Visão geral":
        st.title("📊 S&P Sovereign Rating Methodology – Dashboard")
        st.write(
            "Este dashboard é uma implementação **independente de Excel**, baseada no PDF de critérios. "
            "A metodologia avalia **cinco pilares** (1=mais forte, 6=mais fraco) e combina em dois perfis: "
            "(i) **Institutional & Economic profile** e (ii) **Flexibility & Performance profile**. "
            "A partir disso, consulta-se a matriz de **Indicative Rating Levels** (Tabela 1) e aplica-se julgamento (±1 notch) e eventuais fatores suplementares."
        )
        col1, col2 = st.columns([1, 1], gap="large")
        with col1:
            st.subheader("Estrutura (5 pilares)")
            img = ASSETS_DIR / "page_03_img_01.png"
            if img.exists():
                show_image(img)
            else:
                st.info("Imagem do framework não encontrada em assets/ (opcional).")
        with col2:
            st.subheader("Matriz de Indicative Rating Levels (Tabela 1)")
            img = ASSETS_DIR / "page_06_img_01.png"
            if img.exists():
                show_image(img)
            else:
                st.info("Imagem da matriz não encontrada em assets/ (opcional).")
        st.markdown("---")
        st.subheader("Como usar")
        st.markdown(
            "1) Vá em cada assessment e preencha os inputs."
            "2) Vá em **Resultados** para ver os perfis e um radar com os 5 pilares."
            "3) O app calcula automaticamente o **Indicative rating level** pela Tabela 1, e você aplica notches/uplift."
        )
    elif method_page == "Economic":
        st.title("Economic assessment")
    
        st.markdown("#### 1) Income level (GDP per capita) → score inicial")
        gdppc = st.number_input(
            "GDP per capita (US$) – ano corrente",
            min_value=0.0,
            value=10000.0,
            step=100.0,
            key="eco_gdppc",
        )
    
        init_score = init_economic_from_gdppc(gdppc)
    
        df_thr = pd.DataFrame(
            [
                {"Faixa (US$)": label, "Initial economic assessment": score}
                for _, score, label in GDP_PC_THRESHOLDS
            ]
        )
        st_dataframe_compat(df_thr, use_container_width=True, hide_index=True)
        st.metric("Score inicial (Income level)", init_score)
    
        st.markdown("#### 2) Ajustes (até ±2 categorias no total)")
    
        bucket = pick_growth_bucket(init_score)
        median_growth = MEDIAN_GROWTH_BY_INIT[bucket]
    
        st.caption(
            f"Referência: mediana de crescimento real per capita (10 anos) para init={bucket}: {median_growth:.1f}%"
        )
    
        trend = st.number_input(
            "Real GDP per capita trend growth (10y, %) – sua estimativa",
            value=median_growth,
            step=0.1,
            key="eco_trend",
        )
    
        # ============================================================
        # Ajuste AUTOMÁTICO por growth prospects
        # Regra:
        # - bucket 1-2: melhora se >= mediana + 0.7 ; piora se < mediana - 0.7
        # - bucket 3:   melhora se >= mediana + 0.7 ; piora se < mediana - 0.7
        # - bucket 4-6: melhora se >= mediana + 0.7 ; piora se < mediana
        # Ou seja, para bucket 4-6, abaixo de 2.7 já piora 1 categoria.
        # ============================================================
        if bucket == "4-6":
            if trend >= median_growth + 0.7:
                adj_growth_auto = -1
            elif trend < median_growth:
                adj_growth_auto = 1
            else:
                adj_growth_auto = 0
        else:
            if trend >= median_growth + 0.7:
                adj_growth_auto = -1
            elif trend < (median_growth - 0.7):
                adj_growth_auto = 1
            else:
                adj_growth_auto = 0
    
        c_auto1, c_auto2 = st.columns([1, 2])
        with c_auto1:
            st.metric("Ajuste automático por growth prospects", f"{adj_growth_auto:+d}")
        with c_auto2:
            st.caption(
                "Para bucket 4-6, valores abaixo da mediana (2.7%) já geram piora de 1 categoria."
            )
    
        use_manual_growth_override = st.checkbox(
            "Override manual do ajuste por growth prospects",
            value=False,
            key="eco_use_manual_growth_override",
        )
    
        if use_manual_growth_override:
            adj_growth = st.selectbox(
                "Ajuste manual por growth prospects",
                options=[-1, 0, 1],
                index=[-1, 0, 1].index(adj_growth_auto),
                key="eco_adj_growth_manual",
                help="-1 melhora 1 categoria; +1 piora 1 categoria.",
            )
        else:
            adj_growth = adj_growth_auto
    
        adj_concentration = st.selectbox(
            "Ajuste por concentração/volatilidade (0 ou +1)",
            options=[0, 1],
            index=0,
            key="eco_adj_conc",
        )
    
        adj_credit_bubble = st.selectbox(
            "Ajuste por credit-bubble risk (0 ou +1)",
            options=[0, 1],
            index=0,
            key="eco_adj_bubble",
        )
    
        adj_data = st.selectbox(
            "Ajuste por inconsistência de dados (0 ou +1)",
            options=[0, 1],
            index=0,
            key="eco_adj_data",
        )
    
        total_adj = adj_growth + adj_concentration + adj_credit_bubble + adj_data
        total_adj = max(-2, min(2, total_adj))
    
        final_score = clamp_score(init_score + total_adj)
    
        st.markdown("---")
        st.metric("Economic assessment (final)", final_score)
        st.caption(
            f"Growth prospects: {adj_growth:+d} | "
            f"Concentração/volatilidade: {adj_concentration:+d} | "
            f"Credit-bubble risk: {adj_credit_bubble:+d} | "
            f"Inconsistência de dados: {adj_data:+d}"
        )
        st.caption(f"Total de ajuste aplicado (limitado a ±2): {total_adj:+d}")
    
        st.session_state["economic"] = int(final_score)

    elif method_page == "Fiscal":
        st.header("Fiscal Assessment")
        st.markdown(
            "The fiscal assessment reflects the sustainability of a sovereign's "
            "deficits and its debt burden (Table 5 & Table 6). It is divided into "
            "**fiscal performance & flexibility** and **debt burden**, and the overall "
            "assessment is the average of those two."
        )

        with st.expander("📖 Reference – Table 5: Fiscal Performance & Flexibility"):
            st.markdown("""
| Change in net GG debt (% GDP) | <0–1% | 0–3% | 2–4% | 3–5% | 4–7% | >6% |
|---|---|---|---|---|---|---|
| **Initial assessment** | 1 | 2 | 3 | 4 | 5 | 6 |

*Positive adjustments* (+1 each): large liquid financial assets (>25 % GDP); greater revenue/expenditure flexibility vs peers.

*Negative adjustments* (−1 each): volatile/unsustainable revenue base; limited ability to raise revenues; shortfalls in basic services/infrastructure; unaddressed age-related spending pressure.
            """)

        with st.expander("📖 Reference – Table 6: Debt Burden"):
            st.markdown("""
| | Net GG debt ≤30% | 30–60% | 60–80% | 80–100% | >100% |
|---|---|---|---|---|---|
| **Interest ≤5% rev** | 1 | 2 | 3 | 4 | 5 |
| **5–10%** | 2 | 3 | 4 | 5 | 6 |
| **10–15%** | 3 | 4 | 5 | 6 | 6 |
| **>15%** | 4 | 5 | 6 | 6 | 6 |

*Negative adjustments* (−1 each, if ≥2 of 4 conditions): >40% FC debt or avg maturity <3 yr;
non‑residents hold >60% commercial debt; lumpy amortisation profile; banking‑sector exposure >20% assets.

*Contingent liabilities* (Table 7): limited → 0; moderate → −1; high → −2; very high → −3.
            """)

        st.markdown("---")

        # ── Fiscal Performance & Flexibility ───────────────────────
        st.subheader("A. Fiscal Performance & Flexibility")

        fis_chg_net_debt = st.number_input(
            "Δ Net GG Debt / GDP (%)",
            value=st.session_state.get("fis_chg_net_debt", 3.0),
            step=0.5, format="%.1f",
            help="Average of current-year estimate and 2-3 yr forecast.",
        )
        st.session_state["fis_chg_net_debt"] = fis_chg_net_debt

        # auto score
        _fp_thresholds = [(1, 1.0), (3, 2.0), (4, 3.0), (5, 4.0), (7, 5.0)]
        _fp_init = 6
        for hi, sc in _fp_thresholds:
            if fis_chg_net_debt <= hi:
                _fp_init = int(sc)
                break

        fp_overlap_adj = st.selectbox(
            "Overlap-zone trend adjustment",
            options=[-1, 0, 1],
            index=1,
            help="If the ratio falls in an overlap zone between two buckets, "
                 "declining trend → −1 (better); rising → +1 (worse).",
        )
        _fp_init_adj = max(1, min(6, _fp_init + fp_overlap_adj))

        fis_pos_adj = st.multiselect(
            "Positive adjustments (+1 each, max 2)",
            options=[
                "Large liquid financial assets (>25% GDP)",
                "Greater revenue/expenditure flexibility vs peers",
            ],
            default=[],
        )
        fis_neg_adj = st.multiselect(
            "Negative adjustments (−1 each, max 2)",
            options=[
                "Volatile/unsustainable revenue base",
                "Limited ability to raise revenues",
                "Shortfalls in basic services / infrastructure",
                "Unaddressed age-related expenditure pressure",
            ],
            default=[],
        )
        _fp_adj = min(len(fis_pos_adj), 2) - min(len(fis_neg_adj), 2)
        fp_final = max(1, min(6, _fp_init_adj + _fp_adj))
        st.session_state["sp_fiscal_perf"] = fp_final

        st.info(f"**Fiscal Performance & Flexibility** initial = {_fp_init} → "
                f"overlap adj → {_fp_init_adj} → net adj {_fp_adj:+d} → **{fp_final}**")

        st.markdown("---")

        # ── Debt Burden ────────────────────────────────────────────
        st.subheader("B. Debt Burden")

        col_a, col_b = st.columns(2)
        with col_a:
            fis_net_debt_gdp = st.number_input(
                "Net GG Debt / GDP (%)", value=st.session_state.get("fis_net_debt_gdp", 60.0),
                step=1.0, format="%.1f",
            )
            st.session_state["fis_net_debt_gdp"] = fis_net_debt_gdp
        with col_b:
            fis_int_rev = st.number_input(
                "GG Interest / Revenue (%)", value=st.session_state.get("fis_int_rev", 8.0),
                step=0.5, format="%.1f",
            )
            st.session_state["fis_int_rev"] = fis_int_rev

        # Table 6 auto-score
        _debt_cols = [30, 60, 80, 100]
        _int_rows  = [5, 10, 15]
        _t6 = [
            [1,2,3,4,5],
            [2,3,4,5,6],
            [3,4,5,6,6],
            [4,5,6,6,6],
        ]
        def _col6(d):
            for i, th in enumerate(_debt_cols):
                if d <= th: return i
            return 4
        def _row6(r):
            for i, th in enumerate(_int_rows):
                if r <= th: return i
            return 3
        db_init = _t6[_row6(fis_int_rev)][_col6(fis_net_debt_gdp)]

        st.markdown("**Debt-structure adjustment** (−1 if ≥2 of 4 conditions met):")
        debt_struct = st.multiselect(
            "Conditions",
            options=[
                ">40% gross debt in FC or avg maturity <3 yr",
                "Non-residents hold >60% commercial debt",
                "Lumpy amortisation profile",
                "Banking sector exposure >20% of assets",
            ],
            default=[],
        )
        _ds_adj = -1 if len(debt_struct) >= 2 else 0

        concess_adj = st.checkbox("Concessional official financing covers gross borrowing (next 2-3 yr)", value=False)
        _conc = 1 if concess_adj else 0

        contingent = st.selectbox(
            "Contingent liabilities (Table 7)",
            options=["Limited (0)", "Moderate (−1)", "High (−2)", "Very high (−3)"],
            index=0,
        )
        _cl_map = {"Limited (0)": 0, "Moderate (−1)": -1, "High (−2)": -2, "Very high (−3)": -3}
        _cl = _cl_map[contingent]

        db_final = max(1, min(6, db_init + _ds_adj + _conc + _cl))
        st.session_state["sp_debt_burden"] = db_final

        st.info(f"**Debt Burden** initial = {db_init} → debt-struct {_ds_adj:+d}, "
                f"concessional {_conc:+d}, contingent {_cl:+d} → **{db_final}**")

        # ── Overall Fiscal ─────────────────────────────────────────
        st.markdown("---")
        st.subheader("C. Overall Fiscal Assessment")
        fiscal_avg = (fp_final + db_final) / 2.0
        fiscal_rounded = round(fiscal_avg)
        st.session_state["sp_fiscal"] = fiscal_rounded

        st.success(f"**Fiscal Assessment** = avg({fp_final}, {db_final}) = "
                   f"{fiscal_avg:.1f} → rounded **{fiscal_rounded}**")


    elif method_page == "Monetary":
        st.header("Monetary Assessment")
        st.markdown(
            "The monetary assessment considers the monetary authority's ability to "
            "fulfil its mandate while sustaining a balanced economy and attenuating "
            "major shocks.  It combines **exchange-rate regime** (Table 8A) and "
            "**monetary-policy credibility** (Table 8B) with weights 40 %/60 %."
        )

        with st.expander("📖 Reference – Table 8A: Exchange-Rate Regime"):
            st.markdown("""
| Score | Regime |
|---|---|
| 1 | Reserve currency |
| 2 | Actively traded or free-floating currency |
| 3 | Managed float, crawling pegs, soft pegs other than conventional pegs |
| 4 | Conventional pegged arrangement; heavy FX intervention |
| 5 | Hard peg (currency board) |
| 6 | No local currency (uses another sovereign's currency) |
            """)

        with st.expander("📖 Reference – Table 8B: Monetary Policy Credibility"):
            st.markdown("""
Assessed 1–6 across five dimensions:
- **Central bank independence** (track record, legal framework)
- **Monetary policy tools & effectiveness**
- **Price stability** (CPI vs trading partners, REER stability)
- **Lender of last resort** capacity
- **Financial system depth** (depository claims + bond market / GDP)
            """)

        with st.expander("📖 Reference – Negative adjustments (¶121)"):
            st.markdown("""
Up to −2 categories from the initial monetary assessment:
1. Weak / significantly weakening transmission mechanisms
2. Dollarisation >50 % of deposits or loans
3. Extensive exchange restrictions (non-compliance with IMF Art. VIII)

**Monetary-union members** (¶122-124): up to −2 additional categories:
- −1 for less flexibility than sovereigns with own central bank
- −1 if economy is unsynchronised with the union at large
            """)

        st.markdown("---")

        # ── Exchange-rate regime ───────────────────────────────────
        st.subheader("A. Exchange-Rate Regime (Table 8A)")
        er_options = [
            "1 – Reserve currency",
            "2 – Actively traded / free-floating",
            "3 – Managed float / crawling peg / soft peg",
            "4 – Conventional peg / heavy FX intervention",
            "5 – Hard peg (currency board)",
            "6 – No local currency",
        ]
        er_idx = st.selectbox(
            "Exchange-rate regime",
            options=er_options,
            index=st.session_state.get("sp_mon_er_idx", 1),
            help="Select the regime that best describes the sovereign.",
        )
        er_score = int(er_idx[0])
        st.session_state["sp_mon_er_idx"] = er_options.index(er_idx)
        st.session_state["sp_mon_er"] = er_score

        st.markdown("---")

        # ── Monetary-policy credibility ────────────────────────────
        st.subheader("B. Monetary Policy Credibility (Table 8B)")
        st.markdown("Rate each dimension 1 (strongest) to 6 (weakest).")

        mc_dims = [
            ("CB independence", "sp_mon_cb_indep", 2,
             "Track record length and legal independence of the central bank."),
            ("Policy tools & effectiveness", "sp_mon_tools", 2,
             "Breadth and tested effectiveness of monetary instruments."),
            ("Price stability", "sp_mon_price", 2,
             "CPI alignment with trading partners; REER stability."),
            ("Lender of last resort", "sp_mon_lolr", 2,
             "Ability to provide emergency liquidity to the financial system."),
            ("Financial system depth", "sp_mon_depth", 3,
             "Depository claims + bond / equity mkt cap relative to GDP."),
        ]
        mc_scores = []
        cols = st.columns(len(mc_dims))
        for col_w, (label, key, default, tip) in zip(cols, mc_dims):
            with col_w:
                v = st.number_input(
                    label, min_value=1, max_value=6,
                    value=st.session_state.get(key, default),
                    help=tip,
                )
                st.session_state[key] = v
                mc_scores.append(v)
        mc_avg = sum(mc_scores) / len(mc_scores)
        mc_rounded = round(mc_avg)
        st.info(f"Monetary-policy credibility avg = {mc_avg:.2f} → rounded **{mc_rounded}**")

        st.markdown("---")

        # ── Initial monetary assessment ────────────────────────────
        st.subheader("C. Initial Monetary Assessment")
        init_mon = round(er_score * 0.4 + mc_rounded * 0.6)
        st.markdown(f"ER regime **{er_score}** × 40 % + Credibility **{mc_rounded}** × 60 % "
                    f"= {er_score*0.4 + mc_rounded*0.6:.1f} → rounded **{init_mon}**")

        st.markdown("---")

        # ── Negative adjustments ───────────────────────────────────
        st.subheader("D. Negative Adjustments")
        neg_mon = st.multiselect(
            "Select applicable adjustments (−1 each, max −2)",
            options=[
                "Weak/weakening transmission mechanisms",
                "Dollarisation >50% (deposits or loans)",
                "Extensive exchange restrictions (IMF Art. VIII non-compliance)",
            ],
            default=[],
        )
        neg_adj = min(len(neg_mon), 2)

        is_mu = st.checkbox("Sovereign is a member of a monetary union", value=False,
                            help="Monetary-union members may receive up to 2 additional negative adjustments.")
        mu_adj = 0
        if is_mu:
            mu_less_flex = st.checkbox("−1: Less flexibility than sovereigns with own CB", value=False)
            mu_unsync = st.checkbox("−1: Economy unsynchronised with the zone at large", value=False)
            mu_adj = int(mu_less_flex) + int(mu_unsync)

        total_neg = neg_adj + mu_adj
        mon_final = max(1, min(6, init_mon + total_neg))
        st.session_state["sp_monetary"] = mon_final

        if not is_mu and total_neg > 2:
            st.warning("Non-union sovereigns: max −2 from initial assessment (¶121).")
        if is_mu and total_neg > 4:
            st.warning("Union members: max −4 total (−2 general + −2 union-specific) (¶124).")

        st.success(f"**Monetary Assessment** = {init_mon} + {total_neg:+d} adjustments → **{mon_final}**")


    elif method_page == "External":
        st.header("External Assessment")
        st.markdown(
            "The external assessment reflects a country's ability to obtain foreign "
            "funds to meet public- and private-sector obligations to non-residents.  "
            "Three factors drive the assessment: **currency status**, **external "
            "liquidity**, and **external indebtedness** (Table 4)."
        )

        with st.expander("📖 Reference – Table 4 grid"):
            st.markdown("""
**Indebtedness** (narrow net ext debt / CAR or CAP) vs **Liquidity** (gross ext financing needs / (CAR + usable reserves)):

| Indebtedness \\ Liquidity | Reserve | Active | ≤50% | 50-100% | 100-150% | >150% |
|---|---|---|---|---|---|---|
| < −50% | 1 | 1 | 1 | 1 | 1 | 2 |
| −50–0% | 1 | 1 | 1 | 1 | 2 | 3 |
| 0–50% | 1 | 2 | 1 | 2 | 3 | 4 |
| 50–100% | 2 | 2 | 2 | 3 | 4 | 5 |
| 100–150% | 2 | 3 | 3 | 4 | 5 | 5 |
| 150–200% | 3 | 4 | 4 | 5 | 5 | 6 |
| >200% | 3 | 4 | 5 | 6 | 6 | 6 |

*Adjustments* (max ±3 net): +1 for strong net IIP or active-currency CA surplus; −1 each for
risk of deteriorating external financing, terms-of-trade volatility, low debt reflecting constraints,
data inconsistencies, active-currency high CA deficit (−2 if very high).
            """)

        st.markdown("---")

        # ── Currency status ────────────────────────────────────────
        st.subheader("A. Currency Status")
        ccy_opts = ["Reserve currency", "Actively traded", "Other"]
        ccy_status = st.selectbox(
            "Currency status in international transactions",
            options=ccy_opts,
            index=st.session_state.get("sp_ext_ccy_idx", 2),
            help="Reserve: >3% of global allocated FX reserves. "
                 "Actively traded: >1% of global FX turnover.",
        )
        st.session_state["sp_ext_ccy_idx"] = ccy_opts.index(ccy_status)

        st.markdown("---")

        # ── Key ratios ─────────────────────────────────────────────
        st.subheader("B. Key Ratios")
        col1, col2 = st.columns(2)
        with col1:
            ext_indebt = st.number_input(
                "Narrow net ext debt / CAR (or CAP) (%)",
                value=st.session_state.get("sp_ext_indebt", 30.0),
                step=5.0, format="%.1f",
                help="Positive = net debtor; negative = net creditor.",
            )
            st.session_state["sp_ext_indebt"] = ext_indebt
        with col2:
            if ccy_status == "Other":
                ext_liq = st.number_input(
                    "Gross ext financing needs / (CAR + usable reserves) (%)",
                    value=st.session_state.get("sp_ext_liq", 80.0),
                    step=5.0, format="%.1f",
                )
                st.session_state["sp_ext_liq"] = ext_liq
            else:
                ext_liq = 0.0
                st.info("Liquidity ratio not used for reserve/actively-traded currencies.")

        # Auto-score
        ext_init = ext_initial_assessment(ccy_status, ext_indebt, ext_liq)
        st.info(f"**Initial external assessment** (Table 4) = **{ext_init}**")

        st.markdown("---")

        # ── Adjustments ────────────────────────────────────────────
        st.subheader("C. Adjustments (max ±3 net)")
        ext_pos = st.multiselect(
            "Positive adjustments (+1 each)",
            options=[
                "Significantly stronger net IIP than narrow net ext debt",
                "Active-currency sovereign running consistent CA surpluses",
            ],
            default=[],
        )
        ext_neg = st.multiselect(
            "Negative adjustments (−1 each, unless noted)",
            options=[
                "Risk of marked deterioration in external financing (−1)",
                "Significant terms-of-trade volatility (−1)",
                "Low external debt reflects debt constraints (−1)",
                "Material data inconsistencies (−1)",
                "Active-currency: high CA deficit >10% CAR (−1)",
                "Active-currency: very high CA deficit >20% CAR (−2)",
            ],
            default=[],
        )
        _pos = min(len(ext_pos), 2)
        _neg = 0
        for item in ext_neg:
            if "(−2)" in item:
                _neg += 2
            else:
                _neg += 1
        net_adj = _pos - _neg
        net_adj = max(-3, min(3, net_adj))
        ext_final = max(1, min(6, ext_init + net_adj))
        st.session_state["sp_external"] = ext_final

        st.success(f"**External Assessment** = {ext_init} + ({net_adj:+d}) = **{ext_final}**")


    elif method_page == "Institutional":
        st.title("Institutional assessment")
        st.markdown("#### Seleção do nível (Tabela 2)")
        inst_choice = st.selectbox("Escolha o nível institucional conforme Table 2", [INST_TABLE2_LABELS[i] for i in [1, 2, 3, 4, 5, 6]], index=3, key="inst_table2_choice")
        init_inst = int(inst_choice.split("–")[0].strip())
        with st.expander("Ver critérios do Table 2 (nível selecionado)", expanded=False):
            st.markdown("**Effectiveness, stability, and predictability of policymaking, political institutions, and civil society**")
            st.markdown(bullets(INST_TABLE2[init_inst]["effectiveness"]))
            st.markdown("**Transparency and accountability of institutions, data, and processes**")
            st.markdown(bullets(INST_TABLE2[init_inst]["transparency"]))
        st.markdown("#### Ajustes")
        debt_culture_risk = st.checkbox("Risco de debt payment culture (cap para 6)", value=False, key="inst_debt_culture")
        war_risk = st.selectbox("External security risk (se aplicável)", options=[0, 1, 2], index=0, key="inst_war_adj")
        if debt_culture_risk:
            final_inst = 6
        else:
            final_inst = clamp_score(init_inst + war_risk)
        st.metric("Institutional assessment (final)", final_inst)
        st.session_state["institutional"] = int(final_inst)

    elif method_page == "Resultados":
        st.title("Resultados e perfis")
        institutional = int(st.session_state.get("institutional", 4))
        economic = int(st.session_state.get("economic", 4))
        external = int(st.session_state.get("external", 3))
        fiscal = float(st.session_state.get("fiscal", 4))
        monetary = float(st.session_state.get("monetary", 3))
        ie_profile = (institutional + economic) / 2.0
        fp_profile = (external + fiscal + monetary) / 3.0
        profiles = {
            "Institutional & Economic profile": round(ie_profile, 2),
            "Flexibility & Performance profile": round(fp_profile, 2),
        }
        st.session_state["profiles"] = profiles
        c1, c2, c3 = st.columns([1, 1, 1])
        c1.metric("Institutional", institutional)
        c2.metric("Economic", economic)
        c3.metric("Institutional & Economic profile (avg)", f"{ie_profile:.2f}")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        c1.metric("External", external)
        c2.metric("Fiscal", fmt_score(fiscal))
        c3.metric("Monetary", fmt_score(monetary))
        c4.metric("Flexibility & Performance profile (avg)", f"{fp_profile:.2f}")
        st.markdown("---")
        st.subheader("Radar (1=melhor; 6=pior)")
        fig = radar({"Institutional": institutional, "Economic": economic, "External": external, "Fiscal": fiscal, "Monetary": monetary})
        st_plotly_chart_compat(fig, use_container_width=True)
        st.markdown("---")
        st.subheader("Indicative rating level & notches")
        img = ASSETS_DIR / "page_06_img_01.png"
        if img.exists():
            _r1, _r2, _r3 = st.columns([0.5, 2, 0.5])
            with _r2:
                st.image(str(img), use_container_width=True)
        indicative_upper = indicative_from_matrix(ie_profile, fp_profile)
        indicative_lower = indicative_upper.lower()
        st.metric("Indicative rating level", indicative_lower)
        with st.expander("Override manual (opcional)"):
            st.selectbox("Indicative rating level (manual override)", RATING_SCALE, index=RATING_SCALE.index(indicative_upper), key="indicative_level_override")
        base_rating = st.session_state.get("indicative_level_override", indicative_upper)
        notch_adj = st.selectbox("Ajuste de notches (−1, 0, +1)", [-1, 0, 1], index=1, key="notch_adj")
        lc_uplift = st.selectbox("Uplift para Local-Currency (0 ou +1)", [0, 1], index=0, key="lc_uplift")
        final_rating = apply_notches(base_rating, notch_adj, lc_uplift)
        st.session_state["indicative"] = indicative_lower
        st.session_state["final_rating"] = final_rating
        st.metric("Final rating", final_rating)
        st.write(f"Notch: **{notch_adj:+d}** LC uplift: **+{lc_uplift}**")

# ============================================================
# App principal
# ============================================================

def render_sp():
    st.title("S&P Methodology + SRI")
    st.caption("1ª aba = metodologia; abas seguintes = dashboards do SRI")

    local_file = find_local_xlsx()
    with st.expander("Arquivo de entrada do SRI", expanded=False):
        uploaded = st.file_uploader("Se quiser, envie um arquivo .xlsx para substituir a base local", type=["xlsx"])
        if uploaded is None and local_file is not None:
            try:
                rel = local_file.relative_to(APP_DIR)
            except Exception:
                rel = local_file
            st.success(f"Usando arquivo do repositório: {rel}")
        elif uploaded is None:
            st.info("Nenhum arquivo local encontrado. Faça upload de um .xlsx ou adicione um arquivo em ./data.")

    uploaded_bytes = uploaded.getvalue() if uploaded is not None else None
    df = load_workbook(uploaded_bytes)
    filtered = None
    if not df.empty:
        with st.expander("Filtros do SRI", expanded=False):
            filtered = build_filters(df)

    tab1, tab2, tab3 = st.tabs(["Metodologia", "SRI – Dashboards", "SRI – Dados em tabela"])

    with tab1:
        render_methodology_tab()

    with tab2:
        if df.empty or filtered is None:
            st.error("Não foi possível interpretar a estrutura do workbook.")
        else:
            render_dashboard_tab(filtered)

    with tab3:
        if df.empty or filtered is None:
            st.error("Não foi possível interpretar a estrutura do workbook.")
        else:
            render_table_tab(filtered)
            with st.expander("Dicionário de campos", expanded=False):
                st.markdown(
                    """
- **sheet**: nome da aba original da planilha.
- **country_name**: nome do país.
- **country_code**: código do país.
- **lt_fc_rating**: rating LT FC.
- **indicator**: nome do indicador.
- **year**: ano original da base (preserva `e` e `f`).
- **year_num**: ano numérico para ordenação.
- **is_forecast**: identifica estimativa/projeção.
- **value**: valor numérico convertido para análise.
                    """
                )

