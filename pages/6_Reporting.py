"""
Reporting — Dashboard KPI, grafici Plotly, export PDF engagement.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Reporting — MESA ERM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth.utils import require_login, can_edit, role_label
from ui.common import inject_css, render_sidebar_nav, badge_html
from db.repositories import (
    get_dashboard_counts,
    get_findings_by_severity, get_findings_by_status,
    get_action_plans_by_status,
    get_all_plans, get_plan_completion, get_plan_items,
    get_all_engagements,
    get_recent_findings, get_engagement_summary,
    get_all_findings, get_all_action_plans,
    get_audit_log, get_audit_log_count,
    get_risk_assessment_ranking,
)

authenticator = require_login()
inject_css()
render_sidebar_nav(authenticator)

# ── Palette MESA ──────────────────────────────────────────────────────────────
GREEN   = "#7BAF2E"
RED     = "#cf1322"
ORANGE  = "#d48806"
GRAY    = "#8c8c8c"
BLUE    = "#1890ff"

SEVERITY_COLORS = {"alto": RED, "medio": ORANGE, "basso": GREEN}
STATUS_F_COLORS = {"open": ORANGE, "validated": BLUE, "closed": GRAY}
STATUS_AP_COLORS = {
    "open": ORANGE, "in_progress": BLUE,
    "closed_pending": "#722ed1", "closed": GRAY,
}

st.markdown(
    """
    <div class="page-header">
      <h2>Reporting</h2>
      <span class="area-chip">Dashboard operativa</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# KPI HEADER
# ══════════════════════════════════════════════════════════════════════════════

counts = get_dashboard_counts()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Controlli in Anagrafica", counts["controls"])
with k2:
    st.metric("Engagement attivi", counts["active_engagements"])
with k3:
    st.metric("Finding aperti", counts["open_findings"],
              delta=f"{counts['open_findings']} aperti" if counts["open_findings"] else None,
              delta_color="inverse")
with k4:
    st.metric("Action plan scaduti", counts["overdue_action_plans"],
              delta=f"{counts['overdue_action_plans']} scaduti" if counts["overdue_action_plans"] else None,
              delta_color="inverse")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# GRAFICI
# ══════════════════════════════════════════════════════════════════════════════

tab_charts, tab_plan, tab_risk, tab_export, tab_log = st.tabs(
    ["📊 Grafici", "📅 Completamento Piano", "⚠️ Risk Assessment", "📥 Export Report", "🗒 Audit Log"]
)

with tab_charts:
    all_f  = get_all_findings()
    all_ap = get_all_action_plans()

    gc1, gc2, gc3 = st.columns(3)

    # ── Findings per severità ─────────────────────────────────────────────────
    with gc1:
        sev_data = get_findings_by_severity()
        if sev_data:
            fig_sev = px.bar(
                sev_data,
                x="severity", y="count",
                color="severity",
                color_discrete_map=SEVERITY_COLORS,
                labels={"severity": "Severità", "count": "N. finding"},
                title="Finding per severità",
            )
            fig_sev.update_layout(
                showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=40, b=20, l=20, r=20), height=280,
                font=dict(family="system-ui", size=12),
            )
            fig_sev.update_traces(marker_line_width=0)
            st.plotly_chart(fig_sev, use_container_width=True, key="chart_sev")
        else:
            st.info("Nessun finding ancora.", icon="ℹ️")

    # ── Findings per stato ────────────────────────────────────────────────────
    with gc2:
        stat_data = get_findings_by_status()
        if stat_data:
            labels_it = {"open": "Aperto", "validated": "Validato", "closed": "Chiuso"}
            fig_stat = px.pie(
                stat_data,
                names=[labels_it.get(d["status"], d["status"]) for d in stat_data],
                values=[d["count"] for d in stat_data],
                color=[labels_it.get(d["status"], d["status"]) for d in stat_data],
                color_discrete_map={labels_it.get(k, k): v for k, v in STATUS_F_COLORS.items()},
                title="Finding per stato",
                hole=0.45,
            )
            fig_stat.update_layout(
                margin=dict(t=40, b=20, l=20, r=20), height=280,
                font=dict(family="system-ui", size=12),
                legend=dict(orientation="h", y=-0.1),
            )
            st.plotly_chart(fig_stat, use_container_width=True, key="chart_stat")
        else:
            st.info("Nessun finding ancora.", icon="ℹ️")

    # ── Action plan per stato ─────────────────────────────────────────────────
    with gc3:
        ap_data = get_action_plans_by_status()
        if ap_data:
            ap_labels_it = {
                "open": "Aperto", "in_progress": "In corso",
                "closed_pending": "Chiuso (verifica)", "closed": "Chiuso",
            }
            fig_ap = px.bar(
                ap_data,
                x=[ap_labels_it.get(d["status"], d["status"]) for d in ap_data],
                y=[d["count"] for d in ap_data],
                color=[ap_labels_it.get(d["status"], d["status"]) for d in ap_data],
                color_discrete_map={ap_labels_it.get(k, k): v for k, v in STATUS_AP_COLORS.items()},
                labels={"x": "Stato", "y": "N. action plan"},
                title="Action plan per stato",
            )
            fig_ap.update_layout(
                showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=40, b=20, l=20, r=20), height=280,
                font=dict(family="system-ui", size=12),
            )
            fig_ap.update_traces(marker_line_width=0)
            st.plotly_chart(fig_ap, use_container_width=True, key="chart_ap")
        else:
            st.info("Nessun action plan ancora.", icon="ℹ️")

    # ── Finding per controllo di origine ─────────────────────────────────────
    if all_f:
        st.markdown("#### Finding per controllo")

        from collections import Counter
        ctrl_counts = Counter(f["control_id"] for f in all_f)
        ctrl_sev: dict[str, dict] = {}
        for f in all_f:
            ctrl_sev.setdefault(f["control_id"], {"alto": 0, "medio": 0, "basso": 0})
            ctrl_sev[f["control_id"]][f["severity"]] += 1

        ctrl_ids = sorted(ctrl_sev.keys())
        fig_ctrl = go.Figure()
        for sev, color in SEVERITY_COLORS.items():
            fig_ctrl.add_trace(go.Bar(
                name=sev.capitalize(),
                x=ctrl_ids,
                y=[ctrl_sev[c].get(sev, 0) for c in ctrl_ids],
                marker_color=color,
            ))
        fig_ctrl.update_layout(
            barmode="stack",
            plot_bgcolor="white", paper_bgcolor="white",
            height=240,
            margin=dict(t=10, b=20, l=20, r=20),
            legend=dict(orientation="h", x=0, y=1.15),
            xaxis=dict(title="Controllo"),
            yaxis=dict(title="N. finding", dtick=1),
            font=dict(family="system-ui", size=12),
        )
        st.plotly_chart(fig_ctrl, use_container_width=True, key="chart_ctrl")

    # ── Finding recenti ───────────────────────────────────────────────────────
    st.markdown("#### Finding recenti")
    recent = get_recent_findings(limit=8)
    if recent:
        for f in recent:
            sev_b  = badge_html(f["severity"])
            stat_b = badge_html(f["status"])
            ctrl_title = f.get("control_title") or f["control_id"]
            st.markdown(
                f"#{f['id']} &nbsp; {sev_b} {stat_b} &nbsp;·&nbsp; "
                f"**{f['control_id']}** — {ctrl_title[:50]} &nbsp;·&nbsp; "
                f"<span style='color:#8c8c8c;font-size:12px;'>"
                f"{f.get('engagement_name','—')} — {f['detected_at'][:10]}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Nessun finding registrato.", icon="ℹ️")


# ══════════════════════════════════════════════════════════════════════════════
# TAB COMPLETAMENTO PIANO
# ══════════════════════════════════════════════════════════════════════════════

with tab_plan:
    plans = get_all_plans()
    if not plans:
        st.info("Nessun Piano di Audit creato. Vai a **Piano di Audit** per creare il primo.", icon="ℹ️")
    else:
        for plan in plans:
            completion  = get_plan_completion(plan["id"])
            total       = completion["total"]
            completed   = completion["completed"]
            in_progress = completion["in_progress"]
            planned_n   = total - completed - in_progress
            pct         = (completed / total * 100) if total else 0

            PLAN_STATUS_LABEL = {"draft": "Bozza", "active": "Attivo", "closed": "Chiuso"}
            st.markdown(
                f"#### {plan['name']} ({plan['year']}) "
                f"— {PLAN_STATUS_LABEL.get(plan['status'], plan['status'])}"
            )

            if total == 0:
                st.caption("Nessun controllo nel piano.")
                continue

            # Stacked bar orizzontale
            fig_plan = go.Figure()
            fig_plan.add_trace(go.Bar(
                name="Completati", x=[completed], y=["Piano"],
                orientation="h", marker_color=GREEN,
            ))
            fig_plan.add_trace(go.Bar(
                name="In corso", x=[in_progress], y=["Piano"],
                orientation="h", marker_color=ORANGE,
            ))
            fig_plan.add_trace(go.Bar(
                name="Pianificati", x=[planned_n], y=["Piano"],
                orientation="h", marker_color="#d9d9d9",
            ))
            fig_plan.update_layout(
                barmode="stack", plot_bgcolor="white", paper_bgcolor="white",
                height=100, margin=dict(t=10, b=10, l=10, r=10),
                showlegend=True, legend=dict(orientation="h", x=0, y=1.3),
                xaxis=dict(range=[0, total], showgrid=False),
                yaxis=dict(showticklabels=False),
                font=dict(family="system-ui", size=12),
            )
            st.plotly_chart(fig_plan, use_container_width=True, key=f"chart_plan_{plan['id']}")
            st.caption(
                f"Completamento: **{pct:.0f}%** — "
                f"{completed} completati, {in_progress} in corso, {planned_n} pianificati"
            )

            # ── Dettaglio controlli del piano ─────────────────────────────────
            items = get_plan_items(plan["id"])
            if items:
                ITEM_ICON = {"planned": "🔵", "in_progress": "🟡", "completed": "🟢"}
                for item in items:
                    ic1, ic2, ic3, ic4 = st.columns([1, 5, 3, 2])
                    with ic1:
                        st.markdown(ITEM_ICON.get(item["status"], "⚪"))
                    with ic2:
                        ctrl_t = item.get("control_title") or item["control_id"]
                        st.markdown(
                            f"**{item['control_id']}** — {ctrl_t[:55]}  \n"
                            f"<span style='color:#8c8c8c;font-size:12px;'>"
                            f"{item.get('control_area','')}</span>",
                            unsafe_allow_html=True,
                        )
                    with ic3:
                        st.caption(
                            f"Assegnato: {item['assigned_to'] or '—'}  \n"
                            f"Scadenza: {item['planned_date'] or '—'}"
                        )
                    with ic4:
                        eng = item.get("engagement_name")
                        if eng:
                            st.caption(f"▶️ {eng[:30]}")
                        else:
                            st.caption("Non avviato")
                    st.markdown(
                        '<hr style="border:none;border-top:1px solid #f5f5f5;margin:2px 0;">',
                        unsafe_allow_html=True,
                    )

            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TAB RISK ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════

with tab_risk:
    ra_year = st.number_input(
        "Anno di riferimento", min_value=2020, max_value=2035,
        value=date.today().year, step=1, key="rep_ra_year",
    )
    ranking = get_risk_assessment_ranking(int(ra_year))

    if not ranking:
        st.info(
            f"Nessuno scoring salvato per il {int(ra_year)}. "
            "Vai in **Risk Assessment** per inserire i valori.",
            icon="ℹ️",
        )
    else:
        import pandas as pd
        import random

        CATEGORY_COLORS_RA = {
            "Operativo":     "#d48806",
            "Finanziario":   "#1890ff",
            "Compliance":    "#722ed1",
            "Strategico":    "#eb2f96",
            "Reputazionale": "#fa8c16",
            "IT / Cyber":    "#13c2c2",
            "Frode":         "#cf1322",
            "Altro":         "#8c8c8c",
        }

        high   = sum(1 for r in ranking if r["score"] >= 16)
        medium = sum(1 for r in ranking if 9 <= r["score"] < 16)
        low    = sum(1 for r in ranking if r["score"] < 9)

        rk1, rk2, rk3 = st.columns(3)
        rk1.metric("🔴 Rischio Alto  (≥ 16)", high)
        rk2.metric("🟡 Rischio Medio (9-15)", medium)
        rk3.metric("🟢 Rischio Basso (< 9)",  low)

        st.markdown("---")
        rc1, rc2 = st.columns([3, 2])

        with rc1:
            st.markdown(f"##### Heat Map rischi — {int(ra_year)}")
            hm_df = pd.DataFrame(ranking)
            hm_df["label"] = hm_df.apply(
                lambda r: r["risk_code"] if r["risk_code"] else r["risk_name"][:10],
                axis=1,
            )
            random.seed(42)
            hm_df["x_j"] = hm_df["likelihood"] + [random.uniform(-0.1, 0.1) for _ in range(len(hm_df))]
            hm_df["y_j"] = hm_df["impact"]     + [random.uniform(-0.1, 0.1) for _ in range(len(hm_df))]

            fig_hm = go.Figure()
            quadrants = [
                (0.5, 2.5, 0.5, 2.5, "rgba(183,235,143,0.20)"),
                (2.5, 5.5, 0.5, 2.5, "rgba(255,229,143,0.25)"),
                (0.5, 2.5, 2.5, 5.5, "rgba(255,229,143,0.25)"),
                (2.5, 5.5, 2.5, 5.5, "rgba(255,163,158,0.25)"),
            ]
            for x0, x1, y0, y1, col in quadrants:
                fig_hm.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                                 fillcolor=col, line_width=0, layer="below")

            for cat, color in CATEGORY_COLORS_RA.items():
                sub = hm_df[hm_df["category"] == cat]
                if sub.empty:
                    continue
                fig_hm.add_trace(go.Scatter(
                    x=sub["x_j"], y=sub["y_j"],
                    mode="markers+text",
                    name=cat,
                    marker=dict(size=sub["score"] * 3 + 8, color=color, opacity=0.85,
                                line=dict(width=1, color="white")),
                    text=sub["label"],
                    textposition="top center",
                    textfont=dict(size=11),
                    customdata=sub[["risk_name", "likelihood", "impact", "score"]].values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "L=%{customdata[1]}  I=%{customdata[2]}  "
                        "Score=%{customdata[3]}<extra></extra>"
                    ),
                ))
            fig_hm.update_layout(
                plot_bgcolor="white", paper_bgcolor="white", height=380,
                xaxis=dict(title="Likelihood →", range=[0.3, 5.7], tickvals=[1,2,3,4,5],
                           showgrid=True, gridcolor="#f0f0f0"),
                yaxis=dict(title="Impact →", range=[0.3, 5.7], tickvals=[1,2,3,4,5],
                           showgrid=True, gridcolor="#f0f0f0"),
                legend=dict(title="Categoria", orientation="v", x=1.02, y=1),
                margin=dict(t=20, b=40, l=50, r=160),
                font=dict(family="system-ui", size=12),
            )
            st.plotly_chart(fig_hm, use_container_width=True, key="chart_hm")

        with rc2:
            st.markdown(f"##### Ranking — Top {len(ranking)} rischi")

            def _color_score(val):
                if val >= 16:  return "background-color:#fff2f0;color:#cf1322;font-weight:700"
                if val >= 9:   return "background-color:#fffbe6;color:#d48806;font-weight:600"
                return "background-color:#f6ffed;color:#389e0d"

            rank_df = pd.DataFrame([{
                "#":          i + 1,
                "Cod.":       r["risk_code"] or "—",
                "Rischio":    r["risk_name"],
                "L":          r["likelihood"],
                "I":          r["impact"],
                "Score":      r["score"],
            } for i, r in enumerate(ranking)])

            styled = rank_df.style.map(_color_score, subset=["Score"])
            st.dataframe(styled, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB EXPORT
# ══════════════════════════════════════════════════════════════════════════════

with tab_export:
    st.markdown("#### Export Report Engagement")
    st.markdown(
        "Genera un PDF che include le verifiche AI, i finding e gli action plan "
        "per un engagement selezionato."
    )

    import io, csv, json

    # ── PDF Engagement ────────────────────────────────────────────────────────
    all_engs = get_all_engagements()
    if not all_engs:
        st.info("Nessun engagement disponibile.", icon="ℹ️")
    else:
        eng_options = {f"#{e['id']} — {e['name']} ({e['status']})": e["id"] for e in all_engs}
        sel_eng_label = st.selectbox("Seleziona Engagement", list(eng_options.keys()), key="exp_eng")
        sel_eng_id = eng_options[sel_eng_label]

        if st.button("Genera PDF Engagement", type="primary"):
            summary = get_engagement_summary(sel_eng_id)
            if not summary["engagement"]:
                st.error("Engagement non trovato.")
            else:
                from core.report_generator import generate_engagement_pdf

                out_path = Path("reports") / f"engagement_{sel_eng_id}.pdf"
                out_path.parent.mkdir(exist_ok=True)

                vers = []
                for v in summary["verifications"]:
                    v2 = dict(v)
                    if isinstance(v2.get("check_points"), str):
                        v2["check_points"] = json.loads(v2["check_points"])
                    vers.append(v2)

                generate_engagement_pdf(
                    engagement=summary["engagement"],
                    verifications=vers,
                    findings=summary["findings"],
                    action_plans=summary["action_plans"],
                    output_path=out_path,
                )

                with open(out_path, "rb") as f_pdf:
                    st.download_button(
                        "📥 Scarica PDF",
                        f_pdf.read(),
                        file_name=f"engagement_{sel_eng_id}_report.pdf",
                        mime="application/pdf",
                        type="primary",
                    )
                st.success("PDF generato.", icon="✅")

    st.markdown("---")
    st.markdown("#### Export dati grezzi")

    # Export CSV findings
    all_f_exp = get_all_findings()
    if all_f_exp:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=all_f_exp[0].keys())
        writer.writeheader()
        writer.writerows(all_f_exp)
        st.download_button(
            "📥 Scarica Findings (CSV)",
            buf.getvalue().encode("utf-8"),
            file_name="findings_export.csv",
            mime="text/csv",
        )
    else:
        st.caption("Nessun finding da esportare.")

    # Export CSV action plans
    all_ap_exp = get_all_action_plans()
    if all_ap_exp:
        buf2 = io.StringIO()
        writer2 = csv.DictWriter(buf2, fieldnames=all_ap_exp[0].keys())
        writer2.writeheader()
        writer2.writerows(all_ap_exp)
        st.download_button(
            "📥 Scarica Action Plans (CSV)",
            buf2.getvalue().encode("utf-8"),
            file_name="action_plans_export.csv",
            mime="text/csv",
        )
    else:
        st.caption("Nessun action plan da esportare.")

    if not can_edit():
        st.info("Export PDF disponibile solo per Auditor e Head IA.", icon="🔒")


# ══════════════════════════════════════════════════════════════════════════════
# TAB AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

with tab_log:
    st.markdown("#### Audit Log operativo")
    st.caption(
        "Registro append-only delle operazioni effettuate nell'applicativo. "
        "Finalità dimostrativa — per audit-grade serve un DB con WORM o event sourcing."
    )

    total_log = get_audit_log_count()

    lc1, lc2 = st.columns([3, 2])
    with lc1:
        log_limit = st.slider("Record da visualizzare", 20, 500, 100, step=20, key="log_limit")
    with lc2:
        st.metric("Operazioni totali nel log", total_log)

    log_entries = get_audit_log(limit=log_limit)

    if not log_entries:
        st.info("Nessuna operazione registrata.", icon="ℹ️")
    else:
        import pandas as pd

        log_df = pd.DataFrame(log_entries)[
            ["ts", "user_name", "action", "entity_type", "entity_id", "details"]
        ]
        log_df.columns = ["Timestamp", "Utente", "Azione", "Entità", "ID", "Dettagli"]

        # Colora per tipo azione
        action_colors = {
            "create": "background-color:#f6ffed",
            "delete": "background-color:#fff2f0",
            "update_status": "background-color:#fffbe6",
            "upsert": "background-color:#e6f7ff",
        }

        def color_action(val):
            return action_colors.get(val, "")

        styled_log = log_df.style.map(color_action, subset=["Azione"])
        st.dataframe(styled_log, use_container_width=True, hide_index=True)
