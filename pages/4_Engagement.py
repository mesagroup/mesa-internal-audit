"""
Engagement — Test dei controlli con verifica AI.
Refactoring del POC originale: controlli letti dal DB, esiti persistiti.
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

from ui.common import inject_css, render_sidebar_nav, badge_html, pending_badge
from db.repositories import (
    get_all_controls, get_active_engagements, create_engagement,
    save_verification, create_finding, get_verifications_for_engagement,
)
from core.document_loader import load_document
from core.llm_verifier import LLMVerifier

inject_css()
render_sidebar_nav()

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
    st.warning("API key OpenAI non configurata. Imposta OPENAI_API_KEY nel file .env.", icon="⚠️")

# ── Carica controlli dal DB ───────────────────────────────────────────────────

controls = get_all_controls()
if not controls:
    st.error(
        "Nessun controllo in Anagrafica. "
        "Vai alla pagina **Anagrafica** e aggiungi almeno un controllo."
    )
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SELEZIONE ENGAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("#### 1. Seleziona o crea un Engagement")

engagements = get_active_engagements()
eng_options = {e["name"]: e["id"] for e in engagements}

col_sel, col_new = st.columns([3, 2])

with col_sel:
    if eng_options:
        selected_eng_name = st.selectbox(
            "Engagement attivi",
            options=list(eng_options.keys()),
            key="eng_select",
        )
        engagement_id = eng_options[selected_eng_name]
    else:
        st.info("Nessun engagement attivo. Creane uno.")
        engagement_id = None

with col_new:
    with st.expander("➕ Nuovo Engagement"):
        eng_name = st.text_input("Nome (es. Audit P2P 2026 Q2)", key="eng_name_input")
        eng_desc = st.text_input("Note (opzionale)", key="eng_desc_input")
        if st.button("Crea", type="primary", key="create_eng"):
            if not eng_name.strip():
                st.error("Il nome è obbligatorio.")
            else:
                new_id = create_engagement(eng_name.strip(), eng_desc.strip())
                st.success(f"Engagement '{eng_name}' creato.", icon="✓")
                st.rerun()

if engagement_id is None:
    st.stop()

st.markdown("---")

# ── Stato controlli nell'engagement corrente ──────────────────────────────────

verifications = get_verifications_for_engagement(engagement_id)
verified_controls = {v["control_id"]: v for v in verifications}

# Sidebar: progress
with st.sidebar:
    st.markdown('<p class="nav-section-label">Progresso engagement</p>', unsafe_allow_html=True)
    for ctrl in controls:
        v = verified_controls.get(ctrl.id)
        b = badge_html(v["overall_status"]) if v else pending_badge()
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:4px 16px;font-size:12px;">'
            f'<span style="font-weight:600;color:#7BAF2E;margin-right:4px;">{ctrl.id}</span>'
            f'{ctrl.title[:24]}…{b}</div>',
            unsafe_allow_html=True,
        )
    done = len(verified_controls)
    total = len(controls)
    st.progress(done / total if total else 0)
    st.caption(f"Progresso: {done} / {total} controlli")

# ══════════════════════════════════════════════════════════════════════════════
# SELEZIONE CONTROLLO
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("#### 2. Seleziona il Controllo da testare")

ctrl_options = [f"{c.id} — {c.title}" for c in controls]
ctrl_idx = st.selectbox("Controllo", options=range(len(ctrl_options)),
                         format_func=lambda i: ctrl_options[i], key="ctrl_select")
control = controls[ctrl_idx]

with st.expander("Descrizione e check points", expanded=False):
    st.markdown(control.description)
    st.markdown("**Check points:**")
    for i, cp in enumerate(control.check_points, 1):
        st.markdown(f"{i}. {cp}")
    st.markdown("**Documenti attesi:**")
    for d in control.expected_documents:
        st.markdown(f"- {d}")

st.markdown("---")

# ── Esito precedente (se già eseguito) ───────────────────────────────────────

prev = verified_controls.get(control.id)
if prev:
    st.info(
        f"Verifica già eseguita il {prev['verified_at'][:16]}. "
        "Puoi ri-eseguirla caricando nuovi documenti — il nuovo esito sovrascriverà il precedente nel DB.",
        icon="ℹ️",
    )

# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD E VERIFICA
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("#### 3. Carica i documenti e avvia la verifica")

uploaded_files = st.file_uploader(
    "Carica uno o più documenti",
    type=["pdf", "docx", "xlsx", "xlsm", "csv", "txt", "md"],
    accept_multiple_files=True,
    key=f"uploader_{control.id}",
)

# Memorizza path in session state per il controllo corrente
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

result_key = f"result_{engagement_id}_{control.id}"

with col_status:
    if result_key in st.session_state:
        res = st.session_state[result_key]
        st.markdown(
            f"Ultima verifica: {badge_html(res.overall_status)}",
            unsafe_allow_html=True,
        )

if run:
    files_info = st.session_state[upload_key]
    documents = []
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
                paths = [p for _, p in files_info]
                result = verifier.verify(control, documents, file_paths=paths)
                # Persisti nel DB
                ver_id = save_verification(engagement_id, control.id, result)
                result._ver_id = ver_id  # attach for finding creation
                st.session_state[result_key] = result
                st.rerun()
            except Exception as e:
                st.error(f"Errore LLM: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# ESITO
# ══════════════════════════════════════════════════════════════════════════════

result = st.session_state.get(result_key)

# Se non in session state ma già nel DB, ricostruisci dalla verifica precedente
if result is None and prev:
    from core.llm_verifier import VerificationResult, CheckPointResult
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

    # ── Apri Finding ──────────────────────────────────────────────────────────

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
            f"Verifica AI del {getattr(result, '_ver_id', '—')} su Engagement #{engagement_id}.",
            "",
            "Check point non conformi:",
        ]
        for cp in non_conformi:
            finding_desc_lines.append(f"- {cp.check_point}: {cp.issue}")
        finding_desc = "\n".join(finding_desc_lines)

        finding_key = f"finding_created_{engagement_id}_{control.id}"
        if finding_key not in st.session_state:
            if st.button("⚠️ Apri Finding", type="primary", key=f"open_finding_{control.id}"):
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
                    icon="✓",
                )
                st.rerun()
        else:
            fid = st.session_state[finding_key]
            st.success(
                f"Finding #{fid} già creato per questo controllo. "
                "Vai a **Findings & Remediation** per gestirlo.",
                icon="✓",
            )
    elif result.overall_status == "conforme":
        st.success(
            "Tutti i check point sono conformi. Nessun finding da aprire.", icon="✓"
        )
