import streamlit as st
import pandas as pd

from database import get_connection


def get_active_season():

    connection = get_connection()

    try:

        result = pd.read_sql_query(
            """
            SELECT
                id,
                name,
                year
            FROM seasons
            WHERE active = TRUE
            ORDER BY year DESC
            LIMIT 1
            """,
            connection
        )

        return result

    finally:
        connection.close()


def get_active_players():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                nickname,
                current_handicap
            FROM players
            WHERE active = TRUE
            ORDER BY name
            """,
            connection
        )

    finally:
        connection.close()


def create_event(
    season_id,
    name,
    event_date,
    course,
    event_format
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO events
                    (
                        season_id,
                        name,
                        event_date,
                        course,
                        format
                    )
                VALUES
                    (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    int(season_id),
                    name.strip(),
                    event_date,
                    course.strip()
                    if course else None,
                    event_format
                )
            )

            event_id = cursor.fetchone()[0]

        connection.commit()

        return int(event_id)

    finally:
        connection.close()


def add_event_players(
    event_id,
    players
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            for player in players:

                cursor.execute(
                    """
                    INSERT INTO event_players
                        (
                            event_id,
                            player_id,
                            event_handicap,
                            group_number,
                            is_scorer
                        )
                    VALUES
                        (%s, %s, %s, %s, %s)
                    """,
                    (
                        int(event_id),
                        int(player["player_id"]),
                        float(player["handicap"]),
                        int(player["group_number"]),
                        bool(player["is_scorer"])
                    )
                )

        connection.commit()

    finally:
        connection.close()


# ============================================================
# PAGE
# ============================================================

st.title("🏌️ Events")

st.caption(
    "Create and configure Golfing Warriors events."
)

st.divider()


# ============================================================
# ACTIVE SEASON
# ============================================================

season = get_active_season()

if season.empty:

    st.warning(
        "You need to create an active season "
        "before creating an event."
    )

    st.stop()


active_season = season.iloc[0]

st.success(
    f"Active Season: "
    f"**{active_season['name']}**"
)


# ============================================================
# PLAYERS
# ============================================================

players = get_active_players()

if players.empty:

    st.warning(
        "You need at least one active player."
    )

    st.stop()


# ============================================================
# EVENT DETAILS
# ============================================================

st.subheader("1️⃣ Event Details")

event_name = st.text_input(
    "Event Name",
    placeholder="e.g. Golfing Warriors Event #1"
)

event_date = st.date_input(
    "Event Date"
)

course = st.text_input(
    "Golf Course",
    placeholder="e.g. Mokopane Golf Club"
)

event_format = st.radio(
    "Competition Format",
    [
        "IPS",
        "NET"
    ],
    horizontal=True
)


st.divider()


# ============================================================
# SELECT PLAYERS
# ============================================================

st.subheader("2️⃣ Select Players")

player_labels = {}

for _, player in players.iterrows():

    label = player["name"]

    if pd.notna(player["nickname"]):

        label += f" ({player['nickname']})"

    label += (
        f" — HCP {player['current_handicap']:g}"
    )

    player_labels[label] = player


selected_labels = st.multiselect(
    "Players participating",
    list(player_labels.keys())
)

if not selected_labels:

    st.info(
        "Select the players who will participate."
    )

    st.stop()


selected_players = [
    player_labels[label]
    for label in selected_labels
]


st.divider()


# ============================================================
# FOURBALL SETUP
# ============================================================

st.subheader("3️⃣ Create Fourballs")

st.caption(
    "Choose the group number and scorer for "
    "each player."
)

event_players = []

for index, player in enumerate(
    selected_players
):

    col1, col2, col3 = st.columns(
        [3, 1, 2]
    )

    with col1:

        st.write(
            f"**{player['name']}**"
        )

    with col2:

        group = st.number_input(
            "Group",
            min_value=1,
            max_value=50,
            value=(index // 4) + 1,
            step=1,
            key=f"group_{player['id']}"
        )

    with col3:

        scorer = st.checkbox(
            "Scorer",
            key=f"scorer_{player['id']}"
        )

    event_players.append(
        {
            "player_id": player["id"],
            "name": player["name"],
            "handicap": float(
                player["current_handicap"]
            ),
            "group_number": int(group),
            "is_scorer": scorer
        }
    )


st.divider()


# ============================================================
# EVENT HANDICAPS
# ============================================================

st.subheader("4️⃣ Event Handicaps")

st.caption(
    "These are the handicaps that will actually "
    "be used for this event. You can change them "
    "without changing the player's normal handicap."
)

final_event_players = []

for player in event_players:

    handicap = st.number_input(
        player["name"],
        min_value=-10.0,
        max_value=64.0,
        value=float(player["handicap"]),
        step=0.1,
        key=f"hcp_{player['player_id']}"
    )

    player["handicap"] = handicap

    final_event_players.append(player)


st.divider()


# ============================================================
# VALIDATION
# ============================================================

errors = []


# Check every group has a scorer

groups = {}

for player in final_event_players:

    group = player["group_number"]

    if group not in groups:

        groups[group] = []

    groups[group].append(player)


for group_number, group_players in groups.items():

    scorers = [
        player
        for player in group_players
        if player["is_scorer"]
    ]

    if len(scorers) != 1:

        errors.append(
            f"Fourball {group_number} must have "
            f"exactly ONE scorer."
        )

    if len(group_players) > 4:

        errors.append(
            f"Fourball {group_number} has more "
            f"than four players."
        )


if not event_name.strip():

    errors.append(
        "Please enter an event name."
    )


# ============================================================
# CREATE EVENT
# ============================================================

st.subheader("5️⃣ Create Event")

if errors:

    for error in errors:

        st.error(error)

else:

    st.success(
        "Event setup looks good!"
    )

    if st.button(
        "🏌️ Create Golfing Warriors Event",
        type="primary"
    ):

        try:

            event_id = create_event(
                active_season["id"],
                event_name,
                event_date,
                course,
                event_format
            )

            add_event_players(
                event_id,
                final_event_players
            )

            st.success(
                f"Event created successfully! "
                f"Event #{event_id}"
            )

            st.info(
                "The event has been created as "
                "**DRAFT**. Live scoring will be "
                "added in the next stage."
            )

        except Exception as error:

            st.error(
                "Unable to create the event."
            )

            st.exception(error)
