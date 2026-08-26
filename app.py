import streamlit as st
import pandas as pd

from database import (
    init_database,
    test_connection,
    get_connection
)
from auth import render_admin_sidebar


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
# DASHBOARD STYLE
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1150px;
    }

    .gw-hero {
        border-radius: 18px;
        padding: 22px 20px;
        margin-bottom: 16px;
        background: rgba(128,128,128,.06);
        border: 1px solid rgba(128,128,128,.18);
    }

    .gw-hero-title {
        font-size: 2.15rem;
        font-weight: 900;
        line-height: 1.1;
        margin-bottom: 5px;
    }

    .gw-hero-subtitle {
        opacity: .72;
        font-size: 1rem;
    }

    .gw-season {
        margin-top: 14px;
        font-size: 1.15rem;
        font-weight: 800;
    }

    .gw-card {
        border: 1px solid rgba(128,128,128,.18);
        border-radius: 16px;
        padding: 16px;
        background: rgba(128,128,128,.035);
        min-height: 145px;
        margin-bottom: 12px;
    }

    .gw-card-title {
        font-size: .82rem;
        font-weight: 800;
        opacity: .70;
        text-transform: uppercase;
        letter-spacing: .03em;
    }

    .gw-card-name {
        font-size: 1.35rem;
        font-weight: 900;
        margin-top: 5px;
    }

    .gw-card-value {
        font-size: 1.9rem;
        font-weight: 900;
        margin-top: 5px;
    }

    .gw-muted {
        opacity: .68;
        font-size: .86rem;
    }

    @media (max-width: 768px) {

        .block-container {
            padding-left: .55rem;
            padding-right: .55rem;
            padding-top: .55rem;
        }

        .gw-hero {
            padding: 17px 15px;
            border-radius: 15px;
        }

        .gw-hero-title {
            font-size: 1.65rem;
        }

        .gw-hero-subtitle {
            font-size: .9rem;
        }

        .gw-card {
            padding: 13px;
            min-height: 0;
            margin-bottom: 9px;
        }

        .gw-card-name {
            font-size: 1.15rem;
        }

        .gw-card-value {
            font-size: 1.55rem;
        }

        div[data-testid="stMetric"] {
            padding: 5px 3px !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: .7rem !important;
        }

        button {
            min-height: 42px !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)


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

    👥 Players  
    📅 Seasons  
    ⛳ Courses  
    🏆 Events  
    📱 Live Scoring  
    📋 Results  
    📊 Leaderboards  
    📈 Golf Statistics  
    👤 Player Profiles  
    ⚔️ Rivalry  
    ⚙️ Ranking Settings
    """
)

# Shared admin login/logout.
render_admin_sidebar()


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
# DASHBOARD HEADER
# ============================================================

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


st.markdown(
    f"""
    <div class="gw-hero">
        <div class="gw-hero-title">
            🏌️ Golfing Warriors
        </div>
        <div class="gw-hero-subtitle">
            Your friends. Your golf. Your championship.
        </div>
        {
            f'<div class="gw-season">🏆 {season_name} {season_year}</div>'
            if season_name
            else ''
        }
    </div>
    """,
    unsafe_allow_html=True
)

if season_id is None:

    st.info(
        "No active season has been set up yet. "
        "An Admin can create one from the Seasons page."
    )


# ============================================================
# TOP STATISTICS
# ============================================================

stat1, stat2, stat3 = st.columns(3)

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
# CHAMPIONSHIP SNAPSHOT
# ============================================================

st.divider()

st.header(
    "🏆 Championship"
)

if leaderboard.empty:

    st.info(
        "No championship points have been awarded yet. "
        "The first completed event will start the championship!"
    )

else:

    leader = leaderboard.iloc[0]

    leader_col1, leader_col2 = st.columns(
        [2, 1]
    )

    with leader_col1:

        st.markdown(
            f"""
            <div class="gw-card">
                <div class="gw-card-title">
                    Current Championship Leader
                </div>
                <div class="gw-card-name">
                    🥇 {leader['name']}
                </div>
                <div class="gw-card-value">
                    {float(leader['total_points']):g} pts
                </div>
                <div class="gw-muted">
                    {int(leader['events_played'])} events
                    • {int(leader['wins'])} wins
                    • {int(leader['podiums'])} podiums
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with leader_col2:

        st.metric(
            "🏆 Championship Points",
            f"{float(leader['total_points']):g}"
        )

        st.caption(
            f"{leader['name']} is currently #1"
        )


# ============================================================
# CURRENT TOP 3
# ============================================================

if not leaderboard.empty:

    st.subheader(
        "🥇 Current Top 3"
    )

    top3 = leaderboard.head(3)

    top_rows = []

    for position, (_, row) in enumerate(
        top3.iterrows(),
        start=1
    ):

        medal = {
            1: "🥇",
            2: "🥈",
            3: "🥉"
        }.get(
            position,
            str(position)
        )

        top_rows.append(
            {
                "Position":
                    f"{medal} {position}",

                "Player":
                    row["name"],

                "Points":
                    float(
                        row["total_points"]
                    ),

                "Events":
                    int(
                        row["events_played"]
                    )
            }
        )

    st.dataframe(
        pd.DataFrame(top_rows),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# NEXT / LAST EVENT
# ============================================================

st.divider()

event_col1, event_col2 = st.columns(2)

with event_col1:

    st.subheader(
        "📅 Next Event"
    )

    if next_event.empty:

        st.info(
            "No upcoming event has been scheduled yet."
        )

    else:

        upcoming = next_event.iloc[0]

        st.markdown(
            f"""
            <div class="gw-card">
                <div class="gw-card-title">
                    Upcoming
                </div>
                <div class="gw-card-name">
                    ⛳ {upcoming['name']}
                </div>
                <div class="gw-muted">
                    📅 {upcoming['event_date']}<br>
                    🏌️ {upcoming['course_name']}<br>
                    🏆 {upcoming['format']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


with event_col2:

    st.subheader(
        "🏆 Last Event"
    )

    if last_event.empty:

        st.info(
            "No completed events yet."
        )

    else:

        previous = last_event.iloc[0]

        st.markdown(
            f"""
            <div class="gw-card">
                <div class="gw-card-title">
                    Most Recent Result
                </div>
                <div class="gw-card-name">
                    ⛳ {previous['name']}
                </div>
                <div class="gw-muted">
                    📅 {previous['event_date']}<br>
                    🏌️ {previous['course_name']}<br>
                    🏆 {previous['format']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
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
                f"won with {result_text}"
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

    leader_id = int(
        leaderboard.iloc[0]["player_id"]
    )

    recent = (
        get_recent_results(
            season_id,
            leader_id
        )
    )

    if not recent.empty:

        st.divider()

        st.header(
            "🔥 Leader Form"
        )

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
            else:
                icon = str(position)

            form_items.append(icon)

        st.markdown(
            "### " + "  ".join(form_items)
        )

        st.caption(
            f"Recent results for "
            f"**{leaderboard.iloc[0]['name']}** "
            f"(most recent first)"
        )


# ============================================================
# QUICK ACCESS
# ============================================================

st.divider()

st.header(
    "⚡ Quick Access"
)

quick1, quick2, quick3, quick4 = st.columns(4)

with quick1:

    if st.button(
        "🏆 Leaderboards",
        use_container_width=True
    ):

        st.switch_page(
            "pages/leaderboards.py"
        )

with quick2:

    if st.button(
        "📋 Results",
        use_container_width=True
    ):

        st.switch_page(
            "pages/results.py"
        )

with quick3:

    if st.button(
        "📊 Statistics",
        use_container_width=True
    ):

        st.switch_page(
            "pages/golf_statistics.py"
        )

with quick4:

    if st.button(
        "👤 Player Profiles",
        use_container_width=True
    ):

        st.switch_page(
            "pages/player_profiles.py"
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
