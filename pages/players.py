import streamlit as st
import pandas as pd

from database import get_connection


def get_players(active_only=False):

    connection = get_connection()

    try:

        query = """
            SELECT
                id,
                name,
                nickname,
                current_handicap,
                active
            FROM players
        """

        if active_only:
            query += " WHERE active = TRUE"

        query += " ORDER BY name"

        return pd.read_sql_query(
            query,
            connection
        )

    finally:
        connection.close()


def add_player(name, nickname, handicap):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO players
                    (
                        name,
                        nickname,
                        current_handicap
                    )
                VALUES
                    (%s, %s, %s)
                """,
                (
                    name.strip(),
                    nickname.strip()
                    if nickname else None,
                    handicap
                )
            )

        connection.commit()

    finally:
        connection.close()


def update_player(
    player_id,
    name,
    nickname,
    handicap,
    active
):

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
                    nickname.strip()
                    if nickname else None,
                    handicap,
                    active,
                    player_id
                )
            )

        connection.commit()

    finally:
        connection.close()


st.title("👥 Players")

st.caption(
    "Manage the golfers participating "
    "in Golfing Warriors."
)

st.divider()


# ============================================================
# ADD PLAYER
# ============================================================

st.subheader("➕ Add Player")

with st.form(
    "add_player_form",
    clear_on_submit=True
):

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
        max_value=64.0,
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
                    f"{name} has been added!"
                )

                st.rerun()

            except Exception as error:

                st.error(
                    "Unable to add player."
                )

                st.exception(error)


st.divider()


# ============================================================
# PLAYER LIST
# ============================================================

st.subheader("Current Players")

players = get_players()

if players.empty:

    st.info(
        "No players have been added yet."
    )

else:

    display_players = players.copy()

    display_players["Status"] = (
        display_players["active"]
        .apply(
            lambda active:
                "🟢 Active"
                if active
                else "⚪ Inactive"
        )
    )

    display_players["Handicap"] = (
        display_players["current_handicap"]
        .map(
            lambda value:
                f"{value:g}"
                if pd.notna(value)
                else "-"
        )
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


    # ========================================================
    # EDIT PLAYER
    # ========================================================

    st.divider()

    st.subheader("✏️ Edit Player")

    player_options = {
        (
            f"{row['name']} "
            f"({row['nickname']})"
            if row["nickname"]
            else row["name"]
        ):
            row["id"]
        for _, row in players.iterrows()
    }

    selected_name = st.selectbox(
        "Select Player",
        list(player_options.keys())
    )

    selected_id = player_options[
        selected_name
    ]

    selected = players[
        players["id"] == selected_id
    ].iloc[0]


    with st.form("edit_player_form"):

        col1, col2 = st.columns(2)

        with col1:

            edit_name = st.text_input(
                "Player Name",
                value=selected["name"]
            )

        with col2:

            edit_nickname = st.text_input(
                "Nickname",
                value=(
                    selected["nickname"]
                    if pd.notna(
                        selected["nickname"]
                    )
                    else ""
                )
            )

        edit_handicap = st.number_input(
            "Current Handicap",
            min_value=-10.0,
            max_value=64.0,
            value=float(
                selected["current_handicap"]
            ),
            step=0.1
        )

        edit_active = st.checkbox(
            "Active Player",
            value=bool(
                selected["active"]
            )
        )

        save = st.form_submit_button(
            "💾 Save Changes",
            type="primary"
        )

        if save:

            if not edit_name.strip():

                st.error(
                    "Player name cannot be empty."
                )

            else:

                update_player(
                    selected_id,
                    edit_name,
                    edit_nickname,
                    edit_handicap,
                    edit_active
                )

                st.success(
                    "Player updated successfully."
                )

                st.rerun()
