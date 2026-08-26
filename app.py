import streamlit as st

from database import (
    init_database,
    test_connection,
    get_connection
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors",
    page_icon="🏌️",
    layout="wide"
)


# ============================================================
# DATABASE
# ============================================================

try:

    init_database()

    database_time = test_connection()

except Exception as error:

    st.error(
        "🔴 Database connection failed."
    )

    st.exception(error)

    st.stop()


# ============================================================
# DASHBOARD
# ============================================================

def get_player_count():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM players
                WHERE active = TRUE
                """
            )

            return cursor.fetchone()[0]

    finally:

        connection.close()


def get_event_count():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM events
                """
            )

            return cursor.fetchone()[0]

    finally:

        connection.close()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🏌️ Golfing Warriors"
)

st.sidebar.caption(
    "Your friends. Your golf. "
    "Your championship."
)

st.sidebar.divider()

st.sidebar.success(
    "🟢 Database connected"
)

st.sidebar.caption(
    f"Server time: {database_time}"
)


# ============================================================
# HOME
# ============================================================

st.title("🏌️ Golfing Warriors")

st.subheader(
    "Your friends. Your golf. Your championship."
)

st.divider()

players = get_player_count()
events = get_event_count()

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Active Players",
        players
    )

with col2:

    st.metric(
        "Events",
        events
    )

with col3:

    st.metric(
        "Championship Points",
        "0"
    )

st.divider()

st.info(
    "Use the pages in the sidebar to manage "
    "players, seasons and events."
)

st.caption(
    "Golfing Warriors V1"
)
