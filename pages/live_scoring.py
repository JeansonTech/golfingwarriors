import streamlit as st
import pandas as pd

from database import get_connection

from scoring.scoring_engine import (
    calculate_player_round,
    calculate_net_score,
    calculate_ips_points,
    rank_completed_players,
    allocate_ranking_points
)


st.set_page_config(
    page_title="Golfing Warriors - Live Scoring",
    page_icon="📱",
    layout="wide"
)


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_live_events():

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
                ON e.course_id = c.id

            WHERE e.status IN (
                'LIVE',
                'PENDING_CLOSE'
            )

            ORDER BY e.event_date DESC
            """,
            connection
        )

    finally:

        connection.close()


def get_event(event_id):

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

            WHERE e.id = %s
            """,
            connection,
            params=(int(event_id),)
        )

        return result

    finally:

        connection.close()


def get_event_players(event_id):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                ep.player_id,
                ep.event_handicap,
                ep.group_number,
                ep.is_scorer,
                p.name,
                p.nickname
            FROM event_players ep

            INNER JOIN players p
                ON ep.player_id = p.id

            WHERE ep.event_id = %s

            ORDER BY
                ep.group_number,
                p.name
            """,
            connection,
            params=(int(event_id),)
        )

    finally:

        connection.close()


def get_event_holes(event_id):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                hole_number,
                par,
                stroke_index
            FROM event_holes
            WHERE event_id = %s
            ORDER BY hole_number
            """,
            connection,
            params=(int(event_id),)
        )

    finally:

        connection.close()


def get_scores(event_id):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                player_id,
                hole_number,
                gross_score
            FROM hole_scores
            WHERE event_id = %s
            ORDER BY
                player_id,
                hole_number
            """,
            connection,
            params=(int(event_id),)
        )

    finally:

        connection.close()


# ============================================================
# SAVE HOLE SCORES
# ============================================================

def save_hole_scores(
    event_id,
    scorer_id,
    hole_number,
    scores
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            for player_id, gross_score in scores.items():

                cursor.execute(
                    """
                    INSERT INTO hole_scores
                        (
                            event_id,
                            player_id,
                            hole_number,
                            gross_score,
                            recorded_by_player_id
                        )
                    VALUES
                        (%s, %s, %s, %s, %s)

                    ON CONFLICT (
                        event_id,
                        player_id,
                        hole_number
                    )

                    DO UPDATE SET
                        gross_score =
                            EXCLUDED.gross_score,

                        recorded_by_player_id =
                            EXCLUDED.recorded_by_player_id,

                        updated_at =
                            CURRENT_TIMESTAMP
                    """,
                    (
                        int(event_id),
                        int(player_id),
                        int(hole_number),
                        int(gross_score),
                        int(scorer_id)
                    )
                )

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# ============================================================
# FINALIZE EVENT
# ============================================================

def finalize_event(
    event_id,
    event_format,
    players,
    holes,
    score_dicts
):

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # CALCULATE ALL PLAYERS
        # ----------------------------------------------------

        round_results = []

        for player in players:

            result = calculate_player_round(
                player,
                holes,
                score_dicts[
                    player["player_id"]
                ]
            )

            if result["completed"] != 18:

                raise ValueError(
                    f"{result['name']} has not "
                    f"completed all 18 holes."
                )

            round_results.append(
                result
            )

        # ----------------------------------------------------
        # RANK PLAYERS
        # ----------------------------------------------------

        ranked_results = rank_completed_players(
            round_results,
            event_format
        )

        # ----------------------------------------------------
        # GET RANKING POINT SETTINGS
        # ----------------------------------------------------

        ranking_df = pd.read_sql_query(
            """
            SELECT
                position,
                points
            FROM ranking_settings
            WHERE active = TRUE
            ORDER BY position
            """,
            connection
        )

        ranking_points = {
            int(row["position"]):
                float(row["points"])
            for _, row in ranking_df.iterrows()
        }

        # ----------------------------------------------------
        # ALLOCATE RANKING POINTS
        # ----------------------------------------------------

        final_results = allocate_ranking_points(
            ranked_results,
            ranking_points,
            event_format
        )

        # ----------------------------------------------------
        # DATABASE TRANSACTION
        # ----------------------------------------------------

        with connection.cursor() as cursor:

            # ----------------------------------------------
            # DELETE EXISTING RESULTS
            # ----------------------------------------------

            cursor.execute(
                """
                DELETE FROM event_results
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

            # ----------------------------------------------
            # DELETE EXISTING RANKING POINTS
            # ----------------------------------------------

            cursor.execute(
                """
                DELETE FROM ranking_points
                WHERE event_id = %s
                """,
                (int(event_id),)
            )

            # ----------------------------------------------
            # SAVE FINAL RESULTS
            # ----------------------------------------------

            for result in final_results:

                last_6_score = (
                    result["last_6_net"]
                    if event_format == "NET"
                    else result["last_6_ips"]
                )

                last_3_score = (
                    result["last_3_net"]
                    if event_format == "NET"
                    else result["last_3_ips"]
                )

                last_hole_score = (
                    result["last_hole_net"]
                    if event_format == "NET"
                    else result["last_hole_ips"]
                )

                cursor.execute(
                    """
                    INSERT INTO event_results
                        (
                            event_id,
                            player_id,
                            gross_total,
                            net_total,
                            ips_total,
                            last_6_score,
                            last_3_score,
                            last_hole_score,
                            final_position,
                            ranking_points
                        )
                    VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                    """,
                    (
                        int(event_id),

                        int(
                            result["player_id"]
                        ),

                        int(
                            result["gross_total"]
                        ),

                        int(
                            result["net_total"]
                        ),

                        int(
                            result["ips_total"]
                        ),

                        int(
                            last_6_score
                        ),

                        int(
                            last_3_score
                        ),

                        int(
                            last_hole_score
                        ),

                        int(
                            result[
                                "final_position"
                            ]
                        ),

                        float(
                            result[
                                "ranking_points"
                            ]
                        )
                    )
                )

                # ------------------------------------------
                # SAVE RANKING POINTS
                # ------------------------------------------

                cursor.execute(
                    """
                    INSERT INTO ranking_points
                        (
                            season_id,
                            event_id,
                            player_id,
                            points
                        )
                    SELECT
                        season_id,
                        %s,
                        %s,
                        %s
                    FROM events
                    WHERE id = %s
                    """,
                    (
                        int(event_id),

                        int(
                            result["player_id"]
                        ),

                        float(
                            result[
                                "ranking_points"
                            ]
                        ),

                        int(event_id)
                    )
                )

            # ----------------------------------------------
            # CLOSE EVENT
            # ----------------------------------------------

            cursor.execute(
                """
                UPDATE events
                SET
                    status = 'CLOSED',
                    closed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                AND status IN (
                    'LIVE',
                    'PENDING_CLOSE'
                )
                """,
                (int(event_id),)
            )

        connection.commit()

        return final_results

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# ============================================================
# PAGE
# ============================================================

st.title("📱 Live Scoring")

st.caption(
    "One scorer per fourball. Enter gross scores and "
    "Golfing Warriors calculates Net and IPS automatically."
)

st.divider()


# ============================================================
# SELECT EVENT
# ============================================================

events = get_live_events()

if events.empty:

    st.info(
        "There are currently no LIVE events."
    )

    st.stop()


event_options = {}

for _, row in events.iterrows():

    label = (
        f"{row['name']} — "
        f"{row['event_date']} — "
        f"{row['format']}"
    )

    event_options[
        label
    ] = int(row["id"])


selected_event_label = st.selectbox(
    "Select Event",
    list(event_options.keys())
)

event_id = event_options[
    selected_event_label
]


event_df = get_event(
    event_id
)

if event_df.empty:

    st.error(
        "Unable to find this event."
    )

    st.stop()


event = event_df.iloc[0]

event_format = event["format"]

status = event["status"]


# ============================================================
# EVENT HEADER
# ============================================================

if status == "LIVE":

    st.success(
        f"🟢 {event['name']} — LIVE"
    )

elif status == "PENDING_CLOSE":

    st.warning(
        f"🏁 {event['name']} — PENDING CLOSE"
    )


col1, col2, col3 = st.columns(3)

with col1:

    st.write(
        f"📅 **Date:** {event['event_date']}"
    )

with col2:

    st.write(
        f"⛳ **Course:** {event['course_name']}"
    )

with col3:

    st.write(
        f"🏆 **Format:** {event_format}"
    )


# ============================================================
# LOAD EVENT DATA
# ============================================================

players_df = get_event_players(
    event_id
)

holes_df = get_event_holes(
    event_id
)

scores_df = get_scores(
    event_id
)


if players_df.empty:

    st.error(
        "This event has no players assigned."
    )

    st.stop()


if len(holes_df) != 18:

    st.error(
        "This event does not have 18 holes configured."
    )

    st.stop()


# ============================================================
# BUILD PLAYER DATA
# ============================================================

players = []

for _, player in players_df.iterrows():

    players.append(
        {
            "player_id":
                int(player["player_id"]),

            "name":
                player["name"],

            "nickname":
                (
                    player["nickname"]
                    if pd.notna(
                        player["nickname"]
                    )
                    else ""
                ),

            "event_handicap":
                float(
                    player["event_handicap"]
                ),

            "group_number":
                int(
                    player["group_number"]
                ),

            "is_scorer":
                bool(
                    player["is_scorer"]
                )
        }
    )


# ============================================================
# SCORE LOOKUP
# ============================================================

score_lookup = {}

for _, row in scores_df.iterrows():

    player_id = int(
        row["player_id"]
    )

    hole_number = int(
        row["hole_number"]
    )

    score_lookup[
        (
            player_id,
            hole_number
        )
    ] = int(
        row["gross_score"]
    )


# ============================================================
# SELECT SCORER
# ============================================================

st.divider()

st.subheader(
    "📝 Select Scorer"
)

scorers = [
    player
    for player in players
    if player["is_scorer"]
]


if not scorers:

    st.error(
        "No scorers have been assigned to this event."
    )

    st.stop()


scorer_options = {}

for player in scorers:

    label = (
        f"{player['name']} "
        f"— Fourball "
        f"{player['group_number']}"
    )

    scorer_options[
        label
    ] = player


selected_scorer_label = st.selectbox(
    "Who is doing the scoring?",
    list(
        scorer_options.keys()
    )
)

selected_scorer = scorer_options[
    selected_scorer_label
]

scorer_id = selected_scorer[
    "player_id"
]

group_number = selected_scorer[
    "group_number"
]


# ============================================================
# GET GROUP
# ============================================================

group_players = [
    player
    for player in players
    if player["group_number"]
    == group_number
]


st.success(
    f"Scoring **Fourball {group_number}** "
    f"for **{selected_scorer['name']}**"
)


# ============================================================
# HOLE SELECTOR
# ============================================================

st.divider()

st.subheader(
    "⛳ Hole"
)

hole_options = list(
    range(1, 19)
)


current_hole_key = (
    f"current_hole_"
    f"{event_id}_"
    f"{group_number}"
)


current_hole = st.session_state.get(
    current_hole_key,
    1
)


selected_hole = st.selectbox(
    "Select Hole",
    hole_options,
    index=current_hole - 1,
    format_func=lambda hole:
        f"Hole {hole}"
)


st.session_state[
    current_hole_key
] = selected_hole


hole = holes_df[
    holes_df["hole_number"]
    == selected_hole
].iloc[0]


par = int(
    hole["par"]
)

stroke_index = int(
    hole["stroke_index"]
)


st.markdown(
    f"## Hole {selected_hole}"
)


hole_col1, hole_col2 = st.columns(2)

with hole_col1:

    st.metric(
        "Par",
        par
    )

with hole_col2:

    st.metric(
        "Stroke Index",
        stroke_index
    )


# ============================================================
# SCORE ENTRY
# ============================================================

st.divider()

st.subheader(
    "Enter Gross Scores"
)

st.caption(
    "Enter the actual gross score for each player. "
    "Net and IPS are calculated automatically."
)


entered_scores = {}


for player in group_players:

    player_id = player[
        "player_id"
    ]

    previous_score = score_lookup.get(
        (
            player_id,
            selected_hole
        )
    )

    default_score = (
        previous_score
        if previous_score is not None
        else par
    )

    score = st.number_input(
        player["name"],
        min_value=1,
        max_value=20,
        value=int(
            default_score
        ),
        step=1,
        key=(
            f"score_"
            f"{event_id}_"
            f"{group_number}_"
            f"{selected_hole}_"
            f"{player_id}"
        )
    )

    entered_scores[
        player_id
    ] = score


# ============================================================
# HOLE PREVIEW
# ============================================================

st.divider()

st.subheader(
    "📊 Hole Preview"
)


preview_rows = []


for player in group_players:

    gross = entered_scores[
        player["player_id"]
    ]

    net = calculate_net_score(
        gross,
        player["event_handicap"],
        stroke_index
    )

    ips = calculate_ips_points(
        gross,
        par,
        player["event_handicap"],
        stroke_index
    )

    preview_rows.append(
        {
            "Player":
                player["name"],

            "HCP":
                player["event_handicap"],

            "Gross":
                gross,

            "Net":
                net,

            "IPS":
                ips
        }
    )


preview_df = pd.DataFrame(
    preview_rows
)


st.dataframe(
    preview_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# SAVE HOLE
# ============================================================

st.divider()


if status == "LIVE":

    if st.button(
        f"💾 Save Hole {selected_hole}",
        type="primary",
        use_container_width=True
    ):

        try:

            save_hole_scores(
                event_id,
                scorer_id,
                selected_hole,
                entered_scores
            )

            st.success(
                f"Hole {selected_hole} saved!"
            )

            # -----------------------------------------------
            # ADVANCE TO NEXT HOLE
            # -----------------------------------------------

            if selected_hole < 18:

                st.session_state[
                    current_hole_key
                ] = selected_hole + 1

            st.rerun()

        except Exception as error:

            st.error(
                "Unable to save scores."
            )

            st.exception(error)

else:

    st.warning(
        "This event is no longer accepting score edits."
    )


# ============================================================
# BUILD SCORE DICTIONARIES
# ============================================================

score_dicts = {}


for player in players:

    player_id = player[
        "player_id"
    ]

    score_dicts[
        player_id
    ] = {}

    for hole_number in hole_options:

        score = score_lookup.get(
            (
                player_id,
                hole_number
            )
        )

        if score is not None:

            score_dicts[
                player_id
            ][hole_number] = score


# ============================================================
# CALCULATE LIVE ROUND RESULTS
# ============================================================

round_results = []


for player in players:

    result = calculate_player_round(
        player,
        holes_df.to_dict(
            "records"
        ),
        score_dicts[
            player["player_id"]
        ]
    )

    round_results.append(
        result
    )


# ============================================================
# LIVE LEADERBOARD
# ============================================================

st.divider()

st.header(
    "🏆 Live Leaderboard"
)


if event_format == "IPS":

    sorted_results = sorted(
        round_results,
        key=lambda result: (
            -result["ips_total"],
            -result["completed"],
            result["name"]
        )
    )

    score_column = "IPS"

else:

    sorted_results = sorted(
        round_results,
        key=lambda result: (
            result["net_total"],
            -result["completed"],
            result["name"]
        )
    )

    score_column = "Net"


leaderboard_rows = []


for position, result in enumerate(
    sorted_results,
    start=1
):

    leaderboard_rows.append(
        {
            "Pos":
                position,

            "Player":
                result["name"],

            "HCP":
                result["handicap"],

            "Holes":
                f"{result['completed']}/18",

            score_column:
                (
                    result["ips_total"]
                    if event_format == "IPS"
                    else result["net_total"]
                )
        }
    )


leaderboard_df = pd.DataFrame(
    leaderboard_rows
)


st.dataframe(
    leaderboard_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# ROUND STATUS
# ============================================================

st.divider()

all_complete = all(
    result["completed"] == 18
    for result in round_results
)


if all_complete:

    st.success(
        "🎉 All players have completed 18 holes!"
    )

    if status == "LIVE":

        st.warning(
            "⚠️ Finalizing this event will "
            "lock the scores and award official "
            "ranking points."
        )

        if st.button(
            "🏆 FINALIZE & CLOSE EVENT",
            type="primary",
            use_container_width=True
        ):

            try:

                final_results = finalize_event(
                    event_id,
                    event_format,
                    players,
                    holes_df.to_dict(
                        "records"
                    ),
                    score_dicts
                )

                st.success(
                    "🏆 Event finalized successfully!"
                )

                st.balloons()

                st.subheader(
                    "🏆 Official Results"
                )

                result_rows = []

                for result in final_results:

                    result_rows.append(
                        {
                            "Position":
                                result[
                                    "final_position"
                                ],

                            "Player":
                                result["name"],

                            "Gross":
                                result[
                                    "gross_total"
                                ],

                            "Net":
                                result[
                                    "net_total"
                                ],

                            "IPS":
                                result[
                                    "ips_total"
                                ],

                            "Ranking Points":
                                result[
                                    "ranking_points"
                                ]
                        }
                    )


                results_display = pd.DataFrame(
                    result_rows
                )


                st.dataframe(
                    results_display,
                    use_container_width=True,
                    hide_index=True
                )


                st.info(
                    "🔒 This event is now CLOSED. "
                    "Scores can no longer be edited."
                )

                st.stop()


            except Exception as error:

                st.error(
                    "Unable to finalize the event."
                )

                st.exception(error)


    elif status == "PENDING_CLOSE":

        st.info(
            "This event is already pending close."
        )


else:

    incomplete = [
        (
            result["name"],
            result["completed"]
        )
        for result in round_results
        if result["completed"] < 18
    ]


    st.info(
        "Round still in progress."
    )


    st.write(
        "Incomplete players:"
    )


    for name, completed in incomplete:

        st.write(
            f"- {name}: "
            f"{completed}/18 holes"
        )
