"""
Internal Audit POC — Streamlit UI (PROCOMP design system)
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
    page_title="Internal Audit — PROCOMP",
    page_icon="🔎",
    layout="wide",
)

# ── Design tokens ────────────────────────────────────────────────────────────

PROCOMP_CSS = """
<style>
/* ── Tokens ── */
:root {
  --primary:        #2C3E7A;
  --primary-bg:     #eef1f9;
  --primary-hover:  #f5f5f5;
  --border:         #f0f0f0;
  --text:           rgba(0,0,0,.88);
  --text-secondary: rgba(0,0,0,.45);
  --radius:         6px;
  --radius-lg:      8px;
}

/* ── Global ── */
html, body, [class*="css"] {
  font-family: 'Helvetica Neue', Arial, sans-serif !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer { visibility: hidden; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }

/* ── Sidebar shell ── */
[data-testid="stSidebar"] {
  background: #ffffff !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding: 0 0 80px 0 !important;   /* room for user footer */
}

/* ── Sidebar sections ── */
.procomp-logo-area {
  height: 44px;
  display: flex;
  align-items: center;
  padding: 0 14px;
  border-bottom: 1px solid var(--border);
}

.nav-section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: .06em;
  padding: 16px 24px 4px;
  margin: 0;
}

/* ── Radio → nav items ── */
[data-testid="stSidebar"] .stRadio { padding: 0 4px; }
[data-testid="stSidebar"] .stRadio > label { display: none; }
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }

[data-testid="stSidebar"] .stRadio div[data-testid="stMarkdownContainer"] p {
  margin: 0;
  font-size: 14px;
}

/* label wrapper */
[data-testid="stSidebar"] .stRadio label {
  display: flex !important;
  align-items: center !important;
  min-height: 40px !important;
  padding: 0 16px 0 20px !important;
  border-radius: var(--radius) !important;
  cursor: pointer !important;
  transition: background .15s !important;
  color: var(--text) !important;
  font-size: 14px !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: var(--primary-hover) !important;
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: var(--primary-bg) !important;
  color: var(--primary) !important;
  font-weight: 600 !important;
  position: relative;
}
[data-testid="stSidebar"] .stRadio label:has(input:checked)::after {
  content: '';
  position: absolute;
  right: 0; top: 6px; bottom: 6px;
  width: 3px;
  background: var(--primary);
  border-radius: 3px 0 0 3px;
}
/* hide radio circle */
[data-testid="stSidebar"] .stRadio input[type="radio"] {
  display: none !important;
}

/* ── Sidebar divider ── */
[data-testid="stSidebar"] hr {
  border-color: var(--border) !important;
  margin: 8px 0 !important;
}

/* ── Sidebar status list ── */
.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 20px;
  font-size: 13px;
  color: var(--text);
}
.status-row span.ctrl-id {
  font-weight: 600;
  color: var(--primary);
  margin-right: 4px;
}

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div {
  background: var(--primary) !important;
}

/* ── User footer ── */
.user-footer {
  position: fixed;
  bottom: 0;
  width: 240px;
  background: #fff;
  border-top: 1px solid var(--border);
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 10;
}
.user-avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  font-size: 11px; font-weight: 500;
  display: inline-flex;
  align-items: center; justify-content: center;
  flex-shrink: 0;
}
.user-name-text {
  font-size: 13px;
  color: #595959;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Main content ── */
.main .block-container {
  padding: 28px 36px !important;
  max-width: 100% !important;
}

/* ── Page header ── */
.page-header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 16px;
  margin-bottom: 24px;
}
.page-header h2 {
  margin: 0 0 2px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
}
.page-header .area-chip {
  display: inline-block;
  background: var(--primary-bg);
  color: var(--primary);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 500;
}

/* ── Cards ── */
.audit-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  margin-bottom: 16px;
}
.audit-card h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

/* ── Metric cards ── */
.metric-grid {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}
.metric-card {
  flex: 1;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  text-align: center;
}
.metric-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--primary);
  line-height: 1.2;
}
.metric-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* ── Status badges ── */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}
.badge-conforme        { background:#f6ffed; color:#389e0d; border:1px solid #b7eb8f; }
.badge-non_conforme    { background:#fff2f0; color:#cf1322; border:1px solid #ffa39e; }
.badge-parziale        { background:#fffbe6; color:#d48806; border:1px solid #ffe58f; }
.badge-non_verificabile{ background:#fafafa; color:#8c8c8c; border:1px solid #d9d9d9; }
.badge-pending         { background:#fafafa; color:#8c8c8c; border:1px solid #d9d9d9; }

/* ── Check-point expanders ── */
[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  margin-bottom: 6px !important;
}
[data-testid="stExpander"] summary {
  font-size: 13px !important;
}

/* ── Buttons ── */
.stButton > button {
  border-radius: var(--radius) !important;
  font-size: 14px !important;
}
.stButton > button[kind="primary"] {
  background: var(--primary) !important;
  border-color: var(--primary) !important;
}
.stButton > button[kind="primary"]:hover {
  background: #1e2d5f !important;
  border-color: #1e2d5f !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  border-radius: var(--radius-lg) !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: var(--radius) !important; }
</style>
"""

st.markdown(PROCOMP_CSS, unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "results" not in st.session_state:
    st.session_state.results: dict[str, VerificationResult] = {}
if "uploaded" not in st.session_state:
    st.session_state.uploaded: dict[str, list] = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

STATUS_META = {
    "conforme":         ("●", "Conforme"),
    "non_conforme":     ("●", "Non conforme"),
    "parziale":         ("●", "Parziale"),
    "non_verificabile": ("●", "Non verif."),
}


def badge_html(status: str) -> str:
    dot, label = STATUS_META.get(status, ("●", status))
    return f'<span class="badge badge-{status}">{dot} {label}</span>'


def pending_badge() -> str:
    return '<span class="badge badge-pending">○ Da eseguire</span>'


# ── Sidebar ───────────────────────────────────────────────────────────────────

# Logo
st.sidebar.markdown("""
<div class="procomp-logo-area">
  <svg viewBox="0 0 180 44" height="22" aria-label="PROCOMP">
    <text x="4" y="34" font-family="'Helvetica Neue',Arial,sans-serif"
          font-size="36" font-weight="200" fill="#2C3E7A">P</text>
    <text x="24" y="34" font-family="'Helvetica Neue',Arial,sans-serif"
          font-size="36" font-weight="200" fill="#BDBDBD">ROCOMP</text>
    <rect x="162" y="10" width="8" height="8" rx="1" fill="#2C3E7A"/>
  </svg>
</div>
""", unsafe_allow_html=True)

# API key warning
if not os.environ.get("OPENAI_API_KEY"):
    st.sidebar.warning("API key non configurata", icon="⚠️")

# Nav — controlli
st.sidebar.markdown('<p class="nav-section-label">Controlli</p>', unsafe_allow_html=True)

selected_id = st.sidebar.radio(
    "controllo",
    options=[c.id for c in CONTROLS_TREE],
    format_func=lambda cid: f"{cid} — {next(c.title for c in CONTROLS_TREE if c.id == cid)}",
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

# Stato esecuzione
st.sidebar.markdown('<p class="nav-section-label">Stato esecuzione</p>', unsafe_allow_html=True)

for c in CONTROLS_TREE:
    res = st.session_state.results.get(c.id)
    b = badge_html(res.overall_status) if res else pending_badge()
    st.sidebar.markdown(
        f'<div class="status-row"><span><span class="ctrl-id">{c.id}</span>{c.title[:28]}…</span>{b}</div>',
        unsafe_allow_html=True,
    )

# Progresso
st.sidebar.markdown("---")
executed = len(st.session_state.results)
total = len(CONTROLS_TREE)
st.sidebar.progress(executed / total if total else 0)
st.sidebar.caption(f"Progresso: {executed} / {total} controlli eseguiti")

st.sidebar.markdown("---")

# Azioni
if executed > 0:
    if st.sidebar.button("Genera report PDF", type="primary", use_container_width=True):
        results_list = [st.session_state.results[c.id] for c in CONTROLS_TREE if c.id in st.session_state.results]
        out_path = Path("reports") / f"audit_report_{os.getpid()}.pdf"
        out_path.parent.mkdir(exist_ok=True)
        generate_pdf_report(results_list, out_path)
        with open(out_path, "rb") as f:
            st.sidebar.download_button(
                "Scarica PDF",
                f.read(),
                file_name="audit_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

if st.sidebar.button("Reset", use_container_width=True):
    st.session_state.results = {}
    st.session_state.uploaded = {}
    st.rerun()

# User footer
st.sidebar.markdown("""
<div class="user-footer">
  <div class="user-avatar">AU</div>
  <span class="user-name-text">Auditor</span>
</div>
""", unsafe_allow_html=True)

# ── Main content ──────────────────────────────────────────────────────────────

control: Control = next(c for c in CONTROLS_TREE if c.id == selected_id)

# Page header
st.markdown(f"""
<div class="page-header">
  <h2>Controllo {control.id} — {control.title}</h2>
  <span class="area-chip">{control.area}</span>
</div>
""", unsafe_allow_html=True)

# Descrizione e check points
with st.expander("Descrizione e check points", expanded=True):
    st.markdown(control.description)
    st.markdown("**Check points da verificare:**")
    for i, cp in enumerate(control.check_points, 1):
        st.markdown(f"{i}. {cp}")
    st.markdown("**Documenti attesi:**")
    for d in control.expected_documents:
        st.markdown(f"- {d}")

st.markdown("---")

# Upload
st.markdown("#### Documenti da verificare")
uploaded_files = st.file_uploader(
    "Carica uno o più documenti",
    type=["pdf", "docx", "xlsx", "xlsm", "csv", "txt", "md"],
    accept_multiple_files=True,
    key=f"uploader_{control.id}",
)

if uploaded_files:
    tmp_dir = Path(tempfile.gettempdir()) / f"audit_{control.id}"
    tmp_dir.mkdir(exist_ok=True)
    saved = []
    for uf in uploaded_files:
        dest = tmp_dir / uf.name
        dest.write_bytes(uf.getbuffer())
        saved.append((uf.name, dest))
    st.session_state.uploaded[control.id] = saved
    st.info(f"{len(saved)} file pronti per la verifica.")

# Esegui verifica
col_btn, col_status = st.columns([1, 3])
with col_btn:
    run = st.button(
        "Esegui verifica",
        type="primary",
        disabled=not st.session_state.uploaded.get(control.id),
        use_container_width=True,
    )
with col_status:
    if control.id in st.session_state.results:
        res_preview = st.session_state.results[control.id]
        st.markdown(
            f"Verifica già eseguita: {badge_html(res_preview.overall_status)}",
            unsafe_allow_html=True,
        )

if run:
    files_info = st.session_state.uploaded[control.id]
    documents = []
    with st.spinner("Estrazione testo dai documenti…"):
        for name, path in files_info:
            try:
                text = load_document(path)
                documents.append((name, text))
            except Exception as e:
                st.error(f"Errore lettura {name}: {e}")

    if documents:
        with st.spinner("Verifica in corso con il modello AI…"):
            try:
                verifier = LLMVerifier()
                paths = [path for _, path in files_info]
                result = verifier.verify(control, documents, file_paths=paths)
                st.session_state.results[control.id] = result
                st.rerun()
            except Exception as e:
                st.error(f"Errore chiamata LLM: {e}")

# ── Esito ─────────────────────────────────────────────────────────────────────

result: VerificationResult | None = st.session_state.results.get(control.id)
if result:
    st.markdown("---")
    st.markdown("#### Esito della verifica")

    nc = sum(1 for cp in result.check_points if cp.status == "non_conforme")

    # Metric cards
    st.markdown(f"""
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
    """, unsafe_allow_html=True)

    st.info(result.summary)

    st.markdown("**Dettaglio check points:**")
    for i, cp in enumerate(result.check_points, 1):
        label = f"{i}. {cp.check_point[:100]}"
        with st.expander(label):
            st.markdown(badge_html(cp.status), unsafe_allow_html=True)
            st.markdown(f"**Evidenza:** {cp.evidence or '—'}")
            if cp.issue:
                st.markdown(f"**Issue:** {cp.issue}")
            if cp.mitigation:
                st.markdown(f"**Mitigazione:** {cp.mitigation}")

    if result.mitigation_plan:
        st.markdown("**Piano di mitigazione consolidato:**")
        for i, m in enumerate(result.mitigation_plan, 1):
            st.markdown(f"{i}. {m}")
