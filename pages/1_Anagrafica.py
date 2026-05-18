"""
Anagrafica — CRUD di Controlli, Owner, Processi, Procedure, Rischi e RCM.
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

from auth.utils import require_login, can_edit, role_label, get_current_username
from ui.common import inject_css, render_sidebar_nav
from db.repositories import (
    # Controlli
    get_all_controls, upsert_control, delete_control, reset_controls_to_defaults,
    # Owner
    get_all_owners, upsert_owner, delete_owner,
    # Processi
    get_all_processes, upsert_process, delete_process,
    # Procedure
    get_all_procedures, upsert_procedure, delete_procedure,
    get_process_ids_for_procedure, set_procedure_processes,
    # Rischi
    get_all_risks, upsert_risk, delete_risk,
    get_procedure_ids_for_risk, set_risk_procedures,
    get_control_ids_for_risk, set_risk_controls,
    # RCM
    get_rcm, get_rcm_gaps,
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

tab_owners, tab_proc, tab_proced, tab_risks, tab_controls, tab_rcm = st.tabs([
    "👤 Owner", "🏢 Processi", "📄 Procedure", "⚠️ Rischi",
    "📋 Controlli", "🗂 Control universe",
])


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
            if st.button("↺ Reset to defaults",
                         help="Ricarica i 3 controlli del POC (C01, C02, C03)"):
                reset_controls_to_defaults()
                st.success("Controlli ripristinati.", icon="✅")
                st.rerun()

    st.markdown("---")

    for ctrl in controls:
        type_badge = "🤖 AI" if ctrl.ctrl_type == "ai" else "📋 Manuale"
        with st.expander(
            f"**{ctrl.id}** — {ctrl.title}  ·  `{ctrl.area}`  ·  {type_badge}"
        ):
            col_form, col_actions = st.columns([5, 1])

            with col_form:
                new_title = st.text_input("Titolo", value=ctrl.title,
                                          key=f"title_{ctrl.id}")
                new_area  = st.text_input("Area", value=ctrl.area,
                                          key=f"area_{ctrl.id}")
                new_desc  = st.text_area("Descrizione", value=ctrl.description,
                                         height=90, key=f"desc_{ctrl.id}")
                new_cp    = st.text_area(
                    "Check points (uno per riga)",
                    value="\n".join(ctrl.check_points),
                    height=120, key=f"cp_{ctrl.id}",
                )
                new_docs  = st.text_area(
                    "Documenti attesi (uno per riga)",
                    value="\n".join(ctrl.expected_documents),
                    height=80, key=f"docs_{ctrl.id}",
                )
                new_type = st.selectbox(
                    "Tipo di verifica",
                    options=["ai", "manual"],
                    index=0 if ctrl.ctrl_type == "ai" else 1,
                    format_func=lambda v: "🤖 AI — verifica tramite modello LLM"
                                          if v == "ai"
                                          else "📋 Manuale — revisione documentale da parte dell'auditor",
                    key=f"type_{ctrl.id}",
                )

            with col_actions:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if can_edit():
                    if st.button("💾 Salva", key=f"save_{ctrl.id}",
                                 type="primary", use_container_width=True):
                        updated = Control(
                            id=ctrl.id,
                            title=new_title.strip(),
                            area=new_area.strip(),
                            description=new_desc.strip(),
                            check_points=[l.strip() for l in new_cp.splitlines()
                                          if l.strip()],
                            expected_documents=[l.strip() for l in
                                                new_docs.splitlines() if l.strip()],
                            ctrl_type=new_type,
                        )
                        upsert_control(updated)
                        st.success("Salvato.", icon="✅")
                        st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑 Elimina", key=f"del_{ctrl.id}",
                                 use_container_width=True):
                        delete_control(ctrl.id)
                        st.rerun()

    st.markdown("---")

    if can_edit():
        with st.expander("➕ Aggiungi nuovo controllo"):
            n_id    = st.text_input("ID (es. C07)", key="new_id")
            n_title = st.text_input("Titolo", key="new_title")
            n_area  = st.text_input("Area", key="new_area")
            n_desc  = st.text_area("Descrizione", height=80, key="new_desc")
            n_cp    = st.text_area("Check points (uno per riga)", height=100,
                                   key="new_cp")
            n_docs  = st.text_area("Documenti attesi (uno per riga)", height=60,
                                   key="new_docs")
            n_type  = st.selectbox(
                "Tipo di verifica",
                options=["ai", "manual"],
                format_func=lambda v: "🤖 AI — verifica tramite modello LLM"
                                      if v == "ai"
                                      else "📋 Manuale — revisione documentale da parte dell'auditor",
                key="new_type",
            )

            if st.button("Aggiungi", type="primary", key="add_ctrl"):
                if not n_id.strip() or not n_title.strip():
                    st.error("ID e Titolo sono obbligatori.")
                else:
                    new_ctrl = Control(
                        id=n_id.strip().upper(),
                        title=n_title.strip(),
                        area=n_area.strip(),
                        description=n_desc.strip(),
                        check_points=[l.strip() for l in n_cp.splitlines()
                                      if l.strip()],
                        expected_documents=[l.strip() for l in
                                            n_docs.splitlines() if l.strip()],
                        ctrl_type=n_type,
                    )
                    upsert_control(new_ctrl)
                    st.success(f"Controllo {new_ctrl.id} aggiunto.", icon="✅")
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
                o_name = st.text_input("Nome", value=o["name"],
                                       key=f"oname_{o['id']}")
                o_role = st.text_input("Ruolo", value=o["role"],
                                       key=f"orole_{o['id']}")
                o_area = st.text_input("Area", value=o["area"],
                                       key=f"oarea_{o['id']}")
            with col_a:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if can_edit():
                    if st.button("💾 Salva", key=f"osave_{o['id']}",
                                 type="primary", use_container_width=True):
                        upsert_owner(o["id"], o_name.strip(), o_role.strip(),
                                     o_area.strip())
                        st.success("Salvato.", icon="✅")
                        st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑 Elimina", key=f"odel_{o['id']}",
                                 use_container_width=True):
                        delete_owner(o["id"])
                        st.rerun()

    st.markdown("---")

    if can_edit():
        with st.expander("➕ Aggiungi owner"):
            on  = st.text_input("Nome", key="o_new_name")
            or_ = st.text_input("Ruolo (es. Process Owner, Control Owner)",
                                key="o_new_role")
            oa  = st.text_input("Area di competenza", key="o_new_area")
            if st.button("Aggiungi", type="primary", key="add_owner"):
                if not on.strip():
                    st.error("Il nome è obbligatorio.")
                else:
                    upsert_owner(None, on.strip(), or_.strip(), oa.strip())
                    st.success(f"Owner '{on}' aggiunto.", icon="✅")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB PROCESSI
# ══════════════════════════════════════════════════════════════════════════════

with tab_proc:
    processes = get_all_processes()

    st.markdown(f"**{len(processes)} processi** registrati.")
    st.caption(
        "I processi aziendali rappresentano il livello più alto della gerarchia "
        "Processo → Procedura → Rischio → Controllo."
    )
    st.markdown("---")

    for p in processes:
        label = f"**{p['code']}** — {p['name']}" if p["code"] else f"**{p['name']}**"
        with st.expander(label):
            col_f, col_a = st.columns([5, 1])
            with col_f:
                p_code  = st.text_input("Codice (es. P01)", value=p["code"],
                                         key=f"pcode_{p['id']}")
                p_name  = st.text_input("Nome", value=p["name"],
                                         key=f"pname_{p['id']}")
                p_desc  = st.text_area("Descrizione", value=p["description"],
                                        height=80, key=f"pdesc_{p['id']}")
                p_owner = st.text_input("Process Owner", value=p["owner"],
                                         key=f"powner_{p['id']}")
            with col_a:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if can_edit():
                    if st.button("💾 Salva", key=f"psave_{p['id']}",
                                 type="primary", use_container_width=True):
                        upsert_process(
                            p["id"], p_code.strip(), p_name.strip(),
                            p_desc.strip(), p_owner.strip(),
                            user=get_current_username(),
                        )
                        st.success("Processo salvato.", icon="✅")
                        st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑 Elimina", key=f"pdel_{p['id']}",
                                 use_container_width=True):
                        delete_process(p["id"], user=get_current_username())
                        st.rerun()

    st.markdown("---")

    if can_edit():
        with st.expander("➕ Aggiungi processo"):
            nc = st.text_input("Codice (es. P01)", key="new_pcode")
            nn = st.text_input("Nome *", key="new_pname")
            nd = st.text_area("Descrizione", height=80, key="new_pdesc")
            no = st.text_input("Process Owner", key="new_powner")
            if st.button("Aggiungi", type="primary", key="add_proc"):
                if not nn.strip():
                    st.error("Il nome è obbligatorio.")
                else:
                    upsert_process(
                        None, nc.strip(), nn.strip(), nd.strip(), no.strip(),
                        user=get_current_username(),
                    )
                    st.success(f"Processo '{nn}' aggiunto.", icon="✅")
                    st.rerun()
    elif not processes:
        st.info("Nessun processo registrato.", icon="ℹ️")


# ══════════════════════════════════════════════════════════════════════════════
# TAB PROCEDURE
# ══════════════════════════════════════════════════════════════════════════════

with tab_proced:
    procedures = get_all_procedures()
    processes  = get_all_processes()

    proc_map   = {p["name"]: p["id"] for p in processes}   # nome → id
    proc_by_id = {p["id"]: p["name"] for p in processes}   # id → nome

    st.markdown(f"**{len(procedures)} procedure** registrate.")
    st.caption(
        "Ogni procedura può essere associata a uno o più processi. "
        "Le procedure contengono i rischi operativi da presidiare."
    )
    st.markdown("---")

    for pr in procedures:
        label = (f"**{pr['code']}** — {pr['name']}"
                 if pr["code"] else f"**{pr['name']}**")
        with st.expander(label):
            col_f, col_a = st.columns([5, 1])
            with col_f:
                pr_code = st.text_input("Codice (es. PR01)", value=pr["code"],
                                         key=f"prcode_{pr['id']}")
                pr_name = st.text_input("Nome", value=pr["name"],
                                         key=f"prname_{pr['id']}")
                pr_desc = st.text_area("Descrizione", value=pr["description"],
                                        height=80, key=f"prdesc_{pr['id']}")

                st.markdown("**Processi associati:**")
                if processes:
                    cur_proc_ids = get_process_ids_for_procedure(pr["id"])
                    cur_proc_names = [proc_by_id[i] for i in cur_proc_ids
                                      if i in proc_by_id]
                    sel_procs = st.multiselect(
                        "Seleziona processi",
                        options=list(proc_map.keys()),
                        default=cur_proc_names,
                        key=f"prprocs_{pr['id']}",
                        label_visibility="collapsed",
                    )
                else:
                    st.caption("⚠️ Nessun processo disponibile — aggiungine uno "
                               "nel tab **Processi**.")
                    sel_procs = []

            with col_a:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if can_edit():
                    if st.button("💾 Salva", key=f"prsave_{pr['id']}",
                                 type="primary", use_container_width=True):
                        upsert_procedure(
                            pr["id"], pr_code.strip(), pr_name.strip(),
                            pr_desc.strip(), user=get_current_username(),
                        )
                        set_procedure_processes(
                            pr["id"],
                            [proc_map[n] for n in sel_procs],
                            user=get_current_username(),
                        )
                        st.success("Procedura salvata.", icon="✅")
                        st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑 Elimina", key=f"prdel_{pr['id']}",
                                 use_container_width=True):
                        delete_procedure(pr["id"], user=get_current_username())
                        st.rerun()

    st.markdown("---")

    if can_edit():
        with st.expander("➕ Aggiungi procedura"):
            npc  = st.text_input("Codice (es. PR01)", key="new_prcode")
            npn  = st.text_input("Nome *", key="new_prname")
            npd  = st.text_area("Descrizione", height=80, key="new_prdesc")
            if processes:
                npp = st.multiselect("Processi associati",
                                     options=list(proc_map.keys()),
                                     key="new_prprocs")
            else:
                npp = []
                st.caption("⚠️ Aggiungi prima almeno un processo.")
            if st.button("Aggiungi", type="primary", key="add_proced"):
                if not npn.strip():
                    st.error("Il nome è obbligatorio.")
                else:
                    new_pid = upsert_procedure(
                        None, npc.strip(), npn.strip(), npd.strip(),
                        user=get_current_username(),
                    )
                    if npp:
                        set_procedure_processes(
                            new_pid,
                            [proc_map[n] for n in npp],
                            user=get_current_username(),
                        )
                    st.success(f"Procedura '{npn}' aggiunta.", icon="✅")
                    st.rerun()
    elif not procedures:
        st.info("Nessuna procedura registrata.", icon="ℹ️")


# ══════════════════════════════════════════════════════════════════════════════
# TAB RISCHI
# ══════════════════════════════════════════════════════════════════════════════

with tab_risks:
    risks      = get_all_risks()
    procedures = get_all_procedures()
    controls   = get_all_controls()

    proced_map   = {pr["name"]: pr["id"] for pr in procedures}
    proced_by_id = {pr["id"]: pr["name"] for pr in procedures}
    ctrl_map     = {f"{c.id} — {c.title}": c.id for c in controls}
    ctrl_by_id   = {c.id: f"{c.id} — {c.title}" for c in controls}

    RISK_CATEGORIES = [
        "Operativo", "Finanziario", "Compliance", "Strategico",
        "Reputazionale", "IT / Cyber", "Frode", "Altro",
    ]

    st.markdown(f"**{len(risks)} rischi** registrati.")
    st.caption(
        "Ogni rischio può essere associato a una o più procedure e "
        "a uno o più controlli mitiganti."
    )
    st.markdown("---")

    for r in risks:
        label = (f"**{r['code']}** — {r['name']}"
                 if r["code"] else f"**{r['name']}**")
        if r["category"]:
            label += f"  ·  `{r['category']}`"
        with st.expander(label):
            col_f, col_a = st.columns([5, 1])
            with col_f:
                r_code = st.text_input("Codice rischio (es. R01)", value=r["code"],
                                        key=f"rcode_{r['id']}")
                r_name = st.text_input("Nome", value=r["name"],
                                        key=f"rname_{r['id']}")
                r_desc = st.text_area("Descrizione", value=r["description"],
                                       height=80, key=f"rdesc_{r['id']}")
                cat_idx = (RISK_CATEGORIES.index(r["category"])
                           if r["category"] in RISK_CATEGORIES else 0)
                r_cat  = st.selectbox("Categoria", RISK_CATEGORIES, index=cat_idx,
                                       key=f"rcat_{r['id']}")

                st.markdown("**Procedure associate:**")
                if procedures:
                    cur_proced_ids = get_procedure_ids_for_risk(r["id"])
                    cur_proced_names = [proced_by_id[i] for i in cur_proced_ids
                                        if i in proced_by_id]
                    sel_proceds = st.multiselect(
                        "Seleziona procedure",
                        options=list(proced_map.keys()),
                        default=cur_proced_names,
                        key=f"rproceds_{r['id']}",
                        label_visibility="collapsed",
                    )
                else:
                    st.caption("⚠️ Nessuna procedura disponibile.")
                    sel_proceds = []

                st.markdown("**Controlli mitiganti:**")
                if controls:
                    cur_ctrl_ids = get_control_ids_for_risk(r["id"])
                    cur_ctrl_labels = [ctrl_by_id[i] for i in cur_ctrl_ids
                                       if i in ctrl_by_id]
                    sel_ctrls = st.multiselect(
                        "Seleziona controlli",
                        options=list(ctrl_map.keys()),
                        default=cur_ctrl_labels,
                        key=f"rctrls_{r['id']}",
                        label_visibility="collapsed",
                    )
                else:
                    st.caption("⚠️ Nessun controllo disponibile.")
                    sel_ctrls = []

            with col_a:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if can_edit():
                    if st.button("💾 Salva", key=f"rsave_{r['id']}",
                                 type="primary", use_container_width=True):
                        upsert_risk(
                            r["id"], r_code.strip(), r_name.strip(),
                            r_desc.strip(), r_cat,
                            user=get_current_username(),
                        )
                        set_risk_procedures(
                            r["id"],
                            [proced_map[n] for n in sel_proceds],
                            user=get_current_username(),
                        )
                        set_risk_controls(
                            r["id"],
                            [ctrl_map[n] for n in sel_ctrls],
                            user=get_current_username(),
                        )
                        st.success("Rischio salvato.", icon="✅")
                        st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑 Elimina", key=f"rdel_{r['id']}",
                                 use_container_width=True):
                        delete_risk(r["id"], user=get_current_username())
                        st.rerun()

    st.markdown("---")

    if can_edit():
        with st.expander("➕ Aggiungi rischio"):
            nrc  = st.text_input("Codice (es. R01)", key="new_rcode")
            nrn  = st.text_input("Nome *", key="new_rname")
            nrd  = st.text_area("Descrizione", height=80, key="new_rdesc")
            nrcat = st.selectbox("Categoria", RISK_CATEGORIES, key="new_rcat")
            if procedures:
                nrp = st.multiselect("Procedure associate",
                                     options=list(proced_map.keys()),
                                     key="new_rproceds")
            else:
                nrp = []
            if controls:
                nrc_ctrls = st.multiselect("Controlli mitiganti",
                                           options=list(ctrl_map.keys()),
                                           key="new_rctrls")
            else:
                nrc_ctrls = []

            if st.button("Aggiungi", type="primary", key="add_risk"):
                if not nrn.strip():
                    st.error("Il nome è obbligatorio.")
                else:
                    new_rid = upsert_risk(
                        None, nrc.strip(), nrn.strip(), nrd.strip(), nrcat,
                        user=get_current_username(),
                    )
                    if nrp:
                        set_risk_procedures(
                            new_rid, [proced_map[n] for n in nrp],
                            user=get_current_username(),
                        )
                    if nrc_ctrls:
                        set_risk_controls(
                            new_rid, [ctrl_map[n] for n in nrc_ctrls],
                            user=get_current_username(),
                        )
                    st.success(f"Rischio '{nrn}' aggiunto.", icon="✅")
                    st.rerun()
    elif not risks:
        st.info("Nessun rischio registrato.", icon="ℹ️")


# ══════════════════════════════════════════════════════════════════════════════
# TAB RCM — Risk Control Matrix (sola lettura)
# ══════════════════════════════════════════════════════════════════════════════

with tab_rcm:
    import pandas as pd
    from collections import OrderedDict

    st.markdown("#### Control Universe")
    st.caption(
        "Vista consolidata in **sola lettura** — catena completa "
        "Processo → Procedura → Rischio → Controllo."
    )

    rcm_rows = get_rcm()

    if not rcm_rows:
        st.info(
            "Nessuna catena completa configurata. "
            "Popola i tab **Processi**, **Procedure** e **Rischi** "
            "con le rispettive associazioni per visualizzare la matrice.",
            icon="ℹ️",
        )
    else:
        # ── Vista / Tabella toggle ────────────────────────────────────────────
        view_mode = st.radio(
            "Modalità di visualizzazione",
            ["🌳 Vista ad albero", "📊 Tabella piatta"],
            horizontal=True,
            label_visibility="collapsed",
        )

        # ── Costruzione albero in memoria ─────────────────────────────────────
        # proc_id → { meta, procedures: { proced_id → { meta, risks: { risk_id → { meta, controls: [...] } } } } }
        tree: dict = OrderedDict()
        for row in rcm_rows:
            pid  = row["proc_id"]
            prid = row["proced_id"]
            rid  = row["risk_id"]

            if pid not in tree:
                tree[pid] = {
                    "code":  row["proc_code"],
                    "name":  row["proc_name"],
                    "owner": row["proc_owner"],
                    "procedures": OrderedDict(),
                }
            proc_node = tree[pid]

            if prid not in proc_node["procedures"]:
                proc_node["procedures"][prid] = {
                    "code": row["proced_code"],
                    "name": row["proced_name"],
                    "desc": row["proced_desc"],
                    "risks": OrderedDict(),
                }
            proced_node = proc_node["procedures"][prid]

            if rid not in proced_node["risks"]:
                proced_node["risks"][rid] = {
                    "code":     row["risk_code"],
                    "name":     row["risk_name"],
                    "desc":     row["risk_desc"],
                    "category": row["risk_category"],
                    "controls": [],
                }
            proced_node["risks"][rid]["controls"].append({
                "id":    row["ctrl_id"],
                "title": row["ctrl_title"],
                "area":  row["ctrl_area"],
            })

        # ── KPI summary ───────────────────────────────────────────────────────
        n_procs   = len({r["proc_id"]   for r in rcm_rows})
        n_proceds = len({r["proced_id"] for r in rcm_rows})
        n_risks   = len({r["risk_id"]   for r in rcm_rows})
        n_ctrls   = len({r["ctrl_id"]   for r in rcm_rows})

        kc1, kc2, kc3, kc4 = st.columns(4)
        kc1.metric("Processi", n_procs)
        kc2.metric("Procedure", n_proceds)
        kc3.metric("Rischi", n_risks)
        kc4.metric("Controlli mappati", n_ctrls)

        st.markdown("---")

        # ── VISTA AD ALBERO ───────────────────────────────────────────────────
        if view_mode == "🌳 Vista ad albero":

            CATEGORY_COLORS = {
                "Operativo":       "#d48806",
                "Finanziario":     "#1890ff",
                "Compliance":      "#722ed1",
                "Strategico":      "#eb2f96",
                "Reputazionale":   "#fa8c16",
                "IT / Cyber":      "#13c2c2",
                "Frode":           "#cf1322",
                "Altro":           "#8c8c8c",
            }

            for pid, proc in tree.items():
                proc_label = (f"{proc['code']} — {proc['name']}"
                              if proc["code"] else proc["name"])

                with st.expander(f"🏢  {proc_label}", expanded=True):

                    if proc["owner"]:
                        st.caption(f"Process Owner: **{proc['owner']}**")

                    for prid, proced in proc["procedures"].items():
                        proced_label = (f"{proced['code']} — {proced['name']}"
                                        if proced["code"] else proced["name"])

                        # Intestazione procedura
                        st.markdown(
                            f"""
                            <div style="
                                background:#e6f7ff;
                                border-left:4px solid #1890ff;
                                padding:8px 14px;
                                margin:10px 0 6px 0;
                                border-radius:0 6px 6px 0;
                            ">
                            <span style="font-weight:700;color:#0050b3;">
                                📄 {proced_label}
                            </span>
                            {"<br><span style='font-size:12px;color:#555;'>" + proced["desc"] + "</span>"
                             if proced["desc"] else ""}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        for rid, risk in proced["risks"].items():
                            risk_label = (f"{risk['code']} — {risk['name']}"
                                          if risk["code"] else risk["name"])
                            cat_color = CATEGORY_COLORS.get(risk["category"], "#8c8c8c")

                            # Blocco rischio (indentato)
                            st.markdown(
                                f"""
                                <div style="
                                    margin:4px 0 4px 24px;
                                    padding:8px 14px;
                                    background:#fff7e6;
                                    border-left:4px solid {cat_color};
                                    border-radius:0 6px 6px 0;
                                ">
                                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                                    <span style="font-weight:600;">⚠️ {risk_label}</span>
                                    <span style="
                                        background:{cat_color};color:#fff;
                                        border-radius:4px;padding:1px 8px;
                                        font-size:11px;font-weight:600;
                                    ">{risk["category"]}</span>
                                </div>
                                {"<div style='font-size:12px;color:#555;margin-top:4px;'>" + risk["desc"] + "</div>"
                                 if risk["desc"] else ""}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            # Controlli associati (indentati ulteriormente)
                            for ctrl in risk["controls"]:
                                st.markdown(
                                    f"""
                                    <div style="
                                        margin:2px 0 2px 48px;
                                        padding:6px 14px;
                                        background:#f6ffed;
                                        border-left:4px solid #7BAF2E;
                                        border-radius:0 6px 6px 0;
                                        display:flex;align-items:center;gap:10px;
                                    ">
                                        <span style="
                                            background:#7BAF2E;color:#fff;
                                            border-radius:4px;padding:1px 8px;
                                            font-size:11px;font-weight:700;
                                            white-space:nowrap;
                                        ">{ctrl["id"]}</span>
                                        <span style="font-size:13px;">
                                            🛡 {ctrl["title"]}
                                        </span>
                                        <span style="
                                            font-size:11px;color:#8c8c8c;
                                            margin-left:auto;white-space:nowrap;
                                        ">{ctrl["area"]}</span>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                        st.markdown("")  # spaziatura

        # ── TABELLA PIATTA ────────────────────────────────────────────────────
        else:
            df = pd.DataFrame([{
                "Processo":         (f"{r['proc_code']} — {r['proc_name']}"
                                     if r["proc_code"] else r["proc_name"]),
                "Procedura":        (f"{r['proced_code']} — {r['proced_name']}"
                                     if r["proced_code"] else r["proced_name"]),
                "Cod. Rischio":     r["risk_code"],
                "Rischio":          r["risk_name"],
                "Categoria":        r["risk_category"],
                "ID Controllo":     r["ctrl_id"],
                "Titolo Controllo": r["ctrl_title"],
                "Area Controllo":   r["ctrl_area"],
            } for r in rcm_rows])

            st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Lacune ────────────────────────────────────────────────────────────────
    gaps = get_rcm_gaps()
    has_gaps = any(gaps[k] for k in gaps)

    if has_gaps:
        st.markdown("---")
        st.markdown("#### ⚠️ Lacune di copertura")
        st.caption(
            "Entità non ancora collegate — completare le associazioni "
            "nei rispettivi tab per includerle nella matrice."
        )

        gc1, gc2, gc3 = st.columns(3)

        with gc1:
            if gaps["processes"]:
                st.markdown("**Processi senza procedure:**")
                for g in gaps["processes"]:
                    st.markdown(f"- {g['name']}")
            else:
                st.markdown("✅ Tutti i processi hanno procedure")

        with gc2:
            if gaps["procedures"]:
                st.markdown("**Procedure senza rischi:**")
                for g in gaps["procedures"]:
                    st.markdown(f"- {g['name']}")
            else:
                st.markdown("✅ Tutte le procedure hanno rischi")

        with gc3:
            if gaps["risks"]:
                st.markdown("**Rischi senza controlli:**")
                for g in gaps["risks"]:
                    st.markdown(f"- {g['name']}")
            else:
                st.markdown("✅ Tutti i rischi hanno controlli")
