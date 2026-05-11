"""
Componenti UI condivisi tra tutte le pagine del prototipo.
Ogni pagina chiama inject_css() e render_sidebar_nav() all'inizio.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

# ── MESA ERM Design System CSS (+ override nav Streamlit) ────────────────────

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
  --border:           #f0f0f0;
  --text:             rgba(0,0,0,.88);
  --text-secondary:   rgba(0,0,0,.45);
  --text-user:        #595959;
  --radius:           6px;
  --radius-lg:        8px;
  --menu-item-h:      40px;
  --font:             -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                      'Helvetica Neue', Arial, sans-serif;
}

html, body, [class*="css"] { font-family: var(--font) !important; font-size: 14px !important; }

/* Hide Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCloseButton"],
button[aria-label="Close sidebar"],
button[aria-label="Collapse sidebar"] { display: none !important; }

/* Hide default page nav — we use custom nav */
[data-testid="stSidebarNav"] { display: none !important; }

/* Page background */
.stApp, [data-testid="stAppViewContainer"] { background: var(--bg-page) !important; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: #ffffff !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }

/* Scrollbar */
*::-webkit-scrollbar { width: 6px; height: 6px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb { background: rgba(0,0,0,.15); border-radius: 3px; }
* { scrollbar-width: thin; scrollbar-color: rgba(0,0,0,.15) transparent; }

/* Logo area */
.mesa-logo-area {
  height: 44px; display: flex; align-items: center; justify-content: center;
  border-bottom: 1px solid var(--border); flex-shrink: 0;
}

/* Nav section label */
.nav-section-label {
  font-size: 11px; font-weight: 600; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: .06em;
  padding: 16px 24px 4px; margin: 0;
}

/* page_link overrides — make them look like menu items */
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
  display: flex !important; align-items: center !important;
  min-height: var(--menu-item-h) !important;
  padding: 0 16px 0 24px !important;
  border-radius: var(--radius) !important;
  margin: 1px 4px !important;
  color: var(--text) !important;
  font-size: 14px !important;
  font-weight: 400 !important;
  text-decoration: none !important;
  transition: background .15s !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
  background: var(--bg-hover) !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"][aria-current="page"] a,
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
  background: var(--primary-bg) !important;
  color: var(--primary) !important;
  font-weight: 600 !important;
}

/* Sidebar divider */
[data-testid="stSidebar"] hr { border-color: var(--border) !important; margin: 6px 0 !important; }

/* User footer */
.user-footer {
  border-top: 1px solid var(--border); padding: 8px;
  display: flex; align-items: center; gap: 8px; margin-top: 8px;
  cursor: pointer; border-radius: var(--radius); transition: background .15s;
}
.user-footer:hover { background: var(--bg-hover); }
.user-avatar {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--primary); color: #fff;
  font-size: 11px; font-weight: 500;
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.user-name-text { font-size: 14px; color: var(--text-user); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Content area */
.main .block-container {
  background: #ffffff !important; border-radius: var(--radius-lg) !important;
  margin: 12px !important; padding: 16px 24px !important; max-width: 100% !important;
}

/* Page header */
.page-header { border-bottom: 1px solid var(--border); padding-bottom: 14px; margin-bottom: 20px; }
.page-header h2 { margin: 0 0 4px 0; font-size: 18px; font-weight: 600; color: var(--text); }
.area-chip {
  display: inline-block; background: var(--primary-bg); color: var(--primary);
  border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: 500;
}

/* Metric cards */
.metric-grid { display: flex; gap: 12px; margin-bottom: 20px; }
.metric-card {
  flex: 1; background: #fff; border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 14px 18px; text-align: center;
}
.metric-value { font-size: 26px; font-weight: 600; color: var(--primary); line-height: 1.2; }
.metric-label { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

/* Status badges */
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
.badge-open            { background:#fff7e6; color:#d46b08; border:1px solid #ffd591; }
.badge-validated       { background:#f6ffed; color:#389e0d; border:1px solid #b7eb8f; }
.badge-closed          { background:#fafafa; color:#8c8c8c; border:1px solid #d9d9d9; }
.badge-alto            { background:#fff2f0; color:#cf1322; border:1px solid #ffa39e; }
.badge-medio           { background:#fffbe6; color:#d48806; border:1px solid #ffe58f; }
.badge-basso           { background:#f6ffed; color:#389e0d; border:1px solid #b7eb8f; }

/* Progress bar */
[data-testid="stProgressBar"] > div > div { background: var(--primary) !important; }

/* Expanders */
[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  margin-bottom: 6px !important;
}

/* Buttons */
.stButton > button { border-radius: var(--radius) !important; font-size: 14px !important; color: var(--text) !important; }
.stButton > button[kind="primary"] { background: var(--primary) !important; border-color: var(--primary) !important; color: #fff !important; }
.stButton > button[kind="primary"]:hover { background: var(--primary-hover) !important; border-color: var(--primary-hover) !important; }
.stButton > button:disabled { background: rgba(0,0,0,.04) !important; border-color: var(--border) !important; color: rgba(0,0,0,.25) !important; }

/* Alerts */
[data-testid="stAlert"] { border-radius: var(--radius) !important; }

/* Links in content */
.main a { color: var(--text) !important; text-decoration: none !important; }
.main a:hover { text-decoration: underline !important; }
</style>
"""


def inject_css() -> None:
    st.markdown(MESA_CSS, unsafe_allow_html=True)
    components.html(
        """
        <script>
        try {
          var p = window.parent;
          var remove = [];
          for (var i = 0; i < p.localStorage.length; i++) {
            var k = p.localStorage.key(i);
            if (k && (k.includes('sidebar') || k.includes('collapsed'))) remove.push(k);
          }
          remove.forEach(function(k) { p.localStorage.removeItem(k); });
          setTimeout(function() {
            var btn = p.document.querySelector('[data-testid="collapsedControl"] button');
            if (btn) btn.click();
          }, 200);
        } catch(e) {}
        </script>
        """,
        height=0,
    )


def render_sidebar_nav(current_page: str = "") -> None:
    """Logo + navigazione modulare nella sidebar."""
    st.sidebar.markdown(
        """
        <div class="mesa-logo-area">
          <svg viewBox="0 0 148 44" height="22" aria-label="MESA ERM">
            <text x="4" y="34"
                  font-family="'Helvetica Neue','Arial',system-ui,sans-serif"
                  font-size="42" font-weight="200" fill="#95C11F">M</text>
            <text x="34" y="34"
                  font-family="'Helvetica Neue','Arial',system-ui,sans-serif"
                  font-size="42" font-weight="200" fill="#BDBDBD">ESA</text>
            <rect x="127" y="10" width="8" height="8" rx="1" fill="#95C11F"/>
          </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        '<p class="nav-section-label">Moduli</p>', unsafe_allow_html=True
    )

    with st.sidebar:
        st.page_link("app.py",                    label="🏠  Home")
        st.page_link("pages/1_Anagrafica.py",     label="📋  Anagrafica")
        st.page_link("pages/4_Engagement.py",     label="🔎  Engagement")
        st.page_link("pages/5_Findings.py",       label="⚠️  Findings & Remediation")

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div class="user-footer">
          <div class="user-avatar">AU</div>
          <span class="user-name-text">Auditor</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Badge helpers ─────────────────────────────────────────────────────────────

_STATUS_LABEL = {
    "conforme":         "Conforme",
    "non_conforme":     "Non conforme",
    "parziale":         "Parziale",
    "non_verificabile": "Non verif.",
    "open":             "Aperto",
    "validated":        "Validato",
    "closed":           "Chiuso",
    "alto":             "Alto",
    "medio":            "Medio",
    "basso":            "Basso",
    "in_progress":      "In corso",
    "closed_pending":   "Chiuso (verifica)",
}


def badge_html(status: str) -> str:
    label = _STATUS_LABEL.get(status, status)
    return f'<span class="badge badge-{status}">● {label}</span>'


def pending_badge() -> str:
    return '<span class="badge badge-pending">○ Da eseguire</span>'
