import streamlit as st
from pathlib import Path

from auth import render_app_sidebar


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors",
    page_icon="🏌️",
    layout="wide",
    initial_sidebar_state="auto",
)


# ============================================================
# PAGE DISCOVERY
# ============================================================

PAGES_DIR = Path(__file__).resolve().parent / "pages"


def first_existing(*names):
    """Return the first existing pages/*.py file from the candidates."""
    for name in names:
        if (PAGES_DIR / name).exists():
            return PAGES_DIR / name
    return None


def make_page(candidates, title, icon):
    """Create a Streamlit Page for the first available candidate."""
    path = first_existing(*candidates)

    if path is None:
        return None

    return st.Page(
        str(path),
        title=title,
        icon=icon,
    )


# ============================================================
# NAVIGATION
# ============================================================

home_page = st.Page(
    str(PAGES_DIR / "dashboard.py"),
    title="Dashboard",
    icon="🏠",
    default=True,
)

competition = [
    page
    for page in [
        make_page(("leaderboards.py",), "Leaderboards", "🏆"),
        make_page(("results.py", "results_scorecards.py"), "Results", "📋"),
        make_page(("live_scoring.py",), "Live Scoring", "📱"),
    ]
    if page is not None
]

golf = [
    page
    for page in [
        make_page(("golf_statistics.py",), "Golf Statistics", "📈"),
        make_page(("player_profiles.py",), "Player Profiles", "👤"),
        make_page(("rivalry.py", "rivalries.py"), "Rivalry", "⚔️"),
    ]
    if page is not None
]

admin = [
    page
    for page in [
        make_page(("players.py",), "Players", "👥"),
        make_page(("courses.py",), "Courses", "⛳"),
        make_page(("events.py", "events_admin.py", "events_updated.py"), "Events", "🏆"),
        make_page(("seasons.py",), "Seasons", "📅"),
        make_page(("ranking_settings.py",), "Ranking Settings", "⚙️"),
    ]
    if page is not None
]

sections = {
    "Home": [home_page],
}

if competition:
    sections["Competition"] = competition

if golf:
    sections["Golf"] = golf

if admin:
    sections["Admin"] = admin


# Hide Streamlit's generated page list. Our own sidebar navigation is
# rendered by auth.render_app_sidebar().
pg = st.navigation(
    sections,
    position="hidden",
)


# ============================================================
# GLOBAL SIDEBAR
# ============================================================

render_app_sidebar()


# ============================================================
# RUN SELECTED PAGE
# ============================================================

pg.run()
