import streamlit as st


# ============================================================
# PUBLIC PAGES
# ============================================================

DASHBOARD = st.Page(
    "app_dashboard_v3_leader_form.py",
    title="Dashboard",
    icon="🏠",
    default=True,
)

PLAYERS = st.Page(
    "pages/players.py",
    title="Players",
    icon="👥",
)

PLAYER_PROFILES = st.Page(
    "pages/player_profiles.py",
    title="Player Profiles",
    icon="👤",
)

LEADERBOARDS = st.Page(
    "pages/leaderboards.py",
    title="Leaderboards",
    icon="🏆",
)

RESULTS = st.Page(
    "pages/results.py",
    title="Results",
    icon="📋",
)

GOLF_STATISTICS = st.Page(
    "pages/golf_statistics.py",
    title="Golf Statistics",
    icon="📊",
)

LIVE_SCORING = st.Page(
    "pages/live_scoring.py",
    title="Live Scoring",
    icon="📱",
)


# ============================================================
# ADMIN / MANAGEMENT PAGES
# ============================================================

SEASONS = st.Page(
    "pages/seasons.py",
    title="Seasons",
    icon="📅",
)

COURSES = st.Page(
    "pages/courses.py",
    title="Courses",
    icon="⛳",
)

EVENTS = st.Page(
    "pages/events.py",
    title="Events",
    icon="🏆",
)

RANKING_SETTINGS = st.Page(
    "pages/ranking_settings.py",
    title="Ranking Settings",
    icon="⚙️",
)


# ============================================================
# NAVIGATION GROUPS
# ============================================================

PUBLIC_PAGES = {
    "Home": [
        DASHBOARD,
        LEADERBOARDS,
        RESULTS,
        PLAYER_PROFILES,
        GOLF_STATISTICS,
        LIVE_SCORING,
    ],
}

ADMIN_PAGES = {
    "Administration": [
        PLAYERS,
        SEASONS,
        COURSES,
        EVENTS,
        RANKING_SETTINGS,
    ],
}
