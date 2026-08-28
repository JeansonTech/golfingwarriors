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


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors - Live Scoring",
    page_icon="🏌️",
    layout="wide"
)


# ============================================================
# MOBILE-FIRST CSS
# ============================================================

st.markdown(
    """
    <style>

    /* -------------------------------------------------------
       GENERAL
    ------------------------------------------------------- */

    .block-container {
        padding-top: 2.4rem !important;
        padding-bottom: 1.5rem;
        max-width: 1100px;
    }


    /* -------------------------------------------------------
       COMPACT HOLE HEADER
    ------------------------------------------------------- */

    .hole-header {
        text-align: center;
        padding: 8px 0 4px 0;
    }

    .hole-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .hole-subtitle {
        font-size: 0.9rem;
        opacity: 0.7;
        margin-top: 2px;
    }


    /* -------------------------------------------------------
       PROGRESS
    ------------------------------------------------------- */

    .progress-title {
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 2px;
    }

    .progress-count {
        font-size: 0.82rem;
        opacity: 0.65;
        margin-bottom: 8px;
    }

    .hole-strip {
        display: grid;
        grid-template-columns: repeat(9, 1fr);
        gap: 5px;
        margin-bottom: 5px;
    }

    .hole-dot {
        height: 31px;
        min-width: 0;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.78rem;
        font-weight: 700;
        border: 1px solid rgba(128,128,128,0.30);
        background: rgba(128,128,128,0.06);
    }

    .hole-dot.completed {
        background: rgba(46, 204, 113, 0.18);
        border-color: rgba(46, 204, 113, 0.55);
    }

    .hole-dot.current {
        background: rgba(52, 152, 219, 0.22);
        border: 2px solid #3498db;
    }


    /* -------------------------------------------------------
       PLAYER CARD
       ------------------------------------------------------- */

    .player-card {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px;
        padding: 9px 11px 4px 11px;
        margin-bottom: 8px;
        background: rgba(128,128,128,0.035);
    }

    .player-name {
        font-size: 1rem;
        font-weight: 750;
        line-height: 1.1;
    }

    .player-hcp {
        font-size: 0.76rem;
        opacity: 0.65;
        margin-top: 2px;
    }

    .player-stats {
        font-size: 0.75rem;
        opacity: 0.75;
        text-align: center;
        padding-top: 5px;
    }


    /* -------------------------------------------------------
       SCORE
       ------------------------------------------------------- */

    div[data-testid="stNumberInput"] {
        margin-bottom: 0 !important;
    }

    div[data-testid="stNumberInput"] label {
        display: none;
    }

    div[data-testid="stNumberInput"] input {
        text-align: center;
        font-size: 1.35rem !important;
        font-weight: 800;
    }


    /* -------------------------------------------------------
       SAVE BUTTON
       ------------------------------------------------------- */

    div.stButton > button {
        min-height: 45px;
        border-radius: 10px;
        font-weight: 700;
    }

    div.stButton > button[kind="primary"] {
        min-height: 55px;
        font-size: 1.05rem;
    }


    /* -------------------------------------------------------
       MOBILE
       ------------------------------------------------------- */

    @media (max-width: 768px) {

        .block-container {
            padding-left: 0.55rem;
            padding-right: 0.55rem;
            padding-top: 2.2rem !important;
        }

        h1 {
            font-size: 1.55rem !important;
            margin-bottom: 0.2rem !important;
        }

        h2 {
            font-size: 1.3rem !important;
        }

        h3 {
            font-size: 1.05rem !important;
        }

        .hole-title {
            font-size: 1.8rem;
        }

        .hole-dot {
            height: 29px;
            font-size: 0.72rem;
            border-radius: 7px;
        }

        .player-card {
            padding: 8px 9px 3px 9px;
            margin-bottom: 6px;
        }

        .player-name {
            font-size: 0.98rem;
        }

        .player-stats {
            font-size: 0.7rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
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

            ORDER BY
                e.event_date DESC
            """,
            connection
        )

    finally:

        connection.close()


def get_event(event_id):

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

            WHERE e.id = %s
            """,
            connection,
            params=(int(event_id),)
        )

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

            ORDER BY
                hole_number
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

                    ON CONFLICT
                        (
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

            round_results.append(result)


        ranked_results = rank_completed_players(
            round_results,
            event_format
        )


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


        final_results = allocate_ranking_points(
            ranked_results,
            ranking_points,
            event_format
        )


        with connection.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM event_results
                WHERE event_id = %s
                """,
                (int(event_id),)
            )


            cursor.execute(
                """
                DELETE FROM ranking_points
                WHERE event_id = %s
                """,
                (int(event_id),)
            )


            for result in final_results:

                if event_format == "NET":

                    last_6_score = result[
                        "last_6_net"
                    ]

                    last_3_score = result[
                        "last_3_net"
                    ]

                    last_hole_score = result[
                        "last_hole_net"
                    ]

                else:

                    last_6_score = result[
                        "last_6_ips"
                    ]

                    last_3_score = result[
                        "last_3_ips"
                    ]

                    last_hole_score = result[
                        "last_hole_ips"
                    ]


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
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                    """,
                    (
                        int(event_id),
                        int(result["player_id"]),
                        int(result["gross_total"]),
                        int(result["net_total"]),
                        int(result["ips_total"]),
                        int(last_6_score),
                        int(last_3_score),
                        int(last_hole_score),
                        int(result["final_position"]),
                        float(result["ranking_points"])
                    )
                )


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
                        int(result["player_id"]),
                        float(result["ranking_points"]),
                        int(event_id)
                    )
                )


            cursor.execute(
                """
                UPDATE events

                SET
                    status = 'CLOSED',
                    closed_at =
                        CURRENT_TIMESTAMP

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
# PAGE HEADER
# ============================================================

st.title("🏌️ Live Scoring")

st.caption(
    "Any player in the fourball can enter the scores • "
    "Gross scores • Net and IPS calculated automatically"
)


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

    event_options[label] = int(row["id"])


selected_event_label = st.selectbox(
    "🏆 Event",
    list(event_options.keys())
)


event_id = event_options[
    selected_event_label
]


event_df = get_event(event_id)


if event_df.empty:

    st.error(
        "Unable to find this event."
    )

    st.stop()


event = event_df.iloc[0]

stored_event_format = str(event["format"])
# IPS is the primary competition for all new events. Legacy NET/MATCH PLAY
# event records are still scored using the IPS engine so they remain usable.
event_format = "IPS"
status = event["status"]


# ============================================================
# EVENT HEADER
# ============================================================

if status == "LIVE":

    st.success(
        f"🟢 {event['name']} — LIVE"
    )

else:

    st.warning(
        f"🔒 {event['name']} — PENDING CLOSE"
    )


event_col1, event_col2, event_col3 = st.columns(3)


with event_col1:

    st.write(
        f"📅 **{event['event_date']}**"
    )


with event_col2:

    st.write(
        f"⛳ **{event['course_name']}**"
    )


with event_col3:

    match_play_connection = get_connection()
    try:
        match_play_count = pd.read_sql_query(
            "SELECT COUNT(*) AS match_count FROM match_play_matches WHERE event_id = %s",
            match_play_connection,
            params=(int(event_id),)
        ).iloc[0]["match_count"]
    except Exception:
        match_play_count = 0
    finally:
        match_play_connection.close()

    competition_label = "IPS + NET"
    if int(match_play_count) > 0:
        competition_label += " + MATCH PLAY"

    st.write(
        f"🏆 **{competition_label}**"
    )


# ============================================================
# LOAD DATA
# ============================================================

players_df = get_event_players(event_id)

holes_df = get_event_holes(event_id)

scores_df = get_scores(event_id)


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
                    if pd.notna(player["nickname"])
                    else ""
                ),

            "event_handicap":
                float(player["event_handicap"]),

            "group_number":
                int(player["group_number"]),

            "is_scorer":
                bool(player["is_scorer"])
        }
    )


# ============================================================
# SCORE LOOKUP
# ============================================================

score_lookup = {}


for _, row in scores_df.iterrows():

    score_lookup[
        (
            int(row["player_id"]),
            int(row["hole_number"])
        )
    ] = int(row["gross_score"])


# ============================================================
# FOURBALL SELECTION
# ============================================================

st.divider()

# No scorer is assigned in the event setup. The players simply decide
# among themselves who will hold the phone and enter the scores.
groups = {}

for player in players:
    groups.setdefault(player["group_number"], []).append(player)

group_options = {}

for group_number, group_players in sorted(groups.items()):
    group_options[
        f"Fourball {group_number} • {len(group_players)} player(s)"
    ] = group_number

if not group_options:
    st.error("No fourballs have been assigned to this event.")
    st.stop()

selected_group_label = st.selectbox(
    "👥 Fourball",
    list(group_options.keys())
)

selected_group = group_options[selected_group_label]

# Technical audit field only: the database column historically expects a
# player ID. It is NOT treated as a designated scorer anywhere in the app.
group_players = groups[selected_group]
scorer_id = group_players[0]["player_id"]


# ============================================================
# GROUP
# ============================================================

group_players = [
    player
    for player in players
    if player["group_number"] == group_number
]


st.caption(
    f"👥 Fourball {group_number} • "
    "Any player in this fourball can enter the scores."
)


# ============================================================
# HOLE STATE
# ============================================================

current_hole_key = (
    f"current_hole_"
    f"{event_id}_"
    f"{group_number}"
)


hole_options = list(range(1, 19))


if current_hole_key not in st.session_state:

    first_incomplete = 1

    for test_hole in hole_options:

        complete = True

        for player in group_players:

            if (
                player["player_id"],
                test_hole
            ) not in score_lookup:

                complete = False
                break

        if not complete:

            first_incomplete = test_hole
            break


    st.session_state[
        current_hole_key
    ] = first_incomplete


current_hole = st.session_state[
    current_hole_key
]


# ============================================================
# PROGRESS
# ============================================================

st.divider()

completed_holes = 0

hole_completed = {}


for test_hole in hole_options:

    complete = True

    for player in group_players:

        if (
            player["player_id"],
            test_hole
        ) not in score_lookup:

            complete = False
            break


    hole_completed[
        test_hole
    ] = complete


    if complete:

        completed_holes += 1


st.markdown(
    """
    <div class="progress-title">
        ⛳ Round Progress
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div class="progress-count">
        {completed_holes} / 18 holes completed
    </div>
    """,
    unsafe_allow_html=True
)


# ------------------------------------------------------------
# Compact visual progress strip
# ------------------------------------------------------------

progress_html = '<div class="hole-strip">'


for hole_number in range(1, 19):

    if hole_number == current_hole:

        css_class = "hole-dot current"
        symbol = "●"

    elif hole_completed[hole_number]:

        css_class = "hole-dot completed"
        symbol = "✓"

    else:

        css_class = "hole-dot"
        symbol = str(hole_number)


    progress_html += (
        f'<div class="{css_class}">'
        f'{symbol}'
        f'</div>'
    )


progress_html += "</div>"


st.markdown(
    progress_html,
    unsafe_allow_html=True
)


# ------------------------------------------------------------
# Compact jump selector
# ------------------------------------------------------------

selected_hole = st.selectbox(
    "Jump to hole",
    hole_options,
    index=current_hole - 1,
    format_func=lambda hole:
        (
            f"✓ Hole {hole}"
            if hole_completed[hole]
            else f"Hole {hole}"
        )
)


if selected_hole != current_hole:

    st.session_state[
        current_hole_key
    ] = selected_hole

    st.rerun()


# ============================================================
# HOLE INFORMATION
# ============================================================

hole = holes_df[
    holes_df["hole_number"] == current_hole
].iloc[0]


par = int(hole["par"])

stroke_index = int(
    hole["stroke_index"]
)


st.markdown(
    f"## ⛳ HOLE {current_hole}"
)

st.caption(
    f"PAR {par}  •  STROKE INDEX {stroke_index}"
)


# ============================================================
# SCORE ENTRY
# ============================================================

st.divider()

st.subheader("🏌️ Scores")

st.caption(
    "Adjust each player's gross score."
)


entered_scores = {}


for player in group_players:

    player_id = player["player_id"]


    score_key = (
        f"mobile_score_"
        f"{event_id}_"
        f"{group_number}_"
        f"{current_hole}_"
        f"{player_id}"
    )


    # --------------------------------------------------------
    # Existing score
    # --------------------------------------------------------

    if score_key not in st.session_state:

        existing_score = score_lookup.get(
            (
                player_id,
                current_hole
            )
        )


        if existing_score is None:

            existing_score = par


        st.session_state[
            score_key
        ] = int(existing_score)


    # --------------------------------------------------------
    # Calculate preview
    # --------------------------------------------------------

    gross = st.session_state[
        score_key
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


    # --------------------------------------------------------
    # PLAYER CARD
    # --------------------------------------------------------

    st.markdown(
    f"**{player['name']}**  •  HCP {player['event_handicap']:g}"
)


    # --------------------------------------------------------
    # SCORE CONTROL
    # --------------------------------------------------------

    score_value = st.number_input(
        "Score",
        min_value=1,
        max_value=20,
        value=int(
            st.session_state[
                score_key
            ]
        ),
        step=1,
        key=score_key
    )


    entered_scores[
        player_id
    ] = int(score_value)


    # --------------------------------------------------------
    # Recalculate after input
    # --------------------------------------------------------

    net = calculate_net_score(
        int(score_value),
        player["event_handicap"],
        stroke_index
    )


    ips = calculate_ips_points(
        int(score_value),
        par,
        player["event_handicap"],
        stroke_index
    )


    # --------------------------------------------------------
    # Compact stats
    # --------------------------------------------------------

    st.markdown(
        f"""
        <div class="player-stats">
            Gross <b>{int(score_value)}</b>
            &nbsp; • &nbsp;
            Net <b>{net}</b>
            &nbsp; • &nbsp;
            IPS <b>{ips}</b>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# SAVE HOLE
# ============================================================

st.divider()


if status == "LIVE":

    if st.button(
        f"💾 SAVE HOLE {current_hole}",
        type="primary",
        use_container_width=True
    ):

        hole_being_saved = current_hole


        try:

            save_hole_scores(
                event_id,
                scorer_id,
                hole_being_saved,
                entered_scores
            )


            # ------------------------------------------------
            # Clear temporary score state
            # ------------------------------------------------

            for player in group_players:

                score_key = (
                    f"mobile_score_"
                    f"{event_id}_"
                    f"{group_number}_"
                    f"{hole_being_saved}_"
                    f"{player['player_id']}"
                )


                if score_key in st.session_state:

                    del st.session_state[
                        score_key
                    ]


            # ------------------------------------------------
            # Move to next hole
            # ------------------------------------------------

            if hole_being_saved < 18:

                st.session_state[
                    current_hole_key
                ] = hole_being_saved + 1

            else:

                st.session_state[
                    current_hole_key
                ] = 18


            st.rerun()


        except Exception as error:

            st.error(
                "Unable to save scores."
            )

            st.exception(error)


else:

    st.warning(
        "🔒 This event is no longer accepting score edits."
    )


# ============================================================
# SCORE DICTIONARIES
# ============================================================

score_dicts = {}


for player in players:

    player_id = player["player_id"]

    score_dicts[player_id] = {}


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
# LIVE ROUND RESULTS
# ============================================================

round_results = []


for player in players:

    result = calculate_player_round(
        player,
        holes_df.to_dict("records"),
        score_dicts[
            player["player_id"]
        ]
    )


    round_results.append(result)


# ============================================================
# COMPACT FOURBALL PROGRESS
# ============================================================

st.divider()

st.subheader("📈 Fourball")


progress_rows = []


group_player_ids = [
    player["player_id"]
    for player in group_players
]


for result in round_results:

    if result["player_id"] not in group_player_ids:

        continue


    progress_rows.append(
        {
            "Player":
                result["name"],

            "Holes":
                f"{result['completed']}/18",

            "Net":
                result["net_total"],

            "IPS":
                result["ips_total"]
        }
    )


progress_df = pd.DataFrame(
    progress_rows
)


st.dataframe(
    progress_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# NAVIGATION
# ============================================================

st.divider()

previous_col, next_col = st.columns(2)


with previous_col:

    if current_hole > 1:

        if st.button(
            "⬅️ PREVIOUS",
            use_container_width=True
        ):

            st.session_state[
                current_hole_key
            ] = current_hole - 1

            st.rerun()


with next_col:

    if current_hole < 18:

        if st.button(
            "NEXT ➡️",
            use_container_width=True
        ):

            st.session_state[
                current_hole_key
            ] = current_hole + 1

            st.rerun()


# ============================================================
# LIVE LEADERBOARD
# ============================================================

st.divider()

st.header("🏆 Live Leaderboard")

sorted_results = sorted(
    round_results,
    key=lambda result: (
        -result["ips_total"],
        -result["completed"],
        result["name"]
    )
)

leaderboard_rows = []

for position, result in enumerate(sorted_results, start=1):
    leaderboard_rows.append(
        {
            "Pos": position,
            "Player": result["name"],
            "HCP": result["handicap"],
            "Holes": f"{result['completed']}/18",
            "IPS": result["ips_total"],
            "Net": result["net_total"]
        }
    )

leaderboard_df = pd.DataFrame(leaderboard_rows)

st.dataframe(
    leaderboard_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# FINALIZE EVENT
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
                    holes_df.to_dict("records"),
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
                                result["final_position"],

                            "Player":
                                result["name"],

                            "Gross":
                                result["gross_total"],

                            "Net":
                                result["net_total"],

                            "IPS":
                                result["ips_total"],

                            "Ranking Points":
                                result["ranking_points"]
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


    for name, completed in incomplete:

        st.write(
            f"• {name}: "
            f"{completed}/18 holes"
        )
