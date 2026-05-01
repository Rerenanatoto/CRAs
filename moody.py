import streamlit as st
import math
import os

# ═══════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════

RATING_SCALE = [
    "aaa","aa1","aa2","aa3","a1","a2","a3",
    "baa1","baa2","baa3","ba1","ba2","ba3",
    "b1","b2","b3","caa1","caa2","caa3","ca"
]

ALPHA_CATS = ["aaa","aa","a","baa","ba","b","caa","ca"]
ALPHA_SCORES = {"aaa":1,"aa":3,"a":6,"baa":9,"ba":12,"b":15,"caa":18,"ca":20}

# ═══════════════════════════════════════════════════════════════════════
# OPÇÕES DESCRITIVAS – FATOR 2 (Institutions & Governance)
# ═══════════════════════════════════════════════════════════════════════

F2_LEGEXEC_OPTS = [
    "WGI-GE >1.5 · Highly professional admin, absorbs shocks, exceptionally deep bench strength",
    "WGI-GE 1.0–1.5 · Professional admin, may face capacity constraints, absorbs shocks but slow",
    "WGI-GE 0.5–1.0 · Generally professional admin, slow when dealing with changing circumstances",
    "WGI-GE 0.0–0.5 · Capable core but limited depth, struggles to respond to shocks",
    "WGI-GE -0.5–0.0 · Capable core but limited depth, struggles to respond to shocks",
    "WGI-GE -1.0– -0.5 · Admin often unable to support policymaking, backlogs accumulate",
    "WGI-GE -1.5– -1.0 · Admin often unable to support policymaking, significant backlogs",
    "WGI-GE < -1.5 · Lacks technical skills, weak willingness to pay creditors",
]

F2_CIVILJUD_OPTS = [
    "WGI-RL/CC >1.5 · Predictable law enforcement, independent judiciary, low corruption",
    "WGI-RL/CC 1.0–1.5 · Predictable enforcement, independent judiciary, low corruption",
    "WGI-RL/CC 0.5–1.0 · Generally predictable, judiciary not always independent",
    "WGI-RL/CC 0.0–0.5 · Generally predictable, corruption may be a problem, slow courts",
    "WGI-RL/CC -0.5–0.0 · Sometimes predictable, judiciary subject to political influence, significant corruption",
    "WGI-RL/CC -1.0– -0.5 · Sometimes predictable, political influence, significant corruption",
    "WGI-RL/CC -1.5– -1.0 · Unpredictable, few checks & balances, endemic corruption",
    "WGI-RL/CC < -1.5 · Unpredictable, no checks & balances, endemic corruption, ineffective courts",
]

F2_FISCAL_OPTS = [
    "Debt/GDP stable through cycles, balanced budget/surplus, targets met",
    "Debt/GDP rises in recession but falls, small deficit, targets met",
    "Debt/GDP rises slowly, small/stable deficit, targets sometimes missed",
    "Debt/GDP rises slowly, deficit, rigid structure, targets sometimes missed",
    "Debt/GDP rises materially in recessions, deficit, rigid structure, targets frequently missed",
    "Deficits are the norm and large, highly rigid structure, high tax evasion",
    "Debt/GDP rises unsustainably, deficits the norm, no fiscal targets, opaque accounts",
    "Very significant constraints on fiscal policy, ad hoc spending, opaque accounts",
]

F2_MONETARY_OPTS = [
    "Price stability, proactive reforms, independent CB, effective macroprudential",
    "Generally proactive, independent & credible CB, effective macroprudential",
    "Generally proactive, CB generally credible, macroprudential sometimes fails",
    "Reactive/short-termist, CB generally credible, macroprudential sometimes fails",
    "Reactive, CB may lack tools/consistency, gov. interferes in monetary policy",
    "Acts only under pressure, CB may lack tools, gov. interferes",
    "Acts only under pressure, CB ineffective, no macroprudential tools used",
    "Does not address stability challenges, CB ineffective, no macroprudential",
]

# ═══════════════════════════════════════════════════════════════════════════════
# DESCRIPTIVE OPTIONS – FACTOR 4 (Susceptibility to Event Risk)
# ═══════════════════════════════════════════════════════════════════════════════

F4_POLITICAL_OPTS = [
    "WGI-VA >1.5, PS >1.5 · Low unemployment, uniform wealth, no social conflict, smooth transitions, harmonious geopolitics",
    "WGI-VA 1.0–1.5, PS 1.0–1.5 · Low unemployment, no significant social conflict, smooth transitions, harmonious geopolitics",
    "WGI-VA 0.5–1.0, PS 0.5–1.0 · Moderate unemployment, some regional disparities, some social conflict, orderly transitions",
    "WGI-VA 0.0–0.5, PS 0.0–0.5 · Moderate unemployment, some disparities, policy continuity may be challenged by gov. changes",
    "WGI-VA -0.5–0.0, PS -0.5–0.0 · High unemployment, unequal wealth, social tensions possible, policy predictability reduced",
    "WGI-VA -1.0– -0.5, PS -1.0– -0.5 · High unemployment, deep social divisions, credit-negative policies likely after gov. changes",
    "WGI-VA -1.5– -1.0, PS -1.5– -1.0 · Mass unemployment, communal tensions/armed conflict, severe disruption of institutions",
    "WGI-VA < -1.5, PS < -1.5 · Mass unemployment, ongoing armed conflict, complete policy dysfunction, opaque succession",
]

F4_GOVLIQ_OPTS = [
    "Extremely deep, liquid domestic market; reserve currency; benchmark issuer; unquestioned access globally",
    "Very deep domestic market; strong track record of reliable global access; broad and diverse investor base",
    "Deep domestic market; generally reliable global access; reasonably broad and diverse investor base",
    "Moderately deep domestic market; generally reliable access; some concentration or funding mix risks",
    "Intermittent access to narrow domestic markets; limited global access; some official sector reliance",
    "Intermittent access to narrow/underdeveloped markets; constrained global access; significant reliance on official lenders",
    "Very limited domestic market access; no/virtually no market-based FX financing; limited official lending",
    "No meaningful market access; heavily dependent on emergency/official funding or in effective default",
]

F4_EXTVULN_OPTS = [
    "Structural CA surplus; low net external liabilities; unfettered access to intl. capital markets (reserve currency)",
    "Structural CA surplus; low net external liabilities; stable access to FX markets; no difficulty servicing ext. debt",
    "Small CA deficits (<5% GDP) mostly financed by FDI; moderate external liabilities; adequate reserves",
    "Small CA deficits mostly financed by FDI; moderate external liabilities; limited vulnerability; EVI around 100%",
    "Large/persistent CA deficits (>5% GDP); high external liabilities; dependent on portfolio flows; EVI rising",
    "Large/persistent CA deficits; very high external liabilities or large short-term debt; EVI around 200%",
    "Very large structural CA deficits; very high external liabilities; reserves at very low levels; EVI >200%",
    "Unsustainable external position; reserves near zero; in or near external debt distress",
]


# ═══════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════

def score_to_alpha21(score):
    idx = max(0, min(19, round(score) - 1))
    return RATING_SCALE[idx]

def alpha21_to_score(r):
    return RATING_SCALE.index(r) + 1

def alpha21_to_broad(r):
    for cat in ["caa","baa","aa","ba","ca","a","b"]:
        if r.startswith(cat) and (len(r) == len(cat) or r[len(cat):].isdigit()):
            return cat
    return r

def broad_to_score(cat):
    return ALPHA_SCORES.get(cat, 20)

def score_to_broad(score):
    score = max(1, min(20, round(score)))
    best = "ca"
    best_diff = 999
    for cat, sc in ALPHA_SCORES.items():
        if abs(sc - score) < best_diff:
            best_diff = abs(sc - score)
            best = cat
    return best

def clamp_score(score, lo=1.0, hi=20.0):
    return max(lo, min(hi, score))

# ═══════════════════════════════════════════════════════════════════════
# INTERPOLAÇÃO QUANTITATIVA
# ═══════════════════════════════════════════════════════════════════════

def interpolate_quant(value, ranges, higher_is_better):
    INF = 90000
    for i, (rating, rlo, rhi) in enumerate(ranges):
        score_best = i + 0.5
        score_worst = i + 1.5
        is_open_lo = (abs(rlo) >= INF)
        is_open_hi = (abs(rhi) >= INF)
        if higher_is_better:
            if is_open_hi:
                if value >= rlo: return float(i + 1)
                continue
            if is_open_lo:
                if value <= rhi: return float(i + 1)
                continue
            if value >= rhi: continue
            if value < rlo: continue
            span = rhi - rlo
            if span == 0: return float(i + 1)
            frac = (rhi - value) / span
            return score_best + frac * (score_worst - score_best)
        else:
            if is_open_lo:
                if value <= rhi: return float(i + 1)
                continue
            if is_open_hi:
                if value >= rlo: return float(i + 1)
                continue
            if value < rlo: continue
            if value >= rhi: continue
            span = rhi - rlo
            if span == 0: return float(i + 1)
            frac = (value - rlo) / span
            return score_best + frac * (score_worst - score_best)
    return 20.0

# ═══════════════════════════════════════════════════════════════════════
# FAIXAS QUANTITATIVAS – FATOR 1 (Economic Strength)
# ═══════════════════════════════════════════════════════════════════════

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

F1_W_GDP = 0.25
F1_W_MAD = 0.10
F1_W_NOM = 0.30
F1_W_PC  = 0.35

# ═══════════════════════════════════════════════════════════════════════
# FAIXAS QUANTITATIVAS – FATOR 3 (Fiscal Strength)
# ═══════════════════════════════════════════════════════════════════════

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
    ("aaa", -99999, 10), ("aa1", 10, 80), ("aa2", 80, 120),
    ("aa3", 120, 140), ("a1", 140, 160), ("a2", 160, 180),
    ("a3", 180, 200), ("baa1", 200, 220), ("baa2", 220, 230),
    ("baa3", 230, 240), ("ba1", 240, 260), ("ba2", 260, 280),
    ("ba3", 280, 320), ("b1", 320, 360), ("b2", 360, 400),
    ("b3", 400, 450), ("caa1", 450, 500), ("caa2", 500, 550),
    ("caa3", 550, 600), ("ca", 600, 99999),
]

F3_INT_REV = [
    ("aaa", -99999, 1.5), ("aa1", 1.5, 3.5), ("aa2", 3.5, 6),
    ("aa3", 6, 7), ("a1", 7, 8), ("a2", 8, 9),
    ("a3", 9, 10), ("baa1", 10, 11), ("baa2", 11, 11.5),
    ("baa3", 11.5, 12), ("ba1", 12, 13), ("ba2", 13, 14),
    ("ba3", 14, 16), ("b1", 16, 18), ("b2", 18, 20),
    ("b3", 20, 22.5), ("caa1", 22.5, 25), ("caa2", 25, 27.5),
    ("caa3", 27.5, 30), ("ca", 30, 99999),
]

F3_INT_GDP = [
    ("aaa", -99999, 0.25), ("aa1", 0.25, 1.0), ("aa2", 1.0, 1.5),
    ("aa3", 1.5, 1.75), ("a1", 1.75, 2.0), ("a2", 2.0, 2.25),
    ("a3", 2.25, 2.5), ("baa1", 2.5, 2.75), ("baa2", 2.75, 3.0),
    ("baa3", 3.0, 3.15), ("ba1", 3.15, 3.25), ("ba2", 3.25, 3.5),
    ("ba3", 3.5, 4.0), ("b1", 4.0, 4.5), ("b2", 4.5, 5.0),
    ("b3", 5.0, 6.0), ("caa1", 6.0, 6.5), ("caa2", 6.5, 7.0),
    ("caa3", 7.0, 7.5), ("ca", 7.5, 99999),
]

# ═══════════════════════════════════════════════════════════════════════
# FATOR 4 – Matriz de Risco do Setor Bancário
# ═══════════════════════════════════════════════════════════════════════

BSR_MATRIX = [
    ["a",   "a",  "baa", "ba", "b",   "b",  "ca"],
    ["a",   "a",  "baa", "baa","ba",  "b",  "ca"],
    ["a",   "a",  "a",   "baa","ba",  "ba", "b"],
    ["a",   "a",  "a",   "a",  "baa", "ba", "ba"],
    ["aaa", "aa", "aa",  "a",  "a",   "baa","ba"],
]

def bsce_to_col(r):
    idx = RATING_SCALE.index(r) if r in RATING_SCALE else 19
    if idx <= 6:  return 0
    if idx == 7:  return 1
    if idx == 8:  return 2
    if idx == 9:  return 3
    if idx <= 11: return 4
    if idx <= 15: return 5
    return 6

def bank_assets_to_row(pct):
    if pct >= 400: return 0
    if pct >= 230: return 1
    if pct >= 180: return 2
    if pct >= 80:  return 3
    return 4

# ═══════════════════════════════════════════════════════════════════════
# MATRIZ GFS 20×20
# ═══════════════════════════════════════════════════════════════════════

GFS_MATRIX = {
    "aaa": ['aaa', 'aaa', 'aaa', 'aaa', 'aaa', 'aa1', 'aa1', 'aa1', 'aa1', 'aa1', 'aa1', 'aa1', 'aa2', 'aa2', 'aa2', 'aa2', 'aa2', 'aa2', 'aa3', 'aa3'],
    "aa1": ['aa1', 'aa1', 'aa1', 'aa1', 'aa1', 'aa1', 'aa1', 'aa2', 'aa2', 'aa2', 'aa2', 'aa2', 'aa2', 'aa2', 'aa3', 'aa3', 'aa3', 'aa3', 'aa3', 'aa3'],
    "aa2": ['aa1', 'aa1', 'aa2', 'aa2', 'aa2', 'aa2', 'aa2', 'aa2', 'aa2', 'aa3', 'aa3', 'aa3', 'aa3', 'aa3', 'aa3', 'aa3', 'a1', 'a1', 'a1', 'a1'],
    "aa3": ['aa2', 'aa2', 'aa2', 'aa2', 'aa3', 'aa3', 'aa3', 'aa3', 'aa3', 'aa3', 'aa3', 'a1', 'a1', 'a1', 'a1', 'a1', 'a1', 'a1', 'a2', 'a2'],
    "a1": ['aa2', 'aa2', 'aa3', 'aa3', 'aa3', 'aa3', 'a1', 'a1', 'a1', 'a1', 'a2', 'a2', 'a2', 'a2', 'a3', 'a3', 'a3', 'a3', 'baa1', 'baa1'],
    "a2": ['aa3', 'aa3', 'aa3', 'a1', 'a1', 'a1', 'a1', 'a2', 'a2', 'a2', 'a2', 'a3', 'a3', 'a3', 'a3', 'baa1', 'baa1', 'baa1', 'baa1', 'baa2'],
    "a3": ['aa3', 'a1', 'a1', 'a1', 'a1', 'a2', 'a2', 'a2', 'a2', 'a3', 'a3', 'a3', 'a3', 'baa1', 'baa1', 'baa1', 'baa1', 'baa2', 'baa2', 'baa2'],
    "baa1": ['a1', 'a1', 'a2', 'a2', 'a2', 'a2', 'a3', 'a3', 'a3', 'a3', 'baa1', 'baa1', 'baa1', 'baa1', 'baa2', 'baa2', 'baa2', 'baa2', 'baa3', 'baa3'],
    "baa2": ['a1', 'a1', 'a2', 'a2', 'a2', 'a3', 'a3', 'a3', 'baa1', 'baa1', 'baa1', 'baa2', 'baa2', 'baa2', 'baa3', 'baa3', 'baa3', 'ba1', 'ba1', 'ba1'],
    "baa3": ['a1', 'a2', 'a2', 'a2', 'a3', 'a3', 'a3', 'baa1', 'baa1', 'baa1', 'baa2', 'baa2', 'baa3', 'baa3', 'baa3', 'ba1', 'ba1', 'ba1', 'ba2', 'ba2'],
    "ba1": ['a2', 'a2', 'a3', 'a3', 'a3', 'baa1', 'baa1', 'baa1', 'baa2', 'baa2', 'baa2', 'baa3', 'baa3', 'baa3', 'ba1', 'ba1', 'ba1', 'ba2', 'ba2', 'ba2'],
    "ba2": ['a2', 'a3', 'a3', 'a3', 'baa1', 'baa1', 'baa1', 'baa2', 'baa2', 'baa2', 'baa3', 'baa3', 'ba1', 'ba1', 'ba1', 'ba2', 'ba2', 'ba2', 'ba3', 'ba3'],
    "ba3": ['baa1', 'baa1', 'baa2', 'baa2', 'baa2', 'baa2', 'baa3', 'baa3', 'baa3', 'baa3', 'ba1', 'ba1', 'ba1', 'ba1', 'ba2', 'ba2', 'ba2', 'ba2', 'ba3', 'ba3'],
    "b1": ['baa2', 'baa2', 'baa2', 'baa2', 'baa3', 'baa3', 'baa3', 'baa3', 'ba1', 'ba1', 'ba1', 'ba1', 'ba2', 'ba2', 'ba2', 'ba2', 'ba3', 'ba3', 'ba3', 'ba3'],
    "b2": ['baa2', 'baa2', 'baa3', 'baa3', 'baa3', 'baa3', 'ba1', 'ba1', 'ba1', 'ba1', 'ba2', 'ba2', 'ba2', 'ba2', 'ba3', 'ba3', 'ba3', 'ba3', 'b1', 'b1'],
    "b3": ['baa3', 'baa3', 'baa3', 'ba1', 'ba1', 'ba1', 'ba1', 'ba2', 'ba2', 'ba2', 'ba2', 'ba3', 'ba3', 'ba3', 'ba3', 'b1', 'b1', 'b1', 'b1', 'b2'],
    "caa1": ['ba2', 'ba2', 'ba2', 'ba2', 'ba3', 'ba3', 'ba3', 'ba3', 'ba3', 'ba3', 'b1', 'b1', 'b1', 'b1', 'b1', 'b1', 'b1', 'b2', 'b2', 'b2'],
    "caa2": ['ba3', 'ba3', 'ba3', 'ba3', 'ba3', 'ba3', 'b1', 'b1', 'b1', 'b1', 'b1', 'b1', 'b2', 'b2', 'b2', 'b2', 'b2', 'b2', 'b2', 'b3'],
    "caa3": ['ba3', 'b1', 'b1', 'b1', 'b1', 'b1', 'b1', 'b1', 'b2', 'b2', 'b2', 'b2', 'b2', 'b2', 'b3', 'b3', 'b3', 'b3', 'b3', 'b3'],
    "ca": ['b1', 'b1', 'b1', 'b2', 'b2', 'b2', 'b2', 'b2', 'b2', 'b2', 'b3', 'b3', 'b3', 'b3', 'b3', 'b3', 'caa1', 'caa1', 'caa1', 'caa1'],
}

FINAL_COLS = [
    "aaa","aa1","aa2","aa3","a1","a2","a3",
    "baa1","baa2","baa3","ba1","ba2","ba3",
    "b1","b2","b3","caa1"
]

FINAL_MATRIX = {
    "aaa": ['aaa', 'aa1', 'aa2', 'aa3', 'a1', 'a2', 'a3', 'baa1', 'baa2', 'baa3', 'ba1', 'ba2', 'ba3', 'b1', 'b2', 'b3', 'caa1'],
    "aa": ['aaa', 'aa1', 'aa2', 'aa3', 'a1', 'a2', 'a3', 'baa1', 'baa2', 'baa3', 'ba1', 'ba2', 'ba3', 'b1', 'b2', 'b3', 'caa1'],
    "a": ['aaa', 'aa1', 'aa2', 'aa3', 'a1', 'a2', 'a3', 'baa2', 'baa3', 'ba1', 'ba2', 'ba3', 'b2', 'b3', 'caa1', 'caa2', 'caa3'],
    "baa": ['aaa', 'aa1', 'aa2', 'aa3', 'a2', 'a3', 'baa1', 'baa2', 'ba1', 'ba2', 'ba3', 'b1', 'b3', 'caa1', 'caa2', 'caa3', 'ca'],
    "ba": ['aa1', 'aa2', 'aa3', 'a1', 'a2', 'baa1', 'baa2', 'baa3', 'ba2', 'ba3', 'b1', 'b2', 'b3', 'caa1', 'caa2', 'caa3', 'ca'],
    "b": ['aa2', 'aa3', 'a1', 'a2', 'a3', 'baa2', 'ba1', 'ba2', 'ba3', 'b1', 'b2', 'b3', 'caa1', 'caa2', 'caa3', 'caa3', 'ca'],
    "caa": ['aa3', 'a1', 'a2', 'a3', 'baa1', 'baa3', 'ba1', 'ba2', 'b1', 'b2', 'b3', 'caa1', 'caa2', 'caa3', 'caa3', 'caa3', 'ca'],
    "ca": ['a1', 'a2', 'a3', 'baa1', 'baa2', 'ba1', 'ba2', 'ba3', 'b1', 'b2', 'b3', 'caa1', 'caa2', 'caa3', 'caa3', 'caa3', 'ca'],
}

# ═══════════════════════════════════════════════════════════════════════
# VISUAL
# ═══════════════════════════════════════════════════════════════════════

def rating_color(rating):
    idx = RATING_SCALE.index(rating) if rating in RATING_SCALE else 19
    if idx <= 2:  return "#15803d"
    if idx <= 6:  return "#22c55e"
    if idx <= 9:  return "#65a30d"
    if idx <= 12: return "#eab308"
    if idx <= 15: return "#f97316"
    return "#ef4444"

def rating_badge(rating):
    c = rating_color(rating)
    idx = RATING_SCALE.index(rating) if rating in RATING_SCALE else 19
    fg = "#fff" if idx <= 6 or idx > 12 else "#1a1a2e"
    return (
        f'<span style="display:inline-block;padding:5px 16px;border-radius:6px;'
        f'background:{c};color:{fg};font-weight:700;font-size:1.1rem;'
        f'text-transform:uppercase;letter-spacing:0.5px;">{rating.upper()}</span>'
    )

def broad_badge(cat):
    r = RATING_SCALE[min(19, ALPHA_SCORES.get(cat, 20) - 1)]
    return rating_badge(r)


# ═══════════════════════════════════════════════════════════════════════════
# CÁLCULOS DOS FATORES
# ═══════════════════════════════════════════════════════════════════════════

def calc_factor1(gdp_growth, mad_vol, nom_gdp, gdp_pc, adj):
    s_gdp = interpolate_quant(gdp_growth, F1_GDP_GROWTH, higher_is_better=True)
    s_mad = interpolate_quant(mad_vol,    F1_MAD_VOL,    higher_is_better=False)
    s_nom = interpolate_quant(nom_gdp,    F1_NOM_GDP,    higher_is_better=True)
    s_pc  = interpolate_quant(gdp_pc,     F1_GDP_PC,     higher_is_better=True)
    weighted = s_gdp * F1_W_GDP + s_mad * F1_W_MAD + s_nom * F1_W_NOM + s_pc * F1_W_PC
    final = clamp_score(weighted + adj)
    return {
        "gdp": s_gdp, "mad": s_mad, "nom": s_nom, "pc": s_pc,
        "weighted": weighted, "adj": adj, "final": final,
        "rating": score_to_alpha21(round(final)),
    }

def calc_factor2(legexec, civiljud, fiscal, monetary, default_hist, adj_other):
    s = {
        "legexec":  broad_to_score(legexec),
        "civiljud": broad_to_score(civiljud),
        "fiscal":   broad_to_score(fiscal),
        "monetary": broad_to_score(monetary),
    }
    weighted = (s["legexec"] * 0.20 + s["civiljud"] * 0.20 +
                s["fiscal"] * 0.30 + s["monetary"] * 0.30)
    total_adj = default_hist + adj_other
    final = clamp_score(weighted + total_adj)
    return {
        "scores": s, "weighted": weighted, "total_adj": total_adj, "final": final,
        "rating": score_to_alpha21(round(final)),
    }

def calc_factor3(gggd_gdp, gggd_rev, int_rev, int_gdp,
                 hist_chg, exp_chg, fc_debt, other_psd, gov_assets, adj_other):
    s1 = interpolate_quant(gggd_gdp, F3_GGGD_GDP, higher_is_better=False)
    s2 = interpolate_quant(gggd_rev, F3_GGGD_REV, higher_is_better=False)
    s3 = interpolate_quant(int_rev,  F3_INT_REV,   higher_is_better=False)
    s4 = interpolate_quant(int_gdp,  F3_INT_GDP,   higher_is_better=False)
    weighted = (s1 + s2 + s3 + s4) / 4.0
    a_hist = 0
    if hist_chg >= 50:    a_hist = -2
    elif hist_chg >= 25:  a_hist = -1
    a_exp = 0
    if exp_chg < -5:      a_exp = 1
    elif exp_chg <= 5:    a_exp = 0
    elif exp_chg <= 10:   a_exp = -1
    elif exp_chg <= 15:   a_exp = -2
    elif exp_chg >= 50:   a_exp = -3
    else:                 a_exp = -2
    a_fc = 0
    if fc_debt >= 60:     a_fc = -6
    elif fc_debt >= 50:   a_fc = -5
    elif fc_debt >= 40:   a_fc = -4
    elif fc_debt >= 30:   a_fc = -3
    elif fc_debt >= 25:   a_fc = -2
    elif fc_debt >= 20:   a_fc = -1
    a_opsd = 0
    if other_psd >= 55:   a_opsd = -3
    elif other_psd >= 40: a_opsd = -2
    elif other_psd >= 20: a_opsd = -1
    a_ga = 0
    if gov_assets >= 100:  a_ga = 4
    elif gov_assets >= 50: a_ga = 3
    elif gov_assets >= 25: a_ga = 2
    elif gov_assets >= 10: a_ga = 1
    total_adj = a_hist + a_exp + a_fc + a_opsd + a_ga + adj_other
    final = clamp_score(weighted + total_adj)
    return {
        "s1": s1, "s2": s2, "s3": s3, "s4": s4,
        "weighted": weighted,
        "a_hist": a_hist, "a_exp": a_exp, "a_fc": a_fc,
        "a_opsd": a_opsd, "a_ga": a_ga, "a_other": adj_other,
        "total_adj": total_adj, "final": final,
        "rating": score_to_alpha21(round(final)),
    }

def calc_factor4(political, ease_access, high_refin,
                 bsce, bank_assets, bank_adj,
                 ext_vuln, ext_adj, f_other):
    pol_score = broad_to_score(political)
    ease_score = broad_to_score(ease_access)
    liq_score = clamp_score(ease_score + high_refin)
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
        "sub_scores": {
            "Political": political,
            "Gov Liquidity": liq_alpha,
            "Banking Sector": bsr_final_alpha,
            "External Vuln": ext_final_alpha,
        },
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
    row = FINAL_MATRIX.get(setr_alpha, FINAL_MATRIX["ca"])
    final_rating = row[min(gfs_col_idx, 16)]
    final_idx = RATING_SCALE.index(final_rating)
    range_hi = RATING_SCALE[max(0, final_idx - 1)]
    range_lo = RATING_SCALE[min(19, final_idx + 1)]
    return {
        "er_score": er_score, "er_rating": er_rating,
        "gfs_rating": gfs_rating,
        "final_rating": final_rating,
        "range": f"{range_hi.upper()} – {range_lo.upper()}",
    }



# ═══════════════════════════════════════════════════════════════════════════
# RENDER – Função principal chamada pelo app.py
# ═══════════════════════════════════════════════════════════════════════════

def render_moody():
    st.title("🏛️ Moody's Sovereign Rating Model")
    st.caption("Baseado em: Moody's Sovereign Rating Methodology, Nov/2022")

    page = st.selectbox("📌 Section", [
        "📋 Overview",
        "1️⃣ Economic Strength",
        "2️⃣ Institutions & Governance",
        "3️⃣ Fiscal Strength",
        "4️⃣ Susceptibility to Event Risk",
        "🏆 Results",
    ], key="moody_page")

    st.markdown("---")

    DEFAULTS = {
        "f1_gdp": 2.2, "f1_mad": 1.80, "f1_nom": 2191.1, "f1_pc": 21052.0, "f1_adj": 0,
        "f2_le": 3, "f2_cj": 3, "f2_fp": 4, "f2_mp": 3, "f2_dh": 0, "f2_ao": 0,
        "f3_gg": 73.8, "f3_gr": 196.9, "f3_ir": 14.8, "f3_ig": 5.6,
        "f3_hc": 8.3, "f3_ec": 6.3, "f3_fc": 3.5, "f3_op": 0.0,
        "f3_ga": 15.1, "f3_adj": -1,
        "f4_pol": 3, "f4_ease": 2, "f4_refin": 0,
        "f4_bsce": 10, "f4_ba": 114.3, "f4_badj": 0,
        "f4_ext": 1, "f4_eadj": 0, "f4_oth": 0,
    }
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 1 – ECONOMIC STRENGTH
    # ═══════════════════════════════════════════════════════════════════
    if page == "📋 Overview":
        st.header("📋 Methodology Overview")
        st.markdown(
            "The Moody\u2019s Sovereign Rating Methodology (Nov 2022) combines **four broad factors** "
            "into a final indicative sovereign rating:\n\n"
            "1. **Economic Strength** \u2014 quantitative metrics: GDP growth, volatility, nominal GDP, GDP per capita.\n"
            "2. **Institutions & Governance** \u2014 qualitative assessment of institutional quality and policy effectiveness, "
            "anchored to World Governance Indicators (WGI).\n"
            "3. **Fiscal Strength** \u2014 quantitative metrics: debt/GDP, debt/revenue, interest/revenue, interest/GDP, plus adjustments.\n"
            "4. **Susceptibility to Event Risk (SETR)** \u2014 qualitative/quantitative: political risk, government liquidity, "
            "banking sector risk, and external vulnerability. The SETR is the **worst** of the 4 sub-factors.\n\n"
            "Factors 1 and 2 combine into **Economic Resiliency (ER)**. "
            "ER is combined with Factor 3 via the **GFS matrix** to produce the **Government Financial Strength (GFS)**. "
            "Finally, GFS is combined with SETR via the **Final matrix** to produce the **Indicative Sovereign Rating**."
        )
        _dir = os.path.dirname(os.path.abspath(__file__))
        st.subheader("Scorecard Framework")
        st.image(os.path.join(_dir, "moody_framework.png"), use_container_width=True)
        st.markdown("---")
        st.subheader("Scorecard Overview (Exhibit 2)")
        st.image(os.path.join(_dir, "moody_scorecard_overview.png"), use_container_width=True)
        st.markdown("---")
        st.subheader("WGI \u2013 World Governance Indicators")
        st.markdown(
            "Several sub-factors in Factors 2 and 4 are anchored to the **World Bank\u2019s Worldwide Governance Indicators (WGI)**. "
            "The acronyms used in the dropdown options refer to:\n\n"
            "| Acronym | Full Name | Used in |\n"
            "|---|---|---|\n"
            "| **GE** | Government Effectiveness | Factor 2 \u2013 Quality of Leg. & Exec. Institutions |\n"
            "| **RL** | Rule of Law | Factor 2 \u2013 Strength of Civil Society & Judiciary |\n"
            "| **CC** | Control of Corruption | Factor 2 \u2013 Strength of Civil Society & Judiciary |\n"
            "| **VA** | Voice & Accountability | Factor 4 \u2013 Political Risk |\n"
            "| **PS** | Political Stability & Absence of Violence | Factor 4 \u2013 Political Risk |\n\n"
            "WGI scores range from approximately **-2.5** (weak) to **+2.5** (strong)."
        )
        st.markdown("---")
        st.subheader("Scoring Scale (Exhibits 14 & 15)")
        st.image(os.path.join(_dir, "moody_subfactor_scores.png"), use_container_width=True)
        st.image(os.path.join(_dir, "moody_scoring_scale.png"), use_container_width=True)

    elif page == "1️⃣ Economic Strength":
        st.header("1️⃣ Factor 1 – Economic Strength")
        st.markdown("Evaluates the growth dynamics, scale of the economy, and national income.")
        _dir = os.path.dirname(os.path.abspath(__file__))
        with st.expander("📊 Methodology reference – Economic Strength scoring ranges"):
            st.image(os.path.join(_dir, "moody_factor1_ranges.png"), use_container_width=True)
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            f1_gdp = st.number_input(
                "📈 Average Real GDP Growth (%)",
                value=st.session_state.f1_gdp,
                min_value=-15.0, max_value=25.0, step=0.1, format="%.2f",
                help="Crescimento médio real do PIB (%)",
            )
            st.session_state.f1_gdp = f1_gdp
        with col2:
            f1_mad = st.number_input(
                "📉 MAD Volatility in Real GDP Growth",
                value=st.session_state.f1_mad,
                min_value=0.0, max_value=15.0, step=0.01, format="%.2f",
                help="Desvio médio absoluto do crescimento do PIB",
            )
            st.session_state.f1_mad = f1_mad
        col3, col4 = st.columns(2)
        with col3:
            f1_nom = st.number_input(
                "🌍 Nominal GDP (US$ bilhões)",
                value=st.session_state.f1_nom,
                min_value=0.0, max_value=100000.0, step=1.0, format="%.1f",
                help="PIB nominal em dólares (bilhões)",
            )
            st.session_state.f1_nom = f1_nom
        with col4:
            f1_pc = st.number_input(
                "👤 GDP per Capita (PPP, US$)",
                value=st.session_state.f1_pc,
                min_value=0.0, max_value=250000.0, step=100.0, format="%.0f",
                help="PIB per capita em PPP (dólares)",
            )
            st.session_state.f1_pc = f1_pc
        st.markdown("---")
        adj_opts = list(range(-9, 10))
        f1_adj = st.selectbox(
            "🔧 Ajuste – Outros (notches)",
            options=adj_opts,
            index=adj_opts.index(st.session_state.f1_adj),
            help="Ajuste discricionário de -9 a +9 notches",
        )
        st.session_state.f1_adj = f1_adj

    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 2 – INSTITUTIONS & GOVERNANCE (opções descritivas)
    # ═══════════════════════════════════════════════════════════════════
    elif page == "2️⃣ Institutions & Governance":
        st.header("2️⃣ Factor 2 – Institutions & Governance")
        st.markdown("Assesses institutional quality and policy effectiveness.")
        st.caption("WGI: **GE** = Government Effectiveness · **RL** = Rule of Law · **CC** = Control of Corruption")
        st.markdown("---")
        _dir = os.path.dirname(os.path.abspath(__file__))
        with st.expander("📊 Methodology reference – Institutions & Governance scoring descriptions (pp. 8-14)"):
            st.image(os.path.join(_dir, "moody_factor2_descriptions.png"), use_container_width=True)

        f2_le = st.selectbox(
            "🏛️ Quality of Legislative & Executive Institutions (20%)",
            options=F2_LEGEXEC_OPTS, index=st.session_state.f2_le,
            help="Quality of legislative and executive institutions (pp. 8-10)",
        )
        st.session_state.f2_le = F2_LEGEXEC_OPTS.index(f2_le)
        _cat = ALPHA_CATS[st.session_state.f2_le]
        st.markdown(f"→ **{_cat.upper()}** · score {ALPHA_SCORES[_cat]}")

        f2_cj = st.selectbox(
            "⚖️ Strength of Civil Society & Judiciary (20%)",
            options=F2_CIVILJUD_OPTS, index=st.session_state.f2_cj,
            help="Strength of civil society and judiciary (pp. 10-12)",
        )
        st.session_state.f2_cj = F2_CIVILJUD_OPTS.index(f2_cj)
        _cat = ALPHA_CATS[st.session_state.f2_cj]
        st.markdown(f"→ **{_cat.upper()}** · score {ALPHA_SCORES[_cat]}")

        st.markdown("---")

        f2_fp = st.selectbox(
            "💰 Fiscal Policy Effectiveness (30%)",
            options=F2_FISCAL_OPTS, index=st.session_state.f2_fp,
            help="Fiscal policy effectiveness (pp. 11-12)",
        )
        st.session_state.f2_fp = F2_FISCAL_OPTS.index(f2_fp)
        _cat = ALPHA_CATS[st.session_state.f2_fp]
        st.markdown(f"→ **{_cat.upper()}** · score {ALPHA_SCORES[_cat]}")

        f2_mp = st.selectbox(
            "📊 Monetary & Macroeconomic Policy Effectiveness (30%)",
            options=F2_MONETARY_OPTS, index=st.session_state.f2_mp,
            help="Monetary and macroeconomic policy effectiveness (pp. 13-14)",
        )
        st.session_state.f2_mp = F2_MONETARY_OPTS.index(f2_mp)
        _cat = ALPHA_CATS[st.session_state.f2_mp]
        st.markdown(f"→ **{_cat.upper()}** · score {ALPHA_SCORES[_cat]}")

        st.markdown("---")
        col5, col6 = st.columns(2)
        with col5:
            dh_opts = [0, -1, -2, -3]
            f2_dh = st.selectbox(
                "📉 Adjustment – Default History (notches)",
                options=dh_opts, index=dh_opts.index(st.session_state.f2_dh),
                help="Penalty for default history (0 to -3)",
            )
            st.session_state.f2_dh = f2_dh
        with col6:
            ao_opts = list(range(-3, 4))
            f2_ao = st.selectbox(
                "🔧 Adjustment – Other (notches)",
                options=ao_opts, index=ao_opts.index(st.session_state.f2_ao),
                help="Discretionary adjustment -3 to +3",
            )
            st.session_state.f2_ao = f2_ao

    
    elif page == "3️⃣ Fiscal Strength":
        st.header("3️⃣ Factor 3 – Fiscal Strength")
        st.markdown("Evaluates fiscal sustainability: debt burden and debt affordability.")
        _dir = os.path.dirname(os.path.abspath(__file__))
        with st.expander("📊 Methodology reference – Fiscal Strength scoring ranges"):
            st.image(os.path.join(_dir, "moody_factor3_ranges.png"), use_container_width=True)
        st.markdown("---")
        st.subheader("📊 Indicadores Quantitativos (peso igual: 25% cada)")
        col1, col2 = st.columns(2)
        with col1:
            f3_gg = st.number_input("🏦 GGGD / GDP (%)", value=st.session_state.f3_gg,
                min_value=0.0, max_value=500.0, step=0.1, format="%.1f",
                help="Dívida bruta do governo geral / PIB")
            st.session_state.f3_gg = f3_gg
        with col2:
            f3_gr = st.number_input("📋 GGGD / Revenue (%)", value=st.session_state.f3_gr,
                min_value=0.0, max_value=3000.0, step=0.1, format="%.1f",
                help="Dívida bruta do governo geral / Receita")
            st.session_state.f3_gr = f3_gr
        col3, col4 = st.columns(2)
        with col3:
            f3_ir = st.number_input("💸 Interest Payments / Revenue (%)", value=st.session_state.f3_ir,
                min_value=0.0, max_value=100.0, step=0.1, format="%.1f",
                help="Pagamento de juros / Receita")
            st.session_state.f3_ir = f3_ir
        with col4:
            f3_ig = st.number_input("📉 Interest Payments / GDP (%)", value=st.session_state.f3_ig,
                min_value=0.0, max_value=50.0, step=0.1, format="%.1f",
                help="Pagamento de juros / PIB")
            st.session_state.f3_ig = f3_ig
        st.markdown("---")
        st.subheader("🔧 Variáveis de Ajuste")
        col5, col6, col7 = st.columns(3)
        with col5:
            f3_hc = st.number_input("📈 Mudança Histórica Dívida/GDP (p.p., t-8→t)",
                value=st.session_state.f3_hc, min_value=-100.0, max_value=200.0, step=0.1, format="%.1f",
                help="Variação acumulada de Dívida/PIB nos últimos 8 anos")
            st.session_state.f3_hc = f3_hc
        with col6:
            f3_ec = st.number_input("🔮 Mudança Esperada Dívida/GDP (p.p., t→t+2)",
                value=st.session_state.f3_ec, min_value=-100.0, max_value=200.0, step=0.1, format="%.1f",
                help="Variação esperada de Dívida/PIB nos próximos 2 anos")
            st.session_state.f3_ec = f3_ec
        with col7:
            f3_fc = st.number_input("💱 FC Debt / GGGD (%)", value=st.session_state.f3_fc,
                min_value=0.0, max_value=100.0, step=0.1, format="%.1f",
                help="Dívida em moeda estrangeira / Dívida bruta")
            st.session_state.f3_fc = f3_fc
        col8, col9, col10 = st.columns(3)
        with col8:
            f3_op = st.number_input("🏢 Other Public Sector Debt / GDP (%)", value=st.session_state.f3_op,
                min_value=0.0, max_value=200.0, step=0.1, format="%.1f",
                help="Outros passivos do setor público / PIB")
            st.session_state.f3_op = f3_op
        with col9:
            f3_ga = st.number_input("💰 Gov. Financial Assets / GDP (%)", value=st.session_state.f3_ga,
                min_value=0.0, max_value=500.0, step=0.1, format="%.1f",
                help="Ativos financeiros do governo / PIB")
            st.session_state.f3_ga = f3_ga
        with col10:
            adj3_opts = list(range(-3, 4))
            f3_adj = st.selectbox("🔧 Ajuste – Outros (notches)",
                options=adj3_opts, index=adj3_opts.index(st.session_state.f3_adj),
                help="Ajuste discricionário de -3 a +3")
            st.session_state.f3_adj = f3_adj

    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 4 – SUSCEPTIBILITY TO EVENT RISK
    # ═══════════════════════════════════════════════════════════════════
    elif page == "4️⃣ Susceptibility to Event Risk":
        st.header("4️⃣ Factor 4 – Susceptibility to Event Risk")
        st.markdown("Avalia os riscos de eventos: político, liquidez, bancário e externo. "
                    "O SETR é determinado pelo **pior** (maior score) dos 4 sub-fatores.")
        st.caption("WGI: **VA** = Voice & Accountability · **PS** = Political Stability & Absence of Violence")
        st.markdown("---")

        _dir = os.path.dirname(os.path.abspath(__file__))
        with st.expander("📊 Methodology reference – Susceptibility to Event Risk scoring descriptions (pp. 16-20)"):
            st.image(os.path.join(_dir, "moody_factor4_descriptions.png"), use_container_width=True)

        # ── Political Risk ──
        st.subheader("🗳️ Political Risk")
        f4_pol_sel = st.selectbox(
            "🗳️ Domestic Political and Geopolitical Risk",
            options=F4_POLITICAL_OPTS, index=st.session_state.f4_pol,
            help="Risco político doméstico e geopolítico (pp. 16-17)",
        )
        st.session_state.f4_pol = F4_POLITICAL_OPTS.index(f4_pol_sel)
        _cat = ALPHA_CATS[st.session_state.f4_pol]
        st.markdown(f"→ **{_cat.upper()}** · score {ALPHA_SCORES[_cat]}")

        st.markdown("---")

        # ── Government Liquidity Risk ──
        st.subheader("💰 Government Liquidity Risk")
        f4_ease_sel = st.selectbox(
            "💰 Ease of Access to Funding",
            options=F4_GOVLIQ_OPTS, index=st.session_state.f4_ease,
            help="Facilidade de acesso a financiamento (pp. 18)",
        )
        st.session_state.f4_ease = F4_GOVLIQ_OPTS.index(f4_ease_sel)
        _cat_ease = ALPHA_CATS[st.session_state.f4_ease]
        st.markdown(f"→ Ease of Access: **{_cat_ease.upper()}** · score {ALPHA_SCORES[_cat_ease]}")

        refin_opts = [0, 1, 2]
        f4_refin = st.selectbox("⬇️ High Refinancing Risk Adj (scoring categories ↓)", options=refin_opts,
            index=refin_opts.index(st.session_state.f4_refin),
            help="Ajuste por alto risco de refinanciamento (0 = sem ajuste, 2 = máx.)")
        st.session_state.f4_refin = f4_refin

        _ease_score = ALPHA_SCORES[_cat_ease]
        _liq_score = clamp_score(_ease_score + st.session_state.f4_refin)
        _liq_alpha = score_to_broad(_liq_score)
        st.markdown(f"→ Gov Liquidity Risk (adjusted): **{_liq_alpha.upper()}** · score {round(_liq_score, 1)}")

        st.markdown("---")

        # ── Banking Sector Risk ──
        st.subheader("🏦 Banking Sector Risk")
        alpha21_opts = [r.upper() for r in RATING_SCALE]
        col3, col4 = st.columns(2)
        with col3:
            f4_bsce = st.selectbox("BSCE (Risk of Banking Sector Credit Event)", options=alpha21_opts,
                index=st.session_state.f4_bsce,
                help="Probabilidade de evento de crédito sistêmico bancário (pp. 43-44)")
            st.session_state.f4_bsce = alpha21_opts.index(f4_bsce)
        with col4:
            f4_ba = st.number_input("Total Bank Assets / GDP (%)", value=st.session_state.f4_ba,
                min_value=0.0, max_value=1500.0, step=0.1, format="%.1f",
                help="Ativos totais do sistema bancário doméstico / PIB (pp. 44)")
            st.session_state.f4_ba = f4_ba

        ba_opts = list(range(-2, 3))
        f4_badj = st.selectbox("🔧 Banking Sector Risk Adj (scoring categories)", options=ba_opts,
            index=ba_opts.index(st.session_state.f4_badj),
            help="Ajuste do risco bancário (-2 a +2 scoring categories, pp. 45)")
        st.session_state.f4_badj = f4_badj

        _bsce_r = RATING_SCALE[st.session_state.f4_bsce]
        _col_idx = bsce_to_col(_bsce_r)
        _row_idx = bank_assets_to_row(st.session_state.f4_ba)
        _bsr_alpha = BSR_MATRIX[_row_idx][_col_idx]
        _bsr_score = broad_to_score(_bsr_alpha)
        _bsr_final = clamp_score(_bsr_score + st.session_state.f4_badj)
        _bsr_final_alpha = score_to_broad(_bsr_final)
        st.markdown(f"→ Banking Sector Risk (matrix + adj): **{_bsr_final_alpha.upper()}** · score {round(_bsr_final, 1)}")

        st.markdown("---")

        # ── External Vulnerability Risk ──
        st.subheader("🌐 External Vulnerability Risk")
        f4_ext_sel = st.selectbox(
            "🌐 External Vulnerability Risk",
            options=F4_EXTVULN_OPTS, index=st.session_state.f4_ext,
            help="Risco de vulnerabilidade externa (pp. 20, 46-47)",
        )
        st.session_state.f4_ext = F4_EXTVULN_OPTS.index(f4_ext_sel)
        _cat_ext = ALPHA_CATS[st.session_state.f4_ext]
        st.markdown(f"→ Ext. Vulnerability: **{_cat_ext.upper()}** · score {ALPHA_SCORES[_cat_ext]}")

        ext_opts = list(range(-2, 3))
        f4_eadj = st.selectbox("🔧 Ext. Vulnerability Adj (scoring categories)", options=ext_opts,
            index=ext_opts.index(st.session_state.f4_eadj),
            help="Ajuste de vulnerabilidade externa (-2 a +2 scoring categories, pp. 48)")
        st.session_state.f4_eadj = f4_eadj

        _ext_score = ALPHA_SCORES[_cat_ext]
        _ext_final = clamp_score(_ext_score + st.session_state.f4_eadj)
        _ext_final_alpha = score_to_broad(_ext_final)
        st.markdown(f"→ Ext. Vulnerability (adjusted): **{_ext_final_alpha.upper()}** · score {round(_ext_final, 1)}")

        st.markdown("---")

        # ── Factor 4 Overall Adjustment ──
        oth_opts = [0, -1, -2]
        f4_oth = st.selectbox("🔧 Factor 4 Adj – Outros (scoring categories ↓)", options=oth_opts,
            index=oth_opts.index(st.session_state.f4_oth),
            help="Ajuste adicional ao fator 4 (0 a -2 scoring categories)")
        st.session_state.f4_oth = f4_oth

    # ═══════════════════════════════════════════════════════════════════
    # RESULTADO CONSOLIDADO
    # ═══════════════════════════════════════════════════════════════════
    else:
        st.header("🏆 Results – Consolidated Scorecard")
        st.markdown("**Consolidated view of all factors, sub-scores and final rating.**")
        st.markdown("---")

        alpha_opts_lc = [c.lower() for c in ALPHA_CATS]
        alpha21_opts_lc = [r.lower() for r in RATING_SCALE]

        f1 = calc_factor1(
            st.session_state.f1_gdp, st.session_state.f1_mad,
            st.session_state.f1_nom, st.session_state.f1_pc, st.session_state.f1_adj)
        f2 = calc_factor2(
            alpha_opts_lc[st.session_state.f2_le], alpha_opts_lc[st.session_state.f2_cj],
            alpha_opts_lc[st.session_state.f2_fp], alpha_opts_lc[st.session_state.f2_mp],
            st.session_state.f2_dh, st.session_state.f2_ao)
        f3 = calc_factor3(
            st.session_state.f3_gg, st.session_state.f3_gr,
            st.session_state.f3_ir, st.session_state.f3_ig,
            st.session_state.f3_hc, st.session_state.f3_ec,
            st.session_state.f3_fc, st.session_state.f3_op,
            st.session_state.f3_ga, st.session_state.f3_adj)
        f4 = calc_factor4(
            alpha_opts_lc[st.session_state.f4_pol], alpha_opts_lc[st.session_state.f4_ease],
            st.session_state.f4_refin,
            alpha21_opts_lc[st.session_state.f4_bsce],
            st.session_state.f4_ba, st.session_state.f4_badj,
            alpha_opts_lc[st.session_state.f4_ext],
            st.session_state.f4_eadj, st.session_state.f4_oth)
        final = calc_final(f1, f2, f3, f4)

        # Rating Final em destaque
        st.subheader("🏆 Scorecard-Indicated Outcome")
        rc1, rc2, rc3 = st.columns([1, 1, 1])
        with rc1:
            st.markdown(f"**Rating Final:** {rating_badge(final['final_rating'])}", unsafe_allow_html=True)
        with rc2:
            hi = RATING_SCALE[max(0, RATING_SCALE.index(final['final_rating'])-1)]
            lo = RATING_SCALE[min(19, RATING_SCALE.index(final['final_rating'])+1)]
            st.markdown(f"**Range:** {rating_badge(hi)} – {rating_badge(lo)}", unsafe_allow_html=True)
        with rc3:
            st.metric("Economic Resiliency Score", f"{final['er_score']}")

        st.markdown("---")

        # Fatores & Combinações
        st.subheader("🔹 Fatores & Combinações")
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
            st.markdown("**↳ Economic Resiliency**")
            st.markdown(rating_badge(final["er_rating"]), unsafe_allow_html=True)
            st.caption(f"Score: {final['er_score']} = round(({f1['final']:.2f} + {f2['final']:.2f}) / 2)")
        with c4:
            st.markdown("**Factor 3 – Fiscal Strength**")
            st.markdown(rating_badge(f3["rating"]), unsafe_allow_html=True)
            st.caption(f"Score: {f3['final']:.2f}")

        st.markdown("")
        c5, c6, c7 = st.columns(3)
        with c5:
            st.markdown("**↳ Gov. Financial Strength**")
            st.markdown(rating_badge(final["gfs_rating"]), unsafe_allow_html=True)
            st.caption(f"= GFS_MATRIX[{final['er_rating'].upper()}][{f3['rating'].upper()}]")
        with c6:
            st.markdown("**Factor 4 – SETR**")
            setr_r = RATING_SCALE[min(19, ALPHA_SCORES.get(f4["setr_alpha"], 20) - 1)]
            st.markdown(rating_badge(setr_r), unsafe_allow_html=True)
            st.caption(f"Categoria: {f4['setr_alpha'].upper()} | Score: {f4['setr_score']:.1f}")
        with c7:
            st.markdown("**🏆 Rating Final**")
            st.markdown(rating_badge(final["final_rating"]), unsafe_allow_html=True)
            st.caption(f"Range: **{final['range']}**")

        st.markdown("---")

        # Detalhes Factor 1
        st.subheader("📊 Factor 1 – Sub-scores")
        sc1, sc2, sc3, sc4 = st.columns(4)
        for col, lb, v, w in zip([sc1, sc2, sc3, sc4],
                ["Avg GDP Growth", "MAD Volatility", "Nominal GDP", "GDP per Capita"],
                [f1["gdp"], f1["mad"], f1["nom"], f1["pc"]], ["25%", "10%", "30%", "35%"]):
            with col:
                r = score_to_alpha21(round(v))
                st.metric(f"{lb} ({w})", f"{v:.2f} → {r.upper()}")
        mc1, mc2 = st.columns(2)
        with mc1:
            st.metric("Score Ponderado", f"{f1['weighted']:.2f}")
        with mc2:
            st.metric("Ajuste Aplicado", f"{f1['adj']:+d}")

        st.markdown("---")

        # Detalhes Factor 2
        st.subheader("📊 Factor 2 – Sub-scores")
        sc1, sc2, sc3, sc4 = st.columns(4)
        for col, lb, k in zip([sc1, sc2, sc3, sc4],
                ["Leg. & Exec. (20%)", "Civil & Jud. (20%)", "Fiscal Pol. (30%)", "Monetary Pol. (30%)"],
                ["legexec", "civiljud", "fiscal", "monetary"]):
            with col:
                v = f2["scores"][k]
                r = score_to_alpha21(round(v))
                st.metric(lb, f"{v} → {r.upper()}")
        mc1, mc2 = st.columns(2)
        with mc1:
            st.metric("Score Ponderado", f"{f2['weighted']:.2f}")
        with mc2:
            st.metric("Total Ajustes", f"{f2['total_adj']:+d}")

        st.markdown("---")

        # Detalhes Factor 3
        st.subheader("📊 Factor 3 – Sub-scores")
        sc1, sc2, sc3, sc4 = st.columns(4)
        for col, lb, v in zip([sc1, sc2, sc3, sc4],
                ["GGGD/GDP", "GGGD/Revenue", "Int./Revenue", "Int./GDP"],
                [f3["s1"], f3["s2"], f3["s3"], f3["s4"]]):
            with col:
                r = score_to_alpha21(round(v))
                st.metric(f"{lb} (25%)", f"{v:.2f} → {r.upper()}")
        st.markdown("**Ajustes Automáticos:**")
        adj_names = ["Mud. Hist. Dív/GDP", "Mud. Esp. Dív/GDP", "FC Debt/GGGD",
                     "Outra Dív. Pub./GDP", "Ativos Gov./GDP", "Outros"]
        adj_vals = [f3["a_hist"], f3["a_exp"], f3["a_fc"], f3["a_opsd"], f3["a_ga"], f3["a_other"]]
        adj_cols = st.columns(6)
        for col, nm, av in zip(adj_cols, adj_names, adj_vals):
            with col:
                color = "🟢" if av > 0 else ("🔴" if av < 0 else "⚪")
                st.metric(nm, f"{av:+d} {color}")
        mc1, mc2 = st.columns(2)
        with mc1:
            st.metric("Score Ponderado", f"{f3['weighted']:.2f}")
        with mc2:
            st.metric("Total Ajustes", f"{f3['total_adj']:+d}")

        st.markdown("---")

        # Detalhes Factor 4
        st.subheader("📊 Factor 4 – Sub-fatores")
        sf_cols = st.columns(4)
        for i, (name, val) in enumerate(f4["sub_scores"].items()):
            with sf_cols[i]:
                st.metric(name, val.upper())

        st.markdown("---")

        # Tabela Resumo
        st.subheader("📋 Tabela Resumo")
        summary_rows = [
            ["Factor 1 – Economic Strength", f"{f1['final']:.2f}", f1["rating"].upper()],
            ["Factor 2 – Institutions & Governance", f"{f2['final']:.2f}", f2["rating"].upper()],
            ["Economic Resiliency (F1+F2)/2", str(final["er_score"]), final["er_rating"].upper()],
            ["Factor 3 – Fiscal Strength", f"{f3['final']:.2f}", f3["rating"].upper()],
            ["Gov. Financial Strength", "—", final["gfs_rating"].upper()],
            ["Factor 4 – SETR", f"{f4['setr_score']:.1f}", f4["setr_alpha"].upper()],
            ["**Scorecard-Indicated Outcome**", "—", f"**{final['final_rating'].upper()}**"],
            ["**Rating Range**", "—", f"**{final['range']}**"],
        ]
        st.markdown(
            "| Componente | Score | Rating |\n|---|---|---|\n"
            + "\n".join([f"| {r[0]} | {r[1]} | {r[2]} |" for r in summary_rows]),
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.caption(
            "⚠️ Este modelo é uma reprodução didática da metodologia Moody's (Nov/2022). "
            "Os resultados são indicativos e não substituem a análise oficial da agência."
        )

