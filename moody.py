import streamlit as st
import math

# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

RATING_SCALE = [
    "aaa","aa1","aa2","aa3","a1","a2","a3",
    "baa1","baa2","baa3","ba1","ba2","ba3",
    "b1","b2","b3","caa1","caa2","caa3","ca"
]

ALPHA_CATS = ["aaa","aa","a","baa","ba","b","caa","ca"]
ALPHA_SCORES = {"aaa":1,"aa":3,"a":6,"baa":9,"ba":12,"b":15,"caa":18,"ca":20}

# Numeric score → alphanumeric  (midpoints at integers 1‥20)
def score_to_alpha21(score):
    idx = max(0, min(19, round(score) - 1))
    return RATING_SCALE[idx]

def alpha21_to_score(r):
    return RATING_SCALE.index(r) + 1

def alpha21_to_broad(r):
    for cat in ["caa","baa","aa","ba","ca","a","b"]:   # check longest first
        if r.startswith(cat) and (len(r) == len(cat) or r[len(cat):].isdigit()):
            return cat
    return r

def broad_to_score(cat):
    return ALPHA_SCORES.get(cat, 20)

def score_to_broad(score):
    score = max(1, min(20, round(score)))
    best = "ca"; best_diff = 999
    for cat, sc in ALPHA_SCORES.items():
        if abs(sc - score) < best_diff:
            best_diff = abs(sc - score)
            best = cat
    return best

def clamp_score(score, lo=1.0, hi=20.0):
    return max(lo, min(hi, score))

# ── Quantitative interpolation ────────────────────────────────────────
# Each range list: [(rating, range_lo, range_hi), …], 20 rows aaa→ca
# For the rating at index i, the score midpoint is i+1.
# We interpolate linearly within the value range → score range [i+0.5, i+1.5].

def interpolate_quant(value, ranges, higher_is_better):
    """Return a continuous score 0.5 … 20.5 using linear interpolation."""
    n = len(ranges)
    for i, (rating, rlo, rhi) in enumerate(ranges):
        score_lo = i + 0.5    # top of this band (best end)
        score_hi = i + 1.5    # bottom of this band (worst end)
        is_infinite = (abs(rlo) >= 9999 or abs(rhi) >= 9999)
        if is_infinite:
            # open-ended bucket – check containment
            if (higher_is_better and rhi >= 9999 and value >= rlo):
                return float(i + 1)
            if (higher_is_better and rlo <= -9999 and value <= rhi):
                return float(i + 1)
            if (not higher_is_better and rlo <= -9999 and value <= rhi):
                return float(i + 1)
            if (not higher_is_better and rhi >= 9999 and value >= rlo):
                return float(i + 1)
            continue
        if higher_is_better:
            # higher value → lower (better) score
            if value > rhi:
                continue
            if value < rlo:
                continue
            span = rhi - rlo
            if span == 0:
                return float(i + 1)
            frac = (rhi - value) / span          # 0 at top (best) → 1 at bottom
            return score_lo + frac * (score_hi - score_lo)
        else:
            # lower value → lower (better) score
            if value < rlo:
                continue
            if value > rhi:
                continue
            span = rhi - rlo
            if span == 0:
                return float(i + 1)
            frac = (value - rlo) / span           # 0 at bottom (best) → 1 at top
            return score_lo + frac * (score_hi - score_lo)
    # If value is beyond worst range, return worst score
    return 20.0

# ── Factor 1 quantitative ranges (from Excel: Factor 1 - Table 1) ────
F1_GDP_GROWTH = [
    ("aaa", 5.7, 99999), ("aa1", 5.3, 5.7), ("aa2", 4.9, 5.3),
    ("aa3", 4.4, 4.9), ("a1", 4.0, 4.4), ("a2", 3.7, 4.0),
    ("a3", 3.3, 3.7), ("baa1", 3.0, 3.3), ("baa2", 2.6, 3.0),
    ("baa3", 2.3, 2.6), ("ba1", 2.0, 2.3), ("ba2", 1.8, 2.0),
    ("ba3", 1.6, 1.8), ("b1", 1.3, 1.6), ("b2", 1.0, 1.3),
    ("b3", 0.5, 1.0), ("caa1", 0.0, 0.5), ("caa2", -0.5, 0.0),
    ("caa3", -1.0, -0.5), ("ca", -99999, -1.0),
]

F1_MAD_VOL = [
    ("aaa", -99999, 0.10), ("aa1", 0.10, 0.20), ("aa2", 0.20, 0.30),
    ("aa3", 0.30, 0.40), ("a1", 0.40, 0.50), ("a2", 0.50, 0.60),
    ("a3", 0.60, 0.75), ("baa1", 0.75, 0.90), ("baa2", 0.90, 1.10),
    ("baa3", 1.10, 1.30), ("ba1", 1.30, 1.50), ("ba2", 1.50, 1.80),
    ("ba3", 1.80, 2.10), ("b1", 2.10, 2.50), ("b2", 2.50, 3.00),
    ("b3", 3.00, 3.50), ("caa1", 3.50, 4.00), ("caa2", 4.00, 5.00),
    ("caa3", 5.00, 6.00), ("ca", 6.00, 99999),
]

F1_NOM_GDP = [
    ("aaa", 1000, 99999), ("aa1", 750, 1000), ("aa2", 600, 750),
    ("aa3", 450, 600), ("a1", 330, 450), ("a2", 250, 330),
    ("a3", 190, 250), ("baa1", 140, 190), ("baa2", 100, 140),
    ("baa3", 80, 100), ("ba1", 60, 80), ("ba2", 45, 60),
    ("ba3", 35, 45), ("b1", 25, 35), ("b2", 18, 25),
    ("b3", 10, 18), ("caa1", 5, 10), ("caa2", 2, 5),
    ("caa3", 1, 2), ("ca", -99999, 1),
]

F1_GDP_PC = [
    ("aaa", 48000, 99999), ("aa1", 42000, 48000), ("aa2", 37000, 42000),
    ("aa3", 32000, 37000), ("a1", 27500, 32000), ("a2", 24500, 27500),
    ("a3", 21000, 24500), ("baa1", 19000, 21000), ("baa2", 16000, 19000),
    ("baa3", 14000, 16000), ("ba1", 12000, 14000), ("ba2", 10750, 12000),
    ("ba3", 9500, 10750), ("b1", 8000, 9500), ("b2", 6500, 8000),
    ("b3", 5000, 6500), ("caa1", 3500, 5000), ("caa2", 2000, 3500),
    ("caa3", 1000, 2000), ("ca", -99999, 1000),
]

# ── Factor 3 quantitative ranges (from Excel: Factor 3 - Table 1) ────
F3_GGGD_GDP = [
    ("aaa", -99999, 5), ("aa1", 5, 20), ("aa2", 20, 30),
    ("aa3", 30, 35), ("a1", 35, 40), ("a2", 40, 45),
    ("a3", 45, 50), ("baa1", 50, 55), ("baa2", 55, 60),
    ("baa3", 60, 65), ("ba1", 65, 70), ("ba2", 70, 75),
    ("ba3", 75, 80), ("b1", 80, 90), ("b2", 90, 100),
    ("b3", 100, 120), ("caa1", 120, 130), ("caa2", 130, 140),
    ("caa3", 140, 150), ("ca", 150, 99999),
]

F3_GGGD_REV = [
    ("aaa", -99999, 50), ("aa1", 50, 65), ("aa2", 65, 80),
    ("aa3", 80, 100), ("a1", 100, 115), ("a2", 115, 130),
    ("a3", 130, 150), ("baa1", 150, 175), ("baa2", 175, 200),
    ("baa3", 200, 225), ("ba1", 225, 250), ("ba2", 250, 275),
    ("ba3", 275, 300), ("b1", 300, 350), ("b2", 350, 425),
    ("b3", 425, 500), ("caa1", 500, 600), ("caa2", 600, 750),
    ("caa3", 750, 1000), ("ca", 1000, 99999),
]

F3_INT_REV = [
    ("aaa", -99999, 2), ("aa1", 2, 3), ("aa2", 3, 3.5),
    ("aa3", 3.5, 4.5), ("a1", 4.5, 5.5), ("a2", 5.5, 6.5),
    ("a3", 6.5, 8), ("baa1", 8, 9), ("baa2", 9, 10),
    ("baa3", 10, 12), ("ba1", 12, 14), ("ba2", 14, 16),
    ("ba3", 16, 20), ("b1", 20, 25), ("b2", 25, 30),
    ("b3", 30, 35), ("caa1", 35, 45), ("caa2", 45, 60),
    ("caa3", 60, 80), ("ca", 80, 99999),
]

F3_INT_GDP = [
    ("aaa", -99999, 1), ("aa1", 1, 1.25), ("aa2", 1.25, 1.5),
    ("aa3", 1.5, 1.75), ("a1", 1.75, 2), ("a2", 2, 2.5),
    ("a3", 2.5, 3), ("baa1", 3, 3.5), ("baa2", 3.5, 4),
    ("baa3", 4, 4.5), ("ba1", 4.5, 5), ("ba2", 5, 5.5),
    ("ba3", 5.5, 6.5), ("b1", 6.5, 7.5), ("b2", 7.5, 9),
    ("b3", 9, 10.5), ("caa1", 10.5, 12), ("caa2", 12, 15),
    ("caa3", 15, 20), ("ca", 20, 99999),
]

# ── Factor 4 – Banking Sector Risk matrix ─────────────────────────────
BSR_MATRIX = [
    ["a","a","baa","ba","b","b","ca"],
    ["a","a","baa","baa","ba","b","ca"],
    ["a","a","a","baa","ba","ba","b"],
    ["a","a","a","a","baa","ba","ba"],
    ["aaa","aa","aa","a","a","baa","ba"],
]

def bsce_to_col(r):
    idx = RATING_SCALE.index(r) if r in RATING_SCALE else 19
    if idx <= 6:   return 0
    if idx == 7:   return 1
    if idx == 8:   return 2
    if idx == 9:   return 3
    if idx <= 11:  return 4
    if idx <= 15:  return 5
    return 6

def bank_assets_to_row(pct):
    if pct >= 400: return 0
    if pct >= 230: return 1
    if pct >= 180: return 2
    if pct >= 80:  return 3
    return 4

# ── GFS Matrix (20×20) ────────────────────────────────────────────────
GFS_MATRIX = {
    "aaa": ["aaa","aaa","aaa","aaa","aaa","aa1","aa1","aa1","aa1","aa1","aa1","aa1","aa2","aa2","aa2","aa2","aa2","aa2","aa3","aa3"],
    "aa1": ["aa1","aa1","aa1","aa1","aa1","aa1","aa1","aa2","aa2","aa2","aa2","aa2","aa2","aa2","aa3","aa3","aa3","aa3","aa3","aa3"],
    "aa2": ["aa1","aa1","aa2","aa2","aa2","aa2","aa2","aa2","aa2","aa3","aa3","aa3","aa3","aa3","aa3","aa3","a1","a1","a1","a1"],
    "aa3": ["aa2","aa2","aa2","aa2","aa3","aa3","aa3","aa3","aa3","aa3","aa3","a1","a1","a1","a1","a1","a1","a1","a2","a2"],
    "a1":  ["aa2","aa2","aa3","aa3","aa3","aa3","a1","a1","a1","a1","a2","a2","a2","a2","a3","a3","a3","a3","baa1","baa1"],
    "a2":  ["aa3","aa3","aa3","a1","a1","a1","a1","a2","a2","a2","a2","a3","a3","a3","a3","baa1","baa1","baa1","baa1","baa2"],
    "a3":  ["aa3","a1","a1","a1","a1","a2","a2","a2","a2","a3","a3","a3","a3","baa1","baa1","baa1","baa1","baa2","baa2","baa2"],
    "baa1":["a1","a1","a2","a2","a2","a2","a3","a3","a3","a3","baa1","baa1","baa1","baa1","baa2","baa2","baa2","baa2","baa3","baa3"],
    "baa2":["a1","a1","a2","a2","a2","a3","a3","a3","baa1","baa1","baa1","baa2","baa2","baa2","baa3","baa3","baa3","ba1","ba1","ba1"],
    "baa3":["a1","a2","a2","a2","a3","a3","a3","baa1","baa1","baa1","baa2","baa2","baa3","baa3","baa3","ba1","ba1","ba1","ba2","ba2"],
    "ba1": ["a2","a2","a3","a3","a3","baa1","baa1","baa1","baa2","baa2","baa2","baa3","baa3","baa3","ba1","ba1","ba1","ba2","ba2","ba2"],
    "ba2": ["a2","a3","a3","a3","baa1","baa1","baa1","baa2","baa2","baa2","baa3","baa3","ba1","ba1","ba1","ba2","ba2","ba2","ba3","ba3"],
    "ba3": ["baa1","baa1","baa2","baa2","baa2","baa2","baa3","baa3","baa3","baa3","ba1","ba1","ba1","ba1","ba2","ba2","ba2","ba2","ba3","ba3"],
    "b1":  ["baa2","baa2","baa2","baa2","baa3","baa3","baa3","baa3","ba1","ba1","ba1","ba1","ba2","ba2","ba2","ba2","ba3","ba3","ba3","ba3"],
    "b2":  ["baa2","baa2","baa3","baa3","baa3","baa3","ba1","ba1","ba1","ba1","ba2","ba2","ba2","ba2","ba3","ba3","ba3","ba3","b1","b1"],
    "b3":  ["baa3","baa3","baa3","ba1","ba1","ba1","ba1","ba2","ba2","ba2","ba2","ba3","ba3","ba3","ba3","b1","b1","b1","b1","b2"],
    "caa1":["ba2","ba2","ba2","ba2","ba3","ba3","ba3","ba3","ba3","ba3","b1","b1","b1","b1","b1","b1","b1","b2","b2","b2"],
    "caa2":["ba3","ba3","ba3","ba3","ba3","ba3","b1","b1","b1","b1","b1","b1","b2","b2","b2","b2","b2","b2","b2","b3"],
    "caa3":["ba3","b1","b1","b1","b1","b1","b1","b1","b2","b2","b2","b2","b2","b2","b3","b3","b3","b3","b3","b3"],
    "ca":  ["b1","b1","b1","b2","b2","b2","b2","b2","b2","b2","b3","b3","b3","b3","b3","b3","caa1","caa1","caa1","caa1"],
}

# ── Final Matrix (SETR alpha × GFS alphanumeric, 17 cols aaa→caa1) ────
FINAL_COLS = ["aaa","aa1","aa2","aa3","a1","a2","a3","baa1","baa2","baa3","ba1","ba2","ba3","b1","b2","b3","caa1"]
FINAL_MATRIX = {
    "aaa": ["aaa","aa1","aa2","aa3","a1","a2","a3","baa1","baa2","baa3","ba1","ba2","ba3","b1","b2","b3","caa1"],
    "aa":  ["aaa","aa1","aa2","aa3","a1","a2","a3","baa1","baa2","baa3","ba1","ba2","ba3","b1","b2","b3","caa1"],
    "a":   ["aaa","aa1","aa2","aa3","a1","a2","a3","baa2","baa3","ba1","ba2","ba3","b2","b3","caa1","caa2","caa3"],
    "baa": ["aaa","aa1","aa2","aa3","a2","a3","baa1","baa2","ba1","ba2","ba3","b1","b3","caa1","caa2","caa3","ca"],
    "ba":  ["aa1","aa2","aa3","a1","a2","baa1","baa2","baa3","ba2","ba3","b1","b2","b3","caa1","caa2","caa3","ca"],
    "b":   ["aa2","aa3","a1","a2","a3","baa2","ba1","ba2","ba3","b1","b2","b3","caa1","caa2","caa3","caa3","ca"],
    "caa": ["aa3","a1","a2","a3","baa1","baa3","ba1","ba2","b1","b2","b3","caa1","caa2","caa3","caa3","caa3","ca"],
    "ca":  ["a1","a2","a3","baa1","baa2","ba1","ba2","ba3","b1","b2","b3","caa1","caa2","caa3","caa3","caa3","ca"],
}

# ── Rating color helper ────────────────────────────────────────────────
def rating_color(rating):
    idx = RATING_SCALE.index(rating) if rating in RATING_SCALE else 19
    if idx <= 2:   return "#15803d"
    if idx <= 6:   return "#22c55e"
    if idx <= 9:   return "#86efac"
    if idx <= 12:  return "#facc15"
    if idx <= 15:  return "#f97316"
    return "#ef4444"

def rating_badge(rating):
    c = rating_color(rating)
    fg = "#fff" if RATING_SCALE.index(rating) <= 6 or RATING_SCALE.index(rating) > 12 else "#1a1a2e"
    return f'<span style="display:inline-block;padding:4px 14px;border-radius:6px;background:{c};color:{fg};font-weight:700;font-size:1.05rem;text-transform:uppercase;">{rating.upper()}</span>'

# ═══════════════════════════════════════════════════════════════════════
# STREAMLIT APP
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Moody's Sovereign Rating Model", layout="wide",
                   page_icon="📊")

st.markdown("""
<style>
    .main {background-color: #f9f9f9;}
    h1, h2, h3, h4 {color: #1a1a2e;}
    div[data-testid="stMetricValue"] {font-size: 1.6rem; font-weight: 700;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────
st.sidebar.title("🏛️ Moody's Sovereign Model")
page = st.sidebar.selectbox("Navegação", [
    "📊 Visão Geral",
    "1️⃣ Economic Strength",
    "2️⃣ Institutions & Governance",
    "3️⃣ Fiscal Strength",
    "4️⃣ Susceptibility to Event Risk",
])

# ═══════════════════════════════════════════════════════════════════════
# FACTOR CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════

def calc_factor1(gdp_growth, mad_vol, nom_gdp, gdp_pc, adj):
    s_gdp = interpolate_quant(gdp_growth, F1_GDP_GROWTH, higher_is_better=True)
    s_mad = interpolate_quant(mad_vol,     F1_MAD_VOL,    higher_is_better=False)
    s_nom = interpolate_quant(nom_gdp,     F1_NOM_GDP,    higher_is_better=True)
    s_pc  = interpolate_quant(gdp_pc,      F1_GDP_PC,     higher_is_better=True)
    weighted = s_gdp * 0.25 + s_mad * 0.10 + s_nom * 0.30 + s_pc * 0.35
    final = clamp_score(weighted + adj)
    return {"gdp": s_gdp, "mad": s_mad, "nom": s_nom, "pc": s_pc,
            "weighted": weighted, "adj": adj, "final": final,
            "rating": score_to_alpha21(round(final))}

def calc_factor2(legexec, civiljud, fiscal, monetary, default_hist, adj_other):
    s = {
        "legexec":  broad_to_score(legexec),
        "civiljud": broad_to_score(civiljud),
        "fiscal":   broad_to_score(fiscal),
        "monetary": broad_to_score(monetary),
    }
    weighted = s["legexec"]*0.20 + s["civiljud"]*0.20 + s["fiscal"]*0.30 + s["monetary"]*0.30
    adj = default_hist + adj_other
    final = clamp_score(weighted + adj)
    return {"scores": s, "weighted": weighted, "adj": adj, "final": final,
            "rating": score_to_alpha21(round(final))}

def calc_factor3(gggd_gdp, gggd_rev, int_rev, int_gdp,
                 hist_chg, exp_chg, fc_debt, other_psd, gov_assets, adj_other):
    s1 = interpolate_quant(gggd_gdp, F3_GGGD_GDP, higher_is_better=False)
    s2 = interpolate_quant(gggd_rev, F3_GGGD_REV, higher_is_better=False)
    s3 = interpolate_quant(int_rev,  F3_INT_REV,   higher_is_better=False)
    s4 = interpolate_quant(int_gdp,  F3_INT_GDP,   higher_is_better=False)
    weighted = (s1 + s2 + s3 + s4) / 4.0

    # Adj – Historical Change in Debt/GDP (p.p.)
    a_hist = 0
    if hist_chg >= 50:    a_hist = -2
    elif hist_chg >= 25:  a_hist = -1

    # Adj – Expected Change in Debt/GDP (p.p.)
    a_exp = 0
    if exp_chg < -5:      a_exp = 1
    elif exp_chg <= 5:    a_exp = 0
    elif exp_chg <= 10:   a_exp = -1
    elif exp_chg <= 15:   a_exp = -2
    else:                 a_exp = -3   # ≥50 in original, but catchall here

    # Adj – FC Debt / GGGD
    a_fc = 0
    if fc_debt >= 60:     a_fc = -6
    elif fc_debt >= 50:   a_fc = -5
    elif fc_debt >= 40:   a_fc = -4
    elif fc_debt >= 30:   a_fc = -3
    elif fc_debt >= 25:   a_fc = -2
    elif fc_debt >= 20:   a_fc = -1

    # Adj – Other Public Sector Debt / GDP
    a_opsd = 0
    if other_psd >= 55:   a_opsd = -3
    elif other_psd >= 40: a_opsd = -2
    elif other_psd >= 20: a_opsd = -1

    # Adj – Gov Financial Assets / GDP
    a_ga = 0
    if gov_assets >= 100:  a_ga = 4
    elif gov_assets >= 50: a_ga = 3
    elif gov_assets >= 25: a_ga = 2
    elif gov_assets >= 10: a_ga = 1

    total_adj = a_hist + a_exp + a_fc + a_opsd + a_ga + adj_other
    final = clamp_score(weighted + total_adj)
    return {"s1":s1,"s2":s2,"s3":s3,"s4":s4,
            "weighted":weighted,"a_hist":a_hist,"a_exp":a_exp,
            "a_fc":a_fc,"a_opsd":a_opsd,"a_ga":a_ga,"a_other":adj_other,
            "total_adj":total_adj,"final":final,
            "rating": score_to_alpha21(round(final))}

def calc_factor4(political, ease_access, high_refin,
                 bsce, bank_assets, bank_adj,
                 ext_vuln, ext_adj, f_other):
    pol_score = broad_to_score(political)

    ease_score = broad_to_score(ease_access)
    liq_score = clamp_score(ease_score - high_refin)  # high_refin is 0/1/2 making it worse
    liq_alpha = score_to_broad(liq_score)

    col_idx = bsce_to_col(bsce)
    row_idx = bank_assets_to_row(bank_assets)
    bsr_alpha = BSR_MATRIX[row_idx][col_idx]
    bsr_score = broad_to_score(bsr_alpha)
    bsr_final_score = clamp_score(bsr_score + bank_adj)
    bsr_final_alpha = score_to_broad(bsr_final_score)

    ext_score = broad_to_score(ext_vuln)
    ext_final_score = clamp_score(ext_score + ext_adj)
    ext_final_alpha = score_to_broad(ext_final_score)

    # SETR = worst (max score) of 4 sub-factors
    all_scores = [pol_score, liq_score, bsr_final_score, ext_final_score]
    setr_score = max(all_scores)
    setr_score_adj = clamp_score(setr_score + f_other)
    setr_alpha = score_to_broad(setr_score_adj)

    return {
        "pol_alpha": political, "pol_score": pol_score,
        "liq_alpha": liq_alpha, "liq_score": liq_score,
        "bsr_alpha": bsr_alpha, "bsr_final_alpha": bsr_final_alpha,
        "bsr_score": bsr_score, "bsr_final_score": bsr_final_score,
        "ext_alpha": ext_vuln, "ext_final_alpha": ext_final_alpha,
        "ext_score": ext_score, "ext_final_score": ext_final_score,
        "setr_alpha": setr_alpha, "setr_score": setr_score_adj,
        "sub_scores": {"Political": political, "Gov Liquidity": liq_alpha,
                       "Banking Sector": bsr_final_alpha, "External Vuln": ext_final_alpha},
    }

def calc_final(f1, f2, f3, f4):
    er_score = round((f1["final"] + f2["final"]) / 2)
    er_rating = score_to_alpha21(er_score)

    fs_idx = RATING_SCALE.index(f3["rating"])
    gfs_rating = GFS_MATRIX[er_rating][fs_idx]

    setr_alpha = f4["setr_alpha"]
    if gfs_rating in FINAL_COLS:
        gfs_col_idx = FINAL_COLS.index(gfs_rating)
    else:
        gfs_col_idx = min(RATING_SCALE.index(gfs_rating), len(FINAL_COLS) - 1)
    final_rating = FINAL_MATRIX.get(setr_alpha, FINAL_MATRIX["ca"])[min(gfs_col_idx, 16)]

    final_idx = RATING_SCALE.index(final_rating)
    range_lo = RATING_SCALE[max(0, final_idx - 1)]
    range_hi = RATING_SCALE[min(19, final_idx + 1)]

    return {
        "er_score": er_score, "er_rating": er_rating,
        "gfs_rating": gfs_rating,
        "final_rating": final_rating,
        "range": f"{range_lo.upper()} – {range_hi.upper()}",
    }

# ═══════════════════════════════════════════════════════════════════════
# BUILD ALL PAGES – inputs + auto-compute
# ═══════════════════════════════════════════════════════════════════════

# ---------- Factor 1 inputs (always present for computation) ----------
if page == "1️⃣ Economic Strength":
    st.title("1️⃣ Factor 1 – Economic Strength")
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        f1_gdp = st.number_input("Average Real GDP Growth (%)", value=2.2,
                                  min_value=-10.0, max_value=20.0, step=0.1, format="%.2f", key="k_f1_gdp")
    with c2:
        f1_mad = st.number_input("MAD Volatility in Real GDP Growth", value=1.80,
                                  min_value=0.0, max_value=10.0, step=0.01, format="%.2f", key="k_f1_mad")
    c3, c4 = st.columns(2)
    with c3:
        f1_nom = st.number_input("Nominal GDP (US$ bn)", value=2191.1,
                                  min_value=0.0, max_value=99999.0, step=1.0, format="%.1f", key="k_f1_nom")
    with c4:
        f1_pc = st.number_input("GDP per Capita (PPP, US$)", value=21052.0,
                                 min_value=0.0, max_value=200000.0, step=100.0, format="%.0f", key="k_f1_pc")
    adj_opts = list(range(-9, 10))
    f1_adj = st.selectbox("Adjustment – Other (notches)", options=adj_opts,
                          index=adj_opts.index(0), key="k_f1_adj")

    res1 = calc_factor1(f1_gdp, f1_mad, f1_nom, f1_pc, f1_adj)

    st.markdown("---")
    st.markdown(f"**Rating:** {rating_badge(res1['rating'])}", unsafe_allow_html=True)
    st.markdown(f"**Weighted Score:** {res1['weighted']:.2f}  |  **Adjusted:** {res1['final']:.2f}")
    st.caption("Pesos: GDP Growth 25% · MAD Vol 10% · Nominal GDP 30% · GDP per Capita 35%")

    st.markdown("---")
    st.subheader("Sub-scores")
    cols = st.columns(4)
    labels = ["GDP Growth","MAD Vol","Nominal GDP","GDP per Capita"]
    vals = [res1["gdp"], res1["mad"], res1["nom"], res1["pc"]]
    for i, (lb, v) in enumerate(zip(labels, vals)):
        with cols[i]:
            r = score_to_alpha21(round(v))
            st.metric(lb, f"{v:.2f} → {r.upper()}")

    # Store for cross-factor use
    st.session_state["f1_res"] = res1

elif page == "2️⃣ Institutions & Governance":
    st.title("2️⃣ Factor 2 – Institutions & Governance")
    st.markdown("---")
    alpha_opts = [c.upper() for c in ALPHA_CATS]

    c1, c2 = st.columns(2)
    with c1:
        f2_le = st.selectbox("Quality of Legislative & Executive Institutions (20%)",
                             options=alpha_opts, index=3, key="k_f2_le")
    with c2:
        f2_cj = st.selectbox("Strength of Civil Society & Judiciary (20%)",
                             options=alpha_opts, index=3, key="k_f2_cj")
    c3, c4 = st.columns(2)
    with c3:
        f2_fp = st.selectbox("Fiscal Policy Effectiveness (30%)",
                             options=alpha_opts, index=4, key="k_f2_fp")
    with c4:
        f2_mp = st.selectbox("Monetary & Macroeconomic Policy Effectiveness (30%)",
                             options=alpha_opts, index=3, key="k_f2_mp")

    st.markdown("---")
    c5, c6 = st.columns(2)
    with c5:
        f2_dh = st.selectbox("Adj – Default History (notches)", options=[0,-1,-2,-3],
                             index=0, key="k_f2_dh")
    with c6:
        adj3 = list(range(-3, 4))
        f2_ao = st.selectbox("Adj – Other (notches)", options=adj3,
                             index=adj3.index(0), key="k_f2_ao")

    res2 = calc_factor2(f2_le.lower(), f2_cj.lower(), f2_fp.lower(), f2_mp.lower(), f2_dh, f2_ao)

    st.markdown("---")
    st.markdown(f"**Rating:** {rating_badge(res2['rating'])}", unsafe_allow_html=True)
    st.markdown(f"**Weighted Score:** {res2['weighted']:.2f}  |  **Adjusted:** {res2['final']:.2f}")

    st.session_state["f2_res"] = res2

elif page == "3️⃣ Fiscal Strength":
    st.title("3️⃣ Factor 3 – Fiscal Strength")
    st.markdown("---")

    st.subheader("Indicadores Quantitativos")
    c1, c2 = st.columns(2)
    with c1:
        f3_gg = st.number_input("GGGD / GDP (%)", value=73.8,
                                min_value=0.0, max_value=500.0, step=0.1, format="%.1f", key="k_f3_gg")
    with c2:
        f3_gr = st.number_input("GGGD / Revenue (%)", value=196.9,
                                min_value=0.0, max_value=2000.0, step=0.1, format="%.1f", key="k_f3_gr")
    c3, c4 = st.columns(2)
    with c3:
        f3_ir = st.number_input("Interest Payments / Revenue (%)", value=14.8,
                                min_value=0.0, max_value=100.0, step=0.1, format="%.1f", key="k_f3_ir")
    with c4:
        f3_ig = st.number_input("Interest Payments / GDP (%)", value=5.6,
                                min_value=0.0, max_value=50.0, step=0.1, format="%.1f", key="k_f3_ig")

    st.markdown("---")
    st.subheader("Variáveis de Ajuste")
    c5, c6, c7 = st.columns(3)
    with c5:
        f3_hc = st.number_input("Hist. Change Debt/GDP (p.p., t-8→t)", value=8.3,
                                min_value=-100.0, max_value=200.0, step=0.1, format="%.1f", key="k_f3_hc")
    with c6:
        f3_ec = st.number_input("Exp. Change Debt/GDP (p.p., t→t+2)", value=6.3,
                                min_value=-100.0, max_value=200.0, step=0.1, format="%.1f", key="k_f3_ec")
    with c7:
        f3_fc = st.number_input("FC Debt / GGGD (%)", value=3.5,
                                min_value=0.0, max_value=100.0, step=0.1, format="%.1f", key="k_f3_fc")
    c8, c9, c10 = st.columns(3)
    with c8:
        f3_op = st.number_input("Other Public Sector Debt / GDP (%)", value=0.0,
                                min_value=0.0, max_value=200.0, step=0.1, format="%.1f", key="k_f3_op")
    with c9:
        f3_ga = st.number_input("Gov. Financial Assets / GDP (%)", value=15.1,
                                min_value=0.0, max_value=500.0, step=0.1, format="%.1f", key="k_f3_ga")
    with c10:
        adj3 = list(range(-3, 4))
        f3_adj = st.selectbox("Adj – Other (notches)", options=adj3,
                              index=adj3.index(-1), key="k_f3_adj")

    res3 = calc_factor3(f3_gg, f3_gr, f3_ir, f3_ig, f3_hc, f3_ec, f3_fc, f3_op, f3_ga, f3_adj)

    st.markdown("---")
    st.markdown(f"**Rating:** {rating_badge(res3['rating'])}", unsafe_allow_html=True)
    st.markdown(f"**Weighted Score:** {res3['weighted']:.2f}  |  "
                f"**Total Adj:** {res3['total_adj']:+d}  |  "
                f"**Final Score:** {res3['final']:.2f}")

    st.subheader("Auto-Adjustments")
    adj_data = {
        "Adjustment": ["Hist ΔDebt/GDP","Exp ΔDebt/GDP","FC Debt","Other PSD","Gov Assets","Other"],
        "Notches": [f"{res3['a_hist']:+d}", f"{res3['a_exp']:+d}", f"{res3['a_fc']:+d}",
                    f"{res3['a_opsd']:+d}", f"{res3['a_ga']:+d}", f"{res3['a_other']:+d}"],
    }
    st.table(adj_data)

    st.session_state["f3_res"] = res3

elif page == "4️⃣ Susceptibility to Event Risk":
    st.title("4️⃣ Factor 4 – Susceptibility to Event Risk")
    st.markdown("---")

    alpha_opts = [c.upper() for c in ALPHA_CATS]
    alpha21_opts = [r.upper() for r in RATING_SCALE]

    st.subheader("🗳️ Political Risk")
    f4_pol = st.selectbox("Domestic Political Risk", options=alpha_opts,
                          index=3, key="k_f4_pol")

    st.markdown("---")
    st.subheader("💰 Government Liquidity Risk")
    c1, c2 = st.columns(2)
    with c1:
        f4_ease = st.selectbox("Ease of Access to Funding", options=alpha_opts,
                               index=2, key="k_f4_ease")
    with c2:
        f4_refin = st.selectbox("High Refinancing Risk Adj (notches)", options=[0, 1, 2],
                                index=0, key="k_f4_refin")

    st.markdown("---")
    st.subheader("🏦 Banking Sector Risk")
    c3, c4, c5 = st.columns(3)
    with c3:
        f4_bsce = st.selectbox("BSCE", options=alpha21_opts,
                               index=10, key="k_f4_bsce")
    with c4:
        f4_ba = st.number_input("Total Bank Assets / GDP (%)", value=114.3,
                                min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="k_f4_ba")
    with c5:
        ba_opts = list(range(-2, 3))
        f4_badj = st.selectbox("Banking Sector Adj (notches)", options=ba_opts,
                               index=ba_opts.index(0), key="k_f4_badj")

    st.markdown("---")
    st.subheader("🌐 External Vulnerability Risk")
    c6, c7 = st.columns(2)
    with c6:
        f4_ext = st.selectbox("External Vulnerability Risk", options=alpha_opts,
                              index=1, key="k_f4_ext")
    with c7:
        ext_opts = list(range(-2, 3))
        f4_eadj = st.selectbox("Ext. Vulnerability Adj (notches)", options=ext_opts,
                               index=ext_opts.index(0), key="k_f4_eadj")

    st.markdown("---")
    f4_oth = st.selectbox("Factor 4 Adj – Other (notches)", options=[0, -1, -2],
                          index=0, key="k_f4_oth")

    res4 = calc_factor4(f4_pol.lower(), f4_ease.lower(), f4_refin,
                        f4_bsce.lower(), f4_ba, f4_badj,
                        f4_ext.lower(), f4_eadj, f4_oth)

    st.markdown("---")
    st.markdown(f"**SETR:** {rating_badge(RATING_SCALE[min(19, ALPHA_SCORES[res4['setr_alpha']]-1)])}", unsafe_allow_html=True)
    st.subheader("Sub-fatores")
    cols = st.columns(4)
    for i, (name, val) in enumerate(res4["sub_scores"].items()):
        with cols[i]:
            st.metric(name, val.upper())

    st.session_state["f4_res"] = res4

else:
    # ═══════════════════════════════════════════════════════════════════
    # VISÃO GERAL – always compute with defaults or stored values
    # ═══════════════════════════════════════════════════════════════════
    st.title("📊 Moody's Sovereign Rating Scorecard")
    st.markdown("---")

    # Use stored results or compute with Brazil defaults
    f1 = st.session_state.get("f1_res", calc_factor1(2.2, 1.8, 2191.1, 21052.0, 0))
    f2 = st.session_state.get("f2_res", calc_factor2("baa","baa","ba","baa", 0, 0))
    f3 = st.session_state.get("f3_res", calc_factor3(73.8, 196.9, 14.8, 5.6, 8.3, 6.3, 3.5, 0.0, 15.1, -1))
    f4 = st.session_state.get("f4_res", calc_factor4("baa","a",0,"ba1",114.3,0,"aa",0,0))
    final = calc_final(f1, f2, f3, f4)

    # Top row – Factor ratings
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**Factor 1 – Economic Strength**")
        st.markdown(rating_badge(f1["rating"]), unsafe_allow_html=True)
        st.caption(f"Score: {f1['final']:.2f}")
    with c2:
        st.markdown("**Factor 2 – Institutions & Gov.**")
        st.markdown(rating_badge(f2["rating"]), unsafe_allow_html=True)
        st.caption(f"Score: {f2['final']:.2f}")
    with c3:
        st.markdown("**Economic Resiliency**")
        st.markdown(rating_badge(final["er_rating"]), unsafe_allow_html=True)
        st.caption(f"Score: {final['er_score']}")
    with c4:
        st.markdown("**Factor 3 – Fiscal Strength**")
        st.markdown(rating_badge(f3["rating"]), unsafe_allow_html=True)
        st.caption(f"Score: {f3['final']:.2f}")

    st.markdown("---")

    c5, c6, c7 = st.columns(3)
    with c5:
        st.markdown("**Gov. Financial Strength**")
        st.markdown(rating_badge(final["gfs_rating"]), unsafe_allow_html=True)
    with c6:
        st.markdown("**Factor 4 – SETR**")
        setr_r = RATING_SCALE[min(19, ALPHA_SCORES[f4["setr_alpha"]]-1)]
        st.markdown(rating_badge(setr_r), unsafe_allow_html=True)
        st.caption(f"({f4['setr_alpha'].upper()})")
    with c7:
        st.markdown("**🏆 Scorecard-Indicated Outcome**")
        st.markdown(rating_badge(final["final_rating"]), unsafe_allow_html=True)
        st.caption(f"Range: {final['range']}")

    st.markdown("---")
    st.subheader("Resumo Completo")

    summary = {
        "Componente": [
            "Factor 1 – Economic Strength",
            "Factor 2 – Institutions & Governance",
            "Economic Resiliency (F1+F2)/2",
            "Factor 3 – Fiscal Strength",
            "Government Financial Strength",
            "Factor 4 – SETR",
            "Scorecard-Indicated Outcome",
            "Rating Range",
        ],
        "Score": [
            f"{f1['final']:.2f}",
            f"{f2['final']:.2f}",
            str(final['er_score']),
            f"{f3['final']:.2f}",
            "—",
            f"{f4['setr_score']:.1f}",
            "—",
            "—",
        ],
        "Rating": [
            f1["rating"].upper(),
            f2["rating"].upper(),
            final["er_rating"].upper(),
            f3["rating"].upper(),
            final["gfs_rating"].upper(),
            f4["setr_alpha"].upper(),
            final["final_rating"].upper(),
            final["range"],
        ],
    }
    st.table(summary)

    st.markdown("---")
    st.subheader("Factor 4 – Sub-fatores")
    sf = f4["sub_scores"]
    cols_sf = st.columns(4)
    for i, (name, val) in enumerate(sf.items()):
        with cols_sf[i]:
            st.metric(name, val.upper())
