
import streamlit as st
import pandas as pd

from database import get_connection


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors - Golf Statistics",
    page_icon="⛳",
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
# DATABASE HELPERS
# ============================================================

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


def get_players():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                nickname,
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


def get_hole_score_columns():

    """
    Discover the actual hole_scores columns at runtime.

    This makes the statistics page safer if the scoring table
    has a slightly different score-column name.
    """

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

        return [
            str(value)
            for value in columns[
                "column_name"
            ].tolist()
        ]

    finally:

        connection.close()


def choose_score_column(columns):

    candidates = [
        "gross_score",
        "score",
        "strokes",
        "gross_strokes",
        "actual_score"
    ]

    lower_map = {
        column.lower(): column
        for column in columns
    }

    for candidate in candidates:

        if candidate in lower_map:

            return lower_map[candidate]

    return None


def quote_identifier(identifier):
    """Safely quote a PostgreSQL identifier discovered from the database."""
    return '"' + str(identifier).replace('"', '""') + '"'


def get_hole_statistics(
    player_id=None,
    season_id=None,
    course_id=None,
    event_id=None,
    score_column=None
):

    connection = get_connection()

    try:

        filters = [
            "e.status = 'CLOSED'"
        ]

        params = []

        if player_id is not None:

            filters.append(
                "hs.player_id = %s"
            )

            params.append(
                int(player_id)
            )

        if season_id is not None:

            filters.append(
                "e.season_id = %s"
            )

            params.append(
                int(season_id)
            )

        if course_id is not None:

            filters.append(
                "e.course_id = %s"
            )

            params.append(
                int(course_id)
            )

        if event_id is not None:

            filters.append(
                "e.id = %s"
            )

            params.append(
                int(event_id)
            )

        if score_column is None:
            raise ValueError("No hole-score column was supplied.")

        score_identifier = quote_identifier(score_column)

        where_clause = " AND ".join(
            filters
        )

        return pd.read_sql_query(
            f"""
            SELECT
                hs.event_id,
                hs.player_id,
                hs.hole_number,
                {score_identifier} AS score,
                eh.par,
                eh.stroke_index,
                e.name AS event_name,
                e.event_date,
                e.format,
                c.name AS course_name,
                p.name AS player_name

            FROM hole_scores hs

            INNER JOIN events e
                ON hs.event_id = e.id

            LEFT JOIN courses c
                ON e.course_id = c.id

            INNER JOIN event_holes eh
                ON eh.event_id = hs.event_id
                AND eh.hole_number = hs.hole_number

            INNER JOIN players p
                ON p.id = hs.player_id

            WHERE
                {where_clause}

            ORDER BY
                e.event_date ASC,
                e.id ASC,
                hs.hole_number ASC
            """,
            connection,
            params=params
        )

    finally:

        connection.close()


def get_event_hole_averages(
    season_id=None,
    course_id=None,
    event_id=None,
    score_column=None
):

    connection = get_connection()

    try:

        filters = [
            "e.status = 'CLOSED'"
        ]

        params = []

        if season_id is not None:

            filters.append(
                "e.season_id = %s"
            )

            params.append(
                int(season_id)
            )

        if course_id is not None:

            filters.append(
                "e.course_id = %s"
            )

            params.append(
                int(course_id)
            )

        if event_id is not None:

            filters.append(
                "e.id = %s"
            )

            params.append(
                int(event_id)
            )

        if score_column is None:
            raise ValueError("No hole-score column was supplied.")

        score_identifier = quote_identifier(score_column)

        where_clause = " AND ".join(
            filters
        )

        return pd.read_sql_query(
            f"""
            SELECT
                c.name AS course_name,
                hs.hole_number,
                eh.par,
                eh.stroke_index,

                AVG(
                    {score_identifier}
                ) AS average_score,

                AVG(
                    {score_identifier} - eh.par
                ) AS average_to_par,

                COUNT(*) AS scores_recorded

            FROM hole_scores hs

            INNER JOIN events e
                ON hs.event_id = e.id

            INNER JOIN event_holes eh
                ON eh.event_id = hs.event_id
                AND eh.hole_number = hs.hole_number

            WHERE
                {where_clause}

            GROUP BY
                c.name,
                hs.hole_number,
                eh.par,
                eh.stroke_index

            ORDER BY
                c.name,
                hs.hole_number
            """,
            connection,
            params=params
        )

    finally:

        connection.close()


# ============================================================
# PAGE HEADER
# ============================================================

st.title(
    "⛳ Golf Statistics"
)

st.caption(
    "The numbers behind the Golfing Warriors."
)


players = get_players()


# ============================================================
# SCORE COLUMN
# ============================================================

try:

    score_columns = get_hole_score_columns()

except Exception as error:

    st.error(
        "Unable to inspect the hole scoring table."
    )

    st.exception(error)

    st.stop()


score_column = choose_score_column(
    score_columns
)


if score_column is None:

    st.error(
        "The hole_scores table was found, but "
        "the score column could not be identified."
    )

    st.caption(
        "Columns found: "
        + ", ".join(score_columns)
    )

    st.stop()


if players.empty:

    st.info(
        "No players have been created yet."
    )

    st.stop()


# ============================================================
# FILTER DATA
# ============================================================

def get_all_seasons():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                year
            FROM seasons
            ORDER BY year DESC, id DESC
            """,
            connection
        )

    finally:

        connection.close()


def get_all_courses():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                location
            FROM courses
            WHERE active = TRUE
            ORDER BY name
            """,
            connection
        )

    finally:

        connection.close()


def get_filter_events(
    season_id=None,
    course_id=None
):

    connection = get_connection()

    try:

        filters = [
            "e.status = 'CLOSED'"
        ]

        params = []

        if season_id is not None:

            filters.append(
                "e.season_id = %s"
            )

            params.append(
                int(season_id)
            )

        if course_id is not None:

            filters.append(
                "e.course_id = %s"
            )

            params.append(
                int(course_id)
            )

        where_clause = " AND ".join(filters)

        return pd.read_sql_query(
            f"""
            SELECT
                e.id,
                e.name,
                e.event_date,
                e.course_id,
                c.name AS course_name
            FROM events e
            LEFT JOIN courses c
                ON e.course_id = c.id
            WHERE
                {where_clause}
            ORDER BY
                e.event_date DESC,
                e.id DESC
            """,
            connection,
            params=params
        )

    finally:

        connection.close()


seasons = get_all_seasons()
courses = get_all_courses()


# ============================================================
# FILTERS
# ============================================================

st.subheader("🔎 Filter Statistics")

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)


with filter_col1:

    player_options = {
        "All Golfers": None
    }

    for _, player in players.iterrows():

        label = player["name"]

        if (
            pd.notna(player["nickname"])
            and player["nickname"]
        ):

            label += (
                f" ({player['nickname']})"
            )

        player_options[label] = int(
            player["id"]
        )

    selected_player_label = st.selectbox(
        "🏌️ Golfer",
        list(player_options.keys())
    )


with filter_col2:

    season_options = {
        "All Seasons": None
    }

    for _, season in seasons.iterrows():

        season_options[
            f"{season['name']} ({season['year']})"
        ] = int(
            season["id"]
        )

    selected_season_label = st.selectbox(
        "🏆 Season",
        list(season_options.keys())
    )


selected_season_id = season_options[
    selected_season_label
]


with filter_col3:

    course_options = {
        "All Courses": None
    }

    for _, course in courses.iterrows():

        label = str(course["name"])

        if (
            pd.notna(course["location"])
            and course["location"]
        ):

            label += (
                f" — {course['location']}"
            )

        course_options[label] = int(
            course["id"]
        )

    selected_course_label = st.selectbox(
        "⛳ Course",
        list(course_options.keys())
    )


selected_course_id = course_options[
    selected_course_label
]


with filter_col4:

    filter_events = get_filter_events(
        season_id=selected_season_id,
        course_id=selected_course_id
    )

    event_options = {
        "All Rounds": None
    }

    for _, event in filter_events.iterrows():

        event_label = (
            f"{event['name']} — "
            f"{event['event_date']}"
        )

        event_options[event_label] = int(
            event["id"]
        )

    selected_event_label = st.selectbox(
        "🏌️ Round / Event",
        list(event_options.keys())
    )


selected_event_id = event_options[
    selected_event_label
]


# ============================================================
# FILTER SUMMARY
# ============================================================

summary_bits = []

if selected_season_label != "All Seasons":
    summary_bits.append(
        f"🏆 {selected_season_label}"
    )

if selected_course_label != "All Courses":
    summary_bits.append(
        f"⛳ {selected_course_label}"
    )

if selected_event_label != "All Rounds":
    summary_bits.append(
        f"🏌️ {selected_event_label}"
    )

if selected_player_label != "All Golfers":
    summary_bits.append(
        f"👤 {selected_player_label}"
    )

if summary_bits:

    st.caption(
        "Showing: " + "  •  ".join(summary_bits)
    )

else:

    st.caption(
        "Showing all completed rounds and all golfers."
    )


# ============================================================
# LOAD HOLE DATA
# ============================================================

try:

    hole_data = get_hole_statistics(
        player_id=selected_player_id,
        season_id=selected_season_id,
        course_id=selected_course_id,
        event_id=selected_event_id,
        score_column=score_column
    )

except Exception as error:

    st.error(
        "Unable to load golf statistics."
    )

    st.exception(error)

    st.stop()


if hole_data.empty:

    st.divider()

    st.info(
        "No completed hole scores match "
        "the selected filters yet."
    )

    st.stop()


hole_data["score"] = pd.to_numeric(
    hole_data["score"],
    errors="coerce"
)

hole_data["par"] = pd.to_numeric(
    hole_data["par"],
    errors="coerce"
)

hole_data = hole_data.dropna(
    subset=[
        "score",
        "par"
    ]
)

hole_data["to_par"] = (
    hole_data["score"]
    - hole_data["par"]
)


# ============================================================
# SUMMARY METRICS
# ============================================================

st.divider()

st.header(
    "📊 Scoring Summary"
)


total_holes = len(
    hole_data
)

total_strokes = (
    hole_data["score"]
    .sum()
)

total_par = (
    hole_data["par"]
    .sum()
)

average_score = (
    hole_data["score"]
    .mean()
)

average_to_par = (
    hole_data["to_par"]
    .mean()
)

birdies = int(
    (
        hole_data["to_par"] == -1
    ).sum()
)

eagles_or_better = int(
    (
        hole_data["to_par"] <= -2
    ).sum()
)

pars = int(
    (
        hole_data["to_par"] == 0
    ).sum()
)

bogeys = int(
    (
        hole_data["to_par"] == 1
    ).sum()
)

double_bogeys = int(
    (
        hole_data["to_par"] >= 2
    ).sum()
)


metric1, metric2 = st.columns(2)

with metric1:

    st.metric(
        "⛳ Holes Scored",
        total_holes
    )

with metric2:

    st.metric(
        "🏌️ Average Score",
        f"{average_score:.2f}"
    )


metric3, metric4 = st.columns(2)

with metric3:

    sign = "+" if average_to_par > 0 else ""

    st.metric(
        "📈 Average vs Par",
        f"{sign}{average_to_par:.2f}"
    )

with metric4:

    st.metric(
        "🎯 Total Strokes",
        f"{total_strokes:.0f}"
    )


# ============================================================
# SCORE BREAKDOWN
# ============================================================

st.subheader(
    "🎯 Score Breakdown"
)


breakdown = pd.DataFrame(
    {
        "Score": [
            "🦅 Eagle or Better",
            "🐦 Birdie",
            "⛳ Par",
            "😬 Bogey",
            "💀 Double Bogey+"
        ],
        "Count": [
            eagles_or_better,
            birdies,
            pars,
            bogeys,
            double_bogeys
        ]
    }
)


st.dataframe(
    breakdown,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# PERSONAL HOLE RECORD
# ============================================================

st.divider()

st.header(
    "🏆 Hole Records"
)


best_row = hole_data.sort_values(
    [
        "to_par",
        "score"
    ],
    ascending=[
        True,
        True
    ]
).iloc[0]


worst_row = hole_data.sort_values(
    [
        "to_par",
        "score"
    ],
    ascending=[
        False,
        False
    ]
).iloc[0]


record_col1, record_col2 = st.columns(2)


with record_col1:

    st.metric(
        "🔥 Best Hole",
        f"Hole {int(best_row['hole_number'])}"
    )

    best_difference = int(
        best_row["to_par"]
    )

    st.caption(
        f"{int(best_row['score'])} "
        f"on a Par {int(best_row['par'])} "
        f"({best_difference:+d})"
        if best_difference < 0
        else
        f"{int(best_row['score'])} "
        f"on a Par {int(best_row['par'])}"
    )

    st.caption(
        f"⛳ {best_row['course_name']} • "
        f"🏌️ {best_row['event_name']} • "
        f"📅 {best_row['event_date']}"
    )


with record_col2:

    st.metric(
        "💀 Toughest Hole",
        f"Hole {int(worst_row['hole_number'])}"
    )

    worst_difference = int(
        worst_row["to_par"]
    )

    st.caption(
        f"{int(worst_row['score'])} "
        f"on a Par {int(worst_row['par'])} "
        f"({worst_difference:+d})"
    )

    st.caption(
        f"⛳ {worst_row['course_name']} • "
        f"🏌️ {worst_row['event_name']} • "
        f"📅 {worst_row['event_date']}"
    )


# ============================================================
# HOLE-BY-HOLE PERFORMANCE
# ============================================================

st.divider()

st.header(
    "⛳ Hole-by-Hole Performance"
)


hole_summary = (
    hole_data
    .groupby(
        (
            [
                "course_name",
                "hole_number",
                "par",
                "stroke_index"
            ]
            if selected_course_id is None
            else
            [
                "hole_number",
                "par",
                "stroke_index"
            ]
        ),
        as_index=False
    )
    .agg(
        Average_Score=(
            "score",
            "mean"
        ),
        Average_To_Par=(
            "to_par",
            "mean"
        ),
        Rounds=(
            "score",
            "count"
        )
    )
)


hole_summary["Hole"] = (
    hole_summary["hole_number"]
    .astype(int)
)

hole_summary["Par"] = (
    hole_summary["par"]
    .astype(int)
)

hole_summary["Stroke"] = (
    hole_summary["stroke_index"]
    .astype(int)
)


if selected_course_id is None:

    hole_summary["Course"] = (
        hole_summary["course_name"]
        .fillna("Unknown Course")
    )

    hole_summary_display = (
        hole_summary[
            [
                "Course",
                "Hole",
                "Par",
                "Stroke",
                "Average_Score",
                "Average_To_Par",
                "Rounds"
            ]
        ]
        .copy()
    )

else:

    hole_summary_display = (
        hole_summary[
            [
                "Hole",
                "Par",
                "Stroke",
                "Average_Score",
                "Average_To_Par",
                "Rounds"
            ]
        ]
        .copy()
    )


if selected_course_id is None:

    hole_summary_display.columns = [
        "Course",
        "Hole",
        "Par",
        "Stroke",
        "Avg Score",
        "Avg vs Par",
        "Rounds"
    ]

else:

    hole_summary_display.columns = [
        "Hole",
        "Par",
        "Stroke",
        "Avg Score",
        "Avg vs Par",
        "Rounds"
    ]


st.dataframe(
    hole_summary_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Avg Score":
            st.column_config.NumberColumn(
                "Avg Score",
                format="%.2f"
            ),

        "Avg vs Par":
            st.column_config.NumberColumn(
                "Avg vs Par",
                format="%.2f"
            )
    }
)


# ============================================================
# BEST / WORST HOLES
# ============================================================

st.subheader(
    "🔥 Best & Worst Holes"
)


best_holes = hole_summary.sort_values(
    "Average_To_Par",
    ascending=True
).head(5)


worst_holes = hole_summary.sort_values(
    "Average_To_Par",
    ascending=False
).head(5)


if selected_course_id is None:

    best_display = best_holes[
        [
            "course_name",
            "Hole",
            "Par",
            "Average_Score",
            "Average_To_Par"
        ]
    ].copy()

    worst_display = worst_holes[
        [
            "course_name",
            "Hole",
            "Par",
            "Average_Score",
            "Average_To_Par"
        ]
    ].copy()

    best_display.columns = [
        "Course",
        "Hole",
        "Par",
        "Avg Score",
        "Avg vs Par"
    ]

    worst_display.columns = [
        "Course",
        "Hole",
        "Par",
        "Avg Score",
        "Avg vs Par"
    ]

else:

    best_display = best_holes[
        [
            "Hole",
            "Par",
            "Average_Score",
            "Average_To_Par"
        ]
    ].copy()

    worst_display = worst_holes[
        [
            "Hole",
            "Par",
            "Average_Score",
            "Average_To_Par"
        ]
    ].copy()


if selected_course_id is not None:

    best_display.columns = [
        "Hole",
        "Par",
        "Avg Score",
        "Avg vs Par"
    ]

    worst_display.columns = [
        "Hole",
        "Par",
        "Avg Score",
        "Avg vs Par"
    ]


best_col, worst_col = st.columns(2)


with best_col:

    st.markdown(
        "### 🏆 Best Scoring Holes"
    )

    st.dataframe(
        best_display,
        use_container_width=True,
        hide_index=True
    )


with worst_col:

    st.markdown(
        "### 😈 Nightmare Holes"
    )

    st.dataframe(
        worst_display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# GROUP / ALL-GOLFER HOLE PERFORMANCE
# ============================================================

if selected_player_id is None:

    st.divider()

    st.header(
        "🔥 Golfing Warriors Hole Difficulty"
    )

    st.caption(
        "Which holes give the whole group the most trouble?"
    )

    all_holes = get_event_hole_averages(
        season_id=selected_season_id,
        course_id=selected_course_id,
        event_id=selected_event_id,
        score_column=score_column
    )

    if not all_holes.empty:

        all_holes["Hole"] = (
            all_holes["hole_number"]
            .astype(int)
        )

        all_holes["Par"] = (
            all_holes["par"]
            .astype(int)
        )

        all_holes["Stroke"] = (
            all_holes["stroke_index"]
            .astype(int)
        )

        all_holes["Avg Score"] = (
            all_holes["average_score"]
            .astype(float)
        )

        all_holes["Avg vs Par"] = (
            all_holes["average_to_par"]
            .astype(float)
        )

        if selected_course_id is None:

            difficulty = all_holes[
                [
                    "course_name",
                    "Hole",
                    "Par",
                    "Stroke",
                    "Avg Score",
                    "Avg vs Par",
                    "scores_recorded"
                ]
            ].copy()

            difficulty.columns = [
                "Course",
                "Hole",
                "Par",
                "Stroke",
                "Avg Score",
                "Avg vs Par",
                "Scores"
            ]

        else:

            difficulty = all_holes[
                [
                    "Hole",
                    "Par",
                    "Stroke",
                    "Avg Score",
                    "Avg vs Par",
                    "scores_recorded"
                ]
            ].copy()

            difficulty.columns = [
                "Hole",
                "Par",
                "Stroke",
                "Avg Score",
                "Avg vs Par",
                "Scores"
            ]

        st.dataframe(
            difficulty.sort_values(
                "Avg vs Par",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Avg Score":
                    st.column_config.NumberColumn(
                        "Avg Score",
                        format="%.2f"
                    ),

                "Avg vs Par":
                    st.column_config.NumberColumn(
                        "Avg vs Par",
                        format="%.2f"
                    )
            }
        )


# ============================================================
# SCORE TREND
# ============================================================

if selected_player_id is not None:

    st.divider()

    st.header(
        "📈 Score Trend"
    )

    trend = (
        hole_data
        .groupby(
            [
                "event_id",
                "event_name",
                "event_date"
            ],
            as_index=False
        )
        .agg(
            Score=(
                "score",
                "sum"
            ),

            Par=(
                "par",
                "sum"
            )
        )
    )

    trend["Vs Par"] = (
        trend["Score"]
        - trend["Par"]
    )

    trend = trend.sort_values(
        [
            "event_date",
            "event_id"
        ]
    )

    chart = trend[
        [
            "event_name",
            "Vs Par"
        ]
    ].copy()

    chart.columns = [
        "Event",
        "Vs Par"
    ]

    chart = chart.set_index(
        "Event"
    )

    st.bar_chart(
        chart,
        use_container_width=True
    )

    st.caption(
        "Lower is better. Negative means under par."
    )


# ============================================================
# NAVIGATION
# ============================================================

st.divider()

nav1, nav2 = st.columns(2)


with nav1:

    if st.button(
        "👤 Player Profiles",
        use_container_width=True
    ):

        st.switch_page(
            "pages/player_profiles.py"
        )


with nav2:

    if st.button(
        "🏆 Leaderboards",
        use_container_width=True
    ):

        st.switch_page(
            "pages/leaderboards.py"
        )


st.caption(
    "🏌️ Golfing Warriors • "
    "Your friends. Your golf. Your championship."
)
