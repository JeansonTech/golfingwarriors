"""Golfing Warriors authentication and shared sidebar helpers."""
import hmac
import os
from pathlib import Path
import streamlit as st

SESSION_KEY = "golfing_warriors_admin"
PASSWORD_KEY = "GOLFING_WARRIORS_ADMIN_PASSWORD"
SIDEBAR_ADMIN_RENDERED_KEY = "gw_sidebar_admin_rendered"

def get_admin_password():
    try:
        password = st.secrets.get(PASSWORD_KEY, "")
    except Exception:
        password = ""
    if password:
        return str(password)
    return os.getenv(PASSWORD_KEY, "")

def is_admin():
    return bool(st.session_state.get(SESSION_KEY, False))

def login_admin(password):
    configured_password = get_admin_password()
    if not configured_password:
        return False
    if hmac.compare_digest(str(password), str(configured_password)):
        st.session_state[SESSION_KEY] = True
        st.session_state.pop("golfing_warriors_admin_password", None)
        return True
    return False

def logout_admin():
    st.session_state[SESSION_KEY] = False
    st.session_state.pop("golfing_warriors_admin_password", None)

def render_admin_sidebar():
    """Render shared admin controls once and return current admin state."""
    if st.session_state.get(SIDEBAR_ADMIN_RENDERED_KEY, False):
        return is_admin()

    st.sidebar.divider()
    st.sidebar.subheader("🔐 Admin Access")

    if is_admin():
        st.sidebar.success("🟢 Admin Mode Active")
        if st.sidebar.button("🔓 Exit Admin Mode", use_container_width=True, key="gw_admin_logout"):
            logout_admin()
            st.rerun()
        st.session_state[SIDEBAR_ADMIN_RENDERED_KEY] = True
        return True

    password = st.sidebar.text_input(
        "Admin Password",
        type="password",
        key="golfing_warriors_admin_password",
    )

    if st.sidebar.button("🔐 Enter Admin Mode", use_container_width=True, key="gw_admin_login"):
        if login_admin(password):
            st.rerun()
        if get_admin_password():
            st.sidebar.error("Incorrect admin password.")
        else:
            st.sidebar.error(
                "Admin password is not configured. Set "
                "GOLFING_WARRIORS_ADMIN_PASSWORD in Railway."
            )

    st.session_state[SIDEBAR_ADMIN_RENDERED_KEY] = True
    return False

def render_app_sidebar():
    """Render the finished Golfing Warriors sidebar navigation."""
    # Reset this per-run guard. Streamlit session state persists across
    # reruns, but the sidebar itself is rendered fresh on every run.
    st.session_state[SIDEBAR_ADMIN_RENDERED_KEY] = False

    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        .gw-nav-title {
            font-size: 1.35rem;
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: 4px;
        }
        .gw-nav-subtitle {
            font-size: .78rem;
            opacity: .65;
            line-height: 1.35;
            margin-bottom: 14px;
        }
        .gw-nav-section {
            font-size: .72rem;
            font-weight: 800;
            opacity: .55;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin: 14px 0 4px 2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        """
        <div class="gw-nav-title">🏌️ Golfing Warriors</div>
        <div class="gw-nav-subtitle">Your friends. Your golf.<br>Your championship.</div>
        """,
        unsafe_allow_html=True,
    )

    def existing_page(*names):
        pages_dir = Path(__file__).resolve().parent / "pages"
        for name in names:
            if (pages_dir / name).exists():
                return f"pages/{name}"
        return None

    st.sidebar.markdown('<div class="gw-nav-section">Home</div>', unsafe_allow_html=True)
    st.sidebar.page_link("app.py", label="🏠 Dashboard")

    st.sidebar.markdown('<div class="gw-nav-section">Competition</div>', unsafe_allow_html=True)
    for candidates, label in [
        (("leaderboards.py",), "🏆 Leaderboards"),
        (("results.py", "results_scorecards.py"), "📋 Results"),
        (("live_scoring.py",), "📱 Live Scoring"),
    ]:
        target = existing_page(*candidates)
        if target:
            st.sidebar.page_link(target, label=label)

    st.sidebar.markdown('<div class="gw-nav-section">Golf</div>', unsafe_allow_html=True)
    for candidates, label in [
        (("golf_statistics.py",), "📈 Golf Statistics"),
        (("player_profiles.py",), "👤 Player Profiles"),
        (("rivalry.py", "rivalries.py"), "⚔️ Rivalry"),
    ]:
        target = existing_page(*candidates)
        if target:
            st.sidebar.page_link(target, label=label)

    if is_admin():
        st.sidebar.markdown('<div class="gw-nav-section">Admin</div>', unsafe_allow_html=True)
        for candidates, label in [
            (("players.py",), "👥 Players"),
            (("courses.py",), "⛳ Courses"),
            (("events.py", "events_admin.py", "events_updated.py"), "🏆 Events"),
            (("seasons.py",), "📅 Seasons"),
            (("ranking_settings.py",), "⚙️ Ranking Settings"),
        ]:
            target = existing_page(*candidates)
            if target:
                st.sidebar.page_link(target, label=label)

    st.sidebar.divider()
    render_admin_sidebar()

def require_admin():
    if not is_admin():
        st.error("🔐 Admin access is required for this action.")
        st.stop()
