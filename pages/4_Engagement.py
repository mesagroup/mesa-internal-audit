"""
Engagement — Test dei controlli con verifica AI o manuale.
Navigazione: il pannello "Engagement avviati" è il punto di ingresso;
la scheda di verifica appare solo dopo aver selezionato un controllo.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Engagement — MESA ERM",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth.utils import require_login, can_edit, get_current_username, role_label
from ui.common import inject_css, render_sidebar_nav, badge_html, pending_badge
from db.repositories import (
    get_all_controls, get_active_engagements, create_engagement,
    save_verification, create_finding, get_verifications_for_engagement,
    get_engagements_by_plan,
)
from core.document_loader import load_document
from core.llm_verifier import LLMVerifier, VerificationResult, CheckPointResult

authenticator = require_login()
inject_css()
render_sidebar_nav(authenticator)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="page-header">
      <h2>Engagement</h2>
      <span class="area-chip">Test dei Controlli</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if not os.environ.get("OPENAI_API_KEY"):
    st.warning(
        "API key OpenAI non configurata. Imposta OPENAI_API_KEY nel file .env.",
        icon="⚠️",
    )

# ── Carica dati base ──────────────────────────────────────────────────────────

controls_list = get_all_controls()
ctrl_by_id    = {c.id: c for c in controls_list}

# ══════════════════════════════════════════════════════════════════════════════
# STATO: quale controllo/engagement è attivo
# ══════════════════════════════════════════════════════════════════════════════

# Chiavi di sessione: "sel_eng_id", "sel_ctrl_id"
sel_eng_id  = st.session_state.get("sel_eng_id")
sel_ctrl_id = st.session_state.get("sel_ctrl_id")

# ══════════════════════════════════════════════════════════════════════════════
# PANNELLO: ENGAGEMENT AVVIATI — raggruppati per Piano  (sempre visibile)
# ══════════════════════════════════════════════════════════════════════════════

plan_eng_rows = get_engagements_by_plan()

# Raggruppa per piano
plans_map: dict = {}
for row in plan_eng_rows:
    pid = row["plan_id"]
    if pid not in plans_map:
        plans_map[pid] = {
            "name":   row["plan_name"],
            "year":   row["plan_year"],
            "status": row["plan_status"],
            "items":  [],
        }
    plans_map[pid]["items"].append(row)

ITEM_STATUS_ICON = {
    "planned":     "🔵",
    "in_progress": "🟡",
    "completed":   "🟢",
}

# Determina se il pannello deve essere aperto:
# aperto quando non c'è nulla di selezionato, collassato quando si sta verificando
panel_expanded = sel_eng_id is None

if plan_eng_rows:
    panel_label = (
        f"📋 Engagement avviati — "
        f"{len(plan_eng_rows)} controllo/i in {len(plans_map)} piano/i"
    )
    with st.expander(panel_label, expanded=panel_expanded):
        for plan_data in plans_map.values():
            st.markdown(
                f"<p style='font-weight:700;margin-bottom:4px;'>"
                f"{plan_data['name']} "
                f"<span style='color:#8c8c8c;font-weight:400;font-size:13px;'>"
                f"({plan_data['year']})</span></p>",
                unsafe_allow_html=True,
            )

            for item in plan_data["items"]:
                type_badge  = "🤖" if item["ctrl_type"] == "ai" else "📋"
                item_icon   = ITEM_STATUS_ICON.get(item["item_status"], "⚪")
                is_selected = (
                    item["engagement_id"] == sel_eng_id
                    and item["control_id"] == sel_ctrl_id
                )

                # Highlight riga attiva
                row_bg = (
                    "background:#f6ffed;border-left:3px solid #52c41a;"
                    "border-radius:4px;padding:6px 10px;"
                ) if is_selected else (
                    "padding:6px 10px;"
                )

                rc1, rc2, rc3, rc4 = st.columns([1, 5, 4, 2])

                with rc1:
                    st.markdown(
                        f"<div style='{row_bg}'>{item_icon}</div>",
                        unsafe_allow_html=True,
                    )
                with rc2:
                    # Verifica già eseguita?
                    vmap = {
                        v["control_id"]: v
                        for v in get_verifications_for_engagement(item["engagement_id"])
                    }
                    ver = vmap.get(item["control_id"])
                    ver_badge = (
                        badge_html(ver["overall_status"]) if ver else pending_badge()
                    )
                    st.markdown(
                        f"<div style='{row_bg}'>"
                        f"<span style='font-weight:600;'>{item['control_id']}</span> "
                        f"{type_badge} — {item['control_title']}  "
                        f"{ver_badge}<br>"
                        f"<span style='color:#8c8c8c;font-size:12px;'>"
                        f"{item['control_area']}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with rc3:
                    st.markdown(
                        f"<div style='{row_bg};font-size:12px;color:#595959;'>"
                        f"<b>{item['engagement_name']}</b><br>"
                        f"Assegnato: {item['assigned_to'] or '—'}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with rc4:
                    if is_selected:
                        if st.button(
                            "✕ Chiudi",
                            key=f"close_{item['item_id']}",
                            use_container_width=True,
                        ):
                            st.session_state.pop("sel_eng_id", None)
                            st.session_state.pop("sel_ctrl_id", None)
                            st.rerun()
                    else:
                        if st.button(
                            "▶ Apri",
                            key=f"open_{item['item_id']}",
                            use_container_width=True,
                            type="primary",
                        ):
                            st.session_state["sel_eng_id"]  = item["engagement_id"]
                            st.session_state["sel_ctrl_id"] = item["control_id"]
                            st.rerun()

                st.markdown(
                    '<hr style="border:none;border-top:1px solid #f0f0f0;margin:2px 0;">',
                    unsafe_allow_html=True,
                )

            st.markdown("")  # spazio tra piani

else:
    st.info(
        "Nessun engagement avviato. Avvia un engagement dal **Piano di Audit** "
        "o usa la sezione qui sotto per crearne uno libero.",
        icon="ℹ️",
    )

# ── Nuovo Engagement (secondario) ─────────────────────────────────────────────

with st.expander("➕ Crea nuovo Engagement libero"):
    col_n1, col_n2 = st.columns([3, 1])
    with col_n1:
        eng_name = st.text_input("Nome", placeholder="es. Audit P2P 2026 Q3", key="eng_name_input")
        eng_desc = st.text_input("Note (opzionale)", key="eng_desc_input")
    with col_n2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Crea", type="primary", key="create_eng", use_container_width=True):
            if not eng_name.strip():
                st.error("Il nome è obbligatorio.")
            else:
                new_id = create_engagement(eng_name.strip(), eng_desc.strip())
                st.success(f"Engagement '{eng_name}' creato (#{new_id}).", icon="✅")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# NESSUNA SELEZIONE → stop qui
# ══════════════════════════════════════════════════════════════════════════════

if not sel_eng_id or not sel_ctrl_id:
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SCHEDA DI VERIFICA — visibile solo dopo aver selezionato un controllo
# ══════════════════════════════════════════════════════════════════════════════

engagement_id = sel_eng_id
control       = ctrl_by_id.get(sel_ctrl_id)

if control is None:
    st.error(f"Controllo {sel_ctrl_id} non trovato in Anagrafica.")
    st.stop()

# Recupera verifica precedente per questo engagement+controllo
verifications    = get_verifications_for_engagement(engagement_id)
verified_controls = {v["control_id"]: v for v in verifications}
prev             = verified_controls.get(control.id)

# ── Sidebar: progresso engagement ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="nav-section-label">Progresso engagement</p>', unsafe_allow_html=True)
    for ctrl in controls_list:
        v = verified_controls.get(ctrl.id)
        b = badge_html(v["overall_status"]) if v else pending_badge()
        is_cur = ctrl.id == control.id
        style = "font-weight:700;color:#52c41a;" if is_cur else "font-weight:600;color:#7BAF2E;"
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:4px 16px;font-size:12px;">'
            f'<span style="{style};margin-right:4px;">{ctrl.id}</span>'
            f'{ctrl.title[:24]}…{b}</div>',
            unsafe_allow_html=True,
        )
    done  = len(verified_controls)
    total = len(controls_list)
    st.progress(done / total if total else 0)
    st.caption(f"Progresso: {done} / {total} controlli")

# ── Intestazione scheda controllo ────────────────────────────────────────────

st.markdown("---")

type_label = "🤖 Verifica AI" if control.ctrl_type == "ai" else "📋 Verifica manuale"
st.markdown(
    f"<h4 style='margin-bottom:4px;'>{control.id} — {control.title}"
    f"<span style='font-size:14px;font-weight:400;color:#595959;margin-left:10px;'>"
    f"{type_label} · {control.area}</span></h4>",
    unsafe_allow_html=True,
)

with st.expander("Descrizione e check points", expanded=False):
    st.markdown(control.description)
    st.markdown("**Check points:**")
    for i, cp in enumerate(control.check_points, 1):
        st.markdown(f"{i}. {cp}")
    st.markdown("**Documenti attesi:**")
    for d in control.expected_documents:
        st.markdown(f"- {d}")

if prev:
    st.info(
        f"Verifica già eseguita il {prev['verified_at'][:16]}. "
        "Puoi ri-eseguirla — il nuovo esito sovrascriverà il precedente.",
        icon="ℹ️",
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# BRANCH: MANUALE vs AI
# ══════════════════════════════════════════════════════════════════════════════

result_key = f"result_{engagement_id}_{control.id}"

if control.ctrl_type == "manual":
    # ── VERIFICA MANUALE ──────────────────────────────────────────────────────
    st.markdown("#### Registra l'esito della verifica manuale")
    st.info(
        "Controllo manuale — esamina la documentazione e registra l'esito direttamente.",
        icon="📋",
    )

    with st.expander("Check points da verificare", expanded=True):
        for i, cp in enumerate(control.check_points, 1):
            st.markdown(f"{i}. {cp}")
        st.markdown("**Documenti da richiedere:**")
        for d in control.expected_documents:
            st.markdown(f"- {d}")

    man_col1, man_col2 = st.columns([1, 2])
    with man_col1:
        man_status = st.selectbox(
            "Esito complessivo",
            options=["conforme", "parziale", "non_conforme"],
            format_func=lambda v: {
                "conforme":     "✅ Conforme",
                "parziale":     "⚠️ Parzialmente conforme",
                "non_conforme": "❌ Non conforme",
            }[v],
            key=f"man_status_{control.id}",
        )
    with man_col2:
        if result_key in st.session_state:
            res = st.session_state[result_key]
            st.markdown(
                f"Ultimo esito registrato: {badge_html(res.overall_status)}",
                unsafe_allow_html=True,
            )

    man_summary  = st.text_area(
        "Sintesi della verifica",
        placeholder="Descrivi le evidenze esaminate e le conclusioni raggiunte…",
        height=120, key=f"man_summary_{control.id}",
    )
    man_evidence = st.text_area(
        "Evidenze / Note (opzionale)",
        placeholder="Documenti esaminati, riferimenti, osservazioni specifiche…",
        height=80, key=f"man_evidence_{control.id}",
    )
    man_issues   = st.text_area(
        "Issue / Anomalie riscontrate (opzionale)",
        placeholder="Descrivi eventuali anomalie o aree di miglioramento…",
        height=80, key=f"man_issues_{control.id}",
    )

    if st.button(
        "💾 Registra esito manuale",
        type="primary",
        key=f"man_save_{control.id}",
        disabled=not can_edit(),
    ):
        if not man_summary.strip():
            st.error("La sintesi della verifica è obbligatoria.")
        else:
            cp_results = [
                CheckPointResult(
                    check_point=cp,
                    status=man_status,
                    evidence=man_evidence.strip(),
                    issue=man_issues.strip() if man_status != "conforme" else "",
                    mitigation="",
                )
                for cp in control.check_points
            ] if control.check_points else [
                CheckPointResult(
                    check_point="Verifica manuale",
                    status=man_status,
                    evidence=man_evidence.strip(),
                    issue=man_issues.strip(),
                    mitigation="",
                )
            ]
            mitigation = (
                [man_issues.strip()]
                if man_issues.strip() and man_status != "conforme"
                else []
            )
            manual_result = VerificationResult(
                control_id=control.id,
                control_title=control.title,
                overall_status=man_status,
                summary=man_summary.strip(),
                check_points=cp_results,
                mitigation_plan=mitigation,
            )
            ver_id = save_verification(
                engagement_id, control.id, manual_result,
                user=get_current_username(),
            )
            manual_result._ver_id = ver_id
            st.session_state[result_key] = manual_result
            st.success("Esito registrato.", icon="✅")
            st.rerun()

else:
    # ── VERIFICA AI ───────────────────────────────────────────────────────────
    st.markdown("#### Carica i documenti e avvia la verifica AI")

    uploaded_files = st.file_uploader(
        "Carica uno o più documenti",
        type=["pdf", "docx", "xlsx", "xlsm", "csv", "txt", "md"],
        accept_multiple_files=True,
        key=f"uploader_{control.id}",
    )

    upload_key = f"uploaded_{control.id}"
    if uploaded_files:
        tmp_dir = Path(tempfile.gettempdir()) / f"audit_{control.id}"
        tmp_dir.mkdir(exist_ok=True)
        saved = []
        for uf in uploaded_files:
            dest = tmp_dir / uf.name
            dest.write_bytes(uf.getbuffer())
            saved.append((uf.name, dest))
        st.session_state[upload_key] = saved
        st.info(f"{len(saved)} file pronti per la verifica.")

    col_run, col_status = st.columns([2, 4])
    with col_run:
        can_run = bool(st.session_state.get(upload_key))
        run = st.button(
            "Esegui verifica AI",
            type="primary",
            disabled=not can_run,
            use_container_width=True,
        )
    with col_status:
        if result_key in st.session_state:
            res = st.session_state[result_key]
            st.markdown(
                f"Ultima verifica: {badge_html(res.overall_status)}",
                unsafe_allow_html=True,
            )

    if run and not can_edit():
        st.error("Solo Auditor e Head IA possono eseguire verifiche.", icon="🔒")
        run = False

    if run:
        files_info = st.session_state[upload_key]
        documents  = []
        with st.spinner("Estrazione testo…"):
            for name, path in files_info:
                try:
                    documents.append((name, load_document(path)))
                except Exception as e:
                    st.error(f"Errore lettura {name}: {e}")

        if documents:
            with st.spinner("Verifica AI in corso…"):
                try:
                    verifier = LLMVerifier()
                    paths    = [p for _, p in files_info]
                    result   = verifier.verify(control, documents, file_paths=paths)
                    ver_id   = save_verification(
                        engagement_id, control.id, result,
                        user=get_current_username(),
                    )
                    result._ver_id = ver_id
                    st.session_state[result_key] = result
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore LLM: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# ESITO
# ══════════════════════════════════════════════════════════════════════════════

result = st.session_state.get(result_key)

# Ricostruisci da DB se non in session state
if result is None and prev:
    result = VerificationResult(
        control_id=control.id,
        control_title=control.title,
        overall_status=prev["overall_status"],
        summary=prev["summary"],
        check_points=[
            CheckPointResult(
                check_point=cp["check_point"],
                status=cp["status"],
                evidence=cp["evidence"],
                issue=cp["issue"],
                mitigation=cp["mitigation"],
            )
            for cp in prev["check_points"]
        ],
        mitigation_plan=prev["mitigation_plan"],
    )
    result._ver_id = prev["id"]

if result:
    st.markdown("---")
    st.markdown("#### Esito della verifica")

    nc = sum(1 for cp in result.check_points if cp.status == "non_conforme")
    st.markdown(
        f"""
        <div class="metric-grid">
          <div class="metric-card">
            <div class="metric-value">{badge_html(result.overall_status)}</div>
            <div class="metric-label">Esito complessivo</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" style="color:#cf1322">{nc} / {len(result.check_points)}</div>
            <div class="metric-label">Check point non conformi</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{len(result.mitigation_plan)}</div>
            <div class="metric-label">Azioni di mitigazione</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(result.summary)

    st.markdown("**Dettaglio check points:**")
    for i, cp in enumerate(result.check_points, 1):
        with st.expander(f"{i}. {cp.check_point[:100]}"):
            st.markdown(badge_html(cp.status), unsafe_allow_html=True)
            st.markdown(f"**Evidenza:** {cp.evidence or '—'}")
            if cp.issue:
                st.markdown(f"**Issue:** {cp.issue}")
            if cp.mitigation:
                st.markdown(f"**Mitigazione proposta:** {cp.mitigation}")

    if result.mitigation_plan:
        st.markdown("**Piano di mitigazione consolidato:**")
        for i, m in enumerate(result.mitigation_plan, 1):
            st.markdown(f"{i}. {m}")

    # ── Genera Finding ────────────────────────────────────────────────────────

    non_conformi = [cp for cp in result.check_points if cp.status == "non_conforme"]
    if non_conformi:
        st.markdown("---")
        st.markdown("#### Genera Finding")
        st.markdown(
            f"Trovati **{len(non_conformi)} check point non conformi**. "
            "Puoi generare un finding consolidato per questo controllo."
        )

        sev_col, _ = st.columns([2, 4])
        with sev_col:
            severity = st.selectbox(
                "Severità finding",
                options=["alto", "medio", "basso"],
                index=0 if nc >= 2 else 1,
                key=f"sev_{control.id}",
            )

        finding_title = f"[{control.id}] Non conformità — {control.title}"
        finding_desc_lines = [
            f"Verifica del {getattr(result, '_ver_id', '—')} su Engagement #{engagement_id}.",
            "",
            "Check point non conformi:",
        ]
        for cp in non_conformi:
            finding_desc_lines.append(f"- {cp.check_point}: {cp.issue}")
        finding_desc = "\n".join(finding_desc_lines)

        finding_key = f"finding_created_{engagement_id}_{control.id}"
        if finding_key not in st.session_state:
            if st.button(
                "⚠️ Apri Finding", type="primary", key=f"open_finding_{control.id}"
            ):
                ver_id = getattr(result, "_ver_id", None)
                fid = create_finding(
                    verification_id=ver_id,
                    control_id=control.id,
                    engagement_id=engagement_id,
                    title=finding_title,
                    description=finding_desc,
                    severity=severity,
                )
                st.session_state[finding_key] = fid
                st.success(
                    f"Finding #{fid} creato con severità **{severity}**. "
                    "Vai a **Findings & Remediation** per gestirlo.",
                    icon="✅",
                )
                st.rerun()
        else:
            fid = st.session_state[finding_key]
            st.success(
                f"Finding #{fid} già creato per questo controllo. "
                "Vai a **Findings & Remediation** per gestirlo.",
                icon="✅",
            )

    elif result.overall_status == "conforme":
        st.success(
            "Tutti i check point sono conformi. Nessun finding da aprire.", icon="✅"
        )
