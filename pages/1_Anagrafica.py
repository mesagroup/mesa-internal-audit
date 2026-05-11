"""
Anagrafica — CRUD di Controlli e Owner.
"""
from __future__ import annotations

import json

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Anagrafica — MESA ERM",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth.utils import require_login, can_edit, role_label
from ui.common import inject_css, render_sidebar_nav
from db.repositories import (
    get_all_controls, upsert_control, delete_control, reset_controls_to_defaults,
    get_all_owners, upsert_owner, delete_owner,
)
from core.controls_tree import Control

authenticator = require_login()
inject_css()
render_sidebar_nav(authenticator)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="page-header">
      <h2>Anagrafica</h2>
      <span class="area-chip">Control Universe</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if not can_edit():
    st.info(f"Visualizzazione in sola lettura — ruolo: {role_label()}", icon="🔒")

tab_controls, tab_owners = st.tabs(["📋 Controlli", "👤 Owner"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB CONTROLLI
# ══════════════════════════════════════════════════════════════════════════════

with tab_controls:
    controls = get_all_controls()

    col_title, col_btn = st.columns([6, 2])
    with col_title:
        st.markdown(f"**{len(controls)} controlli** registrati nel Control Universe.")
    with col_btn:
        if can_edit():
            if st.button("↺ Reset to defaults", help="Ricarica i 3 controlli del POC (C01, C02, C03)"):
                reset_controls_to_defaults()
                st.success("Controlli ripristinati.", icon="✓")
                st.rerun()

    st.markdown("---")

    # ── Lista controlli con expander per dettaglio/modifica ─────────────────

    for ctrl in controls:
        with st.expander(f"**{ctrl.id}** — {ctrl.title}  ·  `{ctrl.area}`"):
            col_form, col_actions = st.columns([5, 1])

            with col_form:
                new_title = st.text_input("Titolo", value=ctrl.title, key=f"title_{ctrl.id}")
                new_area  = st.text_input("Area", value=ctrl.area, key=f"area_{ctrl.id}")
                new_desc  = st.text_area("Descrizione", value=ctrl.description, height=90, key=f"desc_{ctrl.id}")
                new_cp    = st.text_area(
                    "Check points (uno per riga)",
                    value="\n".join(ctrl.check_points),
                    height=120,
                    key=f"cp_{ctrl.id}",
                )
                new_docs  = st.text_area(
                    "Documenti attesi (uno per riga)",
                    value="\n".join(ctrl.expected_documents),
                    height=80,
                    key=f"docs_{ctrl.id}",
                )

            with col_actions:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if can_edit():
                    if st.button("💾 Salva", key=f"save_{ctrl.id}", type="primary", use_container_width=True):
                        updated = Control(
                            id=ctrl.id,
                            title=new_title.strip(),
                            area=new_area.strip(),
                            description=new_desc.strip(),
                            check_points=[l.strip() for l in new_cp.splitlines() if l.strip()],
                            expected_documents=[l.strip() for l in new_docs.splitlines() if l.strip()],
                        )
                        upsert_control(updated)
                        st.success("Salvato.", icon="✓")
                        st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑 Elimina", key=f"del_{ctrl.id}", use_container_width=True):
                        delete_control(ctrl.id)
                        st.rerun()

    st.markdown("---")

    # ── Aggiungi nuovo controllo ─────────────────────────────────────────────

    if not can_edit():
        st.stop()

    with st.expander("➕ Aggiungi nuovo controllo"):
        n_id   = st.text_input("ID (es. C04)", key="new_id")
        n_title = st.text_input("Titolo", key="new_title")
        n_area  = st.text_input("Area", key="new_area")
        n_desc  = st.text_area("Descrizione", height=80, key="new_desc")
        n_cp    = st.text_area("Check points (uno per riga)", height=100, key="new_cp")
        n_docs  = st.text_area("Documenti attesi (uno per riga)", height=60, key="new_docs")

        if st.button("Aggiungi", type="primary", key="add_ctrl"):
            if not n_id.strip() or not n_title.strip():
                st.error("ID e Titolo sono obbligatori.")
            else:
                new_ctrl = Control(
                    id=n_id.strip().upper(),
                    title=n_title.strip(),
                    area=n_area.strip(),
                    description=n_desc.strip(),
                    check_points=[l.strip() for l in n_cp.splitlines() if l.strip()],
                    expected_documents=[l.strip() for l in n_docs.splitlines() if l.strip()],
                )
                upsert_control(new_ctrl)
                st.success(f"Controllo {new_ctrl.id} aggiunto.", icon="✓")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB OWNER
# ══════════════════════════════════════════════════════════════════════════════

with tab_owners:
    owners = get_all_owners()

    st.markdown(f"**{len(owners)} owner** registrati.")
    st.markdown("---")

    for o in owners:
        with st.expander(f"**{o['name']}** — {o['role']}  ·  `{o['area']}`"):
            col_f, col_a = st.columns([5, 1])
            with col_f:
                o_name = st.text_input("Nome", value=o["name"], key=f"oname_{o['id']}")
                o_role = st.text_input("Ruolo", value=o["role"], key=f"orole_{o['id']}")
                o_area = st.text_input("Area", value=o["area"], key=f"oarea_{o['id']}")
            with col_a:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("💾 Salva", key=f"osave_{o['id']}", type="primary", use_container_width=True):
                    upsert_owner(o["id"], o_name.strip(), o_role.strip(), o_area.strip())
                    st.success("Salvato.", icon="✓")
                    st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑 Elimina", key=f"odel_{o['id']}", use_container_width=True):
                    delete_owner(o["id"])
                    st.rerun()

    st.markdown("---")

    with st.expander("➕ Aggiungi owner"):
        on  = st.text_input("Nome", key="o_new_name")
        or_ = st.text_input("Ruolo (es. Process Owner, Control Owner)", key="o_new_role")
        oa  = st.text_input("Area di competenza", key="o_new_area")
        if st.button("Aggiungi", type="primary", key="add_owner"):
            if not on.strip():
                st.error("Il nome è obbligatorio.")
            else:
                upsert_owner(None, on.strip(), or_.strip(), oa.strip())
                st.success(f"Owner '{on}' aggiunto.", icon="✓")
                st.rerun()
