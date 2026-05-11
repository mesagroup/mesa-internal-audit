"""
Piano di Audit — Creazione piano, assegnazione controlli, avvio engagement.
"""
from __future__ import annotations

from datetime import date

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Piano di Audit — MESA ERM",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.common import inject_css, render_sidebar_nav, badge_html
from db.repositories import (
    get_all_plans, create_plan, update_plan_status,
    get_plan_items, add_plan_item, delete_plan_item,
    link_engagement_to_item, update_plan_item_status,
    get_all_controls, create_engagement, get_plan_completion,
)

inject_css()
render_sidebar_nav()

st.markdown(
    """
    <div class="page-header">
      <h2>Piano di Audit</h2>
      <span class="area-chip">Annual Audit Plan</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# CREAZIONE NUOVO PIANO
# ══════════════════════════════════════════════════════════════════════════════

with st.expander("➕ Crea nuovo Piano di Audit"):
    pc1, pc2 = st.columns([3, 1])
    with pc1:
        p_name  = st.text_input("Nome del piano (es. Piano Audit 2026)", key="p_name")
        p_notes = st.text_area("Note", height=60, key="p_notes")
    with pc2:
        p_year = st.number_input(
            "Anno di riferimento",
            min_value=2020, max_value=2035,
            value=date.today().year,
            step=1,
            key="p_year",
        )
    if st.button("Crea Piano", type="primary", key="create_plan"):
        if not p_name.strip():
            st.error("Il nome del piano è obbligatorio.")
        else:
            pid = create_plan(p_name.strip(), int(p_year), p_notes.strip())
            st.success(f"Piano '{p_name}' creato (ID #{pid}).", icon="✓")
            st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# LISTA PIANI
# ══════════════════════════════════════════════════════════════════════════════

plans = get_all_plans()
controls = get_all_controls()
ctrl_by_id = {c.id: c for c in controls}

if not plans:
    st.info("Nessun piano creato. Usa il form sopra per creare il primo Piano di Audit.", icon="ℹ️")
    st.stop()

STATUS_PLAN_COLORS = {
    "draft":  ("📝", "Bozza"),
    "active": ("▶️", "Attivo"),
    "closed": ("✅", "Chiuso"),
}

for plan in plans:
    icon_p, label_p = STATUS_PLAN_COLORS.get(plan["status"], ("", plan["status"]))
    items = get_plan_items(plan["id"])
    completion = get_plan_completion(plan["id"])
    pct = (completion["completed"] / completion["total"] * 100) if completion["total"] else 0

    with st.expander(
        f"{icon_p} **{plan['name']}** ({plan['year']}) — {label_p} — "
        f"{completion['completed']}/{completion['total']} controlli completati",
        expanded=(plan["status"] == "active"),
    ):
        # ── Header piano ─────────────────────────────────────────────────────
        hc1, hc2, hc3 = st.columns([4, 2, 2])
        with hc1:
            if plan["notes"]:
                st.caption(plan["notes"])
            st.progress(pct / 100, text=f"Completamento: {pct:.0f}%")
        with hc2:
            new_plan_status = st.selectbox(
                "Stato piano",
                ["draft", "active", "closed"],
                index=["draft", "active", "closed"].index(plan["status"]),
                key=f"pst_{plan['id']}",
            )
            if st.button("Aggiorna", key=f"pstupd_{plan['id']}", use_container_width=True):
                update_plan_status(plan["id"], new_plan_status)
                st.rerun()
        with hc3:
            st.metric("Totale", completion["total"])
            st.metric("In corso", completion["in_progress"])

        st.markdown("---")

        # ── Aggiungi controlli al piano ───────────────────────────────────────
        st.markdown("**Aggiungi controllo al piano:**")
        with st.form(key=f"add_item_form_{plan['id']}"):
            fi1, fi2, fi3, fi4 = st.columns([3, 3, 2, 2])
            existing_ctrl_ids = {i["control_id"] for i in items}
            available_controls = [c for c in controls if c.id not in existing_ctrl_ids]

            with fi1:
                if available_controls:
                    sel_ctrl = st.selectbox(
                        "Controllo",
                        options=[c.id for c in available_controls],
                        format_func=lambda cid: f"{cid} — {ctrl_by_id[cid].title[:40]}",
                        key=f"fi_ctrl_{plan['id']}",
                    )
                else:
                    st.info("Tutti i controlli dell'Anagrafica sono già nel piano.")
                    sel_ctrl = None
            with fi2:
                fi_assigned = st.text_input(
                    "Assegnato a",
                    placeholder="es. Mario Rossi",
                    key=f"fi_assigned_{plan['id']}",
                )
            with fi3:
                fi_date = st.date_input(
                    "Data prevista",
                    value=date.today(),
                    key=f"fi_date_{plan['id']}",
                )
            with fi4:
                st.markdown("<br>", unsafe_allow_html=True)
                submitted_item = st.form_submit_button("Aggiungi", type="primary")

            if submitted_item and sel_ctrl:
                add_plan_item(
                    plan["id"], sel_ctrl,
                    str(fi_date),
                    fi_assigned.strip(),
                )
                st.rerun()

        st.markdown("---")

        # ── Vista tabellare degli item ────────────────────────────────────────
        if not items:
            st.caption("Nessun controllo aggiunto al piano.")
        else:
            st.markdown("**Controlli nel piano:**")

            ITEM_STATUS_COLORS = {
                "planned":     "🔵",
                "in_progress": "🟡",
                "completed":   "🟢",
            }

            for item in items:
                ic1, ic2, ic3, ic4, ic5 = st.columns([1, 4, 2, 2, 3])

                with ic1:
                    st.markdown(
                        ITEM_STATUS_COLORS.get(item["status"], "⚪"),
                        help=item["status"],
                    )
                with ic2:
                    ctrl_title = item.get("control_title") or item["control_id"]
                    ctrl_area  = item.get("control_area", "")
                    st.markdown(
                        f"**{item['control_id']}** — {ctrl_title[:50]}  \n"
                        f"<span style='color:#8c8c8c;font-size:12px;'>{ctrl_area}</span>",
                        unsafe_allow_html=True,
                    )
                with ic3:
                    st.caption(
                        f"Data: {item['planned_date'] or '—'}  \n"
                        f"Assegnato: {item['assigned_to'] or '—'}"
                    )
                with ic4:
                    # Crea engagement dal piano
                    if item["engagement_id"]:
                        eng_name = item.get("engagement_name") or f"Engagement #{item['engagement_id']}"
                        st.caption(f"Engagement: {eng_name}")
                    else:
                        eng_btn_key = f"create_eng_{item['id']}"
                        if st.button(
                            "▶ Avvia Engagement",
                            key=eng_btn_key,
                            use_container_width=True,
                            type="primary",
                        ):
                            eng_name_auto = (
                                f"{plan['name']} — {item['control_id']}"
                            )
                            new_eng_id = create_engagement(eng_name_auto)
                            link_engagement_to_item(item["id"], new_eng_id)
                            st.success(
                                f"Engagement '{eng_name_auto}' creato. "
                                "Vai a **Engagement** per eseguire la verifica.",
                                icon="✓",
                            )
                            st.rerun()
                with ic5:
                    col_s, col_d = st.columns([3, 1])
                    with col_s:
                        new_item_status = st.selectbox(
                            "",
                            ["planned", "in_progress", "completed"],
                            index=["planned", "in_progress", "completed"].index(item["status"]),
                            key=f"ist_{item['id']}",
                            label_visibility="collapsed",
                        )
                        if new_item_status != item["status"]:
                            update_plan_item_status(item["id"], new_item_status)
                            st.rerun()
                    with col_d:
                        if st.button("🗑", key=f"idel_{item['id']}", use_container_width=True):
                            delete_plan_item(item["id"])
                            st.rerun()

                st.markdown(
                    '<hr style="border:none;border-top:1px solid #f0f0f0;margin:4px 0;">',
                    unsafe_allow_html=True,
                )
