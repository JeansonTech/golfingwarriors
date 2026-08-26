
import streamlit as st
import pandas as pd

from database import get_connection


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors - Live Scoring",
    page_icon="📱",
    layout="wide"
)


# ============================================================
# MOBILE-FIRST UI
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 0.65rem;
        padding-bottom: 1.5rem;
        max-width: 1050px;
    }

    .gw-card {
        border: 1px solid rgba(128,128,128,.22);
        border-radius: 14px;
        padding: 12px;
        margin-bottom: 10px;
        background: rgba(128,128,128,.035);
    }

    .gw-hole {
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        margin-bottom: 8px;
    }

    .gw-hole-current {
        border: 2px solid #2e8b57;
        background: rgba(46,139,87,.10);
    }

    .gw-hole-done {
        background: rgba(46,139,87,.12);
    }

    .gw-hole-number {
        font-size: 1.35rem;
        font-weight: 700;
    }

    .gw-small {
        font-size: .78rem;
        opacity: .72;
    }

    .gw-score {
        font-size: 1.7rem;
        font-weight: 800;
        text-align: center;
    }

    .gw-name {
        font-weight: 700;
        font-size: 1rem;
    }

    /* Hole selector: compact grid instead of full-width stacked buttons */
    div[data-testid="stHorizontalBlock"] .gw-hole-button button {
        min-width: 0 !important;
        width: 100% !important;
    }

    @media (max-width: 768px) {

        .block-container {
            padding-left: .45rem;
            padding-right: .45rem;
        }

        h1 {
            font-size: 1.55rem !important;
        }

        h2 {
            font-size: 1.25rem !important;
        }

        h3 {
            font-size: 1.05rem !important;
        }

        /* Keep normal buttons touch-friendly, but do NOT make them full-height. */
        button {
            min-height: 38px !important;
            padding: 0.25rem 0.45rem !important;
        }

        /* Compact hole selector buttons */
        div[data-testid="stHorizontalBlock"] button {
            min-height: 34px !important;
            padding: 0.15rem 0.25rem !important;
            font-size: 0.82rem !important;
        }

        div[data-testid="stNumberInput"] input {
            font-size: 1.05rem !important;
            min-height: 40px !important;
        }

        div[data-testid="stMetric"] {
            padding: 6px 4px;
            margin-bottom: 0;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.05rem;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.68rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DATABASE HELPERS
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
                s.name AS season_name,
                s.year,
                c.name AS course_name

            FROM events e

            INNER JOIN seasons s
                ON e.season_id = s.id

            LEFT JOIN courses c
                ON e.course_id = c.id

            WHERE
                e.status IN ('LIVE', 'PENDING_CLOSE')

            ORDER BY
                e.event_date DESC,
                e.id DESC
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
                e.season_id,
                s.name AS season_name,
                s.year,
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
                p.name,
                p.nickname,
                ep.event_handicap,
                ep.group_number,
                ep.is_scorer

            FROM event_players ep

            INNER JOIN players p
                ON ep.player_id = p.id

            WHERE
                ep.event_id = %s

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

            WHERE
                event_id = %s

            ORDER BY
                hole_number
            """,
            connection,
            params=(int(event_id),)
        )

    finally:

        connection.close()


def get_score_column():

    connection = get_connection()

    try:

        columns = pd.read_sql_query(
            """
            SELECT
                column_name

            FROM information_schema.columns

            WHERE
                table_schema = 'public'
                AND table_name = 'hole_scores'

            ORDER BY
                ordinal_position
            """,
            connection
        )

        available = {
            str(value).lower(): str(value)
            for value in columns[
                "column_name"
            ].tolist()
        }

        candidates = [
            "gross_score",
            "score",
            "strokes",
            "gross_strokes",
            "actual_score"
        ]

        for candidate in candidates:

            if candidate in available:

                return available[candidate]

        return None

    finally:

        connection.close()


def get_saved_scores(
    event_id,
    player_ids,
    score_column
):

    if not player_ids:

        return pd.DataFrame(
            columns=[
                "player_id",
                "hole_number",
                "score"
            ]
        )

    connection = get_connection()

    try:

        placeholders = ",".join(
            ["%s"] * len(player_ids)
        )

        query = f"""
            SELECT
                player_id,
                hole_number,
                {score_column} AS score

            FROM hole_scores

            WHERE
                event_id = %s
                AND player_id IN ({placeholders})

            ORDER BY
                player_id,
                hole_number
        """

        params = [
            int(event_id)
        ] + [
            int(player_id)
            for player_id in player_ids
        ]

        return pd.read_sql_query(
            query,
            connection,
            params=params
        )

    finally:

        connection.close()


def save_hole_scores(
    event_id,
    hole_number,
    scores,
    score_column
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            for player_id, score in scores.items():

                cursor.execute(
                    f"""
                    DELETE FROM hole_scores
                    WHERE
                        event_id = %s
                        AND player_id = %s
                        AND hole_number = %s
                    """,
                    (
                        int(event_id),
                        int(player_id),
                        int(hole_number)
                    )
                )

                cursor.execute(
                    f"""
                    INSERT INTO hole_scores
                        (
                            event_id,
                            player_id,
                            hole_number,
                            {score_column}
                        )
                    VALUES
                        (%s, %s, %s, %s)
                    """,
                    (
                        int(event_id),
                        int(player_id),
                        int(hole_number),
                        int(score)
                    )
                )

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


def set_pending_close(event_id):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE events
                SET status = 'PENDING_CLOSE'

                WHERE
                    id = %s
                    AND status = 'LIVE'
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
# SCORING HELPERS
# ============================================================

def handicap_strokes(
    handicap,
    stroke_index
):

    """
    Full handicap stroke allocation.

    A handicap of 10 gives one stroke on SI 1-10.
    A handicap of 22 gives one stroke on all holes
    plus a second stroke on SI 1-4.
    """

    handicap = max(
        0,
        int(round(float(handicap)))
    )

    stroke_index = int(
        stroke_index
    )

    base = handicap // 18
    remainder = handicap % 18

    return (
        base
        + (
            1
            if stroke_index <= remainder
            else 0
        )
    )


def net_score(
    gross,
    par,
    handicap,
    stroke_index
):

    strokes = handicap_strokes(
        handicap,
        stroke_index
    )

    return int(
        gross - strokes
    )


def stableford_points(
    gross,
    par,
    handicap,
    stroke_index
):

    net = net_score(
        gross,
        par,
        handicap,
        stroke_index
    )

    difference = (
        int(par) - int(net)
    )

    # Standard Stableford:
    # net double bogey = 0
    # net bogey       = 1
    # net par         = 2
    # net birdie      = 3
    # net eagle       = 4
    # etc.
    return max(
        0,
        2 + difference
    )


def score_icon(
    gross,
    par
):

    difference = (
        int(gross) - int(par)
    )

    if difference <= -2:
        return "🦅"

    if difference == -1:
        return "🐦"

    if difference == 0:
        return "⛳"

    if difference == 1:
        return "😬"

    return "💀"


# ============================================================
# SESSION STATE
# ============================================================

if "gw_event_id" not in st.session_state:

    st.session_state.gw_event_id = None


if "gw_current_hole" not in st.session_state:

    st.session_state.gw_current_hole = 1


if "gw_scores" not in st.session_state:

    st.session_state.gw_scores = {}


# ============================================================
# LOAD EVENTS
# ============================================================

events = get_live_events()


# ============================================================
# PAGE HEADER
# ============================================================

st.title(
    "📱 Live Scoring"
)

st.caption(
    "One scorer records the complete fourball."
)


if events.empty:

    st.info(
        "There are currently no LIVE events."
    )

    st.caption(
        "Start an event from the Events page first."
    )

    st.stop()


# ============================================================
# EVENT SELECTION
# ============================================================

event_options = {}

for _, event in events.iterrows():

    label = (
        f"{event['name']} — "
        f"{event['course_name']} — "
        f"{event['status']}"
    )

    event_options[label] = int(
        event["id"]
    )


selected_label = st.selectbox(
    "🏆 Event",
    list(event_options.keys())
)

selected_event_id = event_options[
    selected_label
]


if (
    st.session_state.gw_event_id
    != selected_event_id
):

    st.session_state.gw_event_id = (
        selected_event_id
    )

    st.session_state.gw_current_hole = 1

    st.session_state.gw_scores = {}


event = get_event(
    selected_event_id
).iloc[0]

event_players = get_event_players(
    selected_event_id
)

holes = get_event_holes(
    selected_event_id
)


if event_players.empty:

    st.error(
        "No players are assigned to this event."
    )

    st.stop()


if holes.empty:

    st.error(
        "No hole snapshot exists for this event."
    )

    st.stop()


score_column = get_score_column()

if score_column is None:

    st.error(
        "Unable to identify the score column "
        "in hole_scores."
    )

    st.stop()


# ============================================================
# SCORER / FOURBALL SELECTION
# ============================================================

groups = {}

for _, player in event_players.iterrows():

    group_number = int(
        player["group_number"]
    )

    groups.setdefault(
        group_number,
        []
    ).append(
        player
    )


group_options = {}

for group_number, group_players in groups.items():

    scorers = [
        player
        for player in group_players
        if bool(player["is_scorer"])
    ]

    scorer_name = (
        scorers[0]["name"]
        if scorers
        else "No scorer assigned"
    )

    group_options[
        f"Fourball {group_number} • Scorer: {scorer_name}"
    ] = group_number


selected_group_label = st.selectbox(
    "👥 Fourball",
    list(group_options.keys())
)

selected_group = group_options[
    selected_group_label
]


fourball = event_players[
    event_players["group_number"]
    == selected_group
].copy()


# ============================================================
# LOAD EXISTING SCORES
# ============================================================

saved = get_saved_scores(
    selected_event_id,
    [
        int(player_id)
        for player_id
        in fourball["player_id"]
    ],
    score_column
)


for _, saved_row in saved.iterrows():

    key = (
        int(saved_row["player_id"]),
        int(saved_row["hole_number"])
    )

    st.session_state.gw_scores[
        key
    ] = int(
        saved_row["score"]
    )


# ============================================================
# HEADER CARD
# ============================================================

st.markdown(
    f"""
    <div class="gw-card">
        <div class="gw-small">LIVE EVENT</div>
        <div style="font-size:1.15rem;font-weight:800;">
            {event['name']}
        </div>
        <div class="gw-small">
            📅 {event['event_date']} &nbsp; • &nbsp;
            ⛳ {event['course_name']} &nbsp; • &nbsp;
            🏆 {event['format']}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


scorer_rows = fourball[
    fourball["is_scorer"] == True
]

scorer_name = (
    scorer_rows.iloc[0]["name"]
    if not scorer_rows.empty
    else "Not assigned"
)

st.success(
    f"📝 **Fourball {selected_group}** "
    f"• Scorer: **{scorer_name}**"
)


# ============================================================
# PROGRESS
# ============================================================

current_hole = int(
    st.session_state.gw_current_hole
)

completed_holes = 0

for hole_number in range(1, 19):

    complete = True

    for player_id in fourball[
        "player_id"
    ]:

        if (
            int(player_id),
            hole_number
        ) not in st.session_state.gw_scores:

            complete = False

            break

    if complete:

        completed_holes += 1


st.subheader(
    "🏌️ Round Progress"
)

st.progress(
    completed_holes / 18
)

st.caption(
    f"**{completed_holes} / 18 holes completed**"
)


# ============================================================
# HOLE BUTTONS
# ============================================================

st.markdown(
    "### Holes"
)

for row_start in [1, 10]:

    row_end = (
        row_start + 9
    )

    cols = st.columns(
        9,
        gap="small"
    )

    for index, hole_number in enumerate(
        range(row_start, row_end)
    ):

        if hole_number > 18:
            continue

        complete = True

        for player_id in fourball[
            "player_id"
        ]:

            if (
                int(player_id),
                hole_number
            ) not in st.session_state.gw_scores:

                complete = False

                break


        label = (
            f"✓ {hole_number}"
            if complete
            else str(hole_number)
        )


        with cols[index]:

            if st.button(
                label,
                key=f"hole_{selected_group}_{hole_number}",
                use_container_width=True,
                type=(
                    "primary"
                    if hole_number == current_hole
                    else "secondary"
                )
            ):

                st.session_state.gw_current_hole = (
                    hole_number
                )

                st.rerun()


# ============================================================
# HOLE NAVIGATION
# ============================================================

nav1, nav2, nav3 = st.columns(
    [1.35, 0.85, 1.35],
    gap="small"
)

with nav1:

    jump_options = list(
        range(1, 19)
    )

    jump_hole = st.selectbox(
        "Jump to hole",
        jump_options,
        index=current_hole - 1,
        key=f"jump_{selected_group}"
    )


with nav2:

    if st.button(
        "◀ Prev",
        use_container_width=True,
        disabled=current_hole <= 1
    ):

        st.session_state.gw_current_hole = (
            current_hole - 1
        )

        st.rerun()


with nav3:

    if st.button(
        "Next ▶",
        use_container_width=True,
        disabled=current_hole >= 18
    ):

        st.session_state.gw_current_hole = (
            current_hole + 1
        )

        st.rerun()


if jump_hole != current_hole:

    st.session_state.gw_current_hole = (
        int(jump_hole)
    )

    st.rerun()


# ============================================================
# CURRENT HOLE
# ============================================================

hole = holes[
    holes["hole_number"]
    == current_hole
].iloc[0]

par = int(
    hole["par"]
)

stroke_index = int(
    hole["stroke_index"]
)


st.markdown(
    f"""
    <div class="gw-card">
        <div style="display:flex;justify-content:space-around;text-align:center;">
            <div>
                <div class="gw-small">HOLE</div>
                <div style="font-size:2rem;font-weight:900;">
                    {current_hole}
                </div>
                <div class="gw-small">of 18</div>
            </div>
            <div>
                <div class="gw-small">PAR</div>
                <div style="font-size:2rem;font-weight:900;">
                    {par}
                </div>
            </div>
            <div>
                <div class="gw-small">STROKE INDEX</div>
                <div style="font-size:2rem;font-weight:900;">
                    {stroke_index}
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# PLAYER SCORING
# ============================================================

st.subheader(
    f"🎯 Hole {current_hole} Scores"
)


current_values = {}

for _, player in fourball.iterrows():

    player_id = int(
        player["player_id"]
    )

    player_name = player["name"]

    handicap = float(
        player["event_handicap"]
    )

    score_key = (
        player_id,
        current_hole
    )

    existing = st.session_state.gw_scores.get(
        score_key,
        par
    )

    st.markdown(
        '<div class="gw-card" style="padding:8px;margin-bottom:7px;">',
        unsafe_allow_html=True
    )

    name_col, hcp_col = st.columns(
        [3, 1]
    )

    with name_col:

        role = (
            " • 📝 Scorer"
            if bool(player["is_scorer"])
            else ""
        )

        st.markdown(
            f'<div class="gw-name">'
            f'{player_name}{role}'
            f'</div>',
            unsafe_allow_html=True
        )

    with hcp_col:

        st.markdown(
            f'<div class="gw-small">'
            f'HCP {handicap:g}'
            f'</div>',
            unsafe_allow_html=True
        )


    score = st.number_input(
        "Gross",
        min_value=1,
        max_value=20,
        value=int(existing),
        step=1,
        key=f"score_{selected_group}_{player_id}_{current_hole}"
    )

    current_values[
        player_id
    ] = int(score)


    net = net_score(
        score,
        par,
        handicap,
        stroke_index
    )

    points = stableford_points(
        score,
        par,
        handicap,
        stroke_index
    )

    icon = score_icon(
        score,
        par
    )


    # Keep Gross / Net / IPS together on one compact row.
    result_col1, result_col2, result_col3 = st.columns(
        [1, 1, 1],
        gap="small"
    )

    with result_col1:
        st.metric(
            f"{icon} Gross",
            score
        )

    with result_col2:
        st.metric(
            "Net",
            net
        )

    with result_col3:
        st.metric(
            "IPS",
            points
        )


    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# SAVE / CLEAR
# ============================================================

st.divider()


save_col, clear_col = st.columns(
    [2, 1]
)


with save_col:

    if st.button(
        f"💾 SAVE HOLE {current_hole}",
        type="primary",
        use_container_width=True
    ):

        try:

            save_hole_scores(
                selected_event_id,
                current_hole,
                current_values,
                score_column
            )

            for player_id, score in current_values.items():

                st.session_state.gw_scores[
                    (
                        int(player_id),
                        current_hole
                    )
                ] = int(score)


            if current_hole < 18:

                st.session_state.gw_current_hole = (
                    current_hole + 1
                )

                st.success(
                    f"Hole {current_hole} saved."
                )

                st.rerun()

            else:

                st.success(
                    "🎉 All 18 holes have been entered."
                )

                st.rerun()


        except Exception as error:

            st.error(
                "Unable to save the hole."
            )

            st.exception(error)


with clear_col:

    if st.button(
        "↻ CLEAR",
        use_container_width=True
    ):

        for player_id in fourball[
            "player_id"
        ]:

            st.session_state.gw_scores.pop(
                (
                    int(player_id),
                    current_hole
                ),
                None
            )

        st.rerun()


# ============================================================
# FOURBALL SUMMARY
# ============================================================

st.divider()

st.subheader(
    "👥 Fourball Progress"
)


summary_rows = []

for _, player in fourball.iterrows():

    player_id = int(
        player["player_id"]
    )

    handicap = float(
        player["event_handicap"]
    )

    gross_total = 0
    net_total = 0
    ips_total = 0
    holes_played = 0

    for _, hole_row in holes.iterrows():

        hole_number = int(
            hole_row["hole_number"]
        )

        score_key = (
            player_id,
            hole_number
        )

        if score_key not in st.session_state.gw_scores:

            continue

        gross = int(
            st.session_state.gw_scores[
                score_key
            ]
        )

        hole_par = int(
            hole_row["par"]
        )

        hole_si = int(
            hole_row["stroke_index"]
        )

        gross_total += gross

        net_total += net_score(
            gross,
            hole_par,
            handicap,
            hole_si
        )

        ips_total += stableford_points(
            gross,
            hole_par,
            handicap,
            hole_si
        )

        holes_played += 1


    summary_rows.append(
        {
            "Player": player["name"],
            "Holes": holes_played,
            "Gross": gross_total,
            "Net": net_total,
            "IPS": ips_total
        }
    )


summary = pd.DataFrame(
    summary_rows
)


st.dataframe(
    summary,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# CLOSE / FINALISE
# ============================================================

if completed_holes == 18:

    st.divider()

    st.success(
        "🎉 All 18 holes are complete for this fourball."
    )

    st.warning(
        "When all fourballs have finished, "
        "use Events/Admin to finalize the event. "
        "This page does not automatically close the event."
    )

    if event["status"] == "LIVE":

        if st.button(
            "🏁 Mark Event Pending Close",
            use_container_width=True
        ):

            try:

                set_pending_close(
                    selected_event_id
                )

                st.success(
                    "Event marked PENDING CLOSE."
                )

                st.rerun()

            except Exception as error:

                st.error(
                    "Unable to mark event pending close."
                )

                st.exception(error)


elif event["status"] == "PENDING_CLOSE":

    st.info(
        "🏁 This event is pending close. "
        "Scoring is locked by the event workflow."
    )


# ============================================================
# LEGEND
# ============================================================

st.divider()

st.caption(
    "🦅 Eagle or better  •  "
    "🐦 Birdie  •  "
    "⛳ Par  •  "
    "😬 Bogey  •  "
    "💀 Double bogey+"
)

st.caption(
    "IPS: 0 points for net double bogey or worse, "
    "2 for net par, with one additional point for "
    "each stroke better than net par."
)
