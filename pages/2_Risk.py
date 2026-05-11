"""
Risk Assessment — Scoring Likelihood × Impact per controllo, heat map, ranking.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Risk Assessment — MESA ERM",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth.utils import require_login, can_edit, get_current_username, role_label
from ui.common import inject_css, render_sidebar_nav

authenticator = require_login()
inject_css()
render_sidebar_nav(authenticator)

from db.repositories import get_all_controls, get_risk_scores, upsert_risk_score, get_risk_ranking

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="page-header">
      <h2>Risk Assessment</h2>
      <span class="area-chip">Likelihood × Impact scoring</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Anno di riferimento ───────────────────────────────────────────────────────

col_y, _ = st.columns([2, 6])
with col_y:
    year = st.number_input(
        "Anno di scoring",
        min_value=2020, max_value=2035,
        value=date.today().year, step=1,
        key="risk_year",
    )

st.markdown("---")

# ── Carica dati ───────────────────────────────────────────────────────────────

controls   = get_all_controls()
existing   = {r["control_id"]: r for r in get_risk_scores(int(year))}

SCALE_OPTIONS = [1, 2, 3, 4, 5]
SCALE_LABELS  = {1: "1 – Molto basso", 2: "2 – Basso", 3: "3 – Medio",
                 4: "4 – Alto", 5: "5 – Molto alto"}

# ══════════════════════════════════════════════════════════════════════════════
# SCORING TABLE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("#### Scoring per controllo")

if not controls:
    st.error("Nessun controllo in Anagrafica.")
    st.stop()

# Costruiamo un DataFrame editabile
rows = []
for c in controls:
    ex = existing.get(c.id, {})
    rows.append({
        "ID":          c.id,
        "Controllo":   c.title,
        "Area":        c.area,
        "Likelihood":  ex.get("likelihood", 3),
        "Impact":      ex.get("impact", 3),
        "Score (L×I)": ex.get("likelihood", 3) * ex.get("impact", 3),
        "Note":        ex.get("notes", ""),
    })

df = pd.DataFrame(rows)

if can_edit():
    st.caption(
        "Modifica Likelihood e Impact per ogni controllo, poi clicca **Salva scoring**."
    )
    edited_df = st.data_editor(
        df,
        column_config={
            "ID":          st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Controllo":   st.column_config.TextColumn("Controllo", disabled=True),
            "Area":        st.column_config.TextColumn("Area", disabled=True, width="medium"),
            "Likelihood":  st.column_config.SelectboxColumn(
                "Likelihood (1-5)", options=SCALE_OPTIONS, required=True, width="small"
            ),
            "Impact":      st.column_config.SelectboxColumn(
                "Impact (1-5)", options=SCALE_OPTIONS, required=True, width="small"
            ),
            "Score (L×I)": st.column_config.NumberColumn(
                "Score", disabled=True, width="small"
            ),
            "Note":        st.column_config.TextColumn("Note", width="large"),
        },
        hide_index=True,
        use_container_width=True,
        key="risk_editor",
    )

    # Ricalcola score dopo editing
    edited_df["Score (L×I)"] = edited_df["Likelihood"] * edited_df["Impact"]

    if st.button("💾 Salva scoring", type="primary"):
        user = get_current_username()
        for _, row in edited_df.iterrows():
            upsert_risk_score(
                row["ID"], int(year),
                int(row["Likelihood"]), int(row["Impact"]),
                row["Note"], user=user,
            )
        st.success(f"Scoring {year} salvato per {len(edited_df)} controlli.", icon="✓")
        st.rerun()
else:
    st.caption(f"Visualizzazione in sola lettura — ruolo: {role_label()}")
    st.dataframe(
        df,
        column_config={
            "Score (L×I)": st.column_config.ProgressColumn(
                "Score", min_value=1, max_value=25, format="%d"
            ),
        },
        hide_index=True,
        use_container_width=True,
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# HEAT MAP
# ══════════════════════════════════════════════════════════════════════════════

ranking = get_risk_ranking(int(year))

if ranking:
    st.markdown("#### Heat Map — Likelihood vs Impact")

    hm_df = pd.DataFrame(ranking)
    hm_df["Score"] = hm_df["likelihood"] * hm_df["impact"]

    # Aggiungi jitter leggero per controlli con stesso L/I
    import random
    random.seed(42)
    hm_df["x_jitter"] = hm_df["likelihood"] + [random.uniform(-0.15, 0.15) for _ in range(len(hm_df))]
    hm_df["y_jitter"] = hm_df["impact"]    + [random.uniform(-0.15, 0.15) for _ in range(len(hm_df))]

    fig = px.scatter(
        hm_df,
        x="x_jitter", y="y_jitter",
        size="Score",
        color="Score",
        text="control_id",
        color_continuous_scale=["#b7eb8f", "#ffe58f", "#ffa39e"],
        size_max=60,
        labels={"x_jitter": "Likelihood →", "y_jitter": "Impact →", "Score": "Rischio"},
        hover_data={"title": True, "likelihood": True, "impact": True, "Score": True,
                    "x_jitter": False, "y_jitter": False},
    )
    fig.update_traces(
        textposition="top center",
        textfont_size=12,
        textfont_color="#222",
        marker=dict(line=dict(width=1, color="#d9d9d9")),
    )

    # Quadranti di rischio (sfondo)
    for x0, x1, y0, y1, col in [
        (0.5, 2.5, 0.5, 2.5, "rgba(183,235,143,0.15)"),  # basso
        (2.5, 5.5, 0.5, 2.5, "rgba(255,229,143,0.2)"),   # medio-basso
        (0.5, 2.5, 2.5, 5.5, "rgba(255,229,143,0.2)"),   # medio-basso
        (2.5, 5.5, 2.5, 5.5, "rgba(255,163,158,0.2)"),   # alto
    ]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      fillcolor=col, line_width=0, layer="below")

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=440,
        xaxis=dict(range=[0.3, 5.7], tickvals=[1,2,3,4,5], ticktext=["1","2","3","4","5"],
                   showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(range=[0.3, 5.7], tickvals=[1,2,3,4,5], ticktext=["1","2","3","4","5"],
                   showgrid=True, gridcolor="#f0f0f0"),
        coloraxis_colorbar=dict(title="Score"),
        margin=dict(t=20, b=40, l=40, r=20),
        font=dict(family="system-ui", size=12),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Ranking ───────────────────────────────────────────────────────────────
    st.markdown("#### Ranking per rischio (input al Piano)")

    rank_df = pd.DataFrame(ranking)[["control_id", "title", "area", "likelihood", "impact", "score"]]
    rank_df.columns = ["ID", "Controllo", "Area", "Likelihood", "Impact", "Score (L×I)"]
    rank_df.index = range(1, len(rank_df) + 1)

    # Colora score con calore
    def color_score(val):
        if val >= 16:
            return "background-color:#fff2f0;color:#cf1322;font-weight:600"
        if val >= 9:
            return "background-color:#fffbe6;color:#d48806;font-weight:600"
        return "background-color:#f6ffed;color:#389e0d"

    styled = rank_df.style.applymap(color_score, subset=["Score (L×I)"])
    st.dataframe(styled, use_container_width=True)

    if can_edit():
        st.info(
            "Il ranking è disponibile nella pagina **Piano di Audit** per guidare "
            "la selezione dei controlli da testare per priorità di rischio.",
            icon="ℹ️",
        )
else:
    st.info(
        f"Nessuno scoring salvato per il {year}. "
        "Compila la tabella sopra e clicca **Salva scoring** per generare la heat map.",
        icon="ℹ️",
    )
