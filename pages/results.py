
import streamlit as st
from pathlib import Path
import pandas as pd

from database import get_connection
from auth import is_admin as auth_is_admin

from scoring.scoring_engine import (
    calculate_ips_points,
    calculate_player_round,
    rank_completed_players,
    allocate_ranking_points,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors - Results",
    page_icon=str(Path(__file__).resolve().parent.parent / "assets" / "golfing-warriors-icon.png"),
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


def get_event_par_total(event_id):
    connection = get_connection()
    try:
        result = pd.read_sql_query(
            """
            SELECT COALESCE(SUM(par), 0) AS total_par
            FROM event_holes
            WHERE event_id = %s
            """,
            connection,
            params=(int(event_id),)
        )
        return int(result.iloc[0]["total_par"])
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



def recalculate_closed_event_after_score_correction(
    event_id,
    player_id,
    hole_number,
    gross_score
):
    """Save one admin correction and rebuild its official results atomically."""
    if not auth_is_admin():
        raise PermissionError("Admin access is required to correct completed scores.")

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status, format
                FROM events
                WHERE id = %s
                FOR UPDATE
                """,
                (int(event_id),)
            )
            event_row = cursor.fetchone()
            if event_row is None or event_row[0] != "CLOSED":
                raise ValueError("Only completed events can be corrected here.")

            cursor.execute(
                """
                SELECT 1
                FROM event_players
                WHERE event_id = %s AND player_id = %s AND status = 'ACTIVE'
                """,
                (int(event_id), int(player_id))
            )
            if cursor.fetchone() is None:
                raise ValueError("The selected player is not active in this event.")

            cursor.execute(
                """
                SELECT 1
                FROM event_holes
                WHERE event_id = %s AND hole_number = %s
                """,
                (int(event_id), int(hole_number))
            )
            if cursor.fetchone() is None:
                raise ValueError("The selected hole is not part of this event.")

            cursor.execute(
                """
                INSERT INTO hole_scores
                    (event_id, player_id, hole_number, gross_score, recorded_by_player_id)
                VALUES (%s, %s, %s, %s, NULL)
                ON CONFLICT (event_id, player_id, hole_number)
                DO UPDATE SET
                    gross_score = EXCLUDED.gross_score,
                    recorded_by_player_id = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    int(event_id),
                    int(player_id),
                    int(hole_number),
                    int(gross_score)
                )
            )

        event_format = str(event_row[1])
        players_df = pd.read_sql_query(
            """
            SELECT ep.player_id, ep.event_handicap, p.name
            FROM event_players ep
            INNER JOIN players p ON p.id = ep.player_id
            WHERE ep.event_id = %s AND ep.status = 'ACTIVE'
            ORDER BY p.name
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
        if players_df.empty:
            raise ValueError("This event has no active players to recalculate.")
        if len(holes_df) != 18:
            raise ValueError("This event must have all 18 holes configured.")

        ranking_df = pd.read_sql_query(
            """
            SELECT position, points
            FROM ranking_settings
            WHERE active = TRUE
            ORDER BY position
            """,
            connection
        )

        holes = holes_df.to_dict("records")
        score_dicts = {}
        for _, score in scores_df.iterrows():
            score_dicts.setdefault(int(score["player_id"]), {})[
                int(score["hole_number"])
            ] = int(score["gross_score"])

        round_results = []
        for player in players_df.to_dict("records"):
            player_id = int(player["player_id"])
            result = calculate_player_round(
                player,
                holes,
                score_dicts.get(player_id, {})
            )
            if result["completed"] != 18:
                raise ValueError(
                    f"{result['name']} must have 18 saved holes before the event can be recalculated."
                )
            round_results.append(result)

        ranked_results = rank_completed_players(round_results, event_format)
        ranking_points = {
            int(row["position"]): float(row["points"])
            for _, row in ranking_df.iterrows()
        }
        final_results = allocate_ranking_points(
            ranked_results,
            ranking_points,
            event_format
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM event_results WHERE event_id = %s",
                (int(event_id),)
            )
            cursor.execute(
                "DELETE FROM ranking_points WHERE event_id = %s",
                (int(event_id),)
            )

            for result in final_results:
                if event_format == "NET":
                    last_6 = result["last_6_net"]
                    last_3 = result["last_3_net"]
                    last_hole = result["last_hole_net"]
                else:
                    last_6 = result["last_6_ips"]
                    last_3 = result["last_3_ips"]
                    last_hole = result["last_hole_ips"]

                cursor.execute(
                    """
                    INSERT INTO event_results
                        (
                            event_id, player_id, gross_total, net_total, ips_total,
                            last_6_score, last_3_score, last_hole_score,
                            final_position, ranking_points
                        )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(event_id),
                        int(result["player_id"]),
                        int(result["gross_total"]),
                        int(result["net_total"]),
                        int(result["ips_total"]),
                        int(last_6),
                        int(last_3),
                        int(last_hole),
                        int(result["final_position"]),
                        float(result["ranking_points"])
                    )
                )
                cursor.execute(
                    """
                    INSERT INTO ranking_points
                        (season_id, event_id, player_id, points)
                    SELECT season_id, %s, %s, %s
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

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def get_closed_event_ranking_rows():
    connection = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                e.id AS event_id,
                e.name AS event_name,
                e.event_date,
                er.player_id,
                p.name AS player_name,
                er.net_total,
                er.final_position,
                er.ranking_points AS result_points,
                rp.points AS ledger_points
            FROM events e
            LEFT JOIN event_results er ON er.event_id = e.id
            LEFT JOIN players p ON p.id = er.player_id
            LEFT JOIN ranking_points rp
                ON rp.event_id = er.event_id
                AND rp.player_id = er.player_id
            WHERE e.status = 'CLOSED'
            ORDER BY e.event_date DESC, e.id DESC, er.final_position, p.name
            """,
            connection
        )
    finally:
        connection.close()


def build_historical_ranking_reallocation_plan(rows_df):
    """Re-rank closed events by net-to-par while preserving each event's point scale."""
    changes = []
    unresolved = []

    if rows_df.empty:
        return changes, unresolved

    for event_id, event_rows in rows_df.groupby("event_id", sort=False):
        event_rows = event_rows.copy()
        event_name = str(event_rows.iloc[0]["event_name"])
        saved_positions = pd.to_numeric(
            event_rows["final_position"],
            errors="coerce"
        )
        saved_points = pd.to_numeric(
            event_rows["result_points"],
            errors="coerce"
        )

        player_count = len(event_rows)
        if (
            event_rows["player_id"].isna().any()
            or pd.to_numeric(event_rows["net_total"], errors="coerce").isna().any()
        ):
            unresolved.append({
                "Event": event_name,
                "Event ID": int(event_id),
                "Reason": "The closed event is missing a complete result row."
            })
            continue

        position_values = [
            int(value) for value in saved_positions if pd.notna(value)
        ]
        if (
            len(position_values) != player_count
            or len(set(position_values)) != player_count
            or sorted(position_values) != list(range(1, player_count + 1))
            or saved_points.isna().any()
        ):
            unresolved.append({
                "Event": event_name,
                "Event ID": int(event_id),
                "Reason": (
                    "Existing places include ties, gaps, or missing values; "
                    "the historical point scale cannot be reconstructed safely."
                )
            })
            continue

        points_by_position = {
            int(row["final_position"]): float(row["result_points"])
            for _, row in event_rows.iterrows()
        }
        ordered = event_rows.sort_values(
            by=["net_total", "player_name"],
            ascending=[True, True],
            kind="stable"
        ).reset_index(drop=True)

        index = 0
        while index < player_count:
            score = int(ordered.iloc[index]["net_total"])
            end_index = index + 1
            while (
                end_index < player_count
                and int(ordered.iloc[end_index]["net_total"]) == score
            ):
                end_index += 1

            first_position = index + 1
            occupied_positions = range(first_position, end_index + 1)
            allocated_points = sum(
                points_by_position[position]
                for position in occupied_positions
            ) / (end_index - index)

            for row_index in range(index, end_index):
                row = ordered.iloc[row_index]
                new_position = first_position
                new_points = allocated_points
                old_position = int(row["final_position"])
                old_points = float(row["result_points"])
                ledger_value = row["ledger_points"]
                ledger_mismatch = (
                    pd.isna(ledger_value)
                    or abs(float(ledger_value) - old_points) > 0.0001
                )
                if (
                    old_position != new_position
                    or abs(old_points - new_points) > 0.0001
                    or ledger_mismatch
                ):
                    changes.append({
                        "Event": event_name,
                        "Event ID": int(event_id),
                        "Player ID": int(row["player_id"]),
                        "Player": row["player_name"],
                        "Old Pos": old_position,
                        "New Pos": new_position,
                        "Old Points": old_points,
                        "New Points": new_points,
                        "Old Ledger Points": ledger_value
                    })

            index = end_index

    return changes, unresolved


def reallocate_closed_event_rankings_to_par():
    """Update all safely reconstructable closed events to score-to-par places."""
    if not auth_is_admin():
        raise PermissionError("Admin access is required to recalculate event rankings.")

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM events WHERE status = 'CLOSED' FOR UPDATE"
            )

        rows_df = pd.read_sql_query(
            """
            SELECT
                e.id AS event_id,
                e.name AS event_name,
                e.event_date,
                er.player_id,
                p.name AS player_name,
                er.net_total,
                er.final_position,
                er.ranking_points AS result_points,
                rp.points AS ledger_points
            FROM events e
            LEFT JOIN event_results er ON er.event_id = e.id
            LEFT JOIN players p ON p.id = er.player_id
            LEFT JOIN ranking_points rp
                ON rp.event_id = er.event_id
                AND rp.player_id = er.player_id
            WHERE e.status = 'CLOSED'
            ORDER BY e.event_date DESC, e.id DESC, er.final_position, p.name
            """,
            connection
        )
        changes, unresolved = build_historical_ranking_reallocation_plan(rows_df)

        with connection.cursor() as cursor:
            for row in changes:
                cursor.execute(
                    """
                    UPDATE event_results
                    SET final_position = %s, ranking_points = %s
                    WHERE event_id = %s AND player_id = %s
                    """,
                    (
                        int(row["New Pos"]),
                        float(row["New Points"]),
                        int(row["Event ID"]),
                        int(row["Player ID"])
                    )
                )
                cursor.execute(
                    """
                    INSERT INTO ranking_points
                        (season_id, event_id, player_id, points)
                    SELECT season_id, %s, %s, %s
                    FROM events
                    WHERE id = %s
                    ON CONFLICT (event_id, player_id)
                    DO UPDATE SET points = EXCLUDED.points
                    """,
                    (
                        int(row["Event ID"]),
                        int(row["Player ID"]),
                        float(row["New Points"]),
                        int(row["Event ID"])
                    )
                )

        connection.commit()
        return changes, unresolved
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# ============================================================
# HELPERS
# ============================================================

def position_label(position, tied=False):

    if pd.isna(position):
        return "—"

    position = int(position)
    if tied:
        return f"T{position}"

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


def format_to_par(value):
    if pd.isna(value):
        return "—"
    value = int(value)
    return "E" if value == 0 else f"{value:+d}"


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

if not results.empty:
    event_par_total = get_event_par_total(event_id)
    results["to_par"] = results["net_total"] - event_par_total
    results = results.sort_values(
        by=["to_par", "final_position", "player_name"],
        ascending=[True, True, True],
        kind="stable"
    ).reset_index(drop=True)
    to_par_values = results["to_par"].tolist()
    tied_positions = {}
    display_positions = []
    for index, to_par in enumerate(to_par_values):
        if to_par not in tied_positions:
            tied_positions[to_par] = index + 1
        position = tied_positions[to_par]
        tied = to_par_values.count(to_par) > 1
        display_positions.append(position_label(position, tied=tied))
    results["display_position"] = display_positions

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

winner_score = format_to_par(winner["to_par"])
winner_is_tied = (
    int((results["to_par"] == winner["to_par"]).sum()) > 1
)
if winner_is_tied:
    tied_winners = results[
        results["to_par"] == winner["to_par"]
    ]["player_name"].tolist()
    st.success(
        f"🏆 **Tied for first: {', '.join(tied_winners)}** "
        f"with **{winner_score} to par**"
    )
else:
    st.success(
        f"🥇 **{winner['player_name']}** "
        f"won with **{winner_score} to par**"
    )

st.caption(
    "Finishing positions and championship points are based on net score to par. "
    "The IPS column shows each player's Stableford-style total."
)


# RESULT LEADERBOARD
# ============================================================

st.subheader(
    "🏆 Final Leaderboard — Sorted by To Par"
)


leaderboard_rows = []

for _, row in results.iterrows():

    score = format_to_par(row["to_par"])

    gross = format_score(
        row["gross_total"]
    )

    leaderboard_rows.append(
        {
            "Pos":
                row["display_position"],

            "Player":
                row["player_name"],

            "To Par":
                score,

            "IPS Pts":
                int(row["ips_total"]),

            "Gross":
                gross,

            "Ranking Points":
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
        "Ranking Points":
            st.column_config.NumberColumn(
                "Ranking Points",
                format="%.0f"
            )
    }
)


if auth_is_admin():
    with st.expander("🔎 Admin: Audit past event ranking points"):
        st.info(
            "This checks every completed event. It reorders positions by net score "
            "to par and preserves each event's recorded points-per-place scale. "
            "Events with old tied, missing, or incomplete places are flagged for "
            "review instead of being changed automatically."
        )
        preview_key = "historical_ranking_to_par_preview"
        if st.button(
            "Preview all completed events",
            key="preview_historical_ranking_to_par",
            use_container_width=True
        ):
            history_rows = get_closed_event_ranking_rows()
            changes, unresolved = build_historical_ranking_reallocation_plan(
                history_rows
            )
            st.session_state[preview_key] = {
                "changes": changes,
                "unresolved": unresolved
            }

        preview = st.session_state.get(preview_key)
        if preview is not None:
            changes = preview["changes"]
            unresolved = preview["unresolved"]

            if changes:
                st.warning(
                    f"{len(changes)} player result(s) need updated positions "
                    "or ranking points."
                )
                st.dataframe(
                    pd.DataFrame(changes)[
                        [
                            "Event", "Player", "Old Pos", "New Pos",
                            "Old Points", "New Points", "Old Ledger Points"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )
                if st.button(
                    "Apply score-to-par places to the listed events",
                    type="primary",
                    key="apply_historical_ranking_to_par",
                    use_container_width=True
                ):
                    try:
                        applied, still_unresolved = (
                            reallocate_closed_event_rankings_to_par()
                        )
                        st.session_state.pop(preview_key, None)
                        st.success(
                            f"Updated {len(applied)} player result(s) across "
                            "completed events."
                        )
                        if still_unresolved:
                            st.warning(
                                f"{len(still_unresolved)} event(s) still need "
                                "manual review because their former point scale "
                                "could not be reconstructed safely."
                            )
                        st.rerun()
                    except Exception as error:
                        st.error("Unable to update historical event rankings.")
                        st.exception(error)
            else:
                st.success(
                    "No safely reconstructable completed-event rows need changes."
                )

            if unresolved:
                st.warning(
                    "Some events have existing ties, missing places, or incomplete "
                    "results. They were not changed automatically."
                )
                st.dataframe(
                    pd.DataFrame(unresolved),
                    use_container_width=True,
                    hide_index=True
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


if auth_is_admin():
    st.divider()
    success_key = f"score_correction_success_{event_id}"
    if st.session_state.pop(success_key, False):
        st.success(
            "Score corrected. Event results and ranking points have been recalculated."
        )

    with st.expander("🔐 Admin: Correct a completed event score"):
        st.warning(
            "Changes are saved to the completed event and its official results "
            "and ranking points are recalculated immediately."
        )

        if event_players.empty:
            st.info("There are no active event players to edit.")
        else:
            player_options = {
                int(row["player_id"]): row["player_name"]
                for _, row in event_players.iterrows()
            }
            correction_player_id = st.selectbox(
                "Player",
                options=list(player_options),
                format_func=lambda player_id: player_options[int(player_id)],
                key=f"correction_player_{event_id}"
            )
            correction_hole = st.selectbox(
                "Hole",
                options=list(range(1, 19)),
                format_func=lambda hole: f"Hole {hole}",
                key=f"correction_hole_{event_id}_{correction_player_id}"
            )

            saved_scores = get_player_hole_scores(
                event_id,
                correction_player_id,
                score_column
            )
            existing_score_rows = saved_scores[
                saved_scores["hole_number"] == correction_hole
            ]
            existing_score = (
                int(existing_score_rows.iloc[0]["score"])
                if not existing_score_rows.empty
                and pd.notna(existing_score_rows.iloc[0]["score"])
                else None
            )
            st.caption(
                f"Currently saved: {existing_score if existing_score is not None else 'no score'}"
            )
            corrected_score = st.number_input(
                "Correct gross score",
                min_value=1,
                max_value=99,
                value=existing_score if existing_score is not None else 4,
                step=1,
                key=f"correction_score_{event_id}_{correction_player_id}_{correction_hole}"
            )

            if st.button(
                "Save correction and recalculate",
                type="primary",
                key=f"save_score_correction_{event_id}",
                use_container_width=True
            ):
                try:
                    recalculate_closed_event_after_score_correction(
                        event_id,
                        correction_player_id,
                        correction_hole,
                        corrected_score
                    )
                    st.session_state[success_key] = True
                    st.rerun()
                except Exception as error:
                    st.error("Unable to correct this event score.")
                    st.exception(error)


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


    position_text = result["display_position"]


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
