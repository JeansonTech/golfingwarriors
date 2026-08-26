import streamlit as st
import pandas as pd


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
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# MOBILE / DESKTOP STYLING
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.22);
        border-radius: 12px;
        padding: 12px;
        background: rgba(128,128,128,0.035);
    }

    div.stButton > button {
        min-height: 48px;
        border-radius: 10px;
        font-weight: 700;
    }

    @media (max-width: 768px) {

        .block-container {
            padding-left: 0.65rem;
            padding-right: 0.65rem;
            padding-top: 0.65rem;
        }

        h1 {
            font-size: 1.75rem !important;
        }

        h2 {
            font-size: 1.35rem !important;
        }

        h3 {
            font-size: 1.1rem !important;
        }

        div[data-testid="stMetric"] {
            padding: 9px;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.35rem;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.75rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DATABASE INITIALISATION
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
# DATABASE FUNCTIONS
# ============================================================

def get_active_player_count():

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


def get_total_event_count():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM events
                WHERE status <> 'DELETED'
                """
            )

            return cursor.fetchone()[0]

    finally:

        connection.close()


def get_closed_event_count():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM events
                WHERE status = 'CLOSED'
                """
            )

            return cursor.fetchone()[0]

    finally:

        connection.close()


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


def get_championship_leaderboard(
    season_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                p.id AS player_id,
                p.name,

                COUNT(
                    DISTINCT rp.event_id
                ) AS events_played,

                COUNT(
                    CASE
                        WHEN er.final_position = 1
                        THEN 1
                    END
                ) AS wins,

                COUNT(
                    CASE
                        WHEN er.final_position <= 3
                        THEN 1
                    END
                ) AS podiums,

                COALESCE(
                    SUM(rp.points),
                    0
                ) AS total_points

            FROM ranking_points rp

            INNER JOIN players p
                ON rp.player_id = p.id

            INNER JOIN events e
                ON rp.event_id = e.id

            LEFT JOIN event_results er
                ON er.event_id = rp.event_id
                AND er.player_id = rp.player_id

            WHERE
                rp.season_id = %s
                AND e.status = 'CLOSED'

            GROUP BY
                p.id,
                p.name

            ORDER BY
                total_points DESC,
                wins DESC,
                podiums DESC,
                p.name ASC
            """,
            connection,
            params=(int(season_id),)
        )

    finally:

        connection.close()


def get_next_event(
    season_id
):

    connection = get_connection()

    try:

        result = pd.read_sql_query(
            """
            SELECT
                e.id,
                e.name,
                e.event_date,
                e.format,
                e.status,

                c.name AS course_name

            FROM events e

            LEFT JOIN courses c
                ON e.course_id = c.id

            WHERE
                e.season_id = %s
                AND e.status NOT IN (
                    'CLOSED',
                    'DELETED'
                )
                AND e.event_date >= CURRENT_DATE

            ORDER BY
                e.event_date ASC,
                e.id ASC

            LIMIT 1
            """,
            connection,
            params=(int(season_id),)
        )

        return result

    finally:

        connection.close()


def get_last_event(
    season_id
):

    connection = get_connection()

    try:

        result = pd.read_sql_query(
            """
            SELECT
                e.id,
                e.name,
                e.event_date,
                e.format,

                c.name AS course_name

            FROM events e

            LEFT JOIN courses c
                ON e.course_id = c.id

            WHERE
                e.season_id = %s
                AND e.status = 'CLOSED'

            ORDER BY
                e.event_date DESC,
                e.id DESC

            LIMIT 1
            """,
            connection,
            params=(int(season_id),)
        )

        return result

    finally:

        connection.close()


def get_recent_results(
    season_id,
    player_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                e.name AS event_name,
                e.format,
                er.final_position,
                er.ranking_points

            FROM event_results er

            INNER JOIN events e
                ON er.event_id = e.id

            WHERE
                e.season_id = %s
                AND er.player_id = %s
                AND e.status = 'CLOSED'

            ORDER BY
                e.event_date DESC,
                e.id DESC

            LIMIT 5
            """,
            connection,
            params=(
                int(season_id),
                int(player_id)
            )
        )

    finally:

        connection.close()


def get_last_event_winner(
    event_id
):

    connection = get_connection()

    try:

        result = pd.read_sql_query(
            """
            SELECT
                p.name,
                er.final_position,
                er.net_total,
                er.ips_total,
                er.ranking_points

            FROM event_results er

            INNER JOIN players p
                ON er.player_id = p.id

            WHERE
                er.event_id = %s
                AND er.final_position = 1

            LIMIT 1
            """,
            connection,
            params=(int(event_id),)
        )

        return result

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

st.sidebar.divider()

st.sidebar.markdown(
    """
    ### Quick Navigation

    🏠 **Dashboard**

    Use the pages below for:

    👥 Players  
    📅 Seasons  
    ⛳ Courses  
    🏆 Events  
    📱 Live Scoring  
    📋 Results  
    📊 Leaderboards  
    ⚙️ Ranking Settings
    """
)


# ============================================================
# BASIC STATISTICS
# ============================================================

active_players = (
    get_active_player_count()
)

total_events = (
    get_total_event_count()
)

closed_events = (
    get_closed_event_count()
)


# ============================================================
# ACTIVE SEASON
# ============================================================

active_season_df = (
    get_active_season()
)


# ============================================================
# MAIN HEADER
# ============================================================

st.title(
    "🏌️ Golfing Warriors"
)

st.caption(
    "Your friends. Your golf. Your championship."
)


if not active_season_df.empty:

    season = active_season_df.iloc[0]

    season_id = int(
        season["id"]
    )

    season_name = season["name"]

    season_year = season["year"]

else:

    season_id = None

    season_name = None

    season_year = None


# ============================================================
# SEASON HEADER
# ============================================================

if season_id is not None:

    st.subheader(
        f"🏆 {season_name}"
    )

    st.caption(
        f"{season_year} Championship"
    )

else:

    st.info(
        "No active season has been set up yet."
    )


# ============================================================
# TOP STATISTICS
# ============================================================

st.divider()

stat1, stat2 = st.columns(2)


with stat1:

    st.metric(
        "👥 Active Players",
        active_players
    )


with stat2:

    st.metric(
        "🏆 Events Completed",
        closed_events
    )


stat3, stat4 = st.columns(2)


with stat3:

    st.metric(
        "📅 Total Events",
        total_events
    )


# ============================================================
# CHAMPIONSHIP DATA
# ============================================================

if season_id is not None:

    leaderboard = (
        get_championship_leaderboard(
            season_id
        )
    )

    next_event = (
        get_next_event(
            season_id
        )
    )

    last_event = (
        get_last_event(
            season_id
        )
    )

else:

    leaderboard = pd.DataFrame()

    next_event = pd.DataFrame()

    last_event = pd.DataFrame()


# ============================================================
# CHAMPIONSHIP
# ============================================================

st.divider()

st.header(
    "🏆 Championship"
)


if leaderboard.empty:

    st.info(
        "No championship points have been "
        "awarded yet."
    )

else:

    leader = leaderboard.iloc[0]

    leader_name = leader["name"]

    leader_points = float(
        leader["total_points"]
    )

    leader_events = int(
        leader["events_played"]
    )

    leader_wins = int(
        leader["wins"]
    )

    leader_podiums = int(
        leader["podiums"]
    )


    # --------------------------------------------------------
    # CURRENT LEADER
    # --------------------------------------------------------

    st.success(
        f"🥇 **Current Leader: {leader_name}**"
    )


    leader_col1, leader_col2, leader_col3 = (
        st.columns(3)
    )


    with leader_col1:

        st.metric(
            "Championship Points",
            f"{leader_points:g}"
        )


    with leader_col2:

        st.metric(
            "Wins",
            leader_wins
        )


    with leader_col3:

        st.metric(
            "Podiums",
            leader_podiums
        )


    st.caption(
        f"{leader_events} event"
        f"{'s' if leader_events != 1 else ''} played"
    )


    # --------------------------------------------------------
    # TOP 5
    # --------------------------------------------------------

    st.subheader(
        "🥇 Championship Top 5"
    )


    top5 = leaderboard.head(5)


    top_rows = []


    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }


    for position, (_, row) in enumerate(
        top5.iterrows(),
        start=1
    ):

        if position in medals:

            display_position = (
                f"{medals[position]} "
                f"{position}"
            )

        else:

            display_position = (
                f"{position}"
            )


        top_rows.append(
            {
                "Pos":
                    display_position,

                "Player":
                    row["name"],

                "Points":
                    float(
                        row["total_points"]
                    ),

                "Events":
                    int(
                        row["events_played"]
                    ),

                "Wins":
                    int(
                        row["wins"]
                    )
            }
        )


    top5_df = pd.DataFrame(
        top_rows
    )


    st.dataframe(
        top5_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Points":
                st.column_config.NumberColumn(
                    "Points",
                    format="%.0f"
                ),

            "Events":
                st.column_config.NumberColumn(
                    "Events",
                    format="%d"
                ),

            "Wins":
                st.column_config.NumberColumn(
                    "Wins",
                    format="%d"
                )
        }
    )


# ============================================================
# NEXT EVENT
# ============================================================

st.divider()

st.header(
    "📅 What's Next?"
)


if next_event.empty:

    st.info(
        "No upcoming event has been scheduled yet."
    )

else:

    upcoming = next_event.iloc[0]


    st.subheader(
        f"⛳ {upcoming['name']}"
    )


    next_col1, next_col2 = st.columns(2)


    with next_col1:

        st.write(
            f"📅 **{upcoming['event_date']}**"
        )

        st.write(
            f"⛳ **{upcoming['course_name']}**"
        )


    with next_col2:

        st.write(
            f"🏆 **{upcoming['format']}**"
        )

        st.write(
            f"🟢 **{upcoming['status']}**"
        )


# ============================================================
# LAST EVENT
# ============================================================

st.divider()

st.header(
    "🏆 Last Battle"
)


if last_event.empty:

    st.info(
        "No completed events yet."
    )

else:

    previous = last_event.iloc[0]


    st.subheader(
        f"⛳ {previous['name']}"
    )


    last_col1, last_col2 = st.columns(2)


    with last_col1:

        st.write(
            f"📅 **{previous['event_date']}**"
        )

        st.write(
            f"⛳ **{previous['course_name']}**"
        )


    with last_col2:

        st.write(
            f"🏆 **{previous['format']}**"
        )


    winner_df = (
        get_last_event_winner(
            int(previous["id"])
        )
    )


    if not winner_df.empty:

        winner = winner_df.iloc[0]


        if previous["format"] == "IPS":

            result_text = (
                f"{int(winner['ips_total'])} IPS"
            )

        else:

            result_text = (
                f"{int(winner['net_total'])} Net"
            )


        st.success(
            f"🥇 **{winner['name']}** "
            f"won with **{result_text}**"
        )


        st.caption(
            f"+{float(winner['ranking_points']):g} "
            f"Championship Points"
        )


# ============================================================
# LEADER FORM
# ============================================================

if (
    season_id is not None
    and not leaderboard.empty
):

    st.divider()

    st.header(
        "🔥 Leader Form"
    )


    leader_id = int(
        leaderboard.iloc[0]["player_id"]
    )


    leader_name = (
        leaderboard.iloc[0]["name"]
    )


    recent = (
        get_recent_results(
            season_id,
            leader_id
        )
    )


    if not recent.empty:

        form_items = []


        for _, result in recent.iterrows():

            position = int(
                result["final_position"]
            )


            if position == 1:

                icon = "🥇"

            elif position == 2:

                icon = "🥈"

            elif position == 3:

                icon = "🥉"

            elif position <= 10:

                icon = f"{position}"

            else:

                icon = "•"


            form_items.append(
                icon
            )


        st.write(
            "  ".join(form_items)
        )


        st.caption(
            f"Recent results for "
            f"**{leader_name}** "
            f"— most recent first"
        )


        recent_display = []


        for _, result in recent.iterrows():

            recent_display.append(
                {
                    "Event":
                        result["event_name"],

                    "Format":
                        result["format"],

                    "Position":
                        int(
                            result["final_position"]
                        ),

                    "Points":
                        float(
                            result["ranking_points"]
                        )
                }
            )


        recent_df = pd.DataFrame(
            recent_display
        )


        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Points":
                    st.column_config.NumberColumn(
                        "Points",
                        format="%.0f"
                    )
            }
        )


# ============================================================
# QUICK ACCESS
# ============================================================

st.divider()

st.header(
    "⚡ Quick Access"
)


quick1, quick2 = st.columns(2)


with quick1:

    if st.button(
        "📱 Live Scoring",
        use_container_width=True
    ):

        st.switch_page(
            "pages/live_scoring.py"
        )


with quick2:

    if st.button(
        "🏆 Leaderboards",
        use_container_width=True
    ):

        st.switch_page(
            "pages/leaderboards.py"
        )


quick3, quick4 = st.columns(2)


with quick3:

    if st.button(
        "📋 Results",
        use_container_width=True
    ):

        st.switch_page(
            "pages/results.py"
        )


with quick4:

    if st.button(
        "👥 Players",
        use_container_width=True
    ):

        st.switch_page(
            "pages/players.py"
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🏌️ Golfing Warriors • "
    "Your friends. Your golf. Your championship."
)

st.caption(
    "Golfing Warriors V1"
)
