"""
Internal Audit POC — Streamlit UI (MESA ERM design system v1.0)
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
    page_title="Internal Audit — MESA ERM",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── MESA ERM Design System CSS ────────────────────────────────────────────────

MESA_CSS = """
<style>
/* ── Design Tokens ── */
:root {
  --primary:          #7BAF2E;
  --primary-logo:     #95C11F;
  --primary-bg:       #f6ffed;
  --primary-hover:    #6a9a26;
  --bg-hover:         #f5f5f5;
  --bg-page:          #f5f5f5;
  --bg-submenu:       #fafafa;
  --border:           #f0f0f0;
  --text:             rgba(0,0,0,.88);
  --text-secondary:   rgba(0,0,0,.45);
  --text-user:        #595959;
  --text-toggle:      #8c8c8c;
  --text-logo-esa:    #BDBDBD;
  --radius:           6px;
  --radius-lg:        8px;
  --menu-item-h:      40px;
  --font:             -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                      'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
}

/* ── Global ── */
html, body, [class*="css"] {
  font-family: var(--font) !important;
  font-size: 14px !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* ── Hide sidebar collapse button — sidebar always stays open ── */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCloseButton"],
button[aria-label="Close sidebar"],
button[aria-label="Collapse sidebar"],
button[title="Close sidebar"] {
  display: none !important;
}

/* ── Page background ── */
.stApp,
[data-testid="stAppViewContainer"] {
  background: var(--bg-page) !important;
}

/* ── Sidebar shell ── */
[data-testid="stSidebar"] {
  background: #ffffff !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding: 0 !important;
}

/* ── Scrollbar (6px — spec §9) ── */
*::-webkit-scrollbar { width: 6px; height: 6px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb { background: rgba(0,0,0,.15); border-radius: 3px; }
*::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,.3); }
* { scrollbar-width: thin; scrollbar-color: rgba(0,0,0,.15) transparent; }

/* ═══════════════════════════════════════
   ZONA A — Logo
════════════════════════════════════════ */
.mesa-logo-area {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
}

/* ═══════════════════════════════════════
   ZONA B — Quick Nav
════════════════════════════════════════ */
.sidebar-quicknav {
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  padding: 4px 0;
}
.quicknav-item {
  display: flex;
  align-items: center;
  height: var(--menu-item-h);
  padding: 0 16px 0 24px;
  gap: 10px;
  cursor: pointer;
  color: var(--text);
  font-size: 14px;
  border-radius: var(--radius);
  margin: 0 4px;
  transition: background .15s ease;
  text-decoration: none;
  user-select: none;
}
.quicknav-item:hover { background: var(--bg-hover); }
.quicknav-item svg { flex-shrink: 0; color: var(--text-secondary); }
.quicknav-item .qnav-label { flex: 1; }
.quicknav-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: #ff4d4f;
  color: #fff;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}

/* ═══════════════════════════════════════
   ZONA C — Radio → nav items
════════════════════════════════════════ */
[data-testid="stSidebar"] .stRadio { padding: 0 4px; }

/* hide widget label only — never target option labels */
[data-testid="stSidebar"] .stRadio > label,
[data-testid="stSidebar"] .stRadio [data-testid="stWidgetLabel"] {
  display: none !important;
}

[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }

[data-testid="stSidebar"] .stRadio div[data-testid="stMarkdownContainer"] p {
  margin: 0;
  font-size: 14px;
}

/* option label */
[data-testid="stSidebar"] .stRadio label {
  display: flex !important;
  align-items: center !important;
  min-height: var(--menu-item-h) !important;
  padding: 0 16px 0 24px !important;
  border-radius: var(--radius) !important;
  cursor: pointer !important;
  transition: background .15s !important;
  color: var(--text) !important;
  font-size: 14px !important;
  font-weight: 400 !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: var(--bg-hover) !important;
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
  right: 0; top: 4px; bottom: 4px;
  width: 3px;
  background: var(--primary);
  border-radius: 3px 0 0 3px;
}

/* Shrink native radio input to nothing */
[data-testid="stSidebar"] .stRadio input[type="radio"] {
  position: absolute !important;
  opacity: 0 !important;
  width: 1px !important;
  height: 1px !important;
  margin: 0 !important;
  pointer-events: none !important;
}
/* Force all label content visible */
[data-testid="stSidebar"] .stRadio label * {
  visibility: visible !important;
  opacity: 1 !important;
}
/* Force the markdown text color */
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
  display: block !important;
  color: inherit !important;
  font-size: 14px !important;
  margin: 0 !important;
}

/* nav section labels */
.nav-section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: .06em;
  padding: 16px 24px 4px;
  margin: 0;
}

/* sidebar divider */
[data-testid="stSidebar"] hr {
  border-color: var(--border) !important;
  margin: 6px 0 !important;
}

/* ── Status rows ── */
.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 16px;
  font-size: 12px;
  color: var(--text);
}
.status-row .ctrl-id {
  font-weight: 600;
  color: var(--primary);
  margin-right: 4px;
}

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div {
  background: var(--primary) !important;
}

/* ═══════════════════════════════════════
   ZONA D — User footer
════════════════════════════════════════ */
.user-footer {
  border-top: 1px solid var(--border);
  padding: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  cursor: pointer;
  border-radius: var(--radius);
  transition: background .15s;
}
.user-footer:hover { background: var(--bg-hover); }
.user-avatar {
  width: 24px; height: 24px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  font-size: 11px; font-weight: 500;
  display: inline-flex;
  align-items: center; justify-content: center;
  flex-shrink: 0;
}
.user-name-text {
  font-size: 14px;
  color: var(--text-user);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ═══════════════════════════════════════
   CONTENT AREA — white card (spec §4)
════════════════════════════════════════ */
.main .block-container {
  background: #ffffff !important;
  border-radius: var(--radius-lg) !important;
  margin: 12px !important;
  padding: 16px 24px !important;
  max-width: 100% !important;
}

/* ── Page header ── */
.page-header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 14px;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
}
.area-chip {
  display: inline-block;
  background: var(--primary-bg);
  color: var(--primary);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 500;
}

/* ── Metric cards ── */
.metric-grid { display: flex; gap: 12px; margin-bottom: 20px; }
.metric-card {
  flex: 1;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px 18px;
  text-align: center;
}
.metric-value {
  font-size: 26px; font-weight: 600;
  color: var(--primary); line-height: 1.2;
}
.metric-label {
  font-size: 12px; color: var(--text-secondary); margin-top: 4px;
}

/* ── Status badges ── */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 4px;
  font-size: 12px; font-weight: 500; white-space: nowrap;
}
.badge-conforme        { background:#f6ffed; color:#389e0d; border:1px solid #b7eb8f; }
.badge-non_conforme    { background:#fff2f0; color:#cf1322; border:1px solid #ffa39e; }
.badge-parziale        { background:#fffbe6; color:#d48806; border:1px solid #ffe58f; }
.badge-non_verificabile{ background:#fafafa; color:#8c8c8c; border:1px solid #d9d9d9; }
.badge-pending         { background:#fafafa; color:#8c8c8c; border:1px solid #d9d9d9; }

/* ── Expanders ── */
[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  margin-bottom: 6px !important;
}

/* ── Buttons ── */
.stButton > button {
  border-radius: var(--radius) !important;
  font-size: 14px !important;
  color: var(--text) !important;
  font-family: var(--font) !important;
}
.stButton > button[kind="primary"] {
  background: var(--primary) !important;
  border-color: var(--primary) !important;
  color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
  background: var(--primary-hover) !important;
  border-color: var(--primary-hover) !important;
  color: #ffffff !important;
}
.stButton > button:disabled,
.stButton > button[disabled] {
  background: rgba(0,0,0,.04) !important;
  border-color: var(--border) !important;
  color: rgba(0,0,0,.25) !important;
  cursor: not-allowed !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: var(--radius) !important; }

/* ── Fix: neutralize default link color in markdown text ── */
.main a { color: var(--text) !important; text-decoration: none !important; }
.main a:hover { text-decoration: underline !important; }
</style>
"""

st.markdown(MESA_CSS, unsafe_allow_html=True)

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


# ── SVG icon helpers (14px, Ant Design outlined style) ────────────────────────

def icon_home():
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/><path d="M9 21V12h6v9"/></svg>'


def icon_star():
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'


def icon_search():
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'


def icon_bell():
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'


def icon_fact_check():
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12l2 2 4-4"/><line x1="15" y1="8" x2="19" y2="8"/><line x1="15" y1="12" x2="19" y2="12"/><line x1="15" y1="16" x2="19" y2="16"/></svg>'


# ── Sidebar — ZONA A: Logo ────────────────────────────────────────────────────

st.sidebar.markdown("""
<div class="mesa-logo-area">
  <svg viewBox="0 0 148 44" height="22" aria-label="MESA ERM">
    <text x="4" y="34"
          font-family="'Helvetica Neue','Arial','Inter',system-ui,sans-serif"
          font-size="42" font-weight="200" fill="#95C11F">M</text>
    <text x="34" y="34"
          font-family="'Helvetica Neue','Arial','Inter',system-ui,sans-serif"
          font-size="42" font-weight="200" fill="#BDBDBD">ESA</text>
    <rect x="127" y="10" width="8" height="8" rx="1" fill="#95C11F"/>
  </svg>
</div>
""", unsafe_allow_html=True)

# API key warning
if not os.environ.get("OPENAI_API_KEY"):
    st.sidebar.warning("API key non configurata", icon="⚠️")

# ── Sidebar — ZONA B: Quick Nav ───────────────────────────────────────────────

st.sidebar.markdown(f"""
<div class="sidebar-quicknav">
  <div class="quicknav-item">{icon_home()}<span class="qnav-label">Home</span></div>
  <div class="quicknav-item">{icon_star()}<span class="qnav-label">Preferiti</span></div>
  <div class="quicknav-item">{icon_search()}<span class="qnav-label">Cerca</span></div>
  <div class="quicknav-item">
    {icon_bell()}
    <span class="qnav-label">Notifiche</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar — ZONA C: Navigazione Controlli ───────────────────────────────────

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
        f'<div class="status-row">'
        f'<span><span class="ctrl-id">{c.id}</span>{c.title[:26]}…</span>{b}'
        f'</div>',
        unsafe_allow_html=True,
    )

# Progresso
st.sidebar.markdown("---")
executed = len(st.session_state.results)
total = len(CONTROLS_TREE)
st.sidebar.progress(executed / total if total else 0)
st.sidebar.caption(f"Progresso: {executed} / {total} controlli")

st.sidebar.markdown("---")

# Azioni
if executed > 0:
    if st.sidebar.button("Genera report PDF", type="primary", use_container_width=True):
        results_list = [
            st.session_state.results[c.id]
            for c in CONTROLS_TREE
            if c.id in st.session_state.results
        ]
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

# ── Sidebar — ZONA D: User footer ─────────────────────────────────────────────

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
        with st.expander(f"{i}. {cp.check_point[:100]}"):
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
