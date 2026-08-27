"""
Golfing Warriors authentication and navigation helpers.

Public pages are available to everyone.
Administrative controls are displayed only after
successful admin authentication.
"""

import hmac
import os

import streamlit as st


SESSION_KEY = "golfing_warriors_admin"
PASSWORD_KEY = "GOLFING_WARRIORS_ADMIN_PASSWORD"


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

def get_admin_password():
    """Return the configured admin password."""

    try:
        password = st.secrets.get(
            PASSWORD_KEY,
            ""
        )
    except Exception:
        password = ""

    if password:
        return str(password)

    return os.getenv(
        PASSWORD_KEY,
        ""
    )


def is_admin():
    """Return True when the current session is authenticated."""

    return bool(
        st.session_state.get(
            SESSION_KEY,
            False
        )
    )


def login_admin(password):
    """Authenticate the current session."""

    configured_password = get_admin_password()

    if not configured_password:
        return False

    if hmac.compare_digest(
        str(password),
        str(configured_password)
    ):
        st.session_state[SESSION_KEY] = True

        st.session_state.pop(
            "golfing_warriors_admin_password",
            None
        )

        return True

    return False


def logout_admin():
    """End the current admin session."""

    st.session_state[SESSION_KEY] = False

    st.session_state.pop(
        "golfing_warriors_admin_password",
        None
    )


# ============================================================
# CUSTOM APPLICATION SIDEBAR
# ============================================================

def render_app_sidebar():
    """
    Render the Golfing Warriors application sidebar.

    Navigation uses the registered Streamlit Page objects
    from navigation.py.
    """

    # Import here deliberately so that navigation objects
    # are only loaded when the sidebar is rendered.
    from navigation import (
        DASHBOARD,
        LEADERBOARDS,
        RESULTS,
        PLAYER_PROFILES,
        GOLF_STATISTICS,
        LIVE_SCORING,
        PLAYERS,
        SEASONS,
        COURSES,
        EVENTS,
        RANKING_SETTINGS,
    )

    # ========================================================
    # BRANDING
    # ========================================================

    st.sidebar.title(
        "🏌️ Golfing Warriors"
    )

    st.sidebar.caption(
        "Your friends. Your golf. "
        "Your championship."
    )

    st.sidebar.divider()

    # ========================================================
    # HOME
    # ========================================================

    st.sidebar.markdown(
        "### 🏠 HOME"
    )

    st.sidebar.page_link(
        DASHBOARD,
        label="Dashboard"
    )

    # ========================================================
    # CHAMPIONSHIP
    # ========================================================

    st.sidebar.markdown(
        "### 🏆 CHAMPIONSHIP"
    )

    st.sidebar.page_link(
        LEADERBOARDS,
        label="Leaderboards"
    )

    st.sidebar.page_link(
        RESULTS,
        label="Results"
    )

    st.sidebar.page_link(
        PLAYER_PROFILES,
        label="Player Profiles"
    )

    # ========================================================
    # GOLF
    # ========================================================

    st.sidebar.markdown(
        "### ⛳ GOLF"
    )

    st.sidebar.page_link(
        GOLF_STATISTICS,
        label="Golf Statistics"
    )

    st.sidebar.page_link(
        LIVE_SCORING,
        label="Live Scoring"
    )

    # ========================================================
    # ADMINISTRATION
    # ========================================================

    if is_admin():

        st.sidebar.markdown(
            "### ⚙️ ADMINISTRATION"
        )

        st.sidebar.page_link(
            PLAYERS,
            label="Players"
        )

        st.sidebar.page_link(
            COURSES,
            label="Courses"
        )

        st.sidebar.page_link(
            EVENTS,
            label="Events"
        )

        st.sidebar.page_link(
            SEASONS,
            label="Seasons"
        )

        st.sidebar.page_link(
            RANKING_SETTINGS,
            label="Ranking Settings"
        )

    # ========================================================
    # ADMIN ACCESS
    # ========================================================

    render_admin_sidebar()


# ============================================================
# ADMIN LOGIN / LOGOUT
# ============================================================

def render_admin_sidebar():
    """
    Render the admin login/logout controls.
    """

    st.sidebar.divider()

    st.sidebar.subheader(
        "🔐 Admin Access"
    )

    if is_admin():

        st.sidebar.success(
            "🟢 Admin Mode Active"
        )

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

            st.sidebar.error(
                "Incorrect admin password."
            )

        else:

            st.sidebar.error(
                "Admin password is not configured. "
                "Set GOLFING_WARRIORS_ADMIN_PASSWORD "
                "in Railway."
            )

    return False


# ============================================================
# ADMIN PAGE PROTECTION
# ============================================================

def require_admin():
    """
    Stop execution unless the current session
    is authenticated as an administrator.
    """

    if not is_admin():

        st.error(
            "🔐 Admin access is required for this action."
        )

        st.stop()
