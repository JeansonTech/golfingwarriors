import streamlit as st
import pandas as pd

from database import (
    init_database,
    test_connection,
    get_connection
)

from scoring.scoring_engine import (
    calculate_player_round,
    calculate_net_score,
    calculate_ips_points
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




def get_live_events():
    """List every event that is currently accepting scores or awaiting close."""
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
                c.name AS course_name
            FROM events e
            LEFT JOIN courses c
                ON c.id = e.course_id
            WHERE e.status IN ('LIVE', 'PENDING_CLOSE')
            ORDER BY e.event_date DESC, e.id DESC
            """,
            connection
        )
    finally:
        connection.close()


def get_live_event_data(event_id, main_format):
    """Load read-only scoring data for a dashboard leaderboard."""
    connection = get_connection()
    try:
        players_df = pd.read_sql_query(
            """
            SELECT ep.player_id, ep.event_handicap, p.name
            FROM event_players ep
            INNER JOIN players p ON p.id = ep.player_id
            WHERE ep.event_id = %s AND ep.status = 'ACTIVE'
            ORDER BY ep.group_number, p.name
            """,
            connection,
            params=(int(event_id),)
        )
        holes_df = pd.read_sql_query(
            """
            SELECT hole_number, par, stroke_index
            FROM event_holes
            WHERE event_id = %s
            ORDER BY hole_number
            """,
            connection,
            params=(int(event_id),)
        )
        scores_df = pd.read_sql_query(
            """
            SELECT player_id, hole_number, gross_score
            FROM hole_scores
            WHERE event_id = %s
            """,
            connection,
            params=(int(event_id),)
        )
        competition_df = pd.read_sql_query(
            """
            SELECT competition_code
            FROM event_competitions
            WHERE event_id = %s
            """,
            connection,
            params=(int(event_id),)
        )
        competitions = set(competition_df["competition_code"].astype(str))
        competitions.add(str(main_format))

        if "MATCH_PLAY" in competitions:
            match_df = pd.read_sql_query(
                """
                SELECT
                    m.match_number,
                    m.match_type,
                    s.side_number,
                    sp.player_id,
                    p.name
                FROM match_play_matches m
                INNER JOIN match_play_sides s ON s.match_id = m.id
                INNER JOIN match_play_side_players sp ON sp.side_id = s.id
                INNER JOIN players p ON p.id = sp.player_id
                WHERE m.event_id = %s
                ORDER BY m.match_number, s.side_number, p.name
                """,
                connection,
                params=(int(event_id),)
            )
        else:
            match_df = pd.DataFrame()
    finally:
        connection.close()
    return players_df, holes_df, scores_df, competitions, match_df


def build_dashboard_scoreboards(players_df, holes_df, scores_df):
    """Calculate read-only IPS and Net leaderboards from saved hole scores."""
    players = players_df.to_dict("records")
    holes = holes_df.to_dict("records")
    score_lookup = {
        (int(row["player_id"]), int(row["hole_number"])): int(row["gross_score"])
        for _, row in scores_df.iterrows()
    }

    results = []
    for player in players:
        player_id = int(player["player_id"])
        player_scores = {
            hole_number: gross
            for (score_player_id, hole_number), gross in score_lookup.items()
            if score_player_id == player_id
        }
        result = calculate_player_round(player, holes, player_scores)

        ips_to_par = 0
        net_to_par = 0
        for hole in holes:
            hole_number = int(hole["hole_number"])
            gross = player_scores.get(hole_number)
            if gross is None:
                continue
            par = int(hole["par"])
            stroke_index = int(hole["stroke_index"])
            ips_to_par += 2 - int(
                calculate_ips_points(
                    gross, par, player["event_handicap"], stroke_index
                )
            )
            net_to_par += int(
                calculate_net_score(
                    gross, player["event_handicap"], stroke_index
                )
            ) - par

        result["ips_to_par"] = ips_to_par
        result["net_to_par"] = net_to_par
        results.append(result)

    def format_to_par(value):
        return "E" if value == 0 else f"{value:+d}"

    def table_for(score_type):
        if score_type == "IPS":
            ordered = sorted(
                results,
                key=lambda item: (
                    -item["ips_total"], -item["completed"], item["name"]
                )
            )
            value_key = "ips_total"
            to_par_key = "ips_to_par"
            score_label = "IPS"
        else:
            ordered = sorted(
                results,
                key=lambda item: (
                    item["net_total"], -item["completed"], item["name"]
                )
            )
            value_key = "net_total"
            to_par_key = "net_to_par"
            score_label = "Net"

        return pd.DataFrame([
            {
                "Pos": position,
                "Player": result["name"],
                "HCP": result["handicap"],
                "Gross": result["gross_total"],
                "Thru": result["completed"],
                "To Par": format_to_par(result[to_par_key]),
                score_label: result[value_key],
            }
            for position, result in enumerate(ordered, start=1)
        ])

    return results, score_lookup, table_for


def build_dashboard_match_play(match_df, players, holes, score_lookup):
    """Calculate Match Play standings from saved scores without score controls."""
    if match_df.empty:
        return []

    player_by_id = {int(player["player_id"]): player for player in players}
    hole_rows = [
        {
            "hole_number": int(hole["hole_number"]),
            "par": int(hole["par"]),
            "stroke_index": int(hole["stroke_index"]),
        }
        for hole in holes
    ]
    output = []

    for match_number in sorted(match_df["match_number"].unique()):
        match_rows = match_df[match_df["match_number"] == match_number]
        match_type = str(match_rows.iloc[0]["match_type"]).upper()
        sides = {1: [], 2: []}
        for side_number in (1, 2):
            side_rows = match_rows[match_rows["side_number"] == side_number]
            for _, row in side_rows.iterrows():
                player_id = int(row["player_id"])
                if player_id in player_by_id:
                    sides[side_number].append(player_by_id[player_id])

        match_players = sides[1] + sides[2]
        if not match_players:
            continue
        lowest_handicap = min(float(player["event_handicap"]) for player in match_players)
        adjusted = {
            int(player["player_id"]): max(
                0.0, float(player["event_handicap"]) - lowest_handicap
            )
            for player in match_players
        }

        hole_diffs = []
        for hole in hole_rows:
            hole_number = hole["hole_number"]
            if any(
                (int(player["player_id"]), hole_number) not in score_lookup
                for player in match_players
            ):
                continue

            side_nets = {}
            for side_number in (1, 2):
                player_nets = []
                for player in sides[side_number]:
                    player_id = int(player["player_id"])
                    gross = score_lookup[(player_id, hole_number)]
                    player_nets.append(
                        calculate_net_score(
                            gross, adjusted[player_id], hole["stroke_index"]
                        )
                    )
                if player_nets:
                    side_nets[side_number] = min(player_nets)

            if 1 in side_nets and 2 in side_nets:
                hole_diffs.append(
                    1 if side_nets[1] < side_nets[2]
                    else -1 if side_nets[2] < side_nets[1]
                    else 0
                )

        match_score = sum(hole_diffs)
        holes_played = len(hole_diffs)
        holes_remaining = max(0, 18 - holes_played)
        margin = abs(match_score)
        if match_score > 0:
            score_text = f"{margin} UP"
        elif match_score < 0:
            score_text = f"{margin} DN"
        else:
            score_text = "ALL SQUARE"

        if holes_played >= 18 or margin > holes_remaining:
            if match_score > 0:
                result_text = f"Side 1 WINS {margin} & {holes_remaining}"
            elif match_score < 0:
                result_text = f"Side 2 WINS {margin} & {holes_remaining}"
            else:
                result_text = "HALVED"
        else:
            result_text = "IN PROGRESS"

        separator = " & " if match_type == "TEAMS" else ""
        output.append({
            "Match": int(match_number),
            "Type": "Teams" if match_type == "TEAMS" else "Singles",
            "Side 1": separator.join(p["name"] for p in sides[1]),
            "Score": score_text,
            "Side 2": separator.join(p["name"] for p in sides[2]),
            "Thru": holes_played,
            "Result": result_text,
        })

    return output


# ============================================================
# LEADER FORM MOBILE STYLE
# ============================================================

st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        div[data-testid="stMetricValue"] {
            font-size: 1.15rem !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: .68rem !important;
        }

        [data-testid="stDataFrame"] {
            font-size: .82rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
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
# HEADER
# ============================================================

st.title(
    "🏌️ Golfing Warriors"
)

st.subheader(
    "Your friends. Your golf. Your championship."
)


if not active_season_df.empty:

    season = active_season_df.iloc[0]

    season_id = int(
        season["id"]
    )

    season_name = season["name"]

    season_year = season["year"]

    st.markdown(
        f"## 🏆 {season_name}"
    )

else:

    season_id = None

    season_name = None

    season_year = None

    st.info(
        "No active season has been set up yet."
    )


# ============================================================
# TOP STATISTICS
# ============================================================

st.divider()

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
# CHAMPIONSHIP LEADER
# ============================================================

st.divider()

st.header(
    "🏆 Championship"
)


if leaderboard.empty:

    st.info(
        "No championship points have been "
        "awarded yet. The first event is waiting!"
    )

else:

    leader = leaderboard.iloc[0]

    leader_col1, leader_col2 = st.columns(
        [2, 1]
    )


    with leader_col1:

        st.markdown(
            f"# 🥇 {leader['name']}"
        )

        st.markdown(
            f"### {float(leader['total_points']):g} Championship Points"
        )

        st.caption(
            f"{int(leader['events_played'])} events • "
            f"{int(leader['wins'])} wins • "
            f"{int(leader['podiums'])} podiums"
        )


    with leader_col2:

        st.metric(
            "Points",
            f"{float(leader['total_points']):g}"
        )


    # --------------------------------------------------------
    # TOP 3
    # --------------------------------------------------------

    st.subheader(
        "🥇 Current Top 3"
    )


    top3 = leaderboard.head(3)


    top_rows = []


    for position, (_, row) in enumerate(
        top3.iterrows(),
        start=1
    ):

        if position == 1:

            medal = "🥇"

        elif position == 2:

            medal = "🥈"

        else:

            medal = "🥉"


        top_rows.append(
            {
                "Position":
                    f"{medal} {position}",

                "Player":
                    row["name"],

                "Points":
                    float(
                        row[
                            "total_points"
                        ]
                    ),

                "Events":
                    int(
                        row[
                            "events_played"
                        ]
                    )
            }
        )


    top3_df = pd.DataFrame(
        top_rows
    )


    st.dataframe(
        top3_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# LIVE EVENT LEADERBOARD (READ ONLY)
# ============================================================

st.divider()
st.header("📱 Live Event Leaderboard")
st.caption(
    "Read-only live standings. This section has no score-entry controls."
)

live_events = get_live_events()

if live_events.empty:
    st.info("There are no events currently in progress.")
else:
    live_event_options = {
        int(row["id"]): (
            f"{row['name']} · "
            f"{str(row['course_name']) if pd.notna(row['course_name']) else 'Course TBC'} · "
            f"{'LIVE' if row['status'] == 'LIVE' else 'PENDING CLOSE'}"
        )
        for _, row in live_events.iterrows()
    }

    event_col, refresh_col = st.columns([5, 1])
    with event_col:
        selected_live_event_id = st.selectbox(
            "Current event",
            options=list(live_event_options),
            format_func=lambda event_id: live_event_options[int(event_id)],
            key="dashboard_live_event"
        )
    with refresh_col:
        st.write("")
        if st.button("↻ Refresh", key="refresh_dashboard_live_board", use_container_width=True):
            st.rerun()

    selected_live_event = live_events[
        live_events["id"] == selected_live_event_id
    ].iloc[0]
    live_players_df, live_holes_df, live_scores_df, live_competitions, live_match_df = (
        get_live_event_data(
            selected_live_event_id,
            selected_live_event["format"]
        )
    )

    st.caption(
        f"⛳ {str(selected_live_event['course_name']) if pd.notna(selected_live_event['course_name']) else 'Course TBC'} · "
        f"Status: {selected_live_event['status']} · "
        "Use Refresh to reload the latest saved scores."
    )

    if live_players_df.empty:
        st.info("No active players are assigned to this event.")
    elif live_holes_df.empty:
        st.info("This event has no hole information available yet.")
    else:
        live_players, live_score_lookup, live_table_for = build_dashboard_scoreboards(
            live_players_df,
            live_holes_df,
            live_scores_df
        )

        leaderboard_labels = {
            "IPS": "🏆 IPS",
            "NET": "🏆 NET",
            "MATCH_PLAY": "⚔️ Match Play",
        }
        visible_live_competitions = [
            code for code in ("IPS", "NET", "MATCH_PLAY")
            if code in live_competitions
        ]
        live_tabs = st.tabs([
            leaderboard_labels[code] for code in visible_live_competitions
        ])

        for competition_code, live_tab in zip(
            visible_live_competitions,
            live_tabs
        ):
            with live_tab:
                if competition_code in ("IPS", "NET"):
                    st.dataframe(
                        live_table_for(competition_code),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Thru": st.column_config.NumberColumn(
                                "Thru",
                                format="%d"
                            )
                        }
                    )
                else:
                    match_results = build_dashboard_match_play(
                        live_match_df,
                        live_players_df.to_dict("records"),
                        live_holes_df.to_dict("records"),
                        live_score_lookup
                    )
                    if not match_results:
                        st.info("No Match Play matches are configured for this event.")
                    else:
                        st.dataframe(
                            pd.DataFrame(match_results),
                            use_container_width=True,
                            hide_index=True
                        )


# ============================================================
# NEXT EVENT / LAST EVENT
# ============================================================

st.divider()

event_col1, event_col2 = st.columns(2)


# ============================================================
# NEXT EVENT
# ============================================================

with event_col1:

    st.subheader(
        "📅 Next Event"
    )


    if next_event.empty:

        st.info(
            "No upcoming event has been scheduled yet."
        )

    else:

        upcoming = (
            next_event.iloc[0]
        )


        st.markdown(
            f"### ⛳ {upcoming['name']}"
        )


        st.write(
            f"📅 **{upcoming['event_date']}**"
        )

        st.write(
            f"🏌️ **{upcoming['course_name']}**"
        )

        st.write(
            f"🏆 **{upcoming['format']}**"
        )

        st.caption(
            f"Status: {upcoming['status']}"
        )


# ============================================================
# LAST EVENT
# ============================================================

with event_col2:

    st.subheader(
        "🏆 Last Event"
    )


    if last_event.empty:

        st.info(
            "No completed events yet."
        )

    else:

        previous = (
            last_event.iloc[0]
        )


        st.markdown(
            f"### ⛳ {previous['name']}"
        )


        st.write(
            f"📅 **{previous['event_date']}**"
        )

        st.write(
            f"🏌️ **{previous['course_name']}**"
        )

        st.write(
            f"🏆 **{previous['format']}**"
        )


        winner_df = (
            get_last_event_winner(
                int(previous["id"])
            )
        )


        if not winner_df.empty:

            winner = (
                winner_df.iloc[0]
            )


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

    st.divider()

    st.header(
        "🔥 Leader Form"
    )

    leader = leaderboard.iloc[0]

    leader_id = int(
        leader["player_id"]
    )

    recent = (
        get_recent_results(
            season_id,
            leader_id
        )
    )

    if not recent.empty:

        # --------------------------------------------------------
        # FORM SUMMARY
        # --------------------------------------------------------

        wins = int(
            (recent["final_position"] == 1).sum()
        )

        podiums = int(
            (recent["final_position"] <= 3).sum()
        )

        average_finish = (
            recent["final_position"].mean()
        )

        total_points = (
            recent["ranking_points"].fillna(0).sum()
        )

        summary1, summary2, summary3, summary4 = st.columns(4)

        with summary1:

            st.metric(
                "🏆 Wins",
                wins
            )

        with summary2:

            st.metric(
                "🥉 Podiums",
                podiums
            )

        with summary3:

            st.metric(
                "📊 Avg Finish",
                f"{average_finish:.1f}"
            )

        with summary4:

            st.metric(
                "⭐ Points",
                f"{float(total_points):g}"
            )


        st.caption(
            f"Last {len(recent)} completed events for "
            f"**{leader['name']}**"
        )


        # --------------------------------------------------------
        # RECENT RESULTS
        # --------------------------------------------------------

        result_rows = []

        for _, result in recent.iterrows():

            position = int(
                result["final_position"]
            )

            if position == 1:
                finish = "🥇 1st"

            elif position == 2:
                finish = "🥈 2nd"

            elif position == 3:
                finish = "🥉 3rd"

            elif position == 4:
                finish = "4th"

            else:
                finish = f"{position}th"

            result_rows.append(
                {
                    "Event":
                        result["event_name"],

                    "Format":
                        result["format"],

                    "Finish":
                        finish,

                    "Points":
                        f"+{float(result['ranking_points']):g}"
                }
            )


        st.dataframe(
            pd.DataFrame(result_rows),
            use_container_width=True,
            hide_index=True
        )


        # --------------------------------------------------------
        # SIMPLE VISUAL FORM
        # --------------------------------------------------------

        form_items = []

        for _, result in recent.iterrows():

            position = int(
                result["final_position"]
            )

            if position == 1:
                form_items.append("🥇")

            elif position == 2:
                form_items.append("🥈")

            elif position == 3:
                form_items.append("🥉")

            else:
                form_items.append(
                    f"**{position}**"
                )

        st.markdown(
            "### Recent form: "
            + "  ".join(form_items)
        )

        st.caption(
            "Most recent result first"
        )

    else:

        st.info(
            f"No completed championship events yet for "
            f"**{leader['name']}**."
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