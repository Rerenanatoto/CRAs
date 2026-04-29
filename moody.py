import math
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==============================================================
# Constantes
# ==============================================================

RATING_SCALE = [
    "Aaa","Aa1","Aa2","Aa3",
    "A1","A2","A3",
    "Baa1","Baa2","Baa3",
    "Ba1","Ba2","Ba3",
    "B1","B2","B3",
    "Caa1","Caa2","Caa3","Ca","C",
]

FACTOR_WEIGHTS = {
    "Economic Strength":       0.25,
    "Institutions & Governance":0.25,
    "Fiscal Strength":         0.25,
    "Susceptibility to Event Risk":0.25,
}

SUB_FACTORS = {
    "Economic Strength": [
        ("Growth dynamics",      0.50),
        ("Scale of the economy", 0.25),
        ("National income",      0.25),
    ],
    "Institutions & Governance": [
        ("Institutional framework & effectiveness", 0.50),
        ("Policy credibility & effectiveness",      0.25),
        ("Transparency & accountability",           0.25),
    ],
    "Fiscal Strength": [
        ("Debt burden",                0.50),
        ("Debt affordability",         0.25),
        ("Government liquidity risks", 0.25),
    ],
    "Susceptibility to Event Risk": [
        ("Political risk",           0.25),
        ("Government liquidity risk",0.25),
        ("Banking sector risk",      0.25),
        ("External vulnerability",   0.25),
    ],
}

# ==============================================================
# Helpers
# ==============================================================

def score_to_numeric(rating: str) -> int:
    if rating in RATING_SCALE:
        return len(RATING_SCALE) - RATING_SCALE.index(rating)
    return 1

def numeric_to_rating(n: float) -> str:
    idx = max(0, min(len(RATING_SCALE)-1, len(RATING_SCALE) - int(round(n))))
    return RATING_SCALE[idx]

def rating_to_numeric(r: str) -> int:
    try:
        return len(RATING_SCALE) - RATING_SCALE.index(r)
    except ValueError:
        return 1

def apply_notches(base: str, adj: int) -> str:
    if base not in RATING_SCALE:
        return base
    idx = RATING_SCALE.index(base)
    new_idx = max(0, min(len(RATING_SCALE)-1, idx - adj))
    return RATING_SCALE[new_idx]

def clamp(x, lo=1, hi=21):
    return max(lo, min(hi, x))

_DEFAULTS = {}
for _f, subs in SUB_FACTORS.items():
    for _s, _ in subs:
        _DEFAULTS[f"moody_{_f}_{_s}"] = 10

def _init_state():
    for k, v in _DEFAULTS.items():
        st.session_state.setdefault(k, v)

def build_radar(scores: dict):
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

# ==============================================================
# Página principal
# ==============================================================

def render_moody():
    _init_state()
    st.title("Moody's Sovereign Rating Methodology")

    pages = (
        ["Visão geral"]
        + list(SUB_FACTORS.keys())
        + ["Resultados"]
    )
    page = st.selectbox("Navegação", pages, key="moody_page",
                         label_visibility="collapsed")
    st.markdown("---")

    if page == "Visão geral":
        st.markdown("""
A metodologia soberana da Moody's avalia **quatro fatores**, cada um com peso igual de 25 %:

| Fator | Peso |
|-------|------|
| Economic Strength | 25 % |
| Institutions & Governance | 25 % |
| Fiscal Strength | 25 % |
| Susceptibility to Event Risk | 25 % |

Cada fator é composto por sub-fatores avaliados numa escala de **1 (mais fraco) a 21 (mais forte)**.
O scorecard gera um rating indicativo que pode ser ajustado por notching.
        """)
        rows = []
        for f, subs in SUB_FACTORS.items():
            for s, w in subs:
                rows.append({"Fator": f, "Sub-fator": s, "Peso no fator": f"{w:.0%}"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    elif page in SUB_FACTORS:
        st.subheader(page)
        st.caption(f"Peso no scorecard: {FACTOR_WEIGHTS[page]:.0%}")
        for sub, weight in SUB_FACTORS[page]:
            key = f"moody_{page}_{sub}"
            st.slider(
                f"{sub}  (peso {weight:.0%})",
                min_value=1, max_value=21,
                value=st.session_state.get(key, 10),
                key=key,
            )

    elif page == "Resultados":
        st.subheader("Resultados do Scorecard")
        factor_scores = {}
        for fac, subs in SUB_FACTORS.items():
            total = 0.0
            for sub, w in subs:
                val = float(st.session_state.get(f"moody_{fac}_{sub}", 10))
                total += val * w
            factor_scores[fac] = round(total, 2)

        weighted = sum(factor_scores[f] * FACTOR_WEIGHTS[f] for f in factor_scores)
        indicative = numeric_to_rating(weighted)

        c1, c2, c3 = st.columns(3)
        c1.metric("Weighted average score", f"{weighted:.2f}")
        c2.metric("Indicative rating", indicative)
        c3.metric("Numeric equiv.", f"{rating_to_numeric(indicative)}")

        st.markdown("---")
        st.subheader("Ajustes de notching")
        notch = st.selectbox("Notch adjustment", [-2, -1, 0, 1, 2], index=2,
                             key="moody_notch")
        final = apply_notches(indicative, notch)
        st.metric("Final rating", final)

        st.markdown("---")
        st.subheader("Radar dos fatores")
        fig = build_radar(factor_scores)
        try:
            st.plotly_chart(fig, use_container_width=True)
        except TypeError:
            st.plotly_chart(fig)

        with st.expander("Detalhes por sub-fator"):
            rows = []
            for fac, subs in SUB_FACTORS.items():
                for sub, w in subs:
                    val = st.session_state.get(f"moody_{fac}_{sub}", 10)
                    rows.append({
                        "Fator": fac, "Sub-fator": sub,
                        "Peso": f"{w:.0%}", "Score": val,
                        "Contribuição": round(val * w, 2),
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True,
                         hide_index=True)
