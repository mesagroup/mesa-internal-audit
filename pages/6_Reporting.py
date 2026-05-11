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

from ui.common import inject_css, render_sidebar_nav, badge_html
from db.repositories import (
    get_dashboard_counts,
    get_findings_by_severity, get_findings_by_status,
    get_action_plans_by_status,
    get_all_plans, get_plan_completion,
    get_active_engagements, get_all_engagements,
    get_recent_findings, get_engagement_summary,
    get_all_findings, get_all_action_plans,
)

inject_css()
render_sidebar_nav()

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

tab_charts, tab_plan, tab_export = st.tabs(
    ["📊 Grafici", "📅 Completamento Piano", "📥 Export Report"]
)

with tab_charts:
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
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(t=40, b=20, l=20, r=20),
                height=280,
                font=dict(family="system-ui", size=12),
            )
            fig_sev.update_traces(marker_line_width=0)
            st.plotly_chart(fig_sev, use_container_width=True)
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
                color=[d["status"] for d in stat_data],
                color_discrete_map={labels_it.get(k, k): v for k, v in STATUS_F_COLORS.items()},
                title="Finding per stato",
                hole=0.45,
            )
            fig_stat.update_layout(
                margin=dict(t=40, b=20, l=20, r=20),
                height=280,
                font=dict(family="system-ui", size=12),
                legend=dict(orientation="h", y=-0.1),
            )
            st.plotly_chart(fig_stat, use_container_width=True)
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
                color=[d["status"] for d in ap_data],
                color_discrete_map={ap_labels_it.get(k, k): v for k, v in STATUS_AP_COLORS.items()},
                labels={"x": "Stato", "y": "N. action plan"},
                title="Action plan per stato",
            )
            fig_ap.update_layout(
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(t=40, b=20, l=20, r=20),
                height=280,
                font=dict(family="system-ui", size=12),
            )
            fig_ap.update_traces(marker_line_width=0)
            st.plotly_chart(fig_ap, use_container_width=True)
        else:
            st.info("Nessun action plan ancora.", icon="ℹ️")

    # ── Finding recenti ───────────────────────────────────────────────────────
    st.markdown("#### Finding recenti")
    recent = get_recent_findings(limit=8)
    if recent:
        for f in recent:
            sev_b  = badge_html(f["severity"])
            stat_b = badge_html(f["status"])
            st.markdown(
                f"#{f['id']} &nbsp; {sev_b} {stat_b} &nbsp;·&nbsp; "
                f"`{f['control_id']}` &nbsp;·&nbsp; **{f['title'][:70]}** &nbsp;·&nbsp; "
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
            completion = get_plan_completion(plan["id"])
            total = completion["total"]
            completed = completion["completed"]
            in_progress = completion["in_progress"]
            planned = total - completed - in_progress

            pct = (completed / total * 100) if total else 0

            st.markdown(f"#### {plan['name']} ({plan['year']}) — {plan['status'].upper()}")

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
                name="Pianificati", x=[planned], y=["Piano"],
                orientation="h", marker_color="#d9d9d9",
            ))
            fig_plan.update_layout(
                barmode="stack",
                plot_bgcolor="white",
                paper_bgcolor="white",
                height=100,
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=True,
                legend=dict(orientation="h", x=0, y=1.3),
                xaxis=dict(range=[0, total], showgrid=False),
                yaxis=dict(showticklabels=False),
                font=dict(family="system-ui", size=12),
            )
            st.plotly_chart(fig_plan, use_container_width=True)
            st.caption(
                f"Completamento: **{pct:.0f}%** — "
                f"{completed} completati, {in_progress} in corso, {planned} pianificati"
            )
            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TAB EXPORT
# ══════════════════════════════════════════════════════════════════════════════

with tab_export:
    st.markdown("#### Export Report Engagement")
    st.markdown(
        "Genera un PDF che include le verifiche AI, i finding e gli action plan "
        "per un engagement selezionato."
    )

    all_engs = get_all_engagements()
    if not all_engs:
        st.info("Nessun engagement disponibile.", icon="ℹ️")
        st.stop()

    eng_options = {f"#{e['id']} — {e['name']} ({e['status']})": e["id"] for e in all_engs}
    sel_eng_label = st.selectbox("Seleziona Engagement", list(eng_options.keys()), key="exp_eng")
    sel_eng_id = eng_options[sel_eng_label]

    if st.button("Genera PDF Engagement", type="primary"):
        summary = get_engagement_summary(sel_eng_id)
        if not summary["engagement"]:
            st.error("Engagement non trovato.")
        else:
            from core.report_generator import generate_engagement_pdf
            import json

            out_path = Path("reports") / f"engagement_{sel_eng_id}.pdf"
            out_path.parent.mkdir(exist_ok=True)

            # Deserializza check_points nei verifications
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
            st.success("PDF generato.", icon="✓")

    st.markdown("---")
    st.markdown("#### Export dati grezzi")

    # Export CSV findings
    all_f = get_all_findings()
    if all_f:
        import io
        import csv

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=all_f[0].keys())
        writer.writeheader()
        writer.writerows(all_f)
        st.download_button(
            "📥 Scarica Findings (CSV)",
            buf.getvalue().encode("utf-8"),
            file_name="findings_export.csv",
            mime="text/csv",
        )

    all_ap = get_all_action_plans()
    if all_ap:
        import io, csv
        buf2 = io.StringIO()
        writer2 = csv.DictWriter(buf2, fieldnames=all_ap[0].keys())
        writer2.writeheader()
        writer2.writerows(all_ap)
        st.download_button(
            "📥 Scarica Action Plans (CSV)",
            buf2.getvalue().encode("utf-8"),
            file_name="action_plans_export.csv",
            mime="text/csv",
        )
