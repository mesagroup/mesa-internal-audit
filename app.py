"""
Internal Audit Prototype — Home
"""
from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Internal Audit — MESA ERM",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.common import inject_css, render_sidebar_nav, badge_html
from db.init_db import init_db
from db import DB_PATH

inject_css()

# Inizializza il DB alla prima esecuzione
if not DB_PATH.exists():
    init_db()

render_sidebar_nav()

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="page-header">
      <h2>Internal Audit — MESA ERM</h2>
      <span class="area-chip">Prototipo v1.1</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if not os.environ.get("OPENAI_API_KEY"):
    st.warning("API key OpenAI non configurata. Imposta OPENAI_API_KEY nel file .env.", icon="⚠️")

# ── KPI ───────────────────────────────────────────────────────────────────────

from db.repositories import get_dashboard_counts

counts = get_dashboard_counts()

st.markdown(
    f"""
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-value">{counts['controls']}</div>
        <div class="metric-label">Controlli in Anagrafica</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{counts['active_engagements']}</div>
        <div class="metric-label">Engagement attivi</div>
      </div>
      <div class="metric-card">
        <div class="metric-value" style="color:#cf1322">{counts['open_findings']}</div>
        <div class="metric-label">Finding aperti</div>
      </div>
      <div class="metric-card">
        <div class="metric-value" style="color:#d48806">{counts['overdue_action_plans']}</div>
        <div class="metric-label">Action plan scaduti</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Flusso di lavoro ──────────────────────────────────────────────────────────

st.markdown("#### Come si usa il prototipo")
st.markdown(
    """
1. **Anagrafica** — verifica o modifica i controlli disponibili. Usa "Reset to defaults" per ricaricare i 3 controlli P2P.
2. **Engagement** — crea un nuovo engagement, seleziona il controllo da testare, carica i documenti ed esegui la verifica AI.
3. **Findings & Remediation** — visualizza i finding generati, aggiorna il loro stato, aggiungi action plan con scadenza e responsabile.
"""
)

st.info(
    "Questo strumento è un **prototipo dimostrativo**. "
    "Persistenza su SQLite locale. Nessuna integrazione live con sistemi ERP/SRM/HR.",
    icon="ℹ️",
)
