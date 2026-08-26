
import streamlit as st
import pandas as pd

from database import get_connection


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors - Player Profiles",
    page_icon="🏌️",
    layout="wide"
)


# ============================================================
# MOBILE-FIRST STYLING
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 2rem;
        max-width: 1150px;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.22);
        border-radius: 12px;
        padding: 11px;
        background: rgba(128,128,128,0.035);
    }

    @media (max-width: 768px) {

        .block-container {
            padding-left: 0.6rem;
            padding-right: 0.6rem;
        }

        h1 {
            font-size: 1.65rem !important;
        }

        h2 {
            font-size: 1.3rem !important;
        }

        h3 {
            font-size: 1.05rem !important;
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
# DATABASE FUNCTIONS
# ============================================================

def get_players():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                nickname,
                current_handicap,
                active

            FROM players

            ORDER BY
                active DESC,
                name ASC
            """,
            connection
        )

    finally:

        connection.close()


def get_active_season():

    connection = get_connection()

    try:

        return pd.read_sql_query(
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

    finally:

        connection.close()


def get_player_season_stats(
    player_id,
    season_id
):

    connection = get_connection()

    try:

        result = pd.read_sql_query(
            """
            SELECT
                COUNT(*) AS events_played,

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
                ) AS ranking_points,

                AVG(
                    er.final_position
                ) AS average_finish,

                MIN(
                    er.net_total
                ) AS best_net,

                AVG(
                    er.net_total
                ) AS average_net,

                MAX(
                    er.ips_total
                ) AS best_ips,

                AVG(
                    er.ips_total
                ) AS average_ips

            FROM event_results er

            INNER JOIN events e
                ON er.event_id = e.id

            LEFT JOIN ranking_points rp
                ON rp.event_id = er.event_id
                AND rp.player_id = er.player_id
                AND rp.season_id = e.season_id

            WHERE
                er.player_id = %s
                AND e.season_id = %s
                AND e.status = 'CLOSED'
            """,
            connection,
            params=(
                int(player_id),
                int(season_id)
            )
        )

        return result.iloc[0]

    finally:

        connection.close()


def get_player_season_results(
    player_id,
    season_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                e.id AS event_id,
                e.name AS event_name,
                e.event_date,
                e.format,
                c.name AS course_name,

                er.gross_total,
                er.net_total,
                er.ips_total,
                er.final_position,
                er.ranking_points

            FROM event_results er

            INNER JOIN events e
                ON er.event_id = e.id

            LEFT JOIN courses c
                ON e.course_id = c.id

            WHERE
                er.player_id = %s
                AND e.season_id = %s
                AND e.status = 'CLOSED'

            ORDER BY
                e.event_date DESC,
                e.id DESC
            """,
            connection,
            params=(
                int(player_id),
                int(season_id)
            )
        )

    finally:

        connection.close()


def get_player_all_time_stats(
    player_id
):

    connection = get_connection()

    try:

        result = pd.read_sql_query(
            """
            SELECT
                COUNT(*) AS events_played,

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

                MIN(er.net_total) AS best_net,

                AVG(er.net_total) AS average_net,

                MAX(er.ips_total) AS best_ips,

                AVG(er.ips_total) AS average_ips

            FROM event_results er

            INNER JOIN events e
                ON er.event_id = e.id

            WHERE
                er.player_id = %s
                AND e.status = 'CLOSED'
            """,
            connection,
            params=(int(player_id),)
        )

        return result.iloc[0]

    finally:

        connection.close()


def get_player_ranking_history(
    player_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                s.name AS season_name,
                s.year,
                COALESCE(
                    SUM(rp.points),
                    0
                ) AS points,

                COUNT(
                    DISTINCT rp.event_id
                ) AS events_played

            FROM ranking_points rp

            INNER JOIN seasons s
                ON rp.season_id = s.id

            INNER JOIN events e
                ON rp.event_id = e.id

            WHERE
                rp.player_id = %s
                AND e.status = 'CLOSED'

            GROUP BY
                s.id,
                s.name,
                s.year

            ORDER BY
                s.year DESC
            """,
            connection,
            params=(int(player_id),)
        )

    finally:

        connection.close()


# ============================================================
# HELPERS
# ============================================================

def format_number(value, decimals=1):

    if pd.isna(value):
        return "—"

    if decimals == 0:
        return f"{float(value):.0f}"

    return f"{float(value):.{decimals}f}"


def position_label(position):

    if pd.isna(position):
        return "—"

    position = int(position)

    if position == 1:
        return "🥇 1st"

    if position == 2:
        return "🥈 2nd"

    if position == 3:
        return "🥉 3rd"

    if position % 100 in (11, 12, 13):
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd"
        }.get(position % 10, "th")

    return f"{position}{suffix}"


# ============================================================
# LOAD DATA
# ============================================================

players = get_players()

active_season = get_active_season()


# ============================================================
# PAGE HEADER
# ============================================================

st.title(
    "🏌️ Player Profiles"
)

st.caption(
    "Golfing Warriors player history, "
    "performance and championship stats."
)


if players.empty:

    st.info(
        "No players have been created yet."
    )

    st.stop()


# ============================================================
# PLAYER SELECTOR
# ============================================================

player_labels = {}

for _, player in players.iterrows():

    label = player["name"]

    if pd.notna(player["nickname"]) and player["nickname"]:

        label += (
            f" ({player['nickname']})"
        )

    if not bool(player["active"]):

        label += " — INACTIVE"

    player_labels[label] = player


selected_label = st.selectbox(
    "🏌️ Select Player",
    list(player_labels.keys())
)


player = player_labels[
    selected_label
]


player_id = int(
    player["id"]
)


player_name = player["name"]


nickname = (
    player["nickname"]
    if pd.notna(player["nickname"])
    else ""
)


current_handicap = float(
    player["current_handicap"]
)


# ============================================================
# PLAYER HEADER
# ============================================================

st.divider()

if nickname:

    st.header(
        f"🏌️ {player_name}"
    )

    st.caption(
        f"Nickname: {nickname}"
    )

else:

    st.header(
        f"🏌️ {player_name}"
    )


profile_col1, profile_col2 = st.columns(2)


with profile_col1:

    st.metric(
        "Current Handicap",
        format_number(
            current_handicap,
            1
        )
    )


with profile_col2:

    if bool(player["active"]):

        st.metric(
            "Status",
            "ACTIVE"
        )

    else:

        st.metric(
            "Status",
            "INACTIVE"
        )


# ============================================================
# ACTIVE SEASON
# ============================================================

if active_season.empty:

    st.info(
        "There is currently no active season."
    )

    season_id = None

else:

    season = active_season.iloc[0]

    season_id = int(
        season["id"]
    )

    season_name = season["name"]

    season_year = season["year"]


# ============================================================
# CURRENT SEASON
# ============================================================

if season_id is not None:

    st.divider()

    st.header(
        f"🏆 {season_name}"
    )

    st.caption(
        f"{season_year} Championship"
    )


    stats = get_player_season_stats(
        player_id,
        season_id
    )


    events_played = int(
        stats["events_played"]
    )

    wins = int(
        stats["wins"]
    )

    podiums = int(
        stats["podiums"]
    )

    points = float(
        stats["ranking_points"]
    )


    # --------------------------------------------------------
    # CHAMPIONSHIP STATS
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "🏆 Ranking Points",
            f"{points:g}"
        )

    with col2:

        st.metric(
            "⛳ Events Played",
            events_played
        )


    col3, col4 = st.columns(2)

    with col3:

        st.metric(
            "🥇 Wins",
            wins
        )

    with col4:

        st.metric(
            "🥉 Podiums",
            podiums
        )


    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    st.subheader(
        "📊 Performance"
    )


    perf1, perf2 = st.columns(2)

    with perf1:

        st.metric(
            "Best Net",
            format_number(
                stats["best_net"],
                0
            )
        )

        st.metric(
            "Average Net",
            format_number(
                stats["average_net"],
                1
            )
        )


    with perf2:

        st.metric(
            "Best IPS",
            format_number(
                stats["best_ips"],
                0
            )
        )

        st.metric(
            "Average IPS",
            format_number(
                stats["average_ips"],
                1
            )
        )


    # --------------------------------------------------------
    # EVENT HISTORY
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "📋 Event History"
    )


    season_results = (
        get_player_season_results(
            player_id,
            season_id
        )
    )


    if season_results.empty:

        st.info(
            "This player has not completed "
            "an event in the current season."
        )

    else:

        display_rows = []


        for _, result in season_results.iterrows():

            if result["format"] == "IPS":

                score = (
                    f"{int(result['ips_total'])} IPS"
                )

            else:

                score = (
                    f"{int(result['net_total'])} Net"
                )


            display_rows.append(
                {
                    "Event":
                        result["event_name"],

                    "Date":
                        result["event_date"],

                    "Format":
                        result["format"],

                    "Course":
                        result["course_name"],

                    "Result":
                        position_label(
                            result["final_position"]
                        ),

                    "Score":
                        score,

                    "Points":
                        float(
                            result["ranking_points"]
                        )
                }
            )


        history_df = pd.DataFrame(
            display_rows
        )


        st.dataframe(
            history_df,
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
# ALL-TIME RECORD
# ============================================================

st.divider()

st.header(
    "📚 Career Record"
)


all_time = (
    get_player_all_time_stats(
        player_id
    )
)


career_col1, career_col2 = st.columns(2)


with career_col1:

    st.metric(
        "Events",
        int(
            all_time["events_played"]
        )
    )

    st.metric(
        "Wins",
        int(
            all_time["wins"]
        )
    )

    st.metric(
        "Podiums",
        int(
            all_time["podiums"]
        )
    )


with career_col2:

    st.metric(
        "Best Net",
        format_number(
            all_time["best_net"],
            0
        )
    )

    st.metric(
        "Average Net",
        format_number(
            all_time["average_net"],
            1
        )
    )

    st.metric(
        "Best IPS",
        format_number(
            all_time["best_ips"],
            0
        )
    )


st.caption(
    f"Average IPS: "
    f"{format_number(all_time['average_ips'], 1)}"
)


# ============================================================
# CHAMPIONSHIP HISTORY
# ============================================================

st.divider()

st.header(
    "🏆 Championship History"
)


ranking_history = (
    get_player_ranking_history(
        player_id
    )
)


if ranking_history.empty:

    st.info(
        "No championship history yet."
    )

else:

    history_rows = []


    for _, row in ranking_history.iterrows():

        history_rows.append(
            {
                "Season":
                    row["season_name"],

                "Year":
                    int(row["year"]),

                "Events":
                    int(row["events_played"]),

                "Points":
                    float(row["points"])
            }
        )


    ranking_history_df = pd.DataFrame(
        history_rows
    )


    st.dataframe(
        ranking_history_df,
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
# QUICK NAVIGATION
# ============================================================

st.divider()

st.subheader(
    "⚡ Quick Access"
)


nav1, nav2 = st.columns(2)


with nav1:

    if st.button(
        "🏆 Leaderboards",
        use_container_width=True
    ):

        st.switch_page(
            "pages/leaderboards.py"
        )


with nav2:

    if st.button(
        "📋 Results",
        use_container_width=True
    ):

        st.switch_page(
            "pages/results.py"
        )


st.caption(
    "🏌️ Golfing Warriors • "
    "Your friends. Your golf. Your championship."
)
