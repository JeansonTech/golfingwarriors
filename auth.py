"""Golfing Warriors authentication and permission helpers.

V1 deliberately keeps authentication simple: the public app remains
viewable by everyone, while administrative actions require the admin
password stored in Streamlit secrets or the Railway environment.
"""

import hmac
import os

import streamlit as st


SESSION_KEY = "golfing_warriors_admin"
PASSWORD_KEY = "GOLFING_WARRIORS_ADMIN_PASSWORD"


def get_admin_password():
    """Return the configured admin password without storing it in code."""
    try:
        password = st.secrets.get(PASSWORD_KEY, "")
    except Exception:
        password = ""

    if password:
        return str(password)

    return os.getenv(PASSWORD_KEY, "")


def is_admin():
    """Return True when the current Streamlit session is authenticated."""
    return bool(st.session_state.get(SESSION_KEY, False))


def login_admin(password):
    """Authenticate the current session with the configured admin password."""
    configured_password = get_admin_password()

    if not configured_password:
        return False

    if hmac.compare_digest(str(password), str(configured_password)):
        st.session_state[SESSION_KEY] = True
        st.session_state.pop("golfing_warriors_admin_password", None)
        return True

    return False


def logout_admin():
    """End the current admin session."""
    st.session_state[SESSION_KEY] = False
    st.session_state.pop("golfing_warriors_admin_password", None)


def render_admin_sidebar():
    """Render the shared admin login/logout controls and return admin state."""
    st.sidebar.divider()
    st.sidebar.subheader("🔐 Admin Access")

    if is_admin():
        st.sidebar.success("🟢 Admin Mode Active")

        if st.sidebar.button(
            "🔓 Exit Admin Mode",
            use_container_width=True,
            key="gw_admin_logout",
        ):
            logout_admin()
            st.rerun()

        return True

    password = st.sidebar.text_input(
        "Admin Password",
        type="password",
        key="golfing_warriors_admin_password",
    )

    if st.sidebar.button(
        "🔐 Enter Admin Mode",
        use_container_width=True,
        key="gw_admin_login",
    ):
        if login_admin(password):
            st.rerun()

        if get_admin_password():
            st.sidebar.error("Incorrect admin password.")
        else:
            st.sidebar.error(
                "Admin password is not configured. "
                "Set GOLFING_WARRIORS_ADMIN_PASSWORD in Railway."
            )

    return False


def require_admin():
    """Stop execution unless the current session is an authenticated admin."""
    if not is_admin():
        st.error("🔐 Admin access is required for this action.")
        st.stop()
