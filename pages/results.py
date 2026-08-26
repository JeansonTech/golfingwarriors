import streamlit as st
import pandas as pd

from database import get_connection


st.set_page_config(
    page_title="Golfing Warriors - Results",
    page_icon="🏆",
    layout="wide"
)


# ============================================================
# DATABASE FUNCTIONS
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
                e.status,
                s.name AS season_name,
                c.name AS course_name
            FROM events e

            LEFT JOIN seasons s
                ON e.season_id = s.id

            LEFT JOIN courses c
                ON e.course_id = c.id

            WHERE e.status = 'CLOSED'

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
                p.name,
                p.nickname,

                ep.event_handicap,

                er.gross_total,
                er.net_total,
                er.ips_total,

                er.last_6_score,
                er.last_3_score,
                er.last_hole_score,

                er.final_position,
                er.ranking_points

            FROM event_results er

            INNER JOIN players p
                ON er.player_id = p.id

            LEFT JOIN event_players ep
                ON ep.event_id = er.event_id
                AND ep.player_id = er.player_id

            WHERE er.event_id = %s

            ORDER BY
                er.final_position ASC
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


def get_event_info(event_id):

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

                c.name AS course_name,
                c.location AS course_location

            FROM events e

            LEFT JOIN seasons s
                ON e.season_id = s.id

            LEFT JOIN courses c
                ON e.course_id = c.id

            WHERE e.id = %s
            """,
            connection,
            params=(int(event_id),)
        )

    finally:

        connection.close()


# ============================================================
# PAGE
# ============================================================

st.title("🏆 Event Results")

st.caption(
    "View official results from completed Golfing Warriors events."
)

st.divider()


# ============================================================
# LOAD EVENTS
# ============================================================

events = get_closed_events()


if events.empty:

    st.info(
        "There are no completed events yet."
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

    event_options[
        label
    ] = int(event["id"])


selected_event_label = st.selectbox(
    "Select Event",
    list(event_options.keys())
)


event_id = event_options[
    selected_event_label
]


# ============================================================
# EVENT INFORMATION
# ============================================================

event_info_df = get_event_info(
    event_id
)


if event_info_df.empty:

    st.error(
        "Unable to load event information."
    )

    st.stop()


event = event_info_df.iloc[0]


# ============================================================
# EVENT HEADER
# ============================================================

st.success(
    f"🔒 {event['name']} — CLOSED"
)


st.markdown(
    f"# {event['name']}"
)


info_col1, info_col2, info_col3, info_col4 = st.columns(4)


with info_col1:

    st.metric(
        "Date",
        str(event["event_date"])
    )


with info_col2:

    st.metric(
        "Format",
        event["format"]
    )


with info_col3:

    st.metric(
        "Course",
        event["course_name"]
    )


with info_col4:

    st.metric(
        "Season",
        event["season_name"]
    )


if pd.notna(
    event["course_location"]
):

    st.caption(
        f"📍 {event['course_location']}"
    )


# ============================================================
# RESULTS
# ============================================================

results = get_event_results(
    event_id
)


if results.empty:

    st.warning(
        "This event has no recorded results."
    )

    st.stop()


# ============================================================
# WINNER
# ============================================================

winner = results.iloc[0]


st.divider()

st.subheader(
    "🥇 Event Winner"
)


winner_col1, winner_col2, winner_col3 = st.columns(3)


with winner_col1:

    st.markdown(
        f"## 🏆 {winner['name']}"
    )


with winner_col2:

    if event["format"] == "IPS":

        st.metric(
            "Winning IPS",
            int(winner["ips_total"])
        )

    else:

        st.metric(
            "Winning Net",
            int(winner["net_total"])
        )


with winner_col3:

    st.metric(
        "Ranking Points",
        float(winner["ranking_points"])
    )


# ============================================================
# FULL RESULTS
# ============================================================

st.divider()

st.subheader(
    "📊 Official Results"
)


display_rows = []


for _, result in results.iterrows():

    position = int(
        result["final_position"]
    )

    # --------------------------------------------------------
    # POSITION DISPLAY
    # --------------------------------------------------------

    if position == 1:

        position_display = "🥇 1"

    elif position == 2:

        position_display = "🥈 2"

    elif position == 3:

        position_display = "🥉 3"

    else:

        position_display = str(
            position
        )


    display_rows.append(
        {
            "Pos":
                position_display,

            "Player":
                result["name"],

            "HCP":
                float(
                    result[
                        "event_handicap"
                    ]
                ),

            "Gross":
                int(
                    result[
                        "gross_total"
                    ]
                ),

            "Net":
                int(
                    result[
                        "net_total"
                    ]
                ),

            "IPS":
                int(
                    result[
                        "ips_total"
                    ]
                ),

            "Last 6":
                int(
                    result[
                        "last_6_score"
                    ]
                ),

            "Last 3":
                int(
                    result[
                        "last_3_score"
                    ]
                ),

            "Hole 18":
                int(
                    result[
                        "last_hole_score"
                    ]
                ),

            "Ranking Points":
                float(
                    result[
                        "ranking_points"
                    ]
                )
        }
    )


results_display = pd.DataFrame(
    display_rows
)


st.dataframe(
    results_display,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# FORMAT EXPLANATION
# ============================================================

st.divider()

if event["format"] == "IPS":

    st.info(
        """
        **IPS event**

        Players are ranked by highest total IPS points.

        Tie-break:
        1. Highest IPS
        2. Highest IPS over the last 6 holes
        3. Highest IPS over the last 3 holes
        4. Highest IPS on hole 18
        """
    )

else:

    st.info(
        """
        **NET event**

        Players are ranked by lowest total net score.

        Tie-break:
        1. Lowest Net
        2. Lowest Net over the last 6 holes
        3. Lowest Net over the last 3 holes
        4. Lowest Net on hole 18
        """
    )


# ============================================================
# RANKING POINTS
# ============================================================

st.divider()

st.subheader(
    "🏆 Ranking Points Awarded"
)


ranking_display = results[
    [
        "final_position",
        "name",
        "ranking_points"
    ]
].copy()


ranking_display.columns = [
    "Position",
    "Player",
    "Points"
]


ranking_display["Position"] = (
    ranking_display["Position"]
    .astype(int)
)


ranking_display["Points"] = (
    ranking_display["Points"]
    .astype(float)
)


st.dataframe(
    ranking_display,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# COURSE SNAPSHOT
# ============================================================

st.divider()

with st.expander(
    "⛳ View Event Course / Stroke Index"
):

    event_holes = get_event_holes(
        event_id
    )


    if event_holes.empty:

        st.info(
            "No course hole information available."
        )

    else:

        course_display = (
            event_holes.copy()
        )

        course_display.columns = [
            "Hole",
            "Par",
            "Stroke Index"
        ]

        st.dataframe(
            course_display,
            use_container_width=True,
            hide_index=True
        )


        st.caption(
            "This is the course snapshot saved "
            "with the event. Changes made to the "
            "master course later do not affect this event."
        )


# ============================================================
# PLAYER DETAIL
# ============================================================

st.divider()

st.subheader(
    "🔎 Player Detail"
)


player_options = {
    result["name"]:
        int(result["player_id"])
    for _, result in results.iterrows()
}


selected_player_name = st.selectbox(
    "Select a player to view their result",
    list(player_options.keys())
)


selected_player_id = player_options[
    selected_player_name
]


player_result = results[
    results["player_id"]
    == selected_player_id
].iloc[0]


detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)


with detail_col1:

    st.metric(
        "Handicap",
        float(
            player_result[
                "event_handicap"
            ]
        )
    )


with detail_col2:

    st.metric(
        "Gross",
        int(
            player_result[
                "gross_total"
            ]
        )
    )


with detail_col3:

    st.metric(
        "Net",
        int(
            player_result[
                "net_total"
            ]
        )
    )


with detail_col4:

    st.metric(
        "IPS",
        int(
            player_result[
                "ips_total"
            ]
        )
    )


tie_col1, tie_col2, tie_col3 = st.columns(3)


with tie_col1:

    st.metric(
        "Last 6",
        int(
            player_result[
                "last_6_score"
            ]
        )
    )


with tie_col2:

    st.metric(
        "Last 3",
        int(
            player_result[
                "last_3_score"
            ]
        )
    )


with tie_col3:

    st.metric(
        "Hole 18",
        int(
            player_result[
                "last_hole_score"
            ]
        )
    )


st.success(
    f"🏆 Final Position: "
    f"{int(player_result['final_position'])}"
)


st.success(
    f"⭐ Ranking Points: "
    f"{float(player_result['ranking_points'])}"
)
