"""
Risk Assessment — Scoring Likelihood × Impact per Rischio.
Dimensioni: Processo → Procedura → Rischio (allineato all'Anagrafica).
"""
from __future__ import annotations

import random
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

from db.repositories import (
    get_risks_for_assessment,
    get_risk_assessment_scores,
    upsert_risk_assessment,
    get_risk_assessment_ranking,
)

# ── Palette categorie (coerente con RCM) ──────────────────────────────────────

CATEGORY_COLORS = {
    "Operativo":     "#d48806",
    "Finanziario":   "#1890ff",
    "Compliance":    "#722ed1",
    "Strategico":    "#eb2f96",
    "Reputazionale": "#fa8c16",
    "IT / Cyber":    "#13c2c2",
    "Frode":         "#cf1322",
    "Altro":         "#8c8c8c",
}

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="page-header">
      <h2>Risk Assessment</h2>
      <span class="area-chip">Likelihood × Impact — per Rischio</span>
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

risks    = get_risks_for_assessment()
existing = get_risk_assessment_scores(int(year))   # {risk_id: {L,I,notes}}

if not risks:
    st.warning(
        "Nessun rischio configurato in Anagrafica. "
        "Vai in **Anagrafica → Rischi** e aggiungi almeno un rischio.",
        icon="⚠️",
    )
    st.stop()

SCALE_OPTIONS = [1, 2, 3, 4, 5]

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_scoring, tab_heatmap, tab_ranking = st.tabs(
    ["📝 Valutazione", "🗺 Heat Map", "🏆 Ranking"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB VALUTAZIONE — tabella di scoring editabile
# ══════════════════════════════════════════════════════════════════════════════

with tab_scoring:
    st.markdown(f"#### Scoring rischi — {int(year)}")

    # Costruzione DataFrame
    rows_data = []
    for r in risks:
        ex = existing.get(r["risk_id"], {})
        rows_data.append({
            "_risk_id":   r["risk_id"],
            "Cod.":       r["risk_code"] or "—",
            "Rischio":    r["risk_name"],
            "Categoria":  r["category"] or "—",
            "Processo":   r["processi"] or "—",
            "Procedura":  r["procedure"] or "—",
            "Likelihood": ex.get("likelihood", 3),
            "Impact":     ex.get("impact", 3),
            "Score":      ex.get("likelihood", 3) * ex.get("impact", 3),
            "Note":       ex.get("notes", ""),
        })

    df = pd.DataFrame(rows_data)

    if can_edit():
        st.caption(
            "Modifica **Likelihood**, **Impact** o **Note** — "
            "il salvataggio avviene automaticamente."
        )

        edited_df = st.data_editor(
            df.drop(columns=["_risk_id"]),
            column_config={
                "Cod.":      st.column_config.TextColumn("Cod.", disabled=True,
                                                          width="small"),
                "Rischio":   st.column_config.TextColumn("Rischio", disabled=True,
                                                          width="large"),
                "Categoria": st.column_config.TextColumn("Categoria", disabled=True,
                                                          width="medium"),
                "Processo":  st.column_config.TextColumn("Processo", disabled=True,
                                                          width="medium"),
                "Procedura": st.column_config.TextColumn("Procedura", disabled=True,
                                                          width="medium"),
                "Likelihood": st.column_config.SelectboxColumn(
                    "Likelihood (1-5)", options=SCALE_OPTIONS,
                    required=True, width="small",
                ),
                "Impact":    st.column_config.SelectboxColumn(
                    "Impact (1-5)", options=SCALE_OPTIONS,
                    required=True, width="small",
                ),
                "Score":     st.column_config.NumberColumn(
                    "Score L×I", disabled=True, width="small",
                ),
                "Note":      st.column_config.TextColumn("Note", width="large"),
            },
            hide_index=True,
            use_container_width=True,
            key="risk_editor",
        )

        # Auto-save: persisti solo le righe effettivamente modificate
        editor_state = st.session_state.get("risk_editor", {})
        edited_rows  = editor_state.get("edited_rows", {})
        if edited_rows:
            user = get_current_username()
            for row_idx in edited_rows:
                row     = edited_df.iloc[row_idx]
                risk_id = df["_risk_id"].iloc[row_idx]
                upsert_risk_assessment(
                    risk_id, int(year),
                    int(row["Likelihood"]), int(row["Impact"]),
                    str(row["Note"]), user=user,
                )
            st.toast(
                f"{len(edited_rows)} riga/e aggiornata/e",
                icon="✅",
            )

    else:
        st.caption(f"Visualizzazione in sola lettura — ruolo: {role_label()}")
        st.dataframe(
            df.drop(columns=["_risk_id"]),
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score L×I", min_value=1, max_value=25, format="%d"
                ),
            },
            hide_index=True,
            use_container_width=True,
        )

    # ── Legenda scala ─────────────────────────────────────────────────────────
    with st.expander("ℹ️ Scala di valutazione", expanded=False):
        lc1, lc2 = st.columns(2)
        with lc1:
            st.markdown(
                "**Likelihood (probabilità)**\n"
                "- 1 = Improbabile (< 1 volta in 10 anni)\n"
                "- 2 = Poco probabile (ogni 5-10 anni)\n"
                "- 3 = Possibile (ogni 2-5 anni)\n"
                "- 4 = Probabile (ogni 1-2 anni)\n"
                "- 5 = Quasi certo (> 1 volta l'anno)"
            )
        with lc2:
            st.markdown(
                "**Impact (impatto)**\n"
                "- 1 = Trascurabile\n"
                "- 2 = Minore\n"
                "- 3 = Moderato\n"
                "- 4 = Significativo\n"
                "- 5 = Critico"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB HEAT MAP
# ══════════════════════════════════════════════════════════════════════════════

with tab_heatmap:
    ranking = get_risk_assessment_ranking(int(year))

    if not ranking:
        st.info(
            f"Nessuno scoring salvato per il {int(year)}. "
            "Compila la tabella in **Valutazione** e salva.",
            icon="ℹ️",
        )
    else:
        st.markdown(f"#### Heat Map Rischi — {int(year)}")

        hm_df = pd.DataFrame(ranking)
        hm_df["label"] = hm_df.apply(
            lambda r: r["risk_code"] if r["risk_code"] else r["risk_name"][:10],
            axis=1,
        )
        hm_df["hover_name"] = hm_df["risk_name"]

        # Colore per categoria, fallback grigio
        hm_df["color"] = hm_df["category"].map(
            lambda c: CATEGORY_COLORS.get(c, "#8c8c8c")
        )

        # Jitter anti-sovrapposizione
        random.seed(42)
        hm_df["x_j"] = hm_df["likelihood"] + [
            random.uniform(-0.12, 0.12) for _ in range(len(hm_df))
        ]
        hm_df["y_j"] = hm_df["impact"] + [
            random.uniform(-0.12, 0.12) for _ in range(len(hm_df))
        ]

        fig = go.Figure()

        # Quadranti (sfondo)
        quadrant_cfg = [
            (0.5, 2.5, 0.5, 2.5, "rgba(183,235,143,0.20)", "Basso"),
            (2.5, 5.5, 0.5, 2.5, "rgba(255,229,143,0.25)", "Medio"),
            (0.5, 2.5, 2.5, 5.5, "rgba(255,229,143,0.25)", "Medio"),
            (2.5, 5.5, 2.5, 5.5, "rgba(255,163,158,0.25)", "Alto"),
        ]
        for x0, x1, y0, y1, col, _ in quadrant_cfg:
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                          fillcolor=col, line_width=0, layer="below")

        # Etichette quadranti
        for x, y, txt, color in [
            (1.5, 1.5, "BASSO",  "#389e0d"),
            (4.0, 1.5, "MEDIO",  "#d48806"),
            (1.5, 4.0, "MEDIO",  "#d48806"),
            (4.0, 4.0, "ALTO",   "#cf1322"),
        ]:
            fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                               font=dict(size=11, color=color, family="system-ui"),
                               opacity=0.45)

        # Un trace per categoria (per avere legenda colorata)
        for cat, color in CATEGORY_COLORS.items():
            sub = hm_df[hm_df["category"] == cat]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["x_j"], y=sub["y_j"],
                mode="markers+text",
                name=cat,
                marker=dict(
                    size=sub["score"] * 3.5 + 8,
                    color=color,
                    opacity=0.82,
                    line=dict(width=1, color="white"),
                ),
                text=sub["label"],
                textposition="top center",
                textfont=dict(size=11, color="#222"),
                customdata=sub[["risk_name", "processi", "procedure",
                                "category", "likelihood", "impact", "score"]].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Processo: %{customdata[1]}<br>"
                    "Procedura: %{customdata[2]}<br>"
                    "Categoria: %{customdata[3]}<br>"
                    "L=%{customdata[4]}  I=%{customdata[5]}  "
                    "Score=%{customdata[6]}<extra></extra>"
                ),
            ))

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=480,
            xaxis=dict(
                title="Likelihood →",
                range=[0.3, 5.7],
                tickvals=[1, 2, 3, 4, 5],
                showgrid=True, gridcolor="#f0f0f0",
            ),
            yaxis=dict(
                title="Impact →",
                range=[0.3, 5.7],
                tickvals=[1, 2, 3, 4, 5],
                showgrid=True, gridcolor="#f0f0f0",
            ),
            legend=dict(
                title="Categoria",
                orientation="v",
                x=1.02, y=1,
            ),
            margin=dict(t=20, b=40, l=50, r=160),
            font=dict(family="system-ui", size=12),
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "La dimensione dei cerchi è proporzionale allo Score (L×I). "
            "Il colore indica la categoria di rischio."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB RANKING
# ══════════════════════════════════════════════════════════════════════════════

with tab_ranking:
    ranking = get_risk_assessment_ranking(int(year))

    if not ranking:
        st.info(
            f"Nessuno scoring salvato per il {int(year)}.",
            icon="ℹ️",
        )
    else:
        st.markdown(f"#### Ranking rischi — {int(year)}")
        st.caption(
            "Rischi ordinati per Score (Likelihood × Impact) decrescente. "
            "Usa questo ranking come input per il **Piano di Audit**."
        )

        rank_df = pd.DataFrame([{
            "#":          i + 1,
            "Cod.":       r["risk_code"] or "—",
            "Rischio":    r["risk_name"],
            "Categoria":  r["category"],
            "Processo":   r["processi"],
            "Procedura":  r["procedure"],
            "Likelihood": r["likelihood"],
            "Impact":     r["impact"],
            "Score L×I":  r["score"],
        } for i, r in enumerate(ranking)])

        def _color_score(val):
            if val >= 16:
                return "background-color:#fff2f0;color:#cf1322;font-weight:700"
            if val >= 9:
                return "background-color:#fffbe6;color:#d48806;font-weight:600"
            return "background-color:#f6ffed;color:#389e0d"

        def _color_cat(val):
            c = CATEGORY_COLORS.get(val, "#8c8c8c")
            return f"color:{c};font-weight:600"

        styled = (
            rank_df.style
            .map(_color_score, subset=["Score L×I"])
            .map(_color_cat,   subset=["Categoria"])
        )

        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Mini summary per soglia
        high   = sum(1 for r in ranking if r["score"] >= 16)
        medium = sum(1 for r in ranking if 9 <= r["score"] < 16)
        low    = sum(1 for r in ranking if r["score"] < 9)

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("🔴 Rischio Alto  (≥ 16)", high)
        mc2.metric("🟡 Rischio Medio (9-15)", medium)
        mc3.metric("🟢 Rischio Basso (< 9)",  low)

        if can_edit():
            st.info(
                "Il ranking è disponibile come riferimento nella pagina "
                "**Piano di Audit** per guidare la selezione dei controlli "
                "da testare per priorità di rischio.",
                icon="ℹ️",
            )
