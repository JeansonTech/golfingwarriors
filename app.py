import streamlit as st
import pandas as pd

from database import init_database, test_connection, get_connection


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors",
    page_icon="🏌️",
    layout="wide"
)


# ============================================================
# DATABASE INITIALISATION
# ============================================================

try:
    init_database()
    database_time = test_connection()
except Exception as error:
    st.error("🔴 Database connection failed.")
    st.exception(error)
    st.stop()


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_players(active_only=False):
    """Return players from the database."""

    connection = get_connection()

    try:
        query = """
            SELECT
                id,
                name,
                nickname,
                current_handicap,
                active,
                created_at
            FROM players
        """

        if active_only:
            query += " WHERE active = TRUE"

        query += " ORDER BY name"

        return pd.read_sql_query(query, connection)

    finally:
        connection.close()


def add_player(name, nickname, handicap):
    """Add a new player."""

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO players
                    (name, nickname, current_handicap)
                VALUES
                    (%s, %s, %s)
                """,
                (
                    name.strip(),
                    nickname.strip() if nickname else None,
                    handicap
                )
            )

        connection.commit()

    finally:
        connection.close()


def update_player(player_id, name, nickname, handicap, active):
    """Update an existing player."""

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE players
                SET
                    name = %s,
                    nickname = %s,
                    current_handicap = %s,
                    active = %s
                WHERE id = %s
                """,
                (
                    name.strip(),
                    nickname.strip() if nickname else None,
                    handicap,
                    active,
                    player_id
                )
            )

        connection.commit()

    finally:
        connection.close()


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.title("🏌️ Golfing Warriors")

st.sidebar.caption("Golfing Warriors Championship")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "👥 Players"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    f"Database connected\n\n"
    f"Server time: {database_time}"
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title("🏌️ Golfing Warriors")

    st.subheader("Your friends. Your golf. Your championship.")

    st.divider()

    players = get_players()

    active_players = players[
        players["active"] == True
    ]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Players",
            len(active_players)
        )

    with col2:
        st.metric(
            "Events",
            "0"
        )

    with col3:
        st.metric(
            "Championship Points",
            "0"
        )

    st.divider()

    st.info(
        "Welcome to Golfing Warriors! "
        "Start by adding your players."
    )


# ============================================================
# PLAYER MANAGEMENT
# ============================================================

elif page == "👥 Players":

    st.title("👥 Players")

    st.caption(
        "Manage the golfers participating in Golfing Warriors."
    )

    st.divider()

    # --------------------------------------------------------
    # ADD PLAYER
    # --------------------------------------------------------

    st.subheader("➕ Add Player")

    with st.form("add_player_form", clear_on_submit=True):

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Player Name *",
                placeholder="e.g. Peter Smith"
            )

        with col2:
            nickname = st.text_input(
                "Nickname",
                placeholder="Optional"
            )

        handicap = st.number_input(
            "Current Handicap",
            min_value=-10.0,
            max_value=54.0,
            value=18.0,
            step=0.1
        )

        submitted = st.form_submit_button(
            "➕ Add Player",
            type="primary"
        )

        if submitted:

            if not name.strip():

                st.error(
                    "Please enter the player's name."
                )

            else:

                try:

                    add_player(
                        name,
                        nickname,
                        handicap
                    )

                    st.success(
                        f"{name} has been added to Golfing Warriors!"
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        "Unable to add player."
                    )

                    st.exception(error)

    st.divider()

    # --------------------------------------------------------
    # PLAYER LIST
    # --------------------------------------------------------

    st.subheader("Current Players")

    players = get_players()

    if players.empty:

        st.info(
            "No players have been added yet."
        )

    else:

        # Display table

        display_players = players.copy()

        display_players["Status"] = display_players[
            "active"
        ].apply(
            lambda active:
                "🟢 Active" if active else "⚪ Inactive"
        )

        display_players["Handicap"] = display_players[
            "current_handicap"
        ].map(
            lambda value:
                f"{value:g}" if pd.notna(value) else "-"
        )

        display_players = display_players[
            [
                "name",
                "nickname",
                "Handicap",
                "Status"
            ]
        ]

        display_players.columns = [
            "Player",
            "Nickname",
            "Handicap",
            "Status"
        ]

        st.dataframe(
            display_players,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ----------------------------------------------------
        # EDIT PLAYER
        # ----------------------------------------------------

        st.subheader("✏️ Edit Player")

        player_options = {
            f"{row['name']} "
            f"({row['nickname']})"
            if row["nickname"]
            else row["name"]:
                row["id"]
            for _, row in players.iterrows()
        }

        selected_player_name = st.selectbox(
            "Select Player",
            list(player_options.keys())
        )

        selected_player_id = player_options[
            selected_player_name
        ]

        selected_player = players[
            players["id"] == selected_player_id
        ].iloc[0]

        with st.form("edit_player_form"):

            edit_col1, edit_col2 = st.columns(2)

            with edit_col1:

                edit_name = st.text_input(
                    "Player Name",
                    value=selected_player["name"]
                )

            with edit_col2:

                edit_nickname = st.text_input(
                    "Nickname",
                    value=selected_player["nickname"]
                    if pd.notna(
                        selected_player["nickname"]
                    )
                    else ""
                )

            edit_handicap = st.number_input(
                "Current Handicap",
                min_value=-10.0,
                max_value=54.0,
                value=float(
                    selected_player["current_handicap"]
                ),
                step=0.1
            )

            edit_active = st.checkbox(
                "Active Player",
                value=bool(
                    selected_player["active"]
                )
            )

            save_changes = st.form_submit_button(
                "💾 Save Changes",
                type="primary"
            )

            if save_changes:

                if not edit_name.strip():

                    st.error(
                        "Player name cannot be empty."
                    )

                else:

                    try:

                        update_player(
                            selected_player_id,
                            edit_name,
                            edit_nickname,
                            edit_handicap,
                            edit_active
                        )

                        st.success(
                            "Player updated successfully."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            "Unable to update player."
                        )

                        st.exception(error)
