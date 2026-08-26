import streamlit as st
import pandas as pd

from database import get_connection


st.set_page_config(
    page_title="Golfing Warriors - Events",
    page_icon="🏌️",
    layout="wide"
)


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

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


def get_courses():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                location
            FROM courses
            WHERE active = TRUE
            ORDER BY name
            """,
            connection
        )

    finally:

        connection.close()


def get_course_holes(course_id):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                hole_number,
                par,
                stroke_index
            FROM course_holes
            WHERE course_id = %s
            ORDER BY hole_number
            """,
            connection,
            params=(int(course_id),)
        )

    finally:

        connection.close()


def create_event(
    season_id,
    course_id,
    name,
    event_date,
    event_format
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # -------------------------------------------------
            # CREATE EVENT
            # -------------------------------------------------

            cursor.execute(
                """
                INSERT INTO events
                    (
                        season_id,
                        course_id,
                        name,
                        event_date,
                        format
                    )
                VALUES
                    (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    int(season_id),
                    int(course_id),
                    name.strip(),
                    event_date,
                    event_format
                )
            )

            event_id = cursor.fetchone()[0]

            # -------------------------------------------------
            # COPY COURSE HOLES INTO EVENT
            # -------------------------------------------------

            cursor.execute(
                """
                INSERT INTO event_holes
                    (
                        event_id,
                        hole_number,
                        par,
                        stroke_index
                    )
                SELECT
                    %s,
                    hole_number,
                    par,
                    stroke_index
                FROM course_holes
                WHERE course_id = %s
                ORDER BY hole_number
                """,
                (
                    int(event_id),
                    int(course_id)
                )
            )

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


def get_events():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                e.id,
                e.name,
                e.event_date,
                e.format,
                e.status,
                s.name AS season_name,
                c.name AS course_name
            FROM events e

            INNER JOIN seasons s
                ON e.season_id = s.id

            LEFT JOIN courses c
                ON e.course_id = c.id

            ORDER BY e.event_date DESC
            """,
            connection
        )

    finally:

        connection.close()


def start_event(event_id):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE events
                SET status = 'LIVE'
                WHERE id = %s
                AND status = 'DRAFT'
                """,
                (int(event_id),)
            )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# PAGE
# ============================================================

st.title("🏌️ Events")

st.caption(
    "Create and manage Golfing Warriors events."
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
# COURSES
# ============================================================

courses = get_courses()

if courses.empty:

    st.warning(
        "You need to create a golf course "
        "before creating an event."
    )

    st.info(
        "Go to the ⛳ Courses page and add "
        "your first course."
    )

    st.stop()


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
    placeholder="e.g. Golfing Warriors Event #2"
)

event_date = st.date_input(
    "Event Date"
)


# Course selection

course_options = {}

for _, course in courses.iterrows():

    label = course["name"]

    if pd.notna(course["location"]):

        label += f" — {course['location']}"

    course_options[label] = course


selected_course_label = st.selectbox(
    "Golf Course",
    list(course_options.keys())
)

selected_course = course_options[
    selected_course_label
]


event_format = st.radio(
    "Competition Format",
    [
        "IPS",
        "NET"
    ],
    horizontal=True
)


# ============================================================
# COURSE PREVIEW
# ============================================================

course_holes = get_course_holes(
    selected_course["id"]
)

if len(course_holes) != 18:

    st.error(
        "This course does not have exactly "
        "18 holes configured."
    )

    st.stop()


with st.expander(
    "⛳ View Course Hole Information"
):

    course_display = course_holes.copy()

    course_display.columns = [
        "Hole",
        "Par",
        "Stroke Index"
    ]

    st.dataframe(
        course_display,
        use_container_width=True,
        hide_index=True
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
        f" — HCP "
        f"{float(player['current_handicap']):g}"
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
    "Each group can have a maximum of four players "
    "and must have exactly one scorer."
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
            "player_id": int(player["id"]),
            "name": player["name"],
            "handicap": float(
                player["current_handicap"]
            ),
            "group_number": int(group),
            "is_scorer": bool(scorer)
        }
    )


st.divider()


# ============================================================
# EVENT HANDICAPS
# ============================================================

st.subheader("4️⃣ Event Handicaps")

st.caption(
    "These handicaps are stored specifically "
    "for this event."
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

    player["handicap"] = float(handicap)

    final_event_players.append(player)


st.divider()


# ============================================================
# VALIDATION
# ============================================================

errors = []

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
                selected_course["id"],
                event_name,
                event_date,
                event_format
            )

            add_event_players(
                event_id,
                final_event_players
            )

            st.success(
                f"Event #{event_id} created successfully!"
            )

            st.info(
                "The event is currently **DRAFT**. "
                "Review everything before starting it."
            )

            st.rerun()

        except Exception as error:

            st.error(
                "Unable to create the event."
            )

            st.exception(error)


# ============================================================
# EXISTING EVENTS
# ============================================================

st.divider()

st.subheader("📋 Existing Events")

events = get_events()

if events.empty:

    st.info(
        "No events have been created yet."
    )

else:

    for _, event in events.iterrows():

        if event["status"] == "DRAFT":

            status = "📝 DRAFT"

        elif event["status"] == "LIVE":

            status = "🟢 LIVE"

        elif event["status"] == "PENDING_CLOSE":

            status = "🏁 PENDING CLOSE"

        else:

            status = "🔒 CLOSED"


        st.markdown(
            f"### {event['name']}"
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.write(
                f"📅 {event['event_date']}"
            )

        with col2:

            st.write(
                f"⛳ {event['course_name']}"
            )

        with col3:

            st.write(
                f"🏆 {event['format']}"
            )

        with col4:

            st.write(status)


        if event["status"] == "DRAFT":

            if st.button(
                "🟢 Start Event",
                key=f"start_{event['id']}"
            ):

                start_event(
                    event["id"]
                )

                st.success(
                    "Event is now LIVE!"
                )

                st.rerun()

        st.divider()
