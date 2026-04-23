"""
POC di Internal Audit — Streamlit UI.

Flusso:
1. Sidebar: albero dei controlli (3 controlli definiti in core/controls_tree.py)
2. Per ogni controllo:
   - sezione descrittiva con check points
   - upload dei documenti
   - bottone "Esegui verifica" -> chiama ChatGPT
   - visualizzazione esito (status, check point dettagliato, mitigazioni)
3. Quando tutti i controlli sono stati eseguiti, bottone per generare PDF finale.

Requisiti:
- OPENAI_API_KEY in .env o variabile d'ambiente
- pip install -r requirements.txt
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from core.controls_tree import CONTROLS_TREE, Control
from core.document_loader import load_document
from core.llm_verifier import LLMVerifier, VerificationResult
from core.report_generator import generate_pdf_report

load_dotenv()

st.set_page_config(
    page_title="Internal Audit POC",
    page_icon="🔎",
    layout="wide",
)

# ---------- Session state ----------
if "results" not in st.session_state:
    st.session_state.results = {}  # {control_id: VerificationResult}
if "uploaded" not in st.session_state:
    st.session_state.uploaded = {}  # {control_id: [(filename, path)]}


# ---------- Utility ----------
STATUS_BADGES = {
    "conforme": ("🟢", "Conforme"),
    "non_conforme": ("🔴", "Non conforme"),
    "parziale": ("🟡", "Parziale"),
    "non_verificabile": ("⚪", "Non verificabile"),
}


def badge(status: str) -> str:
    emoji, label = STATUS_BADGES.get(status, ("⚪", status))
    return f"{emoji} {label}"


# ---------- Sidebar: albero ----------
st.sidebar.title("🔎 Audit POC")
st.sidebar.markdown("### Albero dei Controlli")

if not os.environ.get("OPENAI_API_KEY"):
    st.sidebar.error("⚠️ OPENAI_API_KEY non impostata")
else:
    st.sidebar.success("✅ API key OK")

st.sidebar.markdown("---")

selected_id = st.sidebar.radio(
    "Seleziona un controllo",
    options=[c.id for c in CONTROLS_TREE],
    format_func=lambda cid: f"{cid} — {next(c.title for c in CONTROLS_TREE if c.id == cid)}",
)

# Stato di esecuzione per ogni controllo
st.sidebar.markdown("### Stato esecuzione")
for c in CONTROLS_TREE:
    res = st.session_state.results.get(c.id)
    if res:
        st.sidebar.markdown(f"- **{c.id}**: {badge(res.overall_status)}")
    else:
        st.sidebar.markdown(f"- **{c.id}**: ⏳ da eseguire")

st.sidebar.markdown("---")

# Bottone report finale
executed_count = len(st.session_state.results)
total_count = len(CONTROLS_TREE)
st.sidebar.markdown(f"**Progresso:** {executed_count}/{total_count}")

if executed_count > 0:
    if st.sidebar.button("📄 Genera report PDF finale", type="primary", use_container_width=True):
        results_list = [st.session_state.results[c.id] for c in CONTROLS_TREE if c.id in st.session_state.results]
        out_path = Path("reports") / f"audit_report_{os.getpid()}.pdf"
        generate_pdf_report(results_list, out_path)
        with open(out_path, "rb") as f:
            st.sidebar.download_button(
                "⬇️ Scarica PDF",
                f.read(),
                file_name="audit_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

if st.sidebar.button("🗑️ Reset POC", use_container_width=True):
    st.session_state.results = {}
    st.session_state.uploaded = {}
    st.rerun()


# ---------- Main: dettaglio controllo ----------
control: Control = next(c for c in CONTROLS_TREE if c.id == selected_id)

st.title(f"Controllo {control.id}")
st.subheader(control.title)
st.caption(f"Area: **{control.area}**")

with st.expander("📖 Descrizione e check points", expanded=True):
    st.markdown(control.description)
    st.markdown("**Check points da verificare:**")
    for i, cp in enumerate(control.check_points, start=1):
        st.markdown(f"{i}. {cp}")
    st.markdown("**Documenti attesi:**")
    for d in control.expected_documents:
        st.markdown(f"- {d}")

st.markdown("---")

# ---------- Upload documenti ----------
st.markdown("### 📎 Documenti da verificare")
uploaded_files = st.file_uploader(
    "Carica uno o più documenti",
    type=["pdf", "docx", "xlsx", "xlsm", "csv", "txt", "md"],
    accept_multiple_files=True,
    key=f"uploader_{control.id}",
)

if uploaded_files:
    # salviamo su tempdir così il loader può leggerli
    tmp_dir = Path(tempfile.gettempdir()) / f"audit_{control.id}"
    tmp_dir.mkdir(exist_ok=True)
    saved = []
    for uf in uploaded_files:
        dest = tmp_dir / uf.name
        dest.write_bytes(uf.getbuffer())
        saved.append((uf.name, dest))
    st.session_state.uploaded[control.id] = saved
    st.info(f"{len(saved)} file pronti per la verifica")

# ---------- Esegui verifica ----------
col1, col2 = st.columns([1, 3])
with col1:
    run = st.button(
        "▶️ Esegui verifica",
        type="primary",
        disabled=not st.session_state.uploaded.get(control.id),
        use_container_width=True,
    )
with col2:
    if control.id in st.session_state.results:
        st.success(f"Verifica già eseguita: {badge(st.session_state.results[control.id].overall_status)}")

if run:
    files_info = st.session_state.uploaded[control.id]
    documents = []
    with st.spinner("Estrazione testo dai documenti..."):
        for name, path in files_info:
            try:
                text = load_document(path)
                documents.append((name, text))
            except Exception as e:
                st.error(f"Errore lettura {name}: {e}")

    if documents:
        with st.spinner("Verifica in corso con ChatGPT..."):
            try:
                verifier = LLMVerifier()
                paths = [path for _, path in files_info]
                result = verifier.verify(control, documents, file_paths=paths)
                st.session_state.results[control.id] = result
                st.rerun()
            except Exception as e:
                st.error(f"Errore chiamata LLM: {e}")

# ---------- Visualizzazione esito ----------
result: VerificationResult | None = st.session_state.results.get(control.id)
if result:
    st.markdown("---")
    st.markdown("### 📊 Esito della verifica")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Esito complessivo", badge(result.overall_status))
    with col2:
        nc = sum(1 for cp in result.check_points if cp.status == "non_conforme")
        st.metric("Check point non conformi", f"{nc} / {len(result.check_points)}")
    with col3:
        st.metric("Azioni di mitigazione", len(result.mitigation_plan))

    st.markdown("**Sintesi:**")
    st.info(result.summary)

    st.markdown("**Dettaglio check points:**")
    for i, cp in enumerate(result.check_points, start=1):
        with st.expander(f"{badge(cp.status)} — {i}. {cp.check_point[:100]}"):
            st.markdown(f"**Evidenza:** {cp.evidence or '—'}")
            if cp.issue:
                st.markdown(f"**Issue:** {cp.issue}")
            if cp.mitigation:
                st.markdown(f"**Mitigazione:** {cp.mitigation}")

    if result.mitigation_plan:
        st.markdown("**Piano di mitigazione consolidato:**")
        for i, m in enumerate(result.mitigation_plan, start=1):
            st.markdown(f"{i}. {m}")
