
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

                MIN(er.final_position) AS best_finish,

                MAX(er.final_position) AS worst_finish,

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


def get_player_current_form(
    player_id,
    limit=5
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
                er.final_position,
                er.net_total,
                er.ips_total,
                er.ranking_points

            FROM event_results er

            INNER JOIN events e
                ON er.event_id = e.id

            WHERE
                er.player_id = %s
                AND e.status = 'CLOSED'

            ORDER BY
                e.event_date DESC,
                e.id DESC

            LIMIT %s
            """,
            connection,
            params=(
                int(player_id),
                int(limit)
            )
        )

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


def get_player_season_points_history(
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
                er.final_position,
                COALESCE(
                    rp.points,
                    er.ranking_points,
                    0
                ) AS event_points

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

            ORDER BY
                e.event_date ASC,
                e.id ASC
            """,
            connection,
            params=(
                int(player_id),
                int(season_id)
            )
        )

    finally:

        connection.close()





def get_head_to_head(
    player_one_id,
    player_two_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                er1.event_id,
                e.name AS event_name,
                e.event_date,
                e.format,

                er1.final_position AS player_one_position,
                er2.final_position AS player_two_position,

                er1.net_total AS player_one_net,
                er2.net_total AS player_two_net,

                er1.ips_total AS player_one_ips,
                er2.ips_total AS player_two_ips,

                er1.ranking_points AS player_one_points,
                er2.ranking_points AS player_two_points

            FROM event_results er1

            INNER JOIN event_results er2
                ON er2.event_id = er1.event_id
                AND er2.player_id = %s

            INNER JOIN events e
                ON e.id = er1.event_id

            WHERE
                er1.player_id = %s
                AND e.status = 'CLOSED'

            ORDER BY
                e.event_date DESC,
                e.id DESC
            """,
            connection,
            params=(
                int(player_two_id),
                int(player_one_id)
            )
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
# CURRENT FORM
# ============================================================

st.divider()

st.header(
    "🔥 Current Form"
)

current_form = get_player_current_form(
    player_id,
    5
)

if current_form.empty:

    st.info(
        "No completed events yet."
    )

else:

    form_icons = []

    for _, result in current_form.iterrows():

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

        form_icons.append(icon)

    st.write(
        "  ".join(form_icons)
    )

    st.caption(
        "Most recent event first."
    )

    form_rows = []

    for _, result in current_form.iterrows():

        if result["format"] == "IPS":
            score = f"{int(result['ips_total'])} IPS"
        else:
            score = f"{int(result['net_total'])} Net"

        form_rows.append(
            {
                "Event": result["event_name"],
                "Format": result["format"],
                "Result": position_label(
                    result["final_position"]
                ),
                "Score": score,
                "Points": float(
                    result["ranking_points"]
                )
            }
        )

    form_df = pd.DataFrame(
        form_rows
    )

    st.dataframe(
        form_df,
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
# CAREER PERFORMANCE RATES
# ============================================================

st.divider()

st.header(
    "🎯 Career Performance"
)

career_stats = get_player_all_time_stats(
    player_id
)

career_events = int(
    career_stats["events_played"]
)

career_wins = int(
    career_stats["wins"]
)

career_podiums = int(
    career_stats["podiums"]
)

if career_events > 0:

    win_rate = (
        career_wins / career_events
    ) * 100

    podium_rate = (
        career_podiums / career_events
    ) * 100

    points_per_event = None

    if season_id is not None:

        ranking_history_for_pp = (
            get_player_ranking_history(
                player_id
            )
        )

        if not ranking_history_for_pp.empty:

            total_points_all_time = float(
                ranking_history_for_pp["points"].sum()
            )

            points_per_event = (
                total_points_all_time
                / career_events
            )

else:

    win_rate = None
    podium_rate = None
    points_per_event = None


rate_col1, rate_col2 = st.columns(2)

with rate_col1:

    st.metric(
        "🥇 Win Rate",
        (
            f"{win_rate:.1f}%"
            if win_rate is not None
            else "—"
        )
    )

with rate_col2:

    st.metric(
        "🥉 Podium Rate",
        (
            f"{podium_rate:.1f}%"
            if podium_rate is not None
            else "—"
        )
    )


rate_col3, rate_col4 = st.columns(2)

with rate_col3:

    st.metric(
        "📈 Points / Event",
        (
            f"{points_per_event:.1f}"
            if points_per_event is not None
            else "—"
        )
    )

with rate_col4:

    st.metric(
        "🏆 Best Finish",
        (
            position_label(
                career_stats["best_finish"]
            )
            if not pd.isna(
                career_stats["best_finish"]
            )
            else "—"
        )
    )


# ============================================================
# SEASON PERFORMANCE
# ============================================================

if season_id is not None:

    st.divider()

    st.header(
        "📈 Season Performance"
    )

    chart_data = get_player_season_points_history(
        player_id,
        season_id
    )

    if chart_data.empty:

        st.info(
            "Complete an event to start "
            "building the season graph."
        )

    else:

        chart_data = chart_data.copy()

        chart_data["Event"] = (
            chart_data["event_name"]
            .astype(str)
        )

        chart_data["Event Points"] = (
            pd.to_numeric(
                chart_data["event_points"]
            )
        )

        chart_data["Cumulative Points"] = (
            chart_data["Event Points"]
            .cumsum()
        )

        graph_df = chart_data[
            [
                "Event",
                "Cumulative Points"
            ]
        ].copy()

        graph_df = graph_df.set_index(
            "Event"
        )

        st.line_chart(
            graph_df,
            use_container_width=True
        )

        st.caption(
            "Cumulative championship points "
            "after each completed event."
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
        "Best Finish",
        (
            position_label(
                all_time["best_finish"]
            )
            if not pd.isna(
                all_time["best_finish"]
            )
            else "—"
        )
    )

    st.metric(
        "Worst Finish",
        (
            position_label(
                all_time["worst_finish"]
            )
            if not pd.isna(
                all_time["worst_finish"]
            )
            else "—"
        )
    )

    st.metric(
        "Best Net",
        format_number(
            all_time["best_net"],
            0
        )
    )

performance_col1, performance_col2 = st.columns(2)

with performance_col1:

    st.metric(
        "Average Net",
        format_number(
            all_time["average_net"],
            1
        )
    )

with performance_col2:

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
# HEAD-TO-HEAD RIVALRY
# ============================================================

st.divider()

st.header(
    "⚔️ Head-to-Head"
)

st.caption(
    "See how this golfer compares against "
    "any other Golfing Warrior."
)


other_players = players[
    players["id"] != player_id
].copy()


if other_players.empty:

    st.info(
        "Add another player to start a rivalry."
    )

else:

    opponent_labels = {}

    for _, opponent in other_players.iterrows():

        opponent_label = opponent["name"]

        if (
            pd.notna(opponent["nickname"])
            and opponent["nickname"]
        ):

            opponent_label += (
                f" ({opponent['nickname']})"
            )

        opponent_labels[
            opponent_label
        ] = opponent


    opponent_label = st.selectbox(
        "⚔️ Choose your opponent",
        list(opponent_labels.keys()),
        key=f"rivalry_opponent_{player_id}"
    )


    opponent = opponent_labels[
        opponent_label
    ]


    opponent_id = int(
        opponent["id"]
    )

    opponent_name = opponent["name"]


    rivalry = get_head_to_head(
        player_id,
        opponent_id
    )


    if rivalry.empty:

        st.info(
            f"{player_name} and {opponent_name} "
            "have not completed an event together yet."
        )

    else:

        player_wins = 0
        opponent_wins = 0
        ties = 0

        for _, row in rivalry.iterrows():

            p1_position = int(
                row["player_one_position"]
            )

            p2_position = int(
                row["player_two_position"]
            )

            if p1_position < p2_position:

                player_wins += 1

            elif p2_position < p1_position:

                opponent_wins += 1

            else:

                ties += 1


        total_battles = len(
            rivalry
        )


        # ----------------------------------------------------
        # RIVALRY SCORE
        # ----------------------------------------------------

        score_col1, score_col2, score_col3 = (
            st.columns(3)
        )


        with score_col1:

            st.metric(
                player_name,
                player_wins
            )


        with score_col2:

            st.metric(
                "🤝 Ties",
                ties
            )


        with score_col3:

            st.metric(
                opponent_name,
                opponent_wins
            )


        # ----------------------------------------------------
        # RIVALRY VERDICT
        # ----------------------------------------------------

        if player_wins > opponent_wins:

            st.success(
                f"🔥 **{player_name} leads "
                f"{player_wins}–{opponent_wins}**"
            )

        elif opponent_wins > player_wins:

            st.warning(
                f"😈 **{opponent_name} leads "
                f"{opponent_wins}–{player_wins}**"
            )

        else:

            st.info(
                f"🤝 **Dead even — "
                f"{player_wins}–{opponent_wins}**"
            )


        st.caption(
            f"{total_battles} event"
            f"{'s' if total_battles != 1 else ''} "
            "played together."
        )


        # ----------------------------------------------------
        # CURRENT STREAK
        # ----------------------------------------------------

        streak_winner = None
        streak_count = 0

        for _, row in rivalry.iterrows():

            p1_position = int(
                row["player_one_position"]
            )

            p2_position = int(
                row["player_two_position"]
            )

            if p1_position < p2_position:

                current_winner = "player"

            elif p2_position < p1_position:

                current_winner = "opponent"

            else:

                current_winner = "tie"


            if streak_winner is None:

                streak_winner = current_winner
                streak_count = 1

            elif current_winner == streak_winner:

                streak_count += 1

            else:

                break


        if streak_winner == "player":

            st.write(
                f"🔥 **Current streak:** "
                f"{player_name} "
                f"has won the last "
                f"{streak_count} battle"
                f"{'s' if streak_count != 1 else ''}."
            )

        elif streak_winner == "opponent":

            st.write(
                f"🔥 **Current streak:** "
                f"{opponent_name} "
                f"has won the last "
                f"{streak_count} battle"
                f"{'s' if streak_count != 1 else ''}."
            )

        else:

            st.write(
                "🤝 The most recent battle was a tie."
            )


        # ----------------------------------------------------
        # AVERAGE FINISH
        # ----------------------------------------------------

        avg_player_finish = (
            rivalry[
                "player_one_position"
            ].mean()
        )

        avg_opponent_finish = (
            rivalry[
                "player_two_position"
            ].mean()
        )


        avg_col1, avg_col2 = st.columns(2)


        with avg_col1:

            st.metric(
                f"{player_name} Avg Finish",
                f"{avg_player_finish:.1f}"
            )


        with avg_col2:

            st.metric(
                f"{opponent_name} Avg Finish",
                f"{avg_opponent_finish:.1f}"
            )


        # ----------------------------------------------------
        # EVENT-BY-EVENT RIVALRY
        # ----------------------------------------------------

        st.subheader(
            "📋 Rivalry History"
        )


        rivalry_rows = []


        for _, row in rivalry.iterrows():

            p1_position = int(
                row["player_one_position"]
            )

            p2_position = int(
                row["player_two_position"]
            )


            if p1_position < p2_position:

                winner = (
                    f"🏆 {player_name}"
                )

            elif p2_position < p1_position:

                winner = (
                    f"🏆 {opponent_name}"
                )

            else:

                winner = "🤝 Tie"


            if row["format"] == "IPS":

                score_text = (
                    f"{int(row['player_one_ips'])} "
                    f"vs "
                    f"{int(row['player_two_ips'])}"
                )

            else:

                score_text = (
                    f"{int(row['player_one_net'])} "
                    f"vs "
                    f"{int(row['player_two_net'])}"
                )


            rivalry_rows.append(
                {
                    "Event":
                        row["event_name"],

                    "Format":
                        row["format"],

                    player_name:
                        position_label(
                            p1_position
                        ),

                    opponent_name:
                        position_label(
                            p2_position
                        ),

                    "Score":
                        score_text,

                    "Winner":
                        winner
                }
            )


        rivalry_df = pd.DataFrame(
            rivalry_rows
        )


        st.dataframe(
            rivalry_df,
            use_container_width=True,
            hide_index=True
        )


        st.caption(
            "Rivalry results are based on each "
            "player's official final event position."
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
