# ============================================================
# Moody's Sovereign Rating Methodology – Streamlit module
# ============================================================

import math
import json
import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ────────────────────────────────────────────
# Rating scale & scorecard weights
# ────────────────────────────────────────────

RATING_SCALE = [
    "Aaa","Aa1","Aa2","Aa3","A1","A2","A3",
    "Baa1","Baa2","Baa3","Ba1","Ba2","Ba3",
    "B1","B2","B3","Caa1","Caa2","Caa3","Ca","C",
]

FACTOR_WEIGHTS = {
    "Economic Strength":       0.25,
    "Institutions & Governance":0.25,
    "Fiscal Strength":         0.25,
    "Susceptibility to Event Risk":0.25,
}

SUB_FACTORS = {
    "Economic Strength": [
        ("GDP per capita (US$)",          0.50),
        ("Nominal GDP (US$ bn)",          0.25),
        ("Real GDP growth (5yr avg, %)",  0.25),
    ],
    "Institutions & Governance": [
        ("WB Government Effectiveness",   0.34),
        ("WB Rule of Law",                0.33),
        ("WB Control of Corruption",      0.33),
    ],
    "Fiscal Strength": [
        ("General government debt (% GDP)",   0.50),
        ("Interest payments (% Revenue)",     0.25),
        ("General government balance (% GDP)",0.25),
    ],
    "Susceptibility to Event Risk": [
        ("Political risk score (1-6)",        0.25),
        ("Banking sector risk score (1-6)",   0.25),
        ("External vulnerability score (1-6)",0.25),
        ("Government liquidity risk (1-6)",   0.25),
    ],
}

# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────

def score_to_numeric(score):
    return max(1, min(21, round(score)))

def numeric_to_rating(n):
    idx = max(0, min(len(RATING_SCALE)-1, int(n)-1))
    return RATING_SCALE[idx]

def rating_to_numeric(r):
    if r in RATING_SCALE:
        return RATING_SCALE.index(r) + 1
    return 10

def apply_notches(base, adj):
    idx = RATING_SCALE.index(base) if base in RATING_SCALE else 9
    new_idx = max(0, min(len(RATING_SCALE)-1, idx - adj))
    return RATING_SCALE[new_idx]

def clamp(x, lo=1.0, hi=6.0):
    return max(lo, min(hi, x))

# ────────────────────────────────────────────
# Module-level defaults for session state
# ────────────────────────────────────────────

_DEFAULTS = {}
for factor, subs in SUB_FACTORS.items():
    for label, _ in subs:
        key = f"moody_{factor}_{label}"
        _DEFAULTS[key] = 3.0

def _init_state():
    for k, v in _DEFAULTS.items():
        st.session_state.setdefault(k, v)

# ────────────────────────────────────────────
# Build radar chart
# ────────────────────────────────────────────

def build_radar(scores):
    cats = list(scores.keys())
    vals = [scores[c] for c in cats]
    cats2 = cats + [cats[0]]
    vals2 = vals + [vals[0]]
    fig = go.Figure(data=[go.Scatterpolar(
        r=vals2, theta=cats2, fill="toself", name="Scores",
        line=dict(color="#1F3864"),
        fillcolor="rgba(31,56,100,0.18)",
    )])
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 21])),
        showlegend=False,
        margin=dict(l=30, r=30, t=30, b=30),
    )
    return fig

# ────────────────────────────────────────────
# Main render function
# ────────────────────────────────────────────

def render_moody():
    _init_state()

    st.title("Moody's Sovereign Rating Methodology")
    st.caption(
        "Scorecard simplificado com 4 fatores, pesos iguais de 25%. "
        "Cada sub-fator recebe um score de 1 (mais forte) a 21 (mais fraco). "
        "O rating indicativo resulta da média ponderada."
    )

    method_page = st.radio(
        "Seção",
        ["Visão geral"] + list(FACTOR_WEIGHTS.keys()) + ["Resultados"],
        horizontal=True,
        key="moody_page",
    )

    st.markdown("---")

    # ── Visão geral ─────────────────────────────
    if method_page == "Visão geral":
        st.subheader("Estrutura do Scorecard")
        rows = []
        for factor, weight in FACTOR_WEIGHTS.items():
            subs = SUB_FACTORS[factor]
            sub_labels = ", ".join([s[0] for s in subs])
            rows.append({
                "Factor": factor,
                "Weight": f"{weight:.0%}",
                "Sub-factors": sub_labels,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.info(
            "Navegue pelas seções acima para preencher cada fator. "
            "Depois vá em **Resultados** para ver o rating indicativo."
        )

    # ── Factor pages ────────────────────────────
    elif method_page in FACTOR_WEIGHTS:
        factor = method_page
        st.subheader(f"{factor} (peso = {FACTOR_WEIGHTS[factor]:.0%})")
        subs = SUB_FACTORS[factor]
        sub_scores = []
        for label, sub_w in subs:
            key = f"moody_{factor}_{label}"
            val = st.slider(
                f"{label} (peso relativo {sub_w:.0%})",
                min_value=1, max_value=21, value=int(st.session_state.get(key, 3)),
                key=key,
                help="1 = mais forte / Aaa … 21 = mais fraco / C",
            )
            sub_scores.append((label, sub_w, val))

        weighted = sum(w * v for _, w, v in sub_scores)
        st.metric(f"Score ponderado – {factor}", f"{weighted:.1f}")
        st.caption("Esse score entra na média final com o peso do fator.")

    # ── Resultados ──────────────────────────────
    elif method_page == "Resultados":
        st.subheader("Resultados do Scorecard")

        factor_scores = {}
        for factor, weight in FACTOR_WEIGHTS.items():
            subs = SUB_FACTORS[factor]
            weighted = 0.0
            for label, sub_w in subs:
                key = f"moody_{factor}_{label}"
                val = float(st.session_state.get(key, 3))
                weighted += sub_w * val
            factor_scores[factor] = round(weighted, 2)

        overall = sum(
            FACTOR_WEIGHTS[f] * factor_scores[f]
            for f in FACTOR_WEIGHTS
        )

        cols = st.columns(len(FACTOR_WEIGHTS))
        for col, (factor, sc) in zip(cols, factor_scores.items()):
            col.metric(factor, f"{sc:.1f}")

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall weighted score", f"{overall:.2f}")
        indicative_num = score_to_numeric(overall)
        indicative_rating = numeric_to_rating(indicative_num)
        c2.metric("Indicative rating", indicative_rating)

        notch_adj = st.selectbox(
            "Notch adjustment (-2 to +2)",
            options=[-2, -1, 0, 1, 2],
            index=2,
            key="moody_notch_adj",
        )
        final_rating = apply_notches(indicative_rating, notch_adj)
        c3.metric("Final rating", final_rating)

        st.markdown("---")
        st.subheader("Radar (1 = mais forte)")
        fig = build_radar(factor_scores)
        try:
            st.plotly_chart(fig, use_container_width=True)
        except TypeError:
            st.plotly_chart(fig)

        with st.expander("Detalhes do scorecard"):
            detail_rows = []
            for factor in FACTOR_WEIGHTS:
                for label, sub_w in SUB_FACTORS[factor]:
                    key = f"moody_{factor}_{label}"
                    val = float(st.session_state.get(key, 3))
                    detail_rows.append({
                        "Factor": factor,
                        "Sub-factor": label,
                        "Weight (within factor)": f"{sub_w:.0%}",
                        "Score": val,
                    })
            st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)
