import streamlit as st
import pandas as pd
import os

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

    except Exception:

        connection.rollback()
        raise

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

    except Exception:

        connection.rollback()
        raise

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

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()




def revert_event_to_draft(event_id):
    """
    Return a LIVE event to DRAFT so an administrator can correct
    event setup before scoring resumes. Existing hole scores remain.
    """
    require_admin()

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE events
                SET status = 'DRAFT',
                    closed_at = NULL
                WHERE id = %s
                AND status = 'LIVE'
                """,
                (int(event_id),)
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    "Only a LIVE event can be returned to DRAFT."
                )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_event(event_id):
    """Return one event with its current course/season information."""
    connection = get_connection()

    try:
        return pd.read_sql_query(
            """
            SELECT
                e.id,
                e.season_id,
                e.course_id,
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
            WHERE e.id = %s
            """,
            connection,
            params=(int(event_id),)
        )
    finally:
        connection.close()


def get_event_players(event_id):
    """Return the player snapshots stored against an event."""
    connection = get_connection()

    try:
        return pd.read_sql_query(
            """
            SELECT
                ep.player_id,
                p.name,
                p.nickname,
                ep.event_handicap,
                ep.group_number,
                ep.is_scorer
            FROM event_players ep
            INNER JOIN players p
                ON ep.player_id = p.id
            WHERE ep.event_id = %s
            ORDER BY ep.group_number, p.name
            """,
            connection,
            params=(int(event_id),)
        )
    finally:
        connection.close()


def update_event(
    event_id,
    course_id,
    name,
    event_date,
    event_format,
    event_players
):
    """
    Update a DRAFT event.

    The event's course-hole snapshot is rebuilt and the event player
    snapshots are replaced. This function must only be used while the
    event is still DRAFT so LIVE/CLOSED scoring data cannot be changed
    accidentally.
    """
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            # -------------------------------------------------
            # Confirm the event is still editable
            # -------------------------------------------------
            cursor.execute(
                """
                SELECT status
                FROM events
                WHERE id = %s
                FOR UPDATE
                """,
                (int(event_id),)
            )

            row = cursor.fetchone()

            if row is None:
                raise ValueError("Event does not exist.")

            if row[0] != "DRAFT":
                raise ValueError(
                    "Only DRAFT events can be edited."
                )

            # -------------------------------------------------
            # Update event details
            # -------------------------------------------------
            cursor.execute(
                """
                UPDATE events
                SET
                    course_id = %s,
                    name = %s,
                    event_date = %s,
                    format = %s
                WHERE id = %s
                """,
                (
                    int(course_id),
                    name.strip(),
                    event_date,
                    event_format,
                    int(event_id)
                )
            )

            # -------------------------------------------------
            # Rebuild course-hole snapshot
            # -------------------------------------------------
            cursor.execute(
                """
                DELETE FROM event_holes
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

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

            # -------------------------------------------------
            # Replace event player snapshots
            # -------------------------------------------------
            cursor.execute(
                """
                DELETE FROM event_players
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

            for player in event_players:
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

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_event(event_id):

    """
    Permanently delete an event and all information
    belonging to that event.

    This includes:

    - Hole scores
    - Results
    - Ranking points
    - Event players
    - Event hole snapshot
    - Event itself
    """

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # -------------------------------------------------
            # DELETE HOLE SCORES
            # -------------------------------------------------

            cursor.execute(
                """
                DELETE FROM hole_scores
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

            # -------------------------------------------------
            # DELETE EVENT RESULTS
            # -------------------------------------------------

            cursor.execute(
                """
                DELETE FROM event_results
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

            # -------------------------------------------------
            # DELETE RANKING POINTS
            # -------------------------------------------------

            cursor.execute(
                """
                DELETE FROM ranking_points
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

            # -------------------------------------------------
            # DELETE EVENT PLAYERS
            # -------------------------------------------------

            cursor.execute(
                """
                DELETE FROM event_players
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

            # -------------------------------------------------
            # DELETE EVENT HOLE SNAPSHOT
            # -------------------------------------------------

            cursor.execute(
                """
                DELETE FROM event_holes
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

            # -------------------------------------------------
            # DELETE EVENT
            # -------------------------------------------------

            cursor.execute(
                """
                DELETE FROM events
                WHERE id = %s
                """,
                (int(event_id),)
            )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()



# ============================================================
# ADMIN MODE
# ============================================================

def get_admin_password():
    """
    Read the admin password from Streamlit secrets first,
    then from the Railway environment variable.
    """
    try:
        password = st.secrets.get(
            "GOLFING_WARRIORS_ADMIN_PASSWORD",
            ""
        )
    except Exception:
        password = ""

    if password:
        return password

    return os.getenv(
        "GOLFING_WARRIORS_ADMIN_PASSWORD",
        ""
    )


def render_admin_mode():
    """
    Simple session-based admin login.

    The password is never stored in this Python file.
    """

    st.sidebar.divider()
    st.sidebar.subheader("🔐 Admin")

    if st.session_state.get(
        "golfing_warriors_admin",
        False
    ):

        st.sidebar.success(
            "🟢 Admin Mode Active"
        )

        if st.sidebar.button(
            "🔓 Exit Admin Mode",
            use_container_width=True
        ):

            st.session_state[
                "golfing_warriors_admin"
            ] = False

            st.rerun()

        return True

    password = st.sidebar.text_input(
        "Admin Password",
        type="password",
        key="golfing_warriors_admin_password"
    )

    if st.sidebar.button(
        "🔐 Enter Admin Mode",
        use_container_width=True
    ):

        configured_password = get_admin_password()

        if (
            configured_password
            and password == configured_password
        ):

            st.session_state[
                "golfing_warriors_admin"
            ] = True

            st.session_state.pop(
                "golfing_warriors_admin_password",
                None
            )

            st.rerun()

        else:

            st.sidebar.error(
                "Incorrect admin password."
            )

    return False


# ============================================================
# PAGE
# ============================================================

st.title("🏌️ Events")

st.caption(
    "Create and manage Golfing Warriors events."
)

is_admin = render_admin_mode()

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


# ------------------------------------------------------------
# COURSE SELECTION
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# FORMAT
# ------------------------------------------------------------

event_format = st.radio(
    "Competition Format",
    [
        "IPS",
        "NET",
        "MATCH PLAY TEAMS",
        "MATCH PLAY SINGLES"
    ],
    horizontal=True
)

if event_format == "MATCH PLAY TEAMS":
    st.info(
        "⚔️ Match Play Teams — betterball teams of two, "
        "with both sides dropping to zero."
    )
elif event_format == "MATCH PLAY SINGLES":
    st.info(
        "⚔️ Match Play Singles — one player versus one player, "
        "with both sides dropping to zero."
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
    "for this event and can be changed without "
    "changing the player's normal handicap."
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


# ------------------------------------------------------------
# CHECK FOURBALLS
# ------------------------------------------------------------

for group_number, group_players in groups.items():

    scorers = [
        player
        for player in group_players
        if player["is_scorer"]
    ]

    # Exactly one scorer

    if len(scorers) != 1:

        errors.append(
            f"Fourball {group_number} must have "
            f"exactly ONE scorer."
        )

    # Maximum four players

    if len(group_players) > 4:

        errors.append(
            f"Fourball {group_number} has more "
            f"than four players."
        )


# ------------------------------------------------------------
# EVENT NAME
# ------------------------------------------------------------

if not event_name.strip():

    errors.append(
        "Please enter an event name."
    )


# ============================================================
# EVENT SUMMARY
# ============================================================

st.subheader("5️⃣ Event Summary")

summary_col1, summary_col2, summary_col3 = st.columns(3)

with summary_col1:

    st.metric(
        "Players",
        len(final_event_players)
    )

with summary_col2:

    st.metric(
        "Fourballs",
        len(groups)
    )

with summary_col3:

    st.metric(
        "Format",
        event_format
    )


# ============================================================
# SHOW FOURBALL SUMMARY
# ============================================================

with st.expander(
    "👥 Review Fourball Groups",
    expanded=True
):

    for group_number in sorted(groups):

        group_players = groups[group_number]

        scorer_names = [
            player["name"]
            for player in group_players
            if player["is_scorer"]
        ]

        scorer_name = (
            scorer_names[0]
            if len(scorer_names) == 1
            else "⚠️ Invalid scorer setup"
        )

        st.markdown(
            f"### Fourball {group_number}"
        )

        for player in group_players:

            scorer_label = (
                " 📝 **SCORER**"
                if player["is_scorer"]
                else ""
            )

            st.write(
                f"- {player['name']} "
                f"— HCP {player['handicap']:g}"
                f"{scorer_label}"
            )

        if len(scorer_names) == 1:

            st.success(
                f"Scorer: {scorer_name}"
            )

        else:

            st.error(
                "This fourball must have exactly "
                "one scorer."
            )


# ============================================================
# CREATE EVENT
# ============================================================

st.divider()

st.subheader("6️⃣ Create Event")

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

            # Create event and copy course snapshot

            event_id = create_event(
                active_season["id"],
                selected_course["id"],
                event_name,
                event_date,
                event_format
            )

            # Add participating players

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

        event_id = int(event["id"])

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if event["status"] == "DRAFT":
            status = "📝 DRAFT"
        elif event["status"] == "LIVE":
            status = "🟢 LIVE"
        elif event["status"] == "PENDING_CLOSE":
            status = "🏁 PENDING CLOSE"
        else:
            status = "🔒 CLOSED"

        # ----------------------------------------------------
        # EVENT HEADER
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # DRAFT EVENT CONTROLS
        # ----------------------------------------------------

        if event["status"] == "DRAFT":

            control_col1, control_col2, control_col3 = st.columns(3)

            # ------------------------------------------------
            # EDIT EVENT
            # ------------------------------------------------

            with control_col1:

                if st.button(
                    "✏️ Edit Event",
                    key=f"edit_{event_id}",
                    use_container_width=True
                ):
                    st.session_state[
                        f"edit_event_{event_id}"
                    ] = True

            # ------------------------------------------------
            # START EVENT
            # ------------------------------------------------

            with control_col2:

                if st.button(
                    "🟢 Start Event",
                    key=f"start_{event_id}",
                    use_container_width=True
                ):

                    try:

                        start_event(event_id)

                        st.success(
                            "Event is now LIVE!"
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            "Unable to start event."
                        )

                        st.exception(error)

            # ------------------------------------------------
            # DELETE EVENT
            # ------------------------------------------------

            with control_col3:

                if st.button(
                    "🗑️ Delete Event",
                    key=f"delete_{event_id}",
                    use_container_width=True
                ):

                    st.session_state[
                        f"confirm_delete_{event_id}"
                    ] = True

            # ------------------------------------------------
            # EDIT FORM
            # ------------------------------------------------

            if st.session_state.get(
                f"edit_event_{event_id}",
                False
            ):

                st.markdown("---")
                st.subheader(
                    f"✏️ Edit: {event['name']}"
                )

                current_event_df = get_event(event_id)
                current_players_df = get_event_players(event_id)

                if current_event_df.empty:

                    st.error(
                        "This event could not be loaded."
                    )

                else:

                    current_event = current_event_df.iloc[0]

                    edit_name = st.text_input(
                        "Event Name",
                        value=str(current_event["name"]),
                        key=f"edit_name_{event_id}"
                    )

                    edit_date = st.date_input(
                        "Event Date",
                        value=pd.to_datetime(
                            current_event["event_date"]
                        ).date(),
                        key=f"edit_date_{event_id}"
                    )

                    edit_course_options = {}

                    for _, course in courses.iterrows():

                        label = course["name"]

                        if pd.notna(course["location"]):
                            label += (
                                f" — {course['location']}"
                            )

                        edit_course_options[label] = course

                    current_course_id = int(
                        current_event["course_id"]
                    )

                    current_course_label = next(
                        (
                            label
                            for label, course in
                            edit_course_options.items()
                            if int(course["id"]) == current_course_id
                        ),
                        list(edit_course_options.keys())[0]
                    )

                    edit_course_label = st.selectbox(
                        "Golf Course",
                        list(edit_course_options.keys()),
                        index=list(
                            edit_course_options.keys()
                        ).index(current_course_label),
                        key=f"edit_course_{event_id}"
                    )

                    edit_course = edit_course_options[
                        edit_course_label
                    ]

                    format_options = [
                        "IPS",
                        "NET",
                        "MATCH PLAY TEAMS",
                        "MATCH PLAY SINGLES"
                    ]

                    current_format = str(
                        current_event["format"]
                    )

                    edit_format = st.radio(
                        "Competition Format",
                        format_options,
                        index=(
                            format_options.index(
                                current_format
                            )
                            if current_format in format_options
                            else 0
                        ),
                        horizontal=True,
                        key=f"edit_format_{event_id}"
                    )

                    st.caption(
                        "Player handicaps below are the event "
                        "snapshots. Changing them here does not "
                        "change the player's normal handicap."
                    )

                    # --------------------------------------------
                    # PLAYER SNAPSHOTS
                    # --------------------------------------------

                    edit_event_players = []

                    if current_players_df.empty:

                        st.warning(
                            "No players are currently assigned "
                            "to this event."
                        )

                    else:

                        for player_index, player in current_players_df.iterrows():

                            player_id = int(
                                player["player_id"]
                            )

                            pcol1, pcol2, pcol3 = st.columns(
                                [3, 1, 2]
                            )

                            with pcol1:
                                st.write(
                                    f"**{player['name']}**"
                                )

                            with pcol2:
                                edit_group = st.number_input(
                                    "Group",
                                    min_value=1,
                                    max_value=50,
                                    value=int(
                                        player["group_number"]
                                    ),
                                    step=1,
                                    key=(
                                        f"edit_group_"
                                        f"{event_id}_{player_id}"
                                    )
                                )

                            with pcol3:
                                edit_scorer = st.checkbox(
                                    "Scorer",
                                    value=bool(
                                        player["is_scorer"]
                                    ),
                                    key=(
                                        f"edit_scorer_"
                                        f"{event_id}_{player_id}"
                                    )
                                )

                            edit_handicap = st.number_input(
                                f"Handicap — {player['name']}",
                                min_value=-10.0,
                                max_value=64.0,
                                value=float(
                                    player["event_handicap"]
                                ),
                                step=0.1,
                                key=(
                                    f"edit_hcp_"
                                    f"{event_id}_{player_id}"
                                )
                            )

                            edit_event_players.append(
                                {
                                    "player_id": player_id,
                                    "name": player["name"],
                                    "handicap": float(
                                        edit_handicap
                                    ),
                                    "group_number": int(
                                        edit_group
                                    ),
                                    "is_scorer": bool(
                                        edit_scorer
                                    )
                                }
                            )

                    # --------------------------------------------
                    # VALIDATE EDIT
                    # --------------------------------------------

                    edit_errors = []

                    edit_groups = {}

                    for player in edit_event_players:

                        group_number = (
                            player["group_number"]
                        )

                        edit_groups.setdefault(
                            group_number,
                            []
                        ).append(player)

                    for group_number, group_players in edit_groups.items():

                        scorer_count = sum(
                            1
                            for player in group_players
                            if player["is_scorer"]
                        )

                        if scorer_count != 1:
                            edit_errors.append(
                                f"Fourball {group_number} "
                                f"must have exactly ONE scorer."
                            )

                        if len(group_players) > 4:
                            edit_errors.append(
                                f"Fourball {group_number} "
                                f"has more than four players."
                            )

                    if not edit_name.strip():
                        edit_errors.append(
                            "Event name cannot be empty."
                        )

                    # --------------------------------------------
                    # SAVE / CANCEL
                    # --------------------------------------------

                    save_col, cancel_col = st.columns(2)

                    with save_col:

                        if edit_errors:

                            for error in edit_errors:
                                st.error(error)

                        if st.button(
                            "💾 Save Event Changes",
                            type="primary",
                            key=f"save_edit_{event_id}",
                            use_container_width=True,
                            disabled=bool(edit_errors)
                        ):

                            try:

                                update_event(
                                    event_id,
                                    int(edit_course["id"]),
                                    edit_name,
                                    edit_date,
                                    edit_format,
                                    edit_event_players
                                )

                                st.session_state.pop(
                                    f"edit_event_{event_id}",
                                    None
                                )

                                st.success(
                                    "Event updated successfully."
                                )

                                st.rerun()

                            except Exception as error:

                                st.error(
                                    "Unable to update the event."
                                )

                                st.exception(error)

                    with cancel_col:

                        if st.button(
                            "Cancel Edit",
                            key=f"cancel_edit_{event_id}",
                            use_container_width=True
                        ):

                            st.session_state.pop(
                                f"edit_event_{event_id}",
                                None
                            )

                            st.rerun()

            # ------------------------------------------------
            # DELETE CONFIRMATION
            # ------------------------------------------------

            if st.session_state.get(
                f"confirm_delete_{event_id}",
                False
            ):

                st.error(
                    "⚠️ Are you absolutely sure?"
                )

                st.warning(
                    "Deleting this event will permanently "
                    "remove the event, players, course snapshot, "
                    "scores, results and ranking points. "
                    "This cannot be undone."
                )

                confirm_col1, confirm_col2 = st.columns(2)

                with confirm_col1:

                    if st.button(
                        "YES — DELETE PERMANENTLY",
                        key=f"confirm_yes_{event_id}",
                        type="primary",
                        use_container_width=True
                    ):

                        try:

                            delete_event(event_id)

                            st.session_state.pop(
                                f"confirm_delete_{event_id}",
                                None
                            )

                            st.success(
                                "Event permanently deleted."
                            )

                            st.rerun()

                        except Exception as error:

                            st.error(
                                "Unable to delete event."
                            )

                            st.exception(error)

                with confirm_col2:

                    if st.button(
                        "Cancel",
                        key=f"confirm_no_{event_id}",
                        use_container_width=True
                    ):

                        st.session_state.pop(
                            f"confirm_delete_{event_id}",
                            None
                        )

                        st.rerun()

        # ----------------------------------------------------
        # LIVE EVENT
        # ----------------------------------------------------

        elif event["status"] == "LIVE":

            st.info(
                "🟢 This event is currently LIVE. "
                "Event setup is locked while scoring is active."
            )

            if is_admin:
                rollback_key = (
                    f"confirm_revert_draft_{event_id}"
                )

                if not st.session_state.get(
                    rollback_key,
                    False
                ):
                    if st.button(
                        "↩️ Return Event to DRAFT",
                        key=f"revert_draft_{event_id}",
                        use_container_width=True
                    ):
                        st.session_state[
                            rollback_key
                        ] = True
                        st.rerun()

                else:
                    st.warning(
                        "⚠️ Return this LIVE event to DRAFT?"
                    )

                    st.caption(
                        "Existing hole scores will be preserved. "
                        "The event will disappear from Live Scoring "
                        "until you start it again."
                    )

                    yes_col, no_col = st.columns(2)

                    with yes_col:
                        if st.button(
                            "YES — RETURN TO DRAFT",
                            key=f"revert_yes_{event_id}",
                            type="primary",
                            use_container_width=True
                        ):
                            try:
                                revert_event_to_draft(event_id)

                                st.session_state.pop(
                                    rollback_key,
                                    None
                                )

                                st.success(
                                    "Event returned to DRAFT. "
                                    "You can now correct the setup."
                                )

                                st.rerun()

                            except Exception as error:
                                st.error(
                                    "Unable to return event to DRAFT."
                                )
                                st.exception(error)

                    with no_col:
                        if st.button(
                            "Cancel",
                            key=f"revert_no_{event_id}",
                            use_container_width=True
                        ):
                            st.session_state.pop(
                                rollback_key,
                                None
                            )
                            st.rerun()

        # ----------------------------------------------------
        # PENDING CLOSE
        # ----------------------------------------------------

        elif event["status"] == "PENDING_CLOSE":

            st.warning(
                "🏁 This event is pending close. "
                "Event setup is locked."
            )

        # ----------------------------------------------------
        # CLOSED EVENT
        # ----------------------------------------------------

        elif event["status"] == "CLOSED":

            st.success(
                "🔒 This event is CLOSED. "
                "Results are locked."
            )

            if is_admin:

                st.warning(
                    "🔐 Admin Mode: You can permanently "
                    "delete this closed event."
                )

                confirm_key = (
                    f"admin_confirm_delete_{event_id}"
                )

                if not st.session_state.get(
                    confirm_key,
                    False
                ):

                    if st.button(
                        "🗑️ Admin — Delete Closed Event",
                        key=f"admin_delete_{event_id}",
                        use_container_width=True
                    ):

                        st.session_state[
                            confirm_key
                        ] = True

                        st.rerun()

                else:

                    st.error(
                        "🚨 ADMIN CONFIRMATION REQUIRED"
                    )

                    st.warning(
                        "This permanently deletes the CLOSED "
                        "event, its scores, results, ranking "
                        "points, event players and hole snapshot. "
                        "This cannot be undone."
                    )

                    st.write(
                        f"**Event:** {event['name']}"
                    )

                    yes_col, no_col = st.columns(2)

                    with yes_col:

                        if st.button(
                            "🚨 DELETE CLOSED EVENT",
                            key=f"admin_confirm_yes_{event_id}",
                            type="primary",
                            use_container_width=True
                        ):

                            try:

                                delete_event(event_id)

                                st.session_state.pop(
                                    confirm_key,
                                    None
                                )

                                st.success(
                                    "Closed event permanently deleted."
                                )

                                st.rerun()

                            except Exception as error:

                                st.error(
                                    "Unable to delete closed event."
                                )

                                st.exception(error)

                    with no_col:

                        if st.button(
                            "Cancel",
                            key=f"admin_confirm_no_{event_id}",
                            use_container_width=True
                        ):

                            st.session_state.pop(
                                confirm_key,
                                None
                            )

                            st.rerun()

            else:

                st.caption(
                    "🔐 Admin access is required to delete "
                    "a closed event."
                )

        st.divider()

