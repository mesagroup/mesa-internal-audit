"""
Findings & Remediation — Gestione finding e action plan.
"""
from __future__ import annotations

from datetime import date, datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Findings — MESA ERM",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth.utils import require_login, can_edit, is_auditee, is_head_ia, get_current_username, role_label
from ui.common import inject_css, render_sidebar_nav, badge_html
from db.repositories import (
    get_all_findings, update_finding_status,
    get_action_plans_for_finding, create_action_plan, update_action_plan_status,
    get_all_action_plans,
)

authenticator = require_login()
inject_css()
render_sidebar_nav(authenticator)

st.markdown(
    """
    <div class="page-header">
      <h2>Findings &amp; Remediation</h2>
      <span class="area-chip">Osservazioni e Action Plan</span>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_findings, tab_actions = st.tabs(["⚠️ Findings", "🔧 Action Plans"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB FINDINGS
# ══════════════════════════════════════════════════════════════════════════════

with tab_findings:
    all_findings = get_all_findings()

    # ── Filtri ────────────────────────────────────────────────────────────────
    fc1, fc2 = st.columns(2)
    with fc1:
        sev_filter = st.multiselect(
            "Severità", ["alto", "medio", "basso"],
            default=["alto", "medio", "basso"], key="f_sev",
        )
    with fc2:
        status_filter = st.multiselect(
            "Stato", ["open", "validated", "closed"],
            default=["open", "validated"], key="f_status",
        )

    findings = [
        f for f in all_findings
        if f["severity"] in sev_filter
        and f["status"] in status_filter
    ]

    st.markdown(f"**{len(findings)}** finding visualizzati su {len(all_findings)} totali.")
    st.markdown("---")

    if not findings:
        st.info(
            "Nessun finding trovato. Esegui una verifica in **Engagement** "
            "e usa il pulsante 'Apri Finding' per creare il primo.",
            icon="ℹ️",
        )

    # ── Raggruppa per controllo di origine ───────────────────────────────────
    # Ordine: C01, C02, … (già ordinato dalla query per control_id ASC)
    groups: dict[str, list] = {}
    for f in findings:
        groups.setdefault(f["control_id"], []).append(f)

    SEV_COLORS = {"alto": "#cf1322", "medio": "#d48806", "basso": "#389e0d"}

    for ctrl_id, ctrl_findings in groups.items():
        # Metadati controllo (dal primo finding, arricchito dalla query)
        sample       = ctrl_findings[0]
        ctrl_title   = sample.get("control_title") or ctrl_id
        ctrl_area    = sample.get("control_area") or ""
        ctrl_type    = sample.get("ctrl_type") or "ai"
        type_badge   = "🤖 AI" if ctrl_type == "ai" else "📋 Manuale"

        # KPI rapidi per questo controllo
        n_alto   = sum(1 for f in ctrl_findings if f["severity"] == "alto")
        n_medio  = sum(1 for f in ctrl_findings if f["severity"] == "medio")
        n_open   = sum(1 for f in ctrl_findings if f["status"] == "open")
        n_total  = len(ctrl_findings)

        # Intestazione gruppo controllo
        st.markdown(
            f"<div style='background:#fafafa;border:1px solid #e8e8e8;"
            f"border-left:4px solid #7BAF2E;border-radius:6px;"
            f"padding:10px 16px;margin-bottom:4px;'>"
            f"<span style='font-size:16px;font-weight:700;'>{ctrl_id}</span>"
            f"<span style='color:#595959;margin-left:8px;'>{ctrl_title}</span>"
            f"<span style='float:right;font-size:12px;color:#8c8c8c;'>"
            f"{type_badge} &nbsp;·&nbsp; {ctrl_area}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # KPI chips
        kc1, kc2, kc3, kc4, _ = st.columns([1, 1, 1, 1, 4])
        kc1.metric("Totali", n_total)
        kc2.metric("Aperti", n_open)
        kc3.metric("🔴 Alto", n_alto)
        kc4.metric("🟡 Medio", n_medio)

        # Finding del controllo
        for f in ctrl_findings:
            sev_badge    = badge_html(f["severity"])
            status_badge = badge_html(f["status"])
            aps          = get_action_plans_for_finding(f["id"])
            ap_count     = len(aps)
            ap_open      = sum(1 for a in aps if a["status"] != "closed")

            with st.expander(
                f"#{f['id']}  {f['title']}",
                expanded=(f["status"] == "open"),
            ):
                col_meta, col_actions = st.columns([4, 2])

                with col_meta:
                    st.markdown(
                        f"{sev_badge} {status_badge} &nbsp;·&nbsp; "
                        f"Engagement: {f.get('engagement_name', '—')} &nbsp;·&nbsp; "
                        f"Rilevato: {f['detected_at'][:10]}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f.get("description", "—"))
                    st.caption(f"Action plan: {ap_count} totali, {ap_open} aperti")

                with col_actions:
                    allowed_statuses = ["open", "validated", "closed"]
                    if is_auditee():
                        st.markdown(badge_html(f["status"]), unsafe_allow_html=True)
                        st.caption("Sola lettura")
                    else:
                        if not is_head_ia():
                            allowed_statuses = ["open"]
                        new_status = st.selectbox(
                            "Aggiorna stato",
                            allowed_statuses,
                            index=min(
                                allowed_statuses.index(f["status"])
                                if f["status"] in allowed_statuses else 0,
                                len(allowed_statuses) - 1,
                            ),
                            key=f"fstatus_{f['id']}",
                        )
                        if st.button(
                            "Aggiorna", key=f"fupd_{f['id']}",
                            type="primary", use_container_width=True,
                        ):
                            update_finding_status(
                                f["id"], new_status, user=get_current_username()
                            )
                            st.success("Stato aggiornato.", icon="✅")
                            st.rerun()

                # ── Action Plan inline ────────────────────────────────────────
                st.markdown("**Action Plan collegati:**")

                if aps:
                    for ap in aps:
                        due     = ap["due_date"]
                        overdue = due < str(date.today()) and ap["status"] != "closed"
                        color   = "#cf1322" if overdue else (
                            "#8c8c8c" if ap["status"] == "closed" else "inherit"
                        )
                        ap_col1, ap_col2, ap_col3 = st.columns([4, 2, 2])
                        with ap_col1:
                            st.markdown(
                                f'<span style="color:{color}">'
                                f'{"🔴 " if overdue else ""}{ap["description"]}</span>',
                                unsafe_allow_html=True,
                            )
                        with ap_col2:
                            st.caption(f"Owner: {ap['owner_name']}  ·  Scadenza: {due}")
                        with ap_col3:
                            ap_new_status = st.selectbox(
                                "",
                                ["open", "in_progress", "closed_pending", "closed"],
                                index=["open", "in_progress", "closed_pending", "closed"]
                                      .index(ap["status"]),
                                key=f"apst_{ap['id']}",
                                label_visibility="collapsed",
                            )
                            if st.button("✓", key=f"apupd_{ap['id']}", use_container_width=True):
                                update_action_plan_status(ap["id"], ap_new_status)
                                st.rerun()
                else:
                    st.caption("Nessun action plan.")

                # ── Aggiungi action plan ──────────────────────────────────────
                with st.form(key=f"ap_form_{f['id']}"):
                    st.markdown("**Aggiungi Action Plan:**")
                    apc1, apc2, apc3 = st.columns([4, 2, 2])
                    with apc1:
                        ap_desc = st.text_input("Descrizione azione", key=f"apdesc_{f['id']}")
                    with apc2:
                        ap_owner = st.text_input("Responsabile", key=f"apown_{f['id']}")
                    with apc3:
                        ap_due = st.date_input(
                            "Scadenza", value=date.today(), key=f"apdue_{f['id']}",
                        )
                    submitted = st.form_submit_button("Aggiungi", type="primary")
                    if submitted:
                        if not ap_desc.strip() or not ap_owner.strip():
                            st.error("Descrizione e responsabile sono obbligatori.")
                        else:
                            create_action_plan(
                                f["id"], ap_desc.strip(), ap_owner.strip(), str(ap_due),
                            )
                            st.success("Action plan aggiunto.", icon="✅")
                            st.rerun()

        st.markdown(
            '<hr style="border:none;border-top:2px solid #f0f0f0;margin:16px 0;">',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB ACTION PLANS
# ══════════════════════════════════════════════════════════════════════════════

with tab_actions:
    all_aps = get_all_action_plans()

    af1, af2 = st.columns(2)
    with af1:
        ap_status_filter = st.multiselect(
            "Stato",
            ["open", "in_progress", "closed_pending", "closed"],
            default=["open", "in_progress", "closed_pending"],
            key="ap_status_f",
        )
    with af2:
        show_overdue = st.checkbox("Solo scaduti", key="ap_overdue_f")

    today = str(date.today())
    filtered_aps = [
        a for a in all_aps
        if a["status"] in ap_status_filter
        and (not show_overdue or (a["due_date"] < today and a["status"] not in ("closed",)))
    ]

    st.markdown(f"**{len(filtered_aps)}** action plan visualizzati su {len(all_aps)} totali.")
    st.markdown("---")

    if not filtered_aps:
        st.info("Nessun action plan trovato.", icon="ℹ️")
    else:
        for ap in filtered_aps:
            overdue = ap["due_date"] < today and ap["status"] not in ("closed",)
            icon = "🔴" if overdue else ("🟡" if ap["status"] == "in_progress" else "⚪")
            with st.expander(
                f"{icon} #{ap['id']}  {ap['description'][:80]}",
                expanded=overdue,
            ):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.markdown(
                        f"**Finding:** #{ap['finding_id']} — {ap.get('finding_title','')[:60]}  \n"
                        f"**Controllo:** `{ap.get('control_id','')}` &nbsp;·&nbsp; "
                        f"**Severità finding:** {badge_html(ap.get('severity',''))}",
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(f"**Responsabile:** {ap['owner_name']}")
                    due_color = "#cf1322" if overdue else "inherit"
                    st.markdown(
                        f'**Scadenza:** <span style="color:{due_color}">{ap["due_date"]}</span>',
                        unsafe_allow_html=True,
                    )
                with c3:
                    new_ap_status = st.selectbox(
                        "Stato",
                        ["open", "in_progress", "closed_pending", "closed"],
                        index=["open", "in_progress", "closed_pending", "closed"].index(ap["status"]),
                        key=f"apst2_{ap['id']}",
                    )
                    if st.button("Aggiorna", key=f"apupd2_{ap['id']}", type="primary", use_container_width=True):
                        update_action_plan_status(ap["id"], new_ap_status)
                        st.rerun()
