"""
Autenticazione e RBAC per il prototipo.
Ogni pagina chiama require_login() subito dopo set_page_config().
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit_authenticator as stauth
import yaml

CREDENTIALS_PATH = Path(__file__).parent / "credentials.yaml"

# Mappa ruolo → etichetta italiana
ROLE_LABELS = {
    "auditor":  "Auditor",
    "head_ia":  "Head of Internal Audit",
    "auditee":  "Auditee",
}

# Iniziali avatar per ruolo
ROLE_INITIALS = {
    "auditor": "AU",
    "head_ia": "HA",
    "auditee": "AE",
}


def _load_config() -> dict:
    with open(CREDENTIALS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_authenticator() -> tuple[stauth.Authenticate, dict]:
    config = _load_config()
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        auto_hash=False,
    )
    return authenticator, config


def require_login() -> stauth.Authenticate:
    """
    Mostra il form di login se l'utente non è autenticato e blocca la pagina.
    Se autenticato, imposta st.session_state['role'] e restituisce l'authenticator
    (usato dalla sidebar per il logout).
    """
    # Assicura che il DB sia inizializzato anche se si arriva direttamente su una pagina
    from db import DB_PATH
    if not DB_PATH.exists():
        from db.init_db import init_db
        init_db()

    authenticator, config = get_authenticator()

    if not st.session_state.get("authentication_status"):
        st.markdown(
            """
            <style>
            .login-wrapper { max-width: 400px; margin: 80px auto; }
            </style>
            <div class="login-wrapper">
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### Internal Audit — MESA ERM")
        st.markdown("Accedi con le credenziali fornite dal tuo team.")

        authenticator.login(location="main", key="Login")

        if st.session_state.get("authentication_status") is False:
            st.error("Username o password non corretti.", icon="🔒")

        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # Aggiorna role in session_state ad ogni page load
    username = st.session_state.get("username", "")
    role = (
        config["credentials"]["usernames"]
        .get(username, {})
        .get("role", "auditor")
    )
    st.session_state["role"] = role
    return authenticator


# ── Helpers di ruolo ──────────────────────────────────────────────────────────

def get_current_role() -> str:
    return st.session_state.get("role", "auditor")


def get_current_user() -> str:
    """Nome completo dell'utente loggato."""
    return st.session_state.get("name", "Utente")


def get_current_username() -> str:
    """Username (chiave nel YAML) dell'utente loggato."""
    return st.session_state.get("username", "system")


def can_edit() -> bool:
    """Auditor e Head IA possono modificare dati."""
    return get_current_role() in ("auditor", "head_ia")


def is_head_ia() -> bool:
    return get_current_role() == "head_ia"


def is_auditee() -> bool:
    return get_current_role() == "auditee"


def role_label() -> str:
    return ROLE_LABELS.get(get_current_role(), get_current_role())


def role_initials() -> str:
    return ROLE_INITIALS.get(get_current_role(), "??")
