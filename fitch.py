# ============================================================
# Fitch Sovereign Methodology + Global Sovereign Data Comparator
# Streamlit App – v4 (fixed layout: sheet=data, row10=periods, colG=countries)
# ============================================================

import io
import math
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

INTERCEPT = 4.877

# ============================================================
# Auto-load local XLSB
# ============================================================

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"


def find_local_xlsb():
    """Return the first .xlsb found in data/ or app dir, or None."""
    for search_dir in [DATA_DIR, APP_DIR]:
        if search_dir.exists():
            files = sorted([p for p in search_dir.glob("*.xlsb") if not p.name.startswith("~$")])
            if files:
                return files[0]
    return None


# ============================================================
# Metadata – SRM
# ============================================================

SRM_VARIABLES = {
    "structural": {
        "governance_indicator": {
            "label": "Composite governance indicator (percentile rank)",
            "coefficient": 0.079, "weight": 22.1,
            "help": "Simple average percentile rank of World Bank governance indicators.",
        },
        "gdp_per_capita_percentile": {
            "label": "GDP per capita percentile rank (USD, market FX)",
            "coefficient": 0.037, "weight": 11.7,
            "help": "Percentile rank across Fitch-rated sovereigns.",
        },
        "share_world_gdp_log": {
            "label": "Share in world GDP (natural log of % share)",
            "coefficient": 0.645, "weight": 14.5,
            "help": "Natural logarithm of the percentage share in world GDP.",
        },
        "years_since_default_transform": {
            "label": "Years since default/restructuring event (SRM transformed value)",
            "coefficient": -1.744, "weight": 4.3,
            "help": "Use 0 if no event after 1980, or input the SRM-ready transformed value.",
        },
        "money_supply_log": {
            "label": "Broad money supply (% of GDP) - natural log",
            "coefficient": 0.148, "weight": 1.1,
            "help": "Natural logarithm of broad money as % of GDP.",
        },
    },
    "macro": {
        "real_gdp_growth_volatility_log": {
            "label": "Real GDP growth volatility - natural log",
            "coefficient": -0.704, "weight": 4.5,
            "help": "Natural log of the exponentially weighted std. deviation of historical real GDP growth.",
        },
        "consumer_price_inflation": {
            "label": "Consumer price inflation (3-year centred average, %, truncated 2%-50%)",
            "coefficient": -0.068, "weight": 3.6,
            "help": "Public criteria truncate this variable to the 2%-50% range.",
        },
        "real_gdp_growth": {
            "label": "Real GDP growth (3-year centred average, %)",
            "coefficient": 0.054, "weight": 1.7,
            "help": "Three-year centred average.",
        },
    },
    "public_finances": {
        "gross_general_govt_debt": {
            "label": "Gross general government debt (% of GDP, 3-year centred average)",
            "coefficient": -0.023, "weight": 9.2,
            "help": "Gross general government debt, centred three-year average.",
        },
        "general_govt_interest_revenue": {
            "label": "General government interest (% of revenues, 3-year centred average)",
            "coefficient": -0.044, "weight": 4.6,
            "help": "General government interest expenditures as % of revenues.",
        },
        "general_govt_fiscal_balance": {
            "label": "General government fiscal balance (% of GDP, 3-year centred average)",
            "coefficient": 0.039, "weight": 2.1,
            "help": "General government fiscal balance, centred three-year average.",
        },
        "fc_govt_debt_share": {
            "label": "Foreign-currency government debt (% of gross government debt, 3-yr centred avg)",
            "coefficient": -0.008, "weight": 3.2,
            "help": "Foreign-currency or indexed government debt as % of gross government debt.",
        },
    },
    "external": {
        "reserve_currency_flexibility": {
            "label": "Reserve-currency flexibility (SRM transformed value)",
            "coefficient": 0.484, "weight": 7.1,
            "help": "Use 0 if the sovereign has no reserve-currency flexibility.",
        },
        "sovereign_net_foreign_assets": {
            "label": "Sovereign net foreign assets (% of GDP, 3-year centred average)",
            "coefficient": 0.010, "weight": 7.5,
            "help": "Three-year centred average of sovereign net foreign assets.",
        },
        "commodity_dependence": {
            "label": "Commodity dependence (% of current external receipts)",
            "coefficient": -0.003, "weight": 1.0,
            "help": "Non-manufactured merchandise exports as % of current external receipts.",
        },
        "fx_reserves_months_cxp": {
            "label": "Official FX reserves (months of CXP) - for non-reserve-currency sovereigns",
            "coefficient": 0.021, "weight": 1.2,
            "help": "Usually set to 0 if reserve-currency flexibility is above 0.",
        },
        "external_interest_service": {
            "label": "External interest service (% of current external receipts, 3-yr centred avg)",
            "coefficient": -0.004, "weight": 0.2,
            "help": "Three-year centred average.",
        },
        "cab_plus_net_fdi": {
            "label": "Current account balance + net inward FDI (% of GDP, 3-yr centred avg)",
            "coefficient": 0.004, "weight": 0.4,
            "help": "Three-year centred average.",
        },
    },
}

PILLAR_LABELS = {
    "structural": "I. Structural Features",
    "macro": "II. Macroeconomic Performance, Policies and Prospects",
    "public_finances": "III. Public Finances",
    "external": "IV. External Finances",
}

QO_FACTORS = {
    "structural": [
        "Political stability and capacity",
        "Financial sector risks",
        "Other structural factors",
    ],
    "macro": [
        "Macroeconomic policy credibility and flexibility",
        "GDP growth outlook",
        "Macroeconomic stability / imbalances",
    ],
    "public_finances": [
        "Fiscal financing flexibility",
        "Public debt sustainability",
        "Fiscal structure",
    ],
    "external": [
        "External financing flexibility",
        "External debt sustainability",
        "Vulnerability to shocks",
    ],
}

QO_GUIDANCE = {
    2: "Exceptionally strong features relative to SRM data and output",
    1: "Strong features relative to SRM data and output",
    0: "Average features relative to SRM data and output",
    -1: "Weak features relative to SRM data and output",
    -2: "Exceptionally weak features relative to SRM data and output",
}

RATING_SCALE_NUMERIC = {
    16: "AAA", 15: "AA+", 14: "AA", 13: "AA-",
    12: "A+", 11: "A", 10: "A-",
    9: "BBB+", 8: "BBB", 7: "BBB-",
    6: "BB+", 5: "BB", 4: "BB-",
    3: "B+", 2: "B", 1: "B-",
}

LONG_TERM_SCALE = [
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
    "B+", "B", "B-", "CCC+", "CCC", "CCC-", "CC", "C", "RD", "D",
]

ST_MAPPING_OPTIONS = {
    "AAA": ("F1+", "F1+"), "AA+": ("F1+", "F1+"), "AA": ("F1+", "F1+"), "AA-": ("F1+", "F1+"),
    "A+": ("F1", "F1+"), "A": ("F1", "F1+"), "A-": ("F2", "F1"),
    "BBB+": ("F2", "F1"), "BBB": ("F3", "F2"), "BBB-": ("F3", "F3"),
    "BB+": ("B", "B"), "BB": ("B", "B"), "BB-": ("B", "B"),
    "B+": ("B", "B"), "B": ("B", "B"), "B-": ("B", "B"),
    "CCC+": ("C", "C"), "CCC": ("C", "C"), "CCC-": ("C", "C"),
    "CC": ("C", "C"), "C": ("C", "C"),
    "RD": ("C/RD/D", "C/RD/D"), "D": ("D", "D"),
}

VARIABLE_RULES = {
    "governance_indicator": {"step": 0.1, "soft_min": 0, "soft_max": 100},
    "gdp_per_capita_percentile": {"step": 0.1, "soft_min": 0, "soft_max": 100},
    "share_world_gdp_log": {"step": 0.1, "soft_min": -20, "soft_max": 5},
    "years_since_default_transform": {"step": 0.01, "soft_min": 0, "soft_max": 5},
    "money_supply_log": {"step": 0.1, "soft_min": -5, "soft_max": 10},
    "real_gdp_growth_volatility_log": {"step": 0.1, "soft_min": -5, "soft_max": 10},
    "consumer_price_inflation": {"step": 0.1, "soft_min": -100, "soft_max": 500},
    "real_gdp_growth": {"step": 0.1, "soft_min": -20, "soft_max": 20},
    "gross_general_govt_debt": {"step": 0.1, "soft_min": 0, "soft_max": 500},
    "general_govt_interest_revenue": {"step": 0.1, "soft_min": 0, "soft_max": 100},
    "general_govt_fiscal_balance": {"step": 0.1, "soft_min": -50, "soft_max": 50},
    "fc_govt_debt_share": {"step": 0.1, "soft_min": 0, "soft_max": 100},
    "reserve_currency_flexibility": {"step": 0.1, "soft_min": 0, "soft_max": 20},
    "sovereign_net_foreign_assets": {"step": 0.1, "soft_min": -300, "soft_max": 300},
    "commodity_dependence": {"step": 0.1, "soft_min": 0, "soft_max": 100},
    "fx_reserves_months_cxp": {"step": 0.1, "soft_min": 0, "soft_max": 60},
    "external_interest_service": {"step": 0.1, "soft_min": 0, "soft_max": 100},
    "cab_plus_net_fdi": {"step": 0.1, "soft_min": -30, "soft_max": 30},
}

# ============================================================
# XLSB -> SRM Auto-Populate (any country)
# ============================================================

SRM_XLSB_MAP = {
    "governance_indicator": {"indicators": [], "measure": "latest", "transform": None, "special": "wgi_composite"},
    "gdp_per_capita_percentile": {"indicators": ["GDP per cap"], "unit_hint": None, "section_hint": "INCOME", "measure": "latest", "transform": "percentile_rank"},
    "share_world_gdp_log": {"indicators": ["GDP"], "unit_hint": "USDbn", "section_hint": "DOMESTIC", "exclude": ["per cap", "real", "volat", "growth"], "measure": "latest", "transform": "world_gdp_share_log"},
    "years_since_default_transform": {"indicators": ["SRM-inverse", "SRM inverse", "yrs since"], "measure": "latest", "transform": None},
    "money_supply_log": {"indicators": ["Broad money"], "unit_hint": "% GDP", "section_hint": "MONEY", "measure": "latest", "transform": "log"},
    "real_gdp_growth_volatility_log": {"indicators": ["GDP volat"], "unit_hint": "Exp mov", "measure": "latest", "transform": "log"},
    "consumer_price_inflation": {"indicators": ["Consumer price", "Consumer prices"], "section_hint": "DOMESTIC", "measure": "3yr_avg", "transform": "truncate_2_50"},
    "real_gdp_growth": {"indicators": ["Real GDP growth"], "section_hint": "DOMESTIC", "exclude": ["volat"], "measure": "3yr_avg", "transform": None},
    "gross_general_govt_debt": {"indicators": ["GG debt"], "unit_hint": "% GDP", "section_hint": "GOVERNMENT", "exclude": ["mat", "% rev"], "measure": "3yr_avg", "transform": None},
    "general_govt_interest_revenue": {"indicators": ["GG int"], "unit_hint": "% rev", "section_hint": "GOVERNMENT", "measure": "3yr_avg", "transform": None},
    "general_govt_fiscal_balance": {"indicators": ["GG balance"], "unit_hint": "% GDP", "section_hint": "GOVERNMENT", "measure": "3yr_avg", "transform": None},
    "fc_govt_debt_share": {"indicators": ["Public FC", "Foreign own-p", "FC govt"], "measure": "3yr_avg", "transform": None},
    "reserve_currency_flexibility": {"indicators": ["SRM-reserve", "SRM reserve"], "measure": "latest", "transform": None},
    "sovereign_net_foreign_assets": {"indicators": ["SNFA", "Sovereign net foreign"], "unit_hint": "% GDP", "measure": "3yr_avg", "transform": None},
    "commodity_dependence": {"indicators": ["Comm. dep", "Commodity dep", "commodity depend"], "measure": "latest", "transform": None},
    "fx_reserves_months_cxp": {"indicators": ["Reserves", "FX reserves"], "unit_hint": "months", "measure": "latest", "transform": None},
    "external_interest_service": {"indicators": ["Ext. int", "External interest"], "unit_hint": "% CXR", "exclude": ["% GDP"], "measure": "3yr_avg", "transform": None},
    "cab_plus_net_fdi": {"indicators": ["CAB+Net FDI", "CAB + Net FDI", "CAB+net FDI"], "unit_hint": "% GDP", "measure": "3yr_avg", "transform": None},
}


def _find_indicator_rows(df_c, patterns, unit_hint=None, section_hint=None, exclude=None):
    if df_c.empty or not patterns:
        return pd.DataFrame()
    mask = pd.Series(False, index=df_c.index)
    ind_lower = df_c["indicator"].str.lower()
    for pat in patterns:
        mask = mask | ind_lower.str.contains(pat.lower(), na=False, regex=False)
    if unit_hint:
        u = df_c["unit"].str.lower() if "unit" in df_c.columns else pd.Series("", index=df_c.index)
        mask = mask & u.str.contains(unit_hint.lower(), na=False, regex=False)
    if section_hint:
        s = df_c["section"].str.lower() if "section" in df_c.columns else pd.Series("", index=df_c.index)
        mask = mask & s.str.contains(section_hint.lower(), na=False, regex=False)
    if exclude:
        for ex in exclude:
            mask = mask & ~ind_lower.str.contains(ex.lower(), na=False, regex=False)
    return df_c[mask]


def _get_val_for_year(df_ind, year):
    sub = df_ind[df_ind["year_num"] == year]
    if sub.empty:
        return None
    vals = sub["value"].dropna()
    return float(vals.iloc[0]) if not vals.empty else None


def _get_latest_val(df_ind):
    if "is_latest" in df_ind.columns:
        lat = df_ind[df_ind["is_latest"] == True]
        if not lat.empty:
            v = lat["value"].dropna()
            if not v.empty:
                return float(v.iloc[0])
    valid = df_ind[df_ind["year_num"] > 0].sort_values("year_num", ascending=False)
    if not valid.empty:
        v = valid["value"].dropna()
        if not v.empty:
            return float(v.iloc[0])
    return None


def _get_avg_val(df_ind):
    if "is_average" in df_ind.columns:
        avg = df_ind[df_ind["is_average"] == True]
        if not avg.empty:
            v = avg["value"].dropna()
            if not v.empty:
                return float(v.iloc[0])
    return None


def _compute_3yr_avg(df_ind, cy):
    vals = []
    for y in [cy - 1, cy, cy + 1]:
        v = _get_val_for_year(df_ind, y)
        if v is not None:
            vals.append(v)
    return float(np.mean(vals)) if vals else None


def _resolve_value(df_ind, measure, center_year):
    if measure == "latest":
        raw = _get_val_for_year(df_ind, center_year)
        if raw is None:
            raw = _get_val_for_year(df_ind, center_year - 1)
        if raw is None:
            raw = _get_val_for_year(df_ind, center_year + 1)
        if raw is None:
            raw = _get_latest_val(df_ind)
        return raw
    else:
        raw = _compute_3yr_avg(df_ind, center_year)
        if raw is None:
            raw = _get_avg_val(df_ind)
        if raw is None:
            raw = _get_latest_val(df_ind)
        return raw


def _match_with_fallback(df_slice, patterns, unit_hint, section_hint, exclude):
    matched = _find_indicator_rows(df_slice, patterns, unit_hint, section_hint, exclude)
    if matched.empty and unit_hint:
        matched = _find_indicator_rows(df_slice, patterns, None, section_hint, exclude)
    if matched.empty and section_hint:
        matched = _find_indicator_rows(df_slice, patterns, unit_hint, None, exclude)
    if matched.empty:
        matched = _find_indicator_rows(df_slice, patterns, None, None, exclude)
    return matched


def extract_country_srm_from_comparator(df, country_name, center_year=2025):
    logs = []
    result = {}
    df_country = df[
        (df["country_name"].str.lower() == country_name.lower())
        & (df["entity_type"] == "COUNTRY")
    ]
    if df_country.empty:
        df_country = df[
            (df["country_name"].str.contains(country_name, case=False, na=False))
            & (df["entity_type"] == "COUNTRY")
        ]
    if df_country.empty:
        logs.append(f"WARN: '{country_name}' nao encontrado.")
        return result, logs
    actual_name = df_country["country_name"].iloc[0]
    logs.append(f"OK {actual_name}: {len(df_country)} registros (cy={center_year})")
    df_countries = df[df["entity_type"] == "COUNTRY"]
    for var_key, cfg in SRM_XLSB_MAP.items():
        special = cfg.get("special")
        measure = cfg["measure"]
        transform = cfg.get("transform")
        if special == "wgi_composite":
            wgi = df_country[df_country["section"].str.contains("GOVERNANCE", case=False, na=False)]
            if wgi.empty:
                wgi = df_country[df_country["unit"].str.contains("p-tile|p.tile|percentile", case=False, na=False, regex=True)]
            if wgi.empty:
                wgi = df_country[df_country["indicator"].str.contains("governance|WGI", case=False, na=False, regex=True)]
            if not wgi.empty:
                raw = _resolve_value(wgi, "latest", center_year)
                if raw is not None:
                    wy = wgi[wgi["year_num"] == center_year]
                    if wy.empty:
                        wy = wgi[wgi["year_num"] == center_year - 1]
                    if wy.empty and "is_latest" in wgi.columns:
                        wy = wgi[wgi["is_latest"] == True]
                    if not wy.empty and len(wy) > 1:
                        composite = float(wy["value"].dropna().mean())
                    else:
                        composite = raw
                    result[var_key] = composite
                    logs.append(f"OK {var_key} = {composite:.2f}")
                    continue
            logs.append(f"WARN {var_key}: WGI nao encontrado")
            continue
        patterns = cfg.get("indicators", [])
        unit_hint = cfg.get("unit_hint")
        section_hint = cfg.get("section_hint")
        exclude = cfg.get("exclude")
        matched = _match_with_fallback(df_country, patterns, unit_hint, section_hint, exclude)
        if matched.empty:
            logs.append(f"WARN {var_key}: nao encontrado ({patterns})")
            continue
        raw = _resolve_value(matched, measure, center_year)
        if raw is None:
            logs.append(f"WARN {var_key}: sem dados disponiveis")
            continue
        if transform == "log":
            if raw > 0:
                final = float(math.log(raw))
            else:
                logs.append(f"WARN {var_key}: valor <= 0 ({raw})")
                continue
        elif transform == "truncate_2_50":
            final = float(min(50.0, max(2.0, raw)))
        elif transform == "percentile_rank":
            am = _match_with_fallback(df_countries, patterns, unit_hint, section_hint, exclude)
            all_vals = []
            for cn in am["country_name"].unique():
                v = _resolve_value(am[am["country_name"] == cn], "latest", center_year)
                if v is not None:
                    all_vals.append(v)
            if all_vals:
                final = float(sum(1 for v in all_vals if v <= raw) / len(all_vals) * 100)
            else:
                logs.append(f"WARN {var_key}: sem cross-country p/ percentile")
                continue
        elif transform == "world_gdp_share_log":
            am = _match_with_fallback(df_countries, patterns, unit_hint, section_hint, exclude)
            all_vals = []
            for cn in am["country_name"].unique():
                v = _resolve_value(am[am["country_name"] == cn], "latest", center_year)
                if v is not None:
                    all_vals.append(v)
            total = sum(all_vals)
            if total > 0 and raw > 0:
                final = float(math.log(raw / total * 100))
            else:
                logs.append(f"WARN {var_key}: sem cross-country p/ world GDP")
                continue
        else:
            final = float(raw)
        result[var_key] = final
        logs.append(f"OK {var_key} = {final:.4f} (raw={raw:.4f})")
    logs.append(f"TOTAL: {len(result)}/18 variaveis extraidas")
    return result, logs


def apply_country_data_to_session(srm_values):
    data = st.session_state.setdefault("_srm_data", {})
    for key, val in srm_values.items():
        data[key] = float(val)


# ============================================================
# Helpers gerais
# ============================================================

def normalize_label(text):
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def slugify(text):
    text = normalize_label(text).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def coerce_numeric(series):
    s = series.astype(str).str.strip()
    s = s.replace({
        "N/A": np.nan, "N.M.": np.nan, "NM": np.nan,
        "None": np.nan, "nan": np.nan, "": np.nan,
        "..": np.nan, "...": np.nan, "n.a": np.nan,
        "n.a.": np.nan, "-": np.nan,
    })
    return pd.to_numeric(s, errors="coerce")


def _cell_str(v):
    """Safely convert any cell value to string, handling NaN/Inf floats."""
    if v is None:
        return ""
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return ""
        if v == int(v):
            return str(int(v))
        return str(v)
    return str(v).strip()


def st_dataframe_compat(df, **kwargs):
    try:
        st.dataframe(df, **kwargs)
    except TypeError:
        st.dataframe(df)


def st_plotly_chart_compat(fig, use_container_width=True):
    try:
        st.plotly_chart(fig, use_container_width=use_container_width)
    except TypeError:
        st.plotly_chart(fig)


# ============================================================
# SRM Helpers
# ============================================================

def clamp_qo(adjustments, crisis_extension=False):
    raw = int(sum(adjustments.values()))
    return raw if crisis_extension else max(-3, min(3, raw))


def score_to_lt_rating(score):
    rounded = int(round(score))
    if rounded >= 16:
        return "AAA"
    if rounded <= 0:
        return "CCC+"
    return RATING_SCALE_NUMERIC.get(rounded, "CCC+")


def rating_index(rating):
    return LONG_TERM_SCALE.index(rating) if rating in LONG_TERM_SCALE else LONG_TERM_SCALE.index("CCC+")


def apply_notches(base_rating, notch_adjustment):
    if base_rating not in LONG_TERM_SCALE:
        return base_rating
    idx = rating_index(base_rating)
    new_idx = max(0, min(len(LONG_TERM_SCALE) - 1, idx - int(notch_adjustment)))
    return LONG_TERM_SCALE[new_idx]


def map_short_term(long_rating, use_higher_option):
    lo, hi = ST_MAPPING_OPTIONS.get(long_rating, ("C", "C"))
    return hi if use_higher_option else lo


def approx_years_since_default_transform(years_since_event=None, no_event_since_1980=True):
    if no_event_since_1980 or years_since_event is None:
        return 0.0
    years_since_event = max(0.0, float(years_since_event))
    return float(math.exp(-math.log(2) * years_since_event / 4.3))


def safe_number_input(var_key, label, default, help_text):
    data = st.session_state["_srm_data"]
    current = data.get(var_key, default)
    rule = VARIABLE_RULES.get(var_key, {"step": 0.1})
    val = st.number_input(
        label, value=float(current),
        step=float(rule.get("step", 0.1)),
        help=help_text,
    )
    data[var_key] = float(val)
    return val


def get_clean_srm_inputs():
    data = st.session_state.get("_srm_data", {})
    inputs = {}
    for pillar in SRM_VARIABLES.values():
        for k in pillar.keys():
            v = float(data.get(k, 0.0))
            if k == "consumer_price_inflation":
                v = min(50.0, max(2.0, v))
            inputs[k] = v
    return inputs


def compute_srm(inputs):
    details = []
    total = INTERCEPT
    for pillar_key, vars_dict in SRM_VARIABLES.items():
        for var_key, meta in vars_dict.items():
            value = float(inputs.get(var_key, 0.0))
            contribution = value * float(meta["coefficient"])
            total += contribution
            details.append({
                "Pillar": PILLAR_LABELS[pillar_key],
                "Variable": meta["label"],
                "Value": value,
                "Coefficient": meta["coefficient"],
                "Contribution": contribution,
            })
    details.append({
        "Pillar": "Intercept", "Variable": "OLS intercept",
        "Value": 1.0, "Coefficient": INTERCEPT, "Contribution": INTERCEPT,
    })
    return total, details


def build_radar(srm_score, qo_total, final_score):
    categories = ["SRM score", "QO total", "Final model score"]
    values = [srm_score, qo_total, final_score]
    categories += categories[:1]
    values += values[:1]
    fig = go.Figure(data=[go.Scatterpolar(r=values, theta=categories, fill="toself")])
    fig.update_layout(showlegend=False, polar=dict(radialaxis=dict(visible=True)))
    return fig


# ============================================================
# State init
# ============================================================

def init_state():
    # Persistent dicts – never cleared by widget lifecycle
    if "_srm_data" not in st.session_state:
        st.session_state["_srm_data"] = {
            "governance_indicator": 50.0,
            "gdp_per_capita_percentile": 50.0,
            "share_world_gdp_log": -4.0,
            "years_since_default_transform": 0.0,
            "money_supply_log": math.log(60.0),
            "real_gdp_growth_volatility_log": math.log(3.0),
            "consumer_price_inflation": 4.0,
            "real_gdp_growth": 3.0,
            "gross_general_govt_debt": 60.0,
            "general_govt_interest_revenue": 8.0,
            "general_govt_fiscal_balance": -3.0,
            "fc_govt_debt_share": 35.0,
            "reserve_currency_flexibility": 0.0,
            "sovereign_net_foreign_assets": -20.0,
            "commodity_dependence": 25.0,
            "fx_reserves_months_cxp": 4.0,
            "external_interest_service": 8.0,
            "cab_plus_net_fdi": -1.0,
        }
    if "_qo_data" not in st.session_state:
        st.session_state["_qo_data"] = {
            "qo_structural": 0,
            "qo_macro": 0,
            "qo_public_finances": 0,
            "qo_external": 0,
        }
    st.session_state.setdefault("_qo_crisis", False)
    st.session_state.setdefault("_lc_adjust", 0)
    st.session_state.setdefault("_fc_robust", False)


# ============================================================
# Fitch XLSB Parser – v4 (fixed layout)
# ============================================================

@st.cache_data(show_spinner=False)
def parse_fitch_comparator(file_bytes):
    """Parse the Fitch Global Sovereign Data Comparator .xlsb file.

    Known layout (March 2026 edition):
      - Sheet named "data"
      - Row  6 (idx 5): top-level section / category
      - Row  7 (idx 6): sub-section
      - Row  8 (idx 7): indicator name
      - Row  9 (idx 8): unit
      - Row 10 (idx 9): period / year
      - Column G (idx 6): country / entity name
      - Data starts at row 11 (idx 10)
    """
    from pyxlsb import open_workbook

    # ── read the right sheet ────────────────────────────────────────
    all_rows = []
    with open_workbook(io.BytesIO(file_bytes)) as wb:
        sheets = wb.sheets
        if not sheets:
            return pd.DataFrame()

        # prefer sheet named "data"
        target = None
        for s in sheets:
            if s.lower().strip() == "data":
                target = s
                break
        if target is None:
            target = sheets[0]

        with wb.get_sheet(target) as sheet:
            for row in sheet.rows():
                all_rows.append([cell.v for cell in row])

    if len(all_rows) < 11:
        return pd.DataFrame()

    raw = pd.DataFrame(all_rows)
    ncols = len(raw.columns)

    # ── locate the period row ───────────────────────────────────────
    def _row_year_count(idx):
        count = 0
        for v in raw.iloc[idx]:
            s = _cell_str(v)
            if re.match(r"^(19|20)\d{2}$", s):
                count += 1
            elif "av." in s.lower() or "average" in s.lower() or "latest" in s.lower():
                count += 1
        return count

    # Known position: row 10 = idx 9
    if len(raw) > 9 and _row_year_count(9) >= 3:
        period_row_idx = 9
    else:
        # Fallback: scan first 60 rows
        period_row_idx = None
        for i in range(min(60, len(raw))):
            if _row_year_count(i) >= 3:
                period_row_idx = i
                break

    if period_row_idx is None:
        diag = []
        for i in range(min(20, len(raw))):
            cells = [_cell_str(v)[:25] for v in raw.iloc[i]][:15]
            diag.append(f"Row {i}: {cells}")
        st.error("Não foi possível localizar a linha de períodos no XLSB.")
        with st.expander("Diagnóstico – primeiras 20 linhas"):
            st.code("\n".join(diag))
        return pd.DataFrame()

    # ── header rows (relative to period row) ────────────────────────
    section_row_idx    = max(0, period_row_idx - 4)   # row 6 → idx 5
    subsection_row_idx = max(0, period_row_idx - 3)   # row 7 → idx 6
    indicator_row_idx  = max(0, period_row_idx - 2)   # row 8 → idx 7
    unit_row_idx       = max(0, period_row_idx - 1)   # row 9 → idx 8

    def get_row_strs(idx):
        return [_cell_str(raw.iloc[idx, c]) if idx < len(raw) else ""
                for c in range(ncols)]

    sections_raw    = get_row_strs(section_row_idx)
    subsections_raw = get_row_strs(subsection_row_idx)
    indicators_raw  = get_row_strs(indicator_row_idx)
    units_raw       = get_row_strs(unit_row_idx)
    periods_raw     = get_row_strs(period_row_idx)

    def forward_fill(lst):
        result, cur = [], ""
        for v in lst:
            if v and v.lower() not in ("none", "nan", ""):
                cur = v
            result.append(cur)
        return result

    sections    = forward_fill(sections_raw)
    subsections = forward_fill(subsections_raw)
    indicators  = forward_fill(indicators_raw)

    # ── first data column ───────────────────────────────────────────
    meta_end = None
    for c in range(ncols):
        p = periods_raw[c]
        if re.match(r"^(19|20)\d{2}$", p) or "av." in p.lower() or "latest" in p.lower():
            meta_end = c
            break
    if meta_end is None:
        meta_end = 14

    # ── column metadata ─────────────────────────────────────────────
    col_meta = []
    for c in range(meta_end, ncols):
        section    = normalize_label(sections[c])    if c < len(sections)    else ""
        subsection = normalize_label(subsections[c]) if c < len(subsections) else ""
        indicator  = normalize_label(indicators[c])  if c < len(indicators)  else ""
        unit       = normalize_label(units_raw[c])   if c < len(units_raw)   else ""
        period     = normalize_label(periods_raw[c]) if c < len(periods_raw) else ""

        if not indicator and not section:
            continue
        if not period or period.lower() in ("none", "nan", ""):
            continue

        year_match = re.search(r"(19|20)\d{2}", period)
        year_num = int(year_match.group()) if year_match else None

        col_meta.append({
            "col_idx": c,
            "section": section if section else subsection,
            "subsection": subsection,
            "indicator": indicator if indicator else subsection,
            "unit": unit,
            "year": period,
            "year_num": year_num if year_num else 0,
            "is_average": "av." in period.lower() or "average" in period.lower(),
            "is_forecast": year_num is not None and year_num >= 2025,
            "is_latest": "latest" in period.lower(),
        })

    if not col_meta:
        st.error("Não foi possível mapear colunas de dados no XLSB.")
        return pd.DataFrame()

    # ── column G (idx 6) = country name ─────────────────────────────
    NAME_COL = 6

    # ── parse data rows ─────────────────────────────────────────────
    data_start = period_row_idx + 1
    records = []

    for r in range(data_start, len(raw)):
        row = raw.iloc[r]

        country_name = _cell_str(row.iloc[NAME_COL]) if len(row) > NAME_COL else ""
        if not country_name or country_name.lower() in ("none", "nan", ""):
            continue

        entity_key = _cell_str(row.iloc[0]) if len(row) > 0 else ""

        # entity type (col E = idx 4)
        et_raw = _cell_str(row.iloc[4]).upper() if len(row) > 4 else ""
        if "COUNTRY" in et_raw:
            entity_type = "COUNTRY"
        elif any(kw in et_raw for kw in ("HEADING", "MEDIAN", "AVERAGE", "GROUP")):
            entity_type = "GROUP"
        else:
            entity_type = "COUNTRY"

        country_code = _cell_str(row.iloc[5]) if len(row) > 5 else ""

        # Rating: try several columns
        lt_fc_rating = ""
        for rc in [7, 8, 1, 2, 3]:
            if len(row) > rc and row.iloc[rc] is not None:
                cand = _cell_str(row.iloc[rc])
                if cand.upper() in [x for x in LONG_TERM_SCALE] + ["NR", "WD"]:
                    lt_fc_rating = cand.upper()
                    break

        dev_status = _cell_str(row.iloc[13]) if len(row) > 13 else ""
        if dev_status.lower() in ("none", "nan"):
            dev_status = ""

        for cm in col_meta:
            c = cm["col_idx"]
            if c >= len(row):
                continue
            raw_val = row.iloc[c]
            if raw_val is None:
                continue

            if isinstance(raw_val, (int, float)):
                if isinstance(raw_val, float) and (math.isnan(raw_val) or math.isinf(raw_val)):
                    continue
                val = float(raw_val)
            else:
                s = str(raw_val).strip()
                if s.lower() in ("", "none", "nan", "n/a", "n.m.", "nm", "..", "...", "n.a", "n.a.", "-"):
                    continue
                try:
                    val = float(s.replace(",", "."))
                except ValueError:
                    continue

            records.append({
                "entity_key": entity_key,
                "entity_type": entity_type,
                "country_name": country_name,
                "country_code": country_code,
                "lt_fc_rating": lt_fc_rating,
                "dev_status": dev_status,
                "section": cm["section"],
                "subsection": cm["subsection"],
                "indicator": cm["indicator"],
                "unit": cm["unit"],
                "year": cm["year"],
                "year_num": cm["year_num"],
                "is_average": cm["is_average"],
                "is_forecast": cm["is_forecast"],
                "value": val,
            })

    df = pd.DataFrame(records)
    if df.empty:
        return df

    for col in ["section", "country_name", "indicator", "subsection"]:
        if col in df.columns:
            df[col] = df[col].str.replace("&amp;", "&", regex=False)
    df["section"] = df["section"].replace({"": "Other"})

    return df


# ============================================================
# Comparator -> Excel export (with line charts)
# ============================================================

def _fix_strref_in_zip(buf):
    """Fix numRef->strRef in cat axis and hollow markers."""
    out = io.BytesIO()
    with zipfile.ZipFile(buf, 'r') as zin, \
         zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith('xl/charts/') and item.filename.endswith('.xml'):
                xml = data.decode('utf-8')
                def _swap(m):
                    inner = (m.group(1)
                        .replace('<c:numRef>', '<c:strRef>')
                        .replace('</c:numRef>', '</c:strRef>')
                        .replace('<c:numCache>', '<c:strCache>')
                        .replace('</c:numCache>', '</c:strCache>'))
                    return '<c:cat>' + inner + '</c:cat>'
                xml = re.sub(r'<c:cat>(.*?)</c:cat>', _swap, xml, flags=re.DOTALL)
                NS_A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
                NOFILL = '<a:noFill ' + NS_A + '/>'
                def _hollow_sppr(m):
                    inner = m.group(1)
                    inner = re.sub(r'<a:solidFill.*?</a:solidFill>', '', inner, flags=re.DOTALL)
                    if 'noFill' not in inner:
                        inner = NOFILL + inner
                    return '<c:spPr>' + inner + '</c:spPr>'
                def _hollow_marker(m):
                    return re.sub(r'<c:spPr>(.*?)</c:spPr>', _hollow_sppr,
                                  m.group(0), flags=re.DOTALL)
                xml = re.sub(r'<c:marker>.*?</c:marker>', _hollow_marker,
                             xml, flags=re.DOTALL)
                data = xml.encode('utf-8')
            zout.writestr(item, data)
    out.seek(0)
    return out


def _sane_sheet(name, used, ml=28):
    safe = re.sub(r'[/\\?\*\[\]:]+', '_', str(name)).strip()[:ml] or 'Sheet'
    base, n = safe, 2
    while safe in used:
        safe = base[:ml-2] + '_' + str(n)
        n += 1
    return safe


@st.cache_data(show_spinner=False)
def comparator_to_excel(df):
    """Export Fitch Comparator data to Excel with line charts."""
    wb = Workbook()
    wb.remove(wb.active)
    used_names = set()

    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )
    header_font_white = Font(bold=True, size=10, color="FFFFFF")
    header_fill = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    num_fmt = '#,##0.00'

    indicators = df["indicator"].unique()

    for ind in indicators:
        idf = df[df["indicator"] == ind].copy()
        if idf.empty:
            continue

        pivot = idf.pivot_table(
            index="year", columns="country_name", values="value", aggfunc="first"
        )
        year_order = idf.drop_duplicates("year").set_index("year")["year_num"]
        sort_keys = pivot.index.to_series().map(lambda y: year_order.get(y, 0))
        pivot = pivot.iloc[sort_keys.values.argsort()]

        sheet_name = _sane_sheet(ind, used_names)
        used_names.add(sheet_name)
        ws = wb.create_sheet(title=sheet_name)

        ws.cell(row=1, column=1, value=ind).font = Font(bold=True, size=12)

        ws.cell(row=3, column=1, value="Year")
        ws['A3'].font = header_font_white
        ws['A3'].fill = header_fill
        ws['A3'].border = thin_border
        for ci, country in enumerate(pivot.columns, 2):
            cell = ws.cell(row=3, column=ci, value=country)
            cell.font = header_font_white
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

        for ri, (year_label, row_data) in enumerate(pivot.iterrows(), 4):
            ws.cell(row=ri, column=1, value=str(year_label)).border = thin_border
            for ci, country in enumerate(pivot.columns, 2):
                val = row_data.get(country)
                cell = ws.cell(row=ri, column=ci)
                if pd.notna(val):
                    cell.value = float(val)
                    cell.number_format = num_fmt
                cell.alignment = Alignment(horizontal="center")
                cell.border = thin_border

        last_data_row = 3 + len(pivot)
        n_countries = len(pivot.columns)

        if len(pivot) >= 2 and n_countries >= 1:
            chart = LineChart()
            chart.title = ind
            chart.width = 28
            chart.height = 14
            chart.style = 10
            cats = Reference(ws, min_col=1, min_row=4, max_row=last_data_row)
            chart.set_categories(cats)
            for ci in range(2, 2 + n_countries):
                data_ref = Reference(ws, min_col=ci, min_row=3, max_row=last_data_row)
                chart.add_data(data_ref, titles_from_data=True)
            for s in chart.series:
                s.graphicalProperties.line.width = 22000
                s.marker.symbol = "circle"
                s.marker.size = 5
                s.smooth = False
            ws.add_chart(chart, f"A{last_data_row + 2}")

        for col_cells in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 3, 25)

    # Summary sheet
    summary_name = _sane_sheet("Dados_completos", used_names)
    used_names.add(summary_name)
    ws_sum = wb.create_sheet(title=summary_name, index=0)
    display_cols = [c for c in ["section", "country_name", "country_code", "lt_fc_rating",
                                "indicator", "unit", "year", "value"] if c in df.columns]
    export_df = df.sort_values(        
        [c for c in ["section", "country_name", "indicator", "year_num"] if c in 
df.columns]    
    )[display_cols]
    for ci, col_name in enumerate(display_cols, 1):
        cell = ws_sum.cell(row=1, column=ci, value=col_name)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.border = thin_border
    for ri, row_data in enumerate(export_df.itertuples(index=False), 2):
        for ci, val in enumerate(row_data, 1):
            cell = ws_sum.cell(row=ri, column=ci)
            if pd.notna(val):
                cell.value = float(val) if isinstance(val, (int, float, np.floating, np.integer)) else str(val)
            cell.border = thin_border
            if isinstance(val, (int, float, np.floating, np.integer)):
                cell.number_format = num_fmt
                cell.alignment = Alignment(horizontal="center")
    for col_cells in ws_sum.columns:
        max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
        ws_sum.column_dimensions[col_cells[0].column_letter].width = min(max_len + 3, 30)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fixed = _fix_strref_in_zip(buf)
    return fixed.read()


# ============================================================
# Comparator UI – Filters
# ============================================================

def build_comparator_filters(df):
    st.subheader("🔍 Filtros do Comparator")
    c1, c2 = st.columns(2)
    with c1:
        entity_type = st.radio(
            "Tipo de entidade", ["Países", "Medianas/Grupos", "Todos"],
            horizontal=True, key="fc_entity_type",
        )
    if entity_type == "Países":
        df = df[df["entity_type"] == "COUNTRY"]
    elif entity_type == "Medianas/Grupos":
        df = df[df["entity_type"] != "COUNTRY"]

    with c2:
        all_ratings = sorted(df["lt_fc_rating"].dropna().unique().tolist())
        sel_ratings = st.multiselect("LT FC Rating", options=all_ratings, default=[], key="fc_ratings")
    if sel_ratings:
        df = df[df["lt_fc_rating"].isin(sel_ratings)]

    c3, c4 = st.columns(2)
    with c3:
        sections = sorted(df["section"].unique())
        sel_sections = st.multiselect("Seções", sections,
            default=sections[:3] if len(sections) >= 3 else sections, key="fc_sections")
    if sel_sections:
        df = df[df["section"].isin(sel_sections)]

    with c4:
        countries = sorted(df["country_name"].unique())
        default_countries = [c for c in ["Brazil", "Mexico", "Colombia", "Chile", "Peru"]
                            if c in countries][:5] or countries[:5]
        sel_countries = st.multiselect("Países / Grupos", countries,
            default=default_countries, key="fc_countries")
    if sel_countries:
        df = df[df["country_name"].isin(sel_countries)]

    all_indicators = sorted(df["indicator"].unique())
    sel_indicators = st.multiselect("Indicadores", options=all_indicators, default=[], key="fc_indicators",
        help="Deixe vazio para considerar todos.")
    if sel_indicators:
        df = df[df["indicator"].isin(sel_indicators)]

    valid_years = df["year_num"].dropna()
    if not valid_years.empty:
        year_min, year_max = int(valid_years.min()), int(valid_years.max())
    else:
        year_min, year_max = 2015, 2028

    c5, c6 = st.columns(2)
    with c5:
        sel_year_range = st.slider("Faixa de anos", min_value=year_min, max_value=year_max,
            value=(year_min, year_max), key="fc_years")
    df = df[df["year_num"].between(sel_year_range[0], sel_year_range[1], inclusive="both")]

    with c6:
        forecast_mode = st.radio("Período", ["Todos", "Somente históricos", "Somente projeções"],
            index=0, key="fc_forecast", horizontal=True)
    if forecast_mode == "Somente históricos":
        df = df[~df["is_forecast"]]
    elif forecast_mode == "Somente projeções":
        df = df[df["is_forecast"]]

    return df


# ============================================================
# Comparator UI – Dashboard (line charts)
# ============================================================

def render_comparator_dashboard(df):
    st.subheader("📊 Dashboard – Fitch Comparator")
    if df.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    indicators = sorted(df["indicator"].unique())
    chart_df = df[~df.get("is_average", pd.Series(False, index=df.index))].copy()
    chart_df = chart_df.sort_values("year_num")

    for ind in indicators:
        idf = chart_df[chart_df["indicator"] == ind].copy()
        if idf.empty:
            continue
        unit = idf["unit"].dropna().iloc[0] if "unit" in idf.columns and not idf["unit"].dropna().empty else ""
        title = f"{ind}" + (f" ({unit})" if unit and unit.lower() not in ("none", "nan", "") else "")
        fig = px.line(idf, x="year", y="value", color="country_name", markers=True, title=title,
            labels={"value": "", "year": "", "country_name": "País"})
        fig.update_traces(mode="lines+markers")
        fig.update_layout(hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
            margin=dict(l=40, r=20, t=50, b=20))
        st_plotly_chart_compat(fig)

    st.markdown("---")
    _c1, _c2 = st.columns(2)
    with _c1:
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Baixar CSV", data=csv_data,
            file_name="fitch_comparator_filtrado.csv", mime="text/csv", key="dl_csv_dash")
    with _c2:
        st.download_button("⬇️ Baixar Excel (.xlsx com gráficos)",
            data=comparator_to_excel(df), file_name="fitch_comparator_filtrado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_excel_dash")


# ============================================================
# Comparator UI – Table
# ============================================================

def render_comparator_table(df):
    st.subheader("📋 Dados em tabela – Fitch Comparator")
    if df.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    view_mode = st.radio("Visualização", ["Longa (recomendada)", "Pivotada"],
        horizontal=True, index=0, key="fc_view_mode")

    long_df = df.sort_values(
        [c for c in ["section", "country_name", "indicator", "year_num"] if c in df.columns]
    ).copy()

    if view_mode == "Longa (recomendada)":
        display_cols = [c for c in ["section", "country_name", "country_code", "lt_fc_rating",
            "indicator", "unit", "year", "value"] if c in long_df.columns]
        display_df = long_df[display_cols]
    else:
        pivot_idx = [c for c in ["section", "country_name", "country_code",
            "lt_fc_rating", "indicator"] if c in long_df.columns]
        display_df = long_df.pivot_table(
            index=pivot_idx, columns="year", values="value", aggfunc="first"
        ).reset_index()

    st_dataframe_compat(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    _c1, _c2 = st.columns(2)
    with _c1:
        csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Baixar CSV", data=csv_data,
            file_name="fitch_comparator_tabela.csv", mime="text/csv", key="dl_csv_tbl")
    with _c2:
        st.download_button("⬇️ Baixar Excel (.xlsx com gráficos)",
            data=comparator_to_excel(long_df), file_name="fitch_comparator_tabela.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_excel_tbl")


# ============================================================
# Methodology rendering
# ============================================================

def render_methodology_overview():
    st.markdown("""
### Fitch Sovereign Rating Methodology

O modelo soberano da Fitch combina:
- **SRM (Sovereign Rating Model)**: modelo quantitativo com 18 variáveis
  agrupadas em 4 pilares, gerando um score numérico.
- **QO (Qualitative Overlay)**: ajuste qualitativo de até ±3 notches
  (extensível em crises), aplicado pilar a pilar.
- **Ratings finais**: LT FC IDR → LT LC IDR → ST FC IDR → ST LC IDR.

#### Pilares do SRM

| Pilar | Peso aprox. |
|-------|-------------|
| I. Structural Features | ~53% |
| II. Macroeconomic Performance | ~10% |
| III. Public Finances | ~19% |
| IV. External Finances | ~17% |

#### Intercepto
O intercepto OLS é **{intercept:.3f}**.

#### Escala
O score do SRM mapeia para a escala de rating usando arredondamento:
- 16 = AAA, 15 = AA+, ..., 1 = B-
- Abaixo de 1 → CCC+
    """.format(intercept=INTERCEPT))


def render_methodology_pillar(pillar_key):
    st.subheader(PILLAR_LABELS[pillar_key])
    st.caption("Insira os valores SRM-ready para este pilar.")
    data = st.session_state["_srm_data"]
    rows = []
    for var_key, meta in SRM_VARIABLES[pillar_key].items():
        value_raw = safe_number_input(var_key, meta["label"],
            data.get(var_key, 0.0), meta["help"])
        contribution = float(value_raw) * float(meta["coefficient"])
        rows.append({
            "Variável": meta["label"], "Valor": value_raw,
            "Coeficiente": meta["coefficient"], "Peso (%)": meta["weight"],
            "Contribuição": contribution,
        })
    rdf = pd.DataFrame(rows)
    st.dataframe(rdf, use_container_width=True, hide_index=True)
    st.metric("Subtotal do pilar", f"{rdf['Contribuição'].sum():.3f}")
    # ── QO for this pillar ──
    st.markdown("---")
    st.markdown("#### Qualitative Overlay (QO)")
    qo_key = f"qo_{pillar_key}"
    qo_data = st.session_state["_qo_data"]
    current_qo = qo_data.get(qo_key, 0)
    qo_opts = list(QO_GUIDANCE.keys())
    cur_idx = qo_opts.index(current_qo) if current_qo in qo_opts else 2
    new_qo = st.selectbox(
        f"QO – {PILLAR_LABELS[pillar_key]}",
        options=qo_opts, index=cur_idx,
        format_func=lambda x: f"{x:+d}  —  {QO_GUIDANCE[x]}",
    )
    qo_data[qo_key] = new_qo
    if pillar_key in QO_FACTORS:
        with st.expander("Fatores considerados"):
            for fct in QO_FACTORS[pillar_key]:
                st.write(f"- {fct}")
    # ── Resultado com ajuste ──
    st.markdown("---")
    st.markdown("#### Resultado com ajuste")
    _inputs = get_clean_srm_inputs()
    _srm_score, _ = compute_srm(_inputs)
    _adjustments = {
        "structural": int(qo_data.get("qo_structural", 0)),
        "macro": int(qo_data.get("qo_macro", 0)),
        "public_finances": int(qo_data.get("qo_public_finances", 0)),
        "external": int(qo_data.get("qo_external", 0)),
    }
    _crisis_ext = bool(st.session_state.get("_qo_crisis", False))
    _qo_total = clamp_qo(_adjustments, _crisis_ext)
    _final_score = _srm_score + _qo_total
    _lt_fc_idr = score_to_lt_rating(_final_score)
    _rc1, _rc2, _rc3 = st.columns(3)
    _rc1.metric("SRM Score", f"{_srm_score:.2f}")
    _rc2.metric("QO Total", f"{_qo_total:+d}")
    _rc3.metric("LT FC IDR (estimado)", _lt_fc_idr, delta=f"score {_final_score:.2f}")


def render_methodology_qo():
    st.subheader("Qualitative Overlay (QO) – Resumo")
    st.caption("Os ajustes QO por pilar estão dentro de cada seção de pilar. Aqui, apenas a opção de extensão de crise.")
    qo_data = st.session_state.get("_qo_data", {})
    for pk in ["structural", "macro", "public_finances", "external"]:
        v = qo_data.get(f"qo_{pk}", 0)
        st.write(f"- **{PILLAR_LABELS[pk]}**: {v:+d}")
    st.markdown("---")
    crisis = st.checkbox(
        "Crisis extension (permite QO fora de ±3)",
        value=bool(st.session_state.get("_qo_crisis", False)),
    )
    st.session_state["_qo_crisis"] = crisis


def render_methodology_results():
    st.subheader("Resultados do Modelo")
    inputs = get_clean_srm_inputs()
    srm_score, details = compute_srm(inputs)

    qo_data = st.session_state.get("_qo_data", {})
    adjustments = {
        "structural": int(qo_data.get("qo_structural", 0)),
        "macro": int(qo_data.get("qo_macro", 0)),
        "public_finances": int(qo_data.get("qo_public_finances", 0)),
        "external": int(qo_data.get("qo_external", 0)),
    }
    crisis_ext = bool(st.session_state.get("_qo_crisis", False))
    qo_total = clamp_qo(adjustments, crisis_ext)
    final_score = srm_score + qo_total

    lt_fc_idr = score_to_lt_rating(final_score)
    lc_adjust = int(st.session_state.get("_lc_adjust", 0))
    lt_lc_idr = apply_notches(lt_fc_idr, -lc_adjust)
    fc_robust = bool(st.session_state.get("_fc_robust", False))
    st_fc_idr = map_short_term(lt_fc_idr, fc_robust)
    st_lc_idr = map_short_term(lt_lc_idr, True)

    c1, c2, c3 = st.columns(3)
    c1.metric("SRM Score", f"{srm_score:.2f}")
    c2.metric("QO Total", f"{qo_total:+d}")
    c3.metric("Final Score", f"{final_score:.2f}")
    st.divider()
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("LT FC IDR", lt_fc_idr)
    r2.metric("LT LC IDR", lt_lc_idr)
    r3.metric("ST FC IDR", st_fc_idr)
    r4.metric("ST LC IDR", st_lc_idr)
    st.divider()
    new_lc = st.number_input(
        "LC notch adjustment vs FC (positivo = LC acima do FC)",
        min_value=-3, max_value=6,
        value=int(st.session_state.get("_lc_adjust", 0)),
        step=1,
    )
    st.session_state["_lc_adjust"] = new_lc
    new_fc = st.checkbox(
        "FC: robust external liquidity (higher ST mapping)",
        value=bool(st.session_state.get("_fc_robust", False)),
    )
    st.session_state["_fc_robust"] = new_fc
    crisis = st.checkbox(
        "Crisis extension (permite QO fora de ±3)",
        value=bool(st.session_state.get("_qo_crisis", False)),
    )
    st.session_state["_qo_crisis"] = crisis
    st.plotly_chart(build_radar(srm_score, qo_total, final_score), use_container_width=True)
    with st.expander("📋 Detalhes do SRM"):
        det_df = pd.DataFrame(details)
        st.dataframe(det_df, use_container_width=True, hide_index=True)


# ============================================================
# MAIN
# ============================================================

def render_fitch():
    init_state()

    st.sidebar.title("📂 Upload")
    st.sidebar.caption("v4 – Metodologia + Comparator (Dashboard & Tabela)")

    uploaded_file = st.sidebar.file_uploader(
        "Envie o XLSB do Fitch Comparator (ou coloque na pasta data/)",
        type=["xlsb"],
        key="xlsb_upload",
    )

    # Determine file bytes: upload takes priority, then local file
    file_bytes = None
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
    else:
        local_xlsb = find_local_xlsb()
        if local_xlsb is not None:
            file_bytes = local_xlsb.read_bytes()
            st.sidebar.info(f"📁 Usando arquivo local: {local_xlsb.name}")

    comparator_df = None
    if file_bytes is not None:
        with st.spinner("Processando XLSB..."):
            comparator_df = parse_fitch_comparator(file_bytes)
        if comparator_df is not None and not comparator_df.empty:
            st.sidebar.success(
                f"✅ {len(comparator_df):,} registros · "
                f"{comparator_df['country_name'].nunique()} entidades · "
                f"{comparator_df['indicator'].nunique()} indicadores"
            )

            # -- Auto-preenchimento SRM ---
            st.sidebar.markdown('---')
            st.sidebar.subheader('Auto-preenchimento SRM')
            _countries = sorted(
                comparator_df[comparator_df["entity_type"] == "COUNTRY"]["country_name"].dropna().unique().tolist()
            )
            _def_idx = 0
            for _i, _c in enumerate(_countries):
                if _c.lower() == "brazil":
                    _def_idx = _i
                    break
            _sel_country = st.sidebar.selectbox("Pais", _countries, index=_def_idx, key="srm_country_select")
            _cyr = st.sidebar.number_input("Ano central", value=2025, min_value=2015, max_value=2030, step=1, key="srm_center_year")
            if st.sidebar.button("Auto-preencher", key="btn_auto_srm"):
                _sv, _lg = extract_country_srm_from_comparator(comparator_df, _sel_country, int(_cyr))
                if _sv:
                    apply_country_data_to_session(_sv)
                    st.session_state["_srm_auto_filled"] = True
                    st.session_state["_srm_auto_log"] = _lg
                    st.session_state["_srm_auto_vals"] = _sv
                    st.session_state["_srm_auto_country"] = _sel_country
            if st.session_state.get("_srm_auto_filled"):
                _acn = st.session_state.get("_srm_auto_country", "")
                with st.sidebar.expander(f"Valores ({_acn})", expanded=False):
                    _vals = st.session_state.get("_srm_auto_vals", {})
                    if _vals:
                        _rws = [{"Var": _k, "Val": round(_v, 4)} for _k, _v in _vals.items()]
                        st.dataframe(pd.DataFrame(_rws), use_container_width=True, hide_index=True)
                    _lgs = st.session_state.get("_srm_auto_log", [])
                    if _lgs:
                        for _l in _lgs:
                            st.text(_l)

        else:
            st.sidebar.error("Não foi possível extrair dados do arquivo.")

    # Main tabs
    tab_met, tab_dash, tab_data = st.tabs([
        "📘 Metodologia",
        "📊 Dashboard",
        "📋 Dados",
    ])

    # ========== TAB 1: Metodologia ==========
    with tab_met:
        st.title("Fitch Sovereign Rating Methodology")
        _nav_opts = [
                "Visão geral",
                PILLAR_LABELS["structural"],
                PILLAR_LABELS["macro"],
                PILLAR_LABELS["public_finances"],
                PILLAR_LABELS["external"],
                "Resultados",
            ]
        _cur_nav = st.session_state.get("_nav_page", "Visão geral")
        _nav_idx = _nav_opts.index(_cur_nav) if _cur_nav in _nav_opts else 0
        sub_page = st.selectbox(
            "Seção", _nav_opts, index=_nav_idx,
            label_visibility="collapsed",
        )
        st.session_state["_nav_page"] = sub_page
        if sub_page == "Visão geral":
            render_methodology_overview()
        elif sub_page == PILLAR_LABELS["structural"]:
            render_methodology_pillar("structural")
        elif sub_page == PILLAR_LABELS["macro"]:
            render_methodology_pillar("macro")
        elif sub_page == PILLAR_LABELS["public_finances"]:
            render_methodology_pillar("public_finances")
        elif sub_page == PILLAR_LABELS["external"]:
            render_methodology_pillar("external")
        elif sub_page == "Resultados":
            render_methodology_results()

    # ========== TAB 2: Dashboard ==========
    with tab_dash:
        st.title("📊 Fitch Global Sovereign Data Comparator – Dashboard")
        if comparator_df is None or comparator_df.empty:
            st.info("⬅️ Envie o arquivo XLSB na barra lateral para ativar o dashboard.")
        else:
            filtered_df = build_comparator_filters(comparator_df)
            render_comparator_dashboard(filtered_df)

    # ========== TAB 3: Dados ==========
    with tab_data:
        st.title("📋 Fitch Global Sovereign Data Comparator – Dados")
        if comparator_df is None or comparator_df.empty:
            st.info("⬅️ Envie o arquivo XLSB na barra lateral para visualizar os dados.")
        else:
            st.markdown("---")
            df_table = comparator_df.copy()

            tc1, tc2 = st.columns(2)
            with tc1:
                entity_type_tbl = st.radio("Tipo de entidade",
                    ["Países", "Medianas/Grupos", "Todos"],
                    horizontal=True, key="fc_entity_type_tbl")
            if entity_type_tbl == "Países":
                df_table = df_table[df_table["entity_type"] == "COUNTRY"]
            elif entity_type_tbl == "Medianas/Grupos":
                df_table = df_table[df_table["entity_type"] != "COUNTRY"]

            with tc2:
                all_ratings_tbl = sorted(df_table["lt_fc_rating"].dropna().unique().tolist())
                sel_ratings_tbl = st.multiselect("LT FC Rating", options=all_ratings_tbl,
                    default=[], key="fc_ratings_tbl")
            if sel_ratings_tbl:
                df_table = df_table[df_table["lt_fc_rating"].isin(sel_ratings_tbl)]

            tc3, tc4 = st.columns(2)
            with tc3:
                sections_tbl = sorted(df_table["section"].unique())
                sel_sections_tbl = st.multiselect("Seções", sections_tbl,
                    default=sections_tbl[:3] if len(sections_tbl) >= 3 else sections_tbl,
                    key="fc_sections_tbl")
            if sel_sections_tbl:
                df_table = df_table[df_table["section"].isin(sel_sections_tbl)]

            with tc4:
                countries_tbl = sorted(df_table["country_name"].unique())
                sel_countries_tbl = st.multiselect("Países", countries_tbl,
                    default=countries_tbl[:10] if len(countries_tbl) >= 10 else countries_tbl,
                    key="fc_countries_tbl")
            if sel_countries_tbl:
                df_table = df_table[df_table["country_name"].isin(sel_countries_tbl)]

            render_comparator_table(df_table)

