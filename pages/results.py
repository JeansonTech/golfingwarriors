
import streamlit as st
import pandas as pd

from database import get_connection

from scoring.scoring_engine import calculate_ips_points


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors - Results",
    page_icon="📋",
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
        padding: 10px;
        background: rgba(128,128,128,0.035);
    }

    @media (max-width: 768px) {

        .block-container {
            padding-left: 0.55rem;
            padding-right: 0.55rem;
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
            font-size: 1.25rem;
        }

    }

    /* -------------------------------------------------------
       PGA-STYLE SCORECARD MARKERS
       ------------------------------------------------------- */

    .scorecard-wrap {
        width: 100%;
        overflow-x: auto;
        margin: 0 0 1rem 0;
    }

    .scorecard-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        table-layout: fixed;
        border: 1px solid rgba(128,128,128,0.20);
        border-radius: 10px;
        overflow: hidden;
        font-size: 0.82rem;
    }

    .scorecard-table th,
    .scorecard-table td {
        height: 42px;
        padding: 3px 2px;
        text-align: center;
        border-right: 1px solid rgba(128,128,128,0.16);
        border-bottom: 1px solid rgba(128,128,128,0.16);
        white-space: nowrap;
    }

    .scorecard-table th {
        width: 62px;
        font-weight: 700;
        background: rgba(128,128,128,0.055);
        text-align: left;
        padding-left: 8px;
    }

    .scorecard-table tr:last-child th,
    .scorecard-table tr:last-child td {
        border-bottom: 0;
    }

    .scorecard-table th:last-child,
    .scorecard-table td:last-child {
        border-right: 0;
    }

    .score-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 28px;
        height: 28px;
        line-height: 1;
        font-weight: 800;
        box-sizing: border-box;
    }

    .score-mark.birdie {
        border: 2px solid #d62728;
        border-radius: 50%;
    }

    .score-mark.eagle {
        border: 2px solid #d62728;
        border-radius: 50%;
        box-shadow: 0 0 0 2px #ffffff, 0 0 0 4px #d62728;
    }

    .score-mark.bogey {
        border: 2px solid #2f5fb3;
        border-radius: 2px;
    }

    .score-mark.double-bogey {
        border: 2px solid #2f5fb3;
        border-radius: 2px;
        box-shadow: 0 0 0 2px #ffffff, 0 0 0 4px #2f5fb3;
    }

    .score-mark.triple-bogey {
        border: 2px solid #7b3fb6;
        border-radius: 2px;
        box-shadow: 0 0 0 2px #ffffff, 0 0 0 4px #7b3fb6;
    }

    .score-mark.triple-bogey > span {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        border: 2px solid #7b3fb6;
        box-sizing: border-box;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DATABASE
# ============================================================

def get_closed_events():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                e.id,
                e.name,
                e.event_date,
                e.format,
                e.season_id,
                s.name AS season_name,
                s.year,
                c.name AS course_name

            FROM events e

            INNER JOIN seasons s
                ON e.season_id = s.id

            LEFT JOIN courses c
                ON e.course_id = c.id

            WHERE
                e.status = 'CLOSED'

            ORDER BY
                e.event_date DESC,
                e.id DESC
            """,
            connection
        )

    finally:

        connection.close()


def get_event_results(event_id):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                er.player_id,
                p.name AS player_name,
                er.gross_total,
                er.net_total,
                er.ips_total,
                er.final_position,
                er.ranking_points

            FROM event_results er

            INNER JOIN players p
                ON er.player_id = p.id

            WHERE
                er.event_id = %s

            ORDER BY
                er.final_position ASC,
                p.name ASC
            """,
            connection,
            params=(int(event_id),)
        )

    finally:

        connection.close()


def ensure_event_player_status_column():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE event_players
                ADD COLUMN IF NOT EXISTS status VARCHAR(20)
                NOT NULL DEFAULT 'ACTIVE'
                """
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

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
                p.name AS player_name

            FROM event_players ep

            INNER JOIN players p
                ON ep.player_id = p.id

            WHERE
                ep.event_id = %s
                AND ep.status = 'ACTIVE'

            ORDER BY
                ep.group_number,
                p.name
            """,
            connection,
            params=(int(event_id),)
        )

    finally:

        connection.close()


ensure_event_player_status_column()


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


def get_player_hole_scores(
    event_id,
    player_id,
    score_column
):

    connection = get_connection()

    try:

        query = f"""
            SELECT
                hole_number,
                {score_column} AS score

            FROM hole_scores

            WHERE
                event_id = %s
                AND player_id = %s

            ORDER BY
                hole_number
        """

        return pd.read_sql_query(
            query,
            connection,
            params=(
                int(event_id),
                int(player_id)
            )
        )

    finally:

        connection.close()


# ============================================================
# HELPERS
# ============================================================

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
        }.get(
            position % 10,
            "th"
        )

    return f"{position}{suffix}"


def score_marker_html(score, par):
    """Return a PGA-style visual score marker around a gross score."""
    difference = int(score - par)
    value = int(score)

    if difference <= -2:
        # Eagle or better: red double circle.
        return f'<span class="score-mark eagle"><span>{value}</span></span>'
    if difference == -1:
        # Birdie: red single circle.
        return f'<span class="score-mark birdie">{value}</span>'
    if difference == 0:
        # Par: no marker.
        return f'<span class="score-mark par">{value}</span>'
    if difference == 1:
        # Bogey: blue single square.
        return f'<span class="score-mark bogey">{value}</span>'
    if difference == 2:
        # Double bogey: blue double square.
        return f'<span class="score-mark double-bogey"><span>{value}</span></span>'

    # Triple bogey or worse: purple triple square.
    return f'<span class="score-mark triple-bogey"><span><span>{value}</span></span></span>'


def render_score_table(card, title):
    """Render a compact 9-hole scorecard with PGA-style score markers."""
    rows = []

    def row_html(label, values, extra_class=""):
        cells = "".join(
            f'<td class="{extra_class}">{value}</td>'
            for value in values
        )
        return f'<tr><th>{label}</th>{cells}</tr>'

    holes = [str(int(v)) for v in card["hole_number"]]
    pars = [str(int(v)) for v in card["par"]]
    sis = [str(int(v)) for v in card["stroke_index"]]

    scores = []
    points = []
    for _, hole in card.iterrows():
        if pd.isna(hole["score"]):
            scores.append("—")
            points.append("—")
        else:
            scores.append(
                score_marker_html(
                    hole["score"],
                    hole["par"]
                )
            )
            points.append(
                "—"
                if pd.isna(hole["ips_points"])
                else str(int(hole["ips_points"]))
            )

    table = (
        '<div class="scorecard-wrap">'
        '<table class="scorecard-table">'
        + row_html("Hole", holes, "hole-number")
        + row_html("Par", pars)
        + row_html("SI", sis)
        + row_html("Score", scores, "score-cell")
        + row_html("IPS Pts", points)
        + '</table></div>'
    )

    st.markdown(f"### {title}")
    st.markdown(table, unsafe_allow_html=True)


def format_score(
    value
):

    if pd.isna(value):

        return "—"

    return f"{int(value)}"


# ============================================================
# LOAD EVENTS
# ============================================================

events = get_closed_events()


# ============================================================
# PAGE HEADER
# ============================================================

st.title(
    "📋 Event Results"
)

st.caption(
    "Official results and scorecards from "
    "completed Golfing Warriors events."
)


if events.empty:

    st.info(
        "No closed events yet. "
        "Complete an event to see the results here."
    )

    st.stop()


# ============================================================
# EVENT SELECTOR
# ============================================================

event_options = {}

for _, event in events.iterrows():

    label = (
        f"{event['name']} — "
        f"{event['event_date']} — "
        f"{event['format']}"
    )

    event_options[label] = event


selected_event_label = st.selectbox(
    "🏆 Select Event",
    list(event_options.keys())
)


event = event_options[
    selected_event_label
]

event_id = int(
    event["id"]
)


# ============================================================
# EVENT HEADER
# ============================================================

st.divider()

st.header(
    f"🏆 {event['name']}"
)

st.caption(
    f"📅 {event['event_date']}  •  "
    f"⛳ {event['course_name']}  •  "
    f"🏆 {event['format']}  •  "
    f"{event['season_name']} ({event['year']})"
)


results = get_event_results(
    event_id
)

event_players = get_event_players(
    event_id
)


if results.empty:

    st.info(
        "No results have been recorded for this event."
    )

    st.stop()


# ============================================================
# WINNER
# ============================================================

winner = results.iloc[0]

if event["format"] == "IPS":

    winner_score = (
        f"{int(winner['ips_total'])} IPS"
    )

else:

    winner_score = (
        f"{int(winner['net_total'])} Net"
    )


st.success(
    f"🥇 **{winner['player_name']}** "
    f"won with **{winner_score}**"
)

st.caption(
    f"+{float(winner['ranking_points']):g} "
    "Championship Points"
)


# ============================================================
# RESULT LEADERBOARD
# ============================================================

st.subheader(
    "🏆 Final Leaderboard"
)


leaderboard_rows = []

for _, row in results.iterrows():

    if event["format"] == "IPS":

        score = (
            f"{format_score(row['ips_total'])} IPS"
        )

    else:

        score = (
            f"{format_score(row['net_total'])} Net"
        )

    gross = format_score(
        row["gross_total"]
    )

    leaderboard_rows.append(
        {
            "Pos":
                position_label(
                    row["final_position"]
                ),

            "Player":
                row["player_name"],

            "Score":
                score,

            "Gross":
                gross,

            "Points":
                float(
                    row["ranking_points"]
                )
        }
    )


leaderboard_df = pd.DataFrame(
    leaderboard_rows
)


st.dataframe(
    leaderboard_df,
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
# SCORECARD DATA
# ============================================================

score_column = get_score_column()

if score_column is None:

    st.warning(
        "The results are available, but the "
        "hole score column could not be identified."
    )

    st.stop()


holes = get_event_holes(
    event_id
)


if holes.empty:

    st.warning(
        "This event does not have a hole snapshot available."
    )

    st.stop()


# ============================================================
# SCORECARDS
# ============================================================

st.divider()

st.header(
    "📋 Scorecards"
)

st.caption(
    "Tap a golfer below to view their complete "
    "18-hole card."
)


# Use the event result order so scorecards follow
# the official leaderboard.
for _, result in results.iterrows():

    player_id = int(
        result["player_id"]
    )

    player_name = (
        result["player_name"]
    )

    player_info = event_players[
        event_players["player_id"] == player_id
    ]

    handicap_text = ""

    group_text = ""

    if not player_info.empty:

        handicap = float(
            player_info.iloc[0][
                "event_handicap"
            ]
        )

        group_number = int(
            player_info.iloc[0][
                "group_number"
            ]
        )

        scorer = bool(
            player_info.iloc[0][
                "is_scorer"
            ]
        )

        handicap_text = (
            f"HCP {handicap:g}"
        )

        group_text = (
            f"Fourball {group_number}"
        )

        if scorer:

            group_text += " • Scorer"


    if event["format"] == "IPS":

        result_text = (
            f"{format_score(result['ips_total'])} IPS"
        )

    else:

        result_text = (
            f"{format_score(result['net_total'])} Net"
        )


    position_text = position_label(
        result["final_position"]
    )


    with st.expander(
        f"{position_text}  •  "
        f"{player_name}  •  "
        f"{result_text}"
    ):

        info_col1, info_col2, info_col3 = (
            st.columns(3)
        )

        with info_col1:

            st.metric(
                "Gross",
                format_score(
                    result["gross_total"]
                )
            )

        with info_col2:

            if event["format"] == "IPS":

                st.metric(
                    "IPS",
                    format_score(
                        result["ips_total"]
                    )
                )

            else:

                st.metric(
                    "Net",
                    format_score(
                        result["net_total"]
                    )
                )

        with info_col3:

            st.metric(
                "Championship Points",
                f"{float(result['ranking_points']):g}"
            )


        if handicap_text:

            st.caption(
                f"🏌️ {handicap_text}  •  "
                f"👥 {group_text}"
            )


        scores = get_player_hole_scores(
            event_id,
            player_id,
            score_column
        )


        card = holes.merge(
            scores,
            on="hole_number",
            how="left"
        )


        card["score"] = pd.to_numeric(
            card["score"],
            errors="coerce"
        )

        card["par"] = pd.to_numeric(
            card["par"],
            errors="coerce"
        )

        card["stroke_index"] = pd.to_numeric(
            card["stroke_index"],
            errors="coerce"
        )

        # Calculate the same IPS points used by the scoring engine so
        # every hole's points can be shown on the scorecard.
        event_handicap = None
        if not player_info.empty:
            event_handicap = float(
                player_info.iloc[0]["event_handicap"]
            )

        def hole_ips_points(row):
            if (
                pd.isna(row["score"])
                or pd.isna(row["par"])
                or pd.isna(row["stroke_index"])
                or event_handicap is None
            ):
                return pd.NA

            return int(
                calculate_ips_points(
                    int(row["score"]),
                    int(row["par"]),
                    event_handicap,
                    int(row["stroke_index"])
                )
            )

        card["ips_points"] = card.apply(
            hole_ips_points,
            axis=1
        )


        # --------------------------------------------------------
        # ROUND TOTALS - kept at the top of the scorecard to reduce scrolling
        # --------------------------------------------------------

        front = card[
            card["hole_number"] <= 9
        ].copy()

        back = card[
            card["hole_number"] >= 10
        ].copy()

        front_score = front["score"].sum(min_count=1)
        back_score = back["score"].sum(min_count=1)
        total_score = card["score"].sum(min_count=1)

        front_points = pd.to_numeric(
            front["ips_points"],
            errors="coerce"
        ).sum(min_count=1)
        back_points = pd.to_numeric(
            back["ips_points"],
            errors="coerce"
        ).sum(min_count=1)
        total_points = pd.to_numeric(
            card["ips_points"],
            errors="coerce"
        ).sum(min_count=1)

        totals_display = pd.DataFrame(
            [
                {
                    "": "Gross",
                    "OUT": format_score(front_score),
                    "IN": format_score(back_score),
                    "TOTAL": format_score(total_score)
                },
                {
                    "": "IPS Points",
                    "OUT": format_score(front_points),
                    "IN": format_score(back_points),
                    "TOTAL": format_score(total_points)
                }
            ]
        )

        st.markdown(
            "### 📊 Round Totals"
        )

        st.dataframe(
            totals_display,
            use_container_width=True,
            hide_index=True
        )


        # --------------------------------------------------------
        # FRONT 9
        # --------------------------------------------------------

        front = card[
            card["hole_number"] <= 9
        ].copy()


        render_score_table(
            front,
            "🟢 Front 9"
        )


        # --------------------------------------------------------
        # BACK 9
        # --------------------------------------------------------

        back = card[
            card["hole_number"] >= 10
        ].copy()


        render_score_table(
            back,
            "🔵 Back 9"
        )


        # --------------------------------------------------------
        # ROUND SUMMARY
        # --------------------------------------------------------

        st.markdown(
            "### 📊 Round Summary"
        )


        valid_scores = card.dropna(
            subset=["score"]
        )


        if not valid_scores.empty:

            to_par = (
                valid_scores["score"]
                - valid_scores["par"]
            )

            birdies = int(
                (to_par == -1).sum()
            )

            eagles = int(
                (to_par <= -2).sum()
            )

            pars = int(
                (to_par == 0).sum()
            )

            bogeys = int(
                (to_par == 1).sum()
            )

            doubles = int(
                (to_par >= 2).sum()
            )


            summary1, summary2 = (
                st.columns(2)
            )

            with summary1:

                st.metric(
                    "🦅 Eagles+",
                    eagles
                )

                st.metric(
                    "🐦 Birdies",
                    birdies
                )

                st.metric(
                    "⛳ Pars",
                    pars
                )


            with summary2:

                st.metric(
                    "😬 Bogeys",
                    bogeys
                )

                st.metric(
                    "💀 Double+",
                    doubles
                )

                st.metric(
                    "Gross",
                    format_score(
                        valid_scores[
                            "score"
                        ].sum()
                    )
                )


        st.caption(
            "Legend: 🦅 Eagle or better  •  "
            "🐦 Birdie  •  • Par  •  "
            "○ Bogey  •  × Double bogey+"
        )


# ============================================================
# NAVIGATION
# ============================================================

st.divider()

nav1, nav2, nav3 = st.columns(3)


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
        "👤 Player Profiles",
        use_container_width=True
    ):

        st.switch_page(
            "pages/player_profiles.py"
        )


with nav3:

    if st.button(
        "⛳ Golf Statistics",
        use_container_width=True
    ):

        st.switch_page(
            "pages/golf_statistics.py"
        )


st.caption(
    "🏌️ Golfing Warriors • "
    "Your friends. Your golf. Your championship."
)
